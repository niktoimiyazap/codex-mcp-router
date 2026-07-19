# CodexPC Connector

> A local MCP stdio adapter for Codex app-server, guarded filesystem access, managed process execution, and downstream MCP routing.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/Protocol-MCP-111827)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/niktoimiyazap/codex-mcp-router/test.yml?branch=main&label=tests)](https://github.com/niktoimiyazap/codex-mcp-router/actions)

## Support the project

Development is community-supported. Choose any convenient option:

[![YooMoney](https://img.shields.io/badge/YooMoney-Support-8B3FFD?style=for-the-badge&logo=yoomoney&logoColor=white)](https://yoomoney.ru/to/4100119516342099/100)
[![USDT](https://img.shields.io/badge/USDT-TRC20-26A17B?style=for-the-badge)](#usdt-trc20)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-30363D?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/niktoimiyazap)

### USDT TRC20

```text
Network: TRON (TRC20)
Token:   USDT
Address: TXeHE4iYgdf2whpTCWeErerKGAng3sRXK1
```

> Send only USDT through the TRON network. Transfers through another network may be lost.

## What it does

CodexPC Connector exposes a controlled local tool layer to MCP clients:

- guarded filesystem reads and mutations;
- atomic UTF-8 writes with conflict protection;
- synchronous and background process execution;
- timeouts, cancellation, bounded output, and process-tree termination;
- downstream MCP inventory, search, and calls through Codex app-server;
- secret-redacted structured logs and single-instance protection.

## Architecture

```text
MCP client
    |
    v
CodexPC Connector
    |-- filesystem policy and UTF-8 validation
    |-- managed local process jobs
    `-- JSON-RPC / JSONL client
             |
             v
       codex app-server
         |-- fs/*
         |-- mcpServerStatus/list
         `-- mcpServer/tool/call
```

The connector starts one long-lived `codex app-server --stdio` process and creates one ephemeral Codex thread for MCP discovery and calls.

## Requirements

- Python 3.11 or newer;
- Codex CLI with `codex app-server` support;
- an authenticated Codex installation;
- MCP servers configured through Codex when downstream routing is needed.

## Quick start

```bash
git clone https://github.com/niktoimiyazap/codex-mcp-router.git
cd codex-mcp-router
python -m pip install -e .
codexpc-connector
```

Windows without package installation:

```bat
wrapper.cmd
```

## Configuration

Copy `config.example.toml` to the platform state directory:

| Platform | Configuration path |
|---|---|
| Windows | `%LOCALAPPDATA%\CodexPCConnector\config.toml` |
| macOS | `~/Library/Application Support/CodexPCConnector/config.toml` |
| Linux | `$XDG_STATE_HOME/codexpc-connector/config.toml` |

Minimal example:

```toml
workspace = "~/projects"
allowed_roots = ["~/projects"]

enable_process = false
enable_shell = false
enable_delete = true
```

Process execution requires `enable_process=true`. Shell command strings additionally require `enable_shell=true`.

See [Configuration](docs/CONFIGURATION.md) for all options.

## Tool groups

### Filesystem

`read_file`, `write_file`, `list_dir`, `create_directory`, `copy_path`, `delete_path`, `download_url`, `save_uploaded_file`

Text writes are UTF-8 by default, atomic, and reject likely mojibake or legacy-encoding corruption.

### Processes

`run_process`, `run_command`, `get_job`, `wait`, `list_jobs`, `cancel_job`

Background jobs expose explicit states:

```text
queued, running, completed, failed, timed_out, cancelled, killed
```

### MCP routing

`mcp_list_servers`, `mcp_list_tools`, `mcp_search_tools`, `mcp_call`

### Connector control

`connector_status`, `list_active_tool_calls`, `cancel_tool_calls`

## Verification

```bash
python -m ruff check codexpc_connector scripts tests main.py
python -m unittest discover -s tests -v
python scripts/self_check.py
python -m bandit -q -r codexpc_connector
```

Integration smoke tests:

```bash
python scripts/smoke_processes.py
python scripts/smoke_stdio.py
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Release process](docs/RELEASING.md)
- [Changelog](CHANGELOG.md)

## Security

This is privileged local software intended for a single trusted user over MCP stdio. Do not expose it directly to a public network. Review [SECURITY.md](SECURITY.md) before enabling process or shell execution.

## License

MIT
