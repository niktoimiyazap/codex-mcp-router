from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from .config import Settings
from .discovery import CodexMCPDiscovery
from .instance_lock import SingleInstanceLock
from .logging_utils import close_logging, configure_logging, log_event
from .mcp_manager import MCPManager
from .security import redact
from .tools import LocalTools


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _bounded_content(content: list[Any], max_chars: int) -> list[Any]:
    remaining = max_chars
    output: list[Any] = []
    truncated = False
    for item in content:
        if getattr(item, "type", None) != "text":
            output.append(item)
            continue
        text = str(item.text)
        if remaining <= 0:
            truncated = True
            continue
        if len(text) > remaining:
            output.append(
                item.model_copy(update={"text": text[:remaining] + "\n... output truncated ...\n"})
            )
            remaining = 0
            truncated = True
        else:
            output.append(item)
            remaining -= len(text)
    if truncated and not any(
        getattr(item, "type", None) == "text" and "output truncated" in str(item.text)
        for item in output
    ):
        output.append(types.TextContent(type="text", text="... output truncated ..."))
    return output


def _gateway_tools() -> list[types.Tool]:
    read_annotations = types.ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )
    return [
        types.Tool(
            name="mcp_list_servers",
            description="Lists MCP servers dynamically discovered from Codex. Secret values are never returned.",
            inputSchema={
                "type": "object",
                "properties": {
                    "refresh": {
                        "type": "boolean",
                        "description": "Force Codex MCP rediscovery instead of using the short cache",
                    }
                },
                "additionalProperties": False,
            },
            annotations=read_annotations,
        ),
        types.Tool(
            name="mcp_list_tools",
            description="Starts one Codex MCP lazily and returns a paginated list of its tools and schemas.",
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {"type": "string"},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                },
                "required": ["server_name"],
                "additionalProperties": False,
            },
            annotations=read_annotations,
        ),
        types.Tool(
            name="mcp_search_tools",
            description=(
                "Searches names and descriptions of tools on one dynamically discovered "
                "Codex MCP server without starting unrelated MCPs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "server_name": {"type": "string"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                },
                "required": ["query", "server_name"],
                "additionalProperties": False,
            },
            annotations=read_annotations,
        ),
        types.Tool(
            name="mcp_call",
            description=(
                "Calls a tool on any enabled MCP server discovered from Codex. "
                "The MCP process starts lazily and shuts down after being idle."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "server_name": {"type": "string"},
                    "tool_name": {"type": "string"},
                    "arguments": {"type": "object", "additionalProperties": True},
                },
                "required": ["server_name", "tool_name"],
                "additionalProperties": False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=True,
            ),
        ),
        types.Tool(
            name="mcp_gateway",
            description=(
                "Backward-compatible alias. Use action=list to list one server's tools "
                "or action=call to execute a tool."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "call"]},
                    "server_name": {"type": "string"},
                    "sub_tool": {"type": "string"},
                    "sub_args": {"type": "object", "additionalProperties": True},
                    "offset": {"type": "integer", "minimum": 0, "default": 0},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25},
                },
                "required": ["action", "server_name"],
                "additionalProperties": False,
            },
            annotations=types.ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=True,
            ),
        ),
    ]


async def run_server(*, acquire_lock: bool = True) -> None:
    settings = Settings.load()
    logger = configure_logging(settings)
    lock = SingleInstanceLock(settings.state_dir / "connector.lock")
    if acquire_lock:
        lock.acquire()

    local_tools = LocalTools(settings, logger)
    discovery = CodexMCPDiscovery(settings, logger)
    manager = MCPManager(discovery, settings, logger)
    server = Server("CodexPCConnector")
    gateway_tools = _gateway_tools()

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return local_tools.list_tools() + gateway_tools

    async def list_remote_tools(server_name: str, offset: int, limit: int) -> str:
        tools = await manager.list_tools(server_name)
        offset = max(0, offset)
        limit = max(1, min(limit, 100))
        selected = tools[offset : offset + limit]
        return _json(
            {
                "server": server_name,
                "total": len(tools),
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(selected) if offset + len(selected) < len(tools) else None,
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                        "annotations": tool.annotations.model_dump(exclude_none=True) if tool.annotations else None,
                    }
                    for tool in selected
                ],
            }
        )

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any] | None):
        args = arguments or {}
        try:
            if name in local_tools.names:
                result = await local_tools.call(name, args)
                return [types.TextContent(type="text", text=result)]

            if name == "mcp_list_servers":
                result = await manager.list_servers(refresh=bool(args.get("refresh", False)))
                return [types.TextContent(type="text", text=_json(result))]

            if name == "mcp_list_tools":
                text = await list_remote_tools(
                    str(args["server_name"]),
                    int(args.get("offset", 0)),
                    int(args.get("limit", 25)),
                )
                return [types.TextContent(type="text", text=text)]

            if name == "mcp_search_tools":
                result = await manager.search_tools(
                    str(args["query"]),
                    server_name=str(args["server_name"]),
                    max_results=int(args.get("max_results", 20)),
                )
                return [types.TextContent(type="text", text=_json(result))]

            if name == "mcp_call":
                result = await manager.call_tool(
                    str(args["server_name"]),
                    str(args["tool_name"]),
                    dict(args.get("arguments") or {}),
                )
                return _bounded_content(result.content, settings.max_output_chars)

            if name == "mcp_gateway":
                action = str(args.get("action", ""))
                if action == "list":
                    text = await list_remote_tools(
                        str(args["server_name"]),
                        int(args.get("offset", 0)),
                        int(args.get("limit", 25)),
                    )
                    return [types.TextContent(type="text", text=text)]
                if action == "call":
                    sub_tool = args.get("sub_tool")
                    if not sub_tool:
                        raise ValueError("sub_tool is required for action=call")
                    result = await manager.call_tool(
                        str(args["server_name"]),
                        str(sub_tool),
                        dict(args.get("sub_args") or {}),
                    )
                    return _bounded_content(result.content, settings.max_output_chars)
                raise ValueError("action must be list or call")

            raise KeyError(f"Unknown tool: {name}")
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "tool_error",
                tool=name,
                error_type=type(exc).__name__,
            )
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: {type(exc).__name__}: {redact(str(exc))}",
                )
            ]

    log_event(
        logger,
        logging.INFO,
        "connector_start",
        local_tool_count=len(local_tools.list_tools()),
        workspace=str(settings.workspace),
        shell_enabled=settings.enable_shell,
        process_enabled=settings.enable_process,
    )
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )
    finally:
        await manager.shutdown()
        await local_tools.shutdown()
        log_event(logger, logging.INFO, "connector_stop")
        if acquire_lock:
            lock.release()
        close_logging(logger)


def main() -> None:
    asyncio.run(run_server())
