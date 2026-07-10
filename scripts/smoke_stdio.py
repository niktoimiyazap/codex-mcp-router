from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        env = os.environ.copy()
        if os.name == "nt":
            env["LOCALAPPDATA"] = temp
        else:
            env["XDG_STATE_HOME"] = temp
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "codexpc_connector"],
            cwd=str(ROOT),
            env=env,
        )
        async with stdio_client(params) as (read_stream, write_stream):  # noqa: SIM117
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                listed = await session.list_tools()
                names = {tool.name for tool in listed.tools}
                required = {"connector_status", "read_file", "patch_file", "mcp_list_servers", "mcp_call"}
                missing = required - names
                if missing:
                    raise RuntimeError(f"Missing tools: {sorted(missing)}")

                status = await session.call_tool("connector_status", {})
                if not status.content or status.content[0].type != "text":
                    raise RuntimeError("connector_status returned no text")
                payload = json.loads(status.content[0].text)
                if payload.get("status") != "ok":
                    raise RuntimeError(f"Unexpected connector status: {payload}")

                servers = await session.call_tool("mcp_list_servers", {"refresh": True})
                if not servers.content or servers.content[0].type != "text":
                    raise RuntimeError("mcp_list_servers returned no text")
                server_payload = json.loads(servers.content[0].text)
                if not isinstance(server_payload, list):
                    raise RuntimeError("mcp_list_servers returned non-list JSON")
                serialized = json.dumps(server_payload)
                if "github_pat_" in serialized or "TELEGRAM_API_HASH\":" in serialized:
                    raise RuntimeError("Discovery response appears to contain a secret")
                print(f"stdio smoke passed: {len(names)} tools, {len(server_payload)} Codex MCP servers")


if __name__ == "__main__":
    asyncio.run(run())
