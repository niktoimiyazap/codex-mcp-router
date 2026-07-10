# CodexPC Connector

A local MCP stdio server that gives an MCP client safe file/process tools and dynamically routes every MCP server already configured in Codex.

## What it does

- Discovers MCP servers through `codex mcp list --json`; no server names or credentials are hardcoded.
- Supports Codex `stdio` and `streamable_http` MCP transports.
- Starts downstream MCP servers only on first use and stops them after an idle timeout.
- Keeps every downstream MCP lifecycle inside its own async worker to avoid AnyIO cross-task shutdown errors.
- Exposes bounded file reading, atomic line patches with unified diff, safe deletion, search, direct process execution, optional shell execution, and background task checks.
- Restricts file access to configured roots and blocks protected system writes unless explicitly confirmed.
- Redacts secrets from logs and never returns MCP environment values.
- Stores configuration and rotating logs outside the repository.

## Requirements

- Python 3.11+
- Codex CLI available as `codex`
- MCP servers configured in Codex

## Install

```bash
python -m pip install -e .
```

Run as an MCP stdio server:

```bash
codexpc-connector
```

Windows without installation:

```bat
wrapper.cmd
```

## Configuration

The connector creates/reads a local `config.toml` from:

- Windows: `%LOCALAPPDATA%\CodexPCConnector\config.toml`
- macOS: `~/Library/Application Support/CodexPCConnector/config.toml`
- Linux: `$XDG_STATE_HOME/codexpc-connector/config.toml`

Copy values from [`config.example.toml`](config.example.toml). Public defaults disable both arbitrary process and shell execution.

Environment overrides:

- `CODEXPC_WORKSPACE`
- `CODEXPC_ALLOWED_ROOTS` (separated by the operating-system path separator)
- `CODEXPC_ENABLE_SHELL`
- `CODEXPC_ENABLE_PROCESS`
- `CODEXPC_ENABLE_DELETE`

## Local tools

- `connector_status`
- `set_working_directory`
- `read_file`
- `write_file`
- `patch_file`
- `delete_file`
- `list_dir`
- `search_files`
- `run_process` (only when process execution is enabled)
- `run_command` (only when both process and shell execution are enabled)
- `check_task`
- `cancel_task`

`patch_file` supports `replace`, `delete`, `insert_before`, and `insert_after`. It can validate an expected SHA-256 and expected original text, preview a unified diff, and then write atomically.

`write_file` creates files atomically. Replacing an existing file requires its current SHA-256 or an explicit `overwrite=true`. `delete_file` can also enforce the expected SHA-256.

## Dynamic Codex MCP tools

- `mcp_list_servers`
- `mcp_list_tools`
- `mcp_search_tools`
- `mcp_call`
- `mcp_gateway` (backward-compatible alias)

The server list is refreshed from Codex, so adding or removing an MCP in Codex does not require editing this project.

## Security model

This is a local privileged connector. Only attach it to clients and tunnels you trust.

- Public defaults expose neither arbitrary process nor shell execution.
- File operations are limited to `allowed_roots` after resolving symlinks/junctions.
- Windows system directories and Unix system roots are protected from writes.
- `codex mcp list --json` may contain credentials; the connector parses them in memory, passes them only to the matching child process, and logs only environment variable names.
- Global instruction/credential files are not exposed as tools.
- Logs contain tool names, timing, counts, and error typesвЂ”not tool arguments or raw outputs.

See [`SECURITY.md`](SECURITY.md) before exposing the connector through any network tunnel.

## Verification

```bash
python -m compileall -q codexpc_connector main.py
python -m ruff check codexpc_connector scripts tests main.py
python -m bandit -q -r codexpc_connector
python -m unittest discover -s tests -v
python scripts/self_check.py
python -m pip_audit -r audit-requirements.txt --progress-spinner off
```

## ChatGPT plan note

The connector itself is standard MCP and works with compatible MCP hosts. Direct custom full-MCP apps in ChatGPT are plan-dependent; this repository does not enable unsupported ChatGPT account features and does not open a public HTTP listener by default.

## License

MIT
