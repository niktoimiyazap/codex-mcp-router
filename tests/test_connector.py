from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import mcp.types as types

from codexpc_connector.config import Settings
from codexpc_connector.discovery import CodexMCPDiscovery
from codexpc_connector.instance_lock import SingleInstanceLock
from codexpc_connector.logging_utils import close_logging, configure_logging
from codexpc_connector.mcp_manager import _normalize_args
from codexpc_connector.security import PathPolicy, redact
from codexpc_connector.server import _bounded_content, _gateway_tools
from codexpc_connector.tools import LocalTools


class ConnectorTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.settings = Settings(
            state_dir=self.root / "state",
            workspace=self.root,
            allowed_roots=[self.root],
            enable_shell=False,
            enable_process=False,
            enable_delete=True,
            discovery_ttl_sec=1,
            mcp_idle_timeout_sec=1,
            default_startup_timeout_sec=5,
            default_tool_timeout_sec=5,
            max_output_chars=20_000,
            max_read_chars=20_000,
            max_search_file_bytes=1024 * 1024,
            max_background_tasks=2,
            log_level="DEBUG",
        )
        self.logger = configure_logging(self.settings)

    def tearDown(self) -> None:
        close_logging(self.logger)
        self.temp.cleanup()

    async def test_local_tool_surface_hides_secret_readers_and_shell_by_default(self) -> None:
        tools = LocalTools(self.settings, self.logger)
        names = tools.names
        self.assertNotIn("read_agents_rules", names)
        self.assertNotIn("read_codex_config", names)
        self.assertNotIn("run_command", names)
        self.assertNotIn("run_process", names)
        self.assertNotIn("cancel_task", names)
        self.assertIn("patch_file", names)
        self.assertIn("connector_status", names)

    async def test_background_process_can_be_cancelled(self) -> None:
        self.settings.enable_process = True
        tools = LocalTools(self.settings, self.logger)
        try:
            started = await tools.call(
                "run_process",
                {
                    "program": sys.executable,
                    "args": ["-c", "import time; time.sleep(30)"],
                    "background": True,
                    "cwd": str(self.root),
                },
            )
            self.assertIn("Task ID:", started)
            task_id = started.split("Task ID: ", 1)[1].split(".", 1)[0]
            cancelled = await tools.call("cancel_task", {"task_id": task_id})
            self.assertIn("Cancelled task", cancelled)
        finally:
            await tools.shutdown()

    async def test_file_read_patch_and_delete(self) -> None:
        tools = LocalTools(self.settings, self.logger)
        target = self.root / "demo.txt"
        target.write_text("one\ntwo\nthree\n", encoding="utf-8")

        read = await tools.call("read_file", {"filepath": str(target), "include_hash": True})
        self.assertIn("SHA-256:", read)
        hash_value = read.split("SHA-256: ", 1)[1].splitlines()[0]

        dry = await tools.call(
            "patch_file",
            {
                "filepath": str(target),
                "expected_sha256": hash_value,
                "dry_run": True,
                "operations": [
                    {
                        "action": "replace",
                        "start_line": 2,
                        "end_line": 2,
                        "content": "TWO",
                        "expected": "two",
                    }
                ],
            },
        )
        self.assertIn("DRY RUN", dry)
        self.assertEqual(target.read_text(encoding="utf-8"), "one\ntwo\nthree\n")

        applied = await tools.call(
            "patch_file",
            {
                "filepath": str(target),
                "expected_sha256": hash_value,
                "operations": [
                    {
                        "action": "replace",
                        "start_line": 2,
                        "end_line": 2,
                        "content": "TWO",
                        "expected": "two",
                    }
                ],
            },
        )
        self.assertIn("Patched", applied)
        self.assertEqual(target.read_text(encoding="utf-8"), "one\nTWO\nthree\n")

        deleted = await tools.call("delete_file", {"filepath": str(target)})
        self.assertIn("Successfully deleted", deleted)
        self.assertFalse(target.exists())

    async def test_atomic_write_and_delete_hash_guards(self) -> None:
        tools = LocalTools(self.settings, self.logger)
        target = self.root / "atomic.txt"

        created = await tools.call(
            "write_file",
            {"filepath": str(target), "content": "first\n"},
        )
        self.assertIn("Successfully wrote", created)

        refused = await tools.call(
            "write_file",
            {"filepath": str(target), "content": "unsafe\n"},
        )
        self.assertIn("expected_sha256 or overwrite=true", refused)
        self.assertEqual(target.read_text(encoding="utf-8"), "first\n")

        read = await tools.call("read_file", {"filepath": str(target), "include_hash": True})
        first_hash = read.split("SHA-256: ", 1)[1].splitlines()[0]
        updated = await tools.call(
            "write_file",
            {
                "filepath": str(target),
                "content": "second\n",
                "expected_sha256": first_hash,
            },
        )
        self.assertIn("Successfully wrote", updated)
        self.assertEqual(target.read_text(encoding="utf-8"), "second\n")

        stale_delete = await tools.call(
            "delete_file",
            {"filepath": str(target), "expected_sha256": first_hash},
        )
        self.assertIn("File changed since it was read", stale_delete)
        self.assertTrue(target.exists())

        current = await tools.call("read_file", {"filepath": str(target), "include_hash": True})
        current_hash = current.split("SHA-256: ", 1)[1].splitlines()[0]
        deleted = await tools.call(
            "delete_file",
            {"filepath": str(target), "expected_sha256": current_hash},
        )
        self.assertIn("Successfully deleted", deleted)
        self.assertFalse(target.exists())

    async def test_path_escape_is_blocked(self) -> None:
        tools = LocalTools(self.settings, self.logger)
        outside = self.root.parent / "outside-codexpc-test.txt"
        result = await tools.call("read_file", {"filepath": str(outside)})
        self.assertIn("PermissionError", result)

    async def test_connector_status_contains_no_secrets(self) -> None:
        tools = LocalTools(self.settings, self.logger)
        status = json.loads(await tools.call("connector_status", {}))
        self.assertEqual(status["status"], "ok")
        self.assertFalse(status["shell_enabled"])
        self.assertFalse(status["process_enabled"])


class PureUnitTests(unittest.TestCase):
    def test_redaction(self) -> None:
        fake_token = "github_" + "pat_" + ("a" * 30)
        value = {
            "GITHUB_PERSONAL_ACCESS_TOKEN": fake_token,
            "normal": "Bearer " + ("b" * 26),
        }
        redacted = redact(value)
        self.assertEqual(redacted["GITHUB_PERSONAL_ACCESS_TOKEN"], "***")
        self.assertNotIn("b" * 20, redacted["normal"])

    def test_path_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            settings = Settings(state_dir=root / "state", workspace=root, allowed_roots=[root])
            policy = PathPolicy(settings)
            self.assertEqual(policy.resolve("file.txt"), root / "file.txt")
            with self.assertRaises(PermissionError):
                policy.resolve(root.parent / "escape.txt")

    def test_npx_argument_normalization(self) -> None:
        self.assertEqual(
            _normalize_args("npx.cmd", ("-y @modelcontextprotocol/server-github",)),
            ["-y", "@modelcontextprotocol/server-github"],
        )

    def test_discovery_public_summary_does_not_expose_env_values(self) -> None:
        item = {
            "name": "example",
            "enabled": True,
            "transport": {
                "type": "stdio",
                "command": "node",
                "args": ["server.js"],
                "env": {"SECRET_TOKEN": "do-not-leak"},
            },
        }
        parsed = CodexMCPDiscovery._parse(item)
        summary = parsed.public_summary()
        self.assertNotIn("do-not-leak", json.dumps(summary))
        self.assertEqual(summary["env_keys"], ["SECRET_TOKEN"])

    def test_gateway_schemas_are_static_and_generic(self) -> None:
        names = [tool.name for tool in _gateway_tools()]
        self.assertEqual(
            names,
            ["mcp_list_servers", "mcp_list_tools", "mcp_search_tools", "mcp_call", "mcp_gateway"],
        )
        list_tool = next(tool for tool in _gateway_tools() if tool.name == "mcp_list_servers")
        self.assertTrue(list_tool.annotations.readOnlyHint)
        search_tool = next(tool for tool in _gateway_tools() if tool.name == "mcp_search_tools")
        self.assertEqual(set(search_tool.inputSchema["required"]), {"query", "server_name"})

    def test_remote_text_output_is_bounded(self) -> None:
        content = [
            types.TextContent(type="text", text="a" * 10),
            types.TextContent(type="text", text="b" * 10),
        ]
        bounded = _bounded_content(content, 12)
        combined = "".join(item.text for item in bounded if item.type == "text")
        self.assertTrue(combined.startswith(("a" * 10) + "bb"))
        self.assertIn("output truncated", combined)

    def test_single_instance_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "connector.lock"
            first = SingleInstanceLock(path)
            second = SingleInstanceLock(path)
            first.acquire()
            try:
                with self.assertRaises(RuntimeError):
                    second.acquire()
            finally:
                first.release()


if __name__ == "__main__":
    unittest.main()
