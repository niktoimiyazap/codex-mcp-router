from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import mcp.types as types

from . import local_tools as legacy
from .config import Settings
from .logging_utils import log_event
from .security import PathPolicy, redact


class LocalTools:
    """Security and lifecycle wrapper around the proven local tool implementation."""

    _HIDDEN = {"read_codex_config", "read_agents_rules", "wait_seconds"}
    _MUTATING_FILES = {"write_file", "patch_file", "delete_file"}
    _READ_ONLY = {"read_file", "list_dir", "search_files", "check_task", "connector_status"}

    def __init__(self, settings: Settings, logger):
        self.settings = settings
        self.logger = logger
        self.policy = PathPolicy(settings)
        self.started_at = time.monotonic()
        legacy.CURRENT_WORKING_DIR = str(settings.workspace)

        def secure_resolve(raw_path: str) -> str:
            raw = raw_path or legacy.CURRENT_WORKING_DIR
            return str(self.policy.resolve(raw, base=Path(legacy.CURRENT_WORKING_DIR)))

        legacy.resolve_path = secure_resolve
        self._tools = self._build_tools()
        self._names = {tool.name for tool in self._tools}

    @property
    def names(self) -> set[str]:
        return set(self._names)

    def _build_tools(self) -> list[types.Tool]:
        tools: list[types.Tool] = []
        for tool in legacy.get_local_tools():
            if tool.name in self._HIDDEN:
                continue
            if tool.name in {"run_process", "cancel_task"} and not self.settings.enable_process:
                continue
            if tool.name == "run_command" and not (
                self.settings.enable_process and self.settings.enable_shell
            ):
                continue
            annotations = types.ToolAnnotations(
                readOnlyHint=tool.name in self._READ_ONLY,
                destructiveHint=(
                    tool.name in self._MUTATING_FILES
                    or tool.name in {"run_process", "run_command", "cancel_task"}
                ),
                idempotentHint=tool.name in self._READ_ONLY,
                openWorldHint=tool.name in {"run_process", "run_command"},
            )
            tools.append(tool.model_copy(update={"annotations": annotations}))

        tools.insert(
            0,
            types.Tool(
                name="connector_status",
                description="Returns connector health and safe local configuration metadata.",
                inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
                annotations=types.ToolAnnotations(
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            ),
        )
        return tools

    def list_tools(self) -> list[types.Tool]:
        return list(self._tools)

    async def call(self, name: str, arguments: dict[str, Any]) -> str:
        started = time.perf_counter()
        try:
            if name == "connector_status":
                running = sum(1 for task in legacy.BACKGROUND_TASKS.values() if not task.get("done"))
                return json.dumps(
                    {
                        "status": "ok",
                        "uptime_sec": round(time.monotonic() - self.started_at, 1),
                        "workspace": legacy.CURRENT_WORKING_DIR,
                        "allowed_roots": [str(root) for root in self.settings.allowed_roots],
                        "shell_enabled": self.settings.enable_shell,
                        "process_enabled": self.settings.enable_process,
                        "delete_enabled": self.settings.enable_delete,
                        "max_edit_file_bytes": self.settings.max_edit_file_bytes,
                        "background_tasks": {
                            "running": running,
                            "total": len(legacy.BACKGROUND_TASKS),
                        },
                        "state_dir": str(self.settings.state_dir),
                    },
                    ensure_ascii=False,
                    indent=2,
                )

            if name not in self._names:
                raise KeyError(f"Unknown or disabled local tool: {name}")
            if name == "run_process" and not self.settings.enable_process:
                raise PermissionError("Process execution is disabled")
            if name == "run_command" and not (
                self.settings.enable_process and self.settings.enable_shell
            ):
                raise PermissionError("Shell execution is disabled")
            if name == "delete_file" and not self.settings.enable_delete:
                raise PermissionError("File deletion is disabled")

            if name in self._MUTATING_FILES or name == "read_file":
                raw_path = arguments.get("filepath", "")
                path = self.policy.resolve(raw_path, base=Path(legacy.CURRENT_WORKING_DIR))
                if name in self._MUTATING_FILES:
                    self.policy.ensure_writable(path, confirm_sensitive=bool(arguments.get("confirm", False)))
                if path.is_file() and path.stat().st_size > self.settings.max_edit_file_bytes:
                    raise ValueError(
                        f"File exceeds max_edit_file_bytes ({self.settings.max_edit_file_bytes}): {path}"
                    )
                if name == "write_file":
                    content_size = len(str(arguments.get("content", "")).encode("utf-8"))
                    if content_size > self.settings.max_edit_file_bytes:
                        raise ValueError("Write content exceeds max_edit_file_bytes")
            result = await legacy.call_local_tool(name, arguments)
            log_event(
                self.logger,
                20,
                "local_tool_call",
                tool=name,
                ok=not str(result).startswith("Error:"),
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
                output_chars=min(len(str(result)), 1_000_000),
            )
            return str(result)
        except Exception as exc:
            log_event(
                self.logger,
                40,
                "local_tool_call",
                tool=name,
                ok=False,
                error_type=type(exc).__name__,
                duration_ms=round((time.perf_counter() - started) * 1000, 1),
            )
            return f"Error: {type(exc).__name__}: {redact(str(exc))}"

    async def shutdown(self) -> None:
        tasks = []
        for item in legacy.BACKGROUND_TASKS.values():
            process = item.get("process")
            if process and process.returncode is None:
                process.terminate()
                tasks.append(process.wait())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
