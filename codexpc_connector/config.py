from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _default_state_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "CodexPCConnector"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CodexPCConnector"
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "codexpc-connector"


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_paths(value: Any, fallback: list[Path]) -> list[Path]:
    if value is None:
        return fallback
    if isinstance(value, str):
        items = [part for part in value.split(os.pathsep) if part]
    elif isinstance(value, list):
        items = [str(part) for part in value]
    else:
        return fallback
    paths = [Path(os.path.expandvars(os.path.expanduser(item))).resolve() for item in items]
    return paths or fallback


@dataclass(slots=True)
class Settings:
    state_dir: Path
    workspace: Path
    allowed_roots: list[Path] = field(default_factory=list)
    enable_shell: bool = False
    enable_process: bool = False
    enable_delete: bool = True
    discovery_ttl_sec: float = 600.0
    mcp_idle_timeout_sec: float = 900.0
    default_startup_timeout_sec: float = 30.0
    default_tool_timeout_sec: float = 120.0
    max_output_chars: int = 100_000
    max_read_chars: int = 500_000
    max_search_file_bytes: int = 5 * 1024 * 1024
    max_edit_file_bytes: int = 20 * 1024 * 1024
    max_background_tasks: int = 32
    log_level: str = "INFO"

    @property
    def config_path(self) -> Path:
        return self.state_dir / "config.toml"

    @property
    def log_dir(self) -> Path:
        return self.state_dir / "logs"

    @classmethod
    def load(cls) -> Settings:
        state_dir = _default_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        config_path = state_dir / "config.toml"
        raw: dict[str, Any] = {}
        if config_path.is_file():
            with config_path.open("rb") as handle:
                raw = tomllib.load(handle)

        home = Path.home().resolve()
        workspace = Path(
            os.path.expandvars(
                os.path.expanduser(
                    os.environ.get("CODEXPC_WORKSPACE", str(raw.get("workspace", home)))
                )
            )
        ).resolve()
        allowed_roots = _as_paths(
            os.environ.get("CODEXPC_ALLOWED_ROOTS", raw.get("allowed_roots")),
            [home],
        )

        return cls(
            state_dir=state_dir,
            workspace=workspace,
            allowed_roots=allowed_roots,
            enable_shell=_as_bool(
                os.environ.get("CODEXPC_ENABLE_SHELL", raw.get("enable_shell")), False
            ),
            enable_process=_as_bool(
                os.environ.get("CODEXPC_ENABLE_PROCESS", raw.get("enable_process")), False
            ),
            enable_delete=_as_bool(
                os.environ.get("CODEXPC_ENABLE_DELETE", raw.get("enable_delete")), True
            ),
            discovery_ttl_sec=float(raw.get("discovery_ttl_sec", 600.0)),
            mcp_idle_timeout_sec=float(raw.get("mcp_idle_timeout_sec", 900.0)),
            default_startup_timeout_sec=float(raw.get("default_startup_timeout_sec", 30.0)),
            default_tool_timeout_sec=float(raw.get("default_tool_timeout_sec", 120.0)),
            max_output_chars=int(raw.get("max_output_chars", 100_000)),
            max_read_chars=int(raw.get("max_read_chars", 500_000)),
            max_search_file_bytes=int(raw.get("max_search_file_bytes", 5 * 1024 * 1024)),
            max_edit_file_bytes=int(raw.get("max_edit_file_bytes", 20 * 1024 * 1024)),
            max_background_tasks=int(raw.get("max_background_tasks", 32)),
            log_level=str(raw.get("log_level", "INFO")).upper(),
        )
