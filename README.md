# CodexPC Connector

An MCP stdio adapter that combines Codex app-server filesystem/MCP routing with a managed local process runner.

## Support This Project

If CodexPC Connector is useful to you, you can support its development:

[![YooMoney](https://img.shields.io/badge/YooMoney-Support-8B3FFD?style=for-the-badge&logo=yoomoney&logoColor=white)](https://yoomoney.ru/to/4100119516342099/100)
[![USDT](https://img.shields.io/badge/USDT-TRC20-26A17B?style=for-the-badge)](#support-this-project)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-30363D?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/niktoimiyazap)

- YooMoney: [support with 100 RUB or choose another amount](https://yoomoney.ru/to/4100119516342099/100)
- USDT (TRC20): `0xda2EB9c240816d5e555eA17Aa94E26C83a13C210`
- GitHub Sponsors: [niktoimiyazap](https://github.com/sponsors/niktoimiyazap)

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Release process](docs/RELEASING.md)

## Architecture

```text
MCP client
   |
   v
CodexPC Connector
   |-- guarded text writes and managed process jobs
   |-- JSON-RPC/JSONL client
          |
          v
     codex app-server
       |-- fs/*
       |-- mcpServerStatus/list
       `-- mcpServer/tool/call
```

The connector starts one long-lived `codex app-server --stdio` process, performs the initialize handshake, and creates one ephemeral Codex thread for MCP inventory and calls.

The Codex thread permission settings remain unchanged:

```text
sandbox = danger-full-access
approvalPolicy = never
```

## Requirements

- Python 3.11+
- Codex CLI with `codex app-server` support
- Codex authentication and MCP servers configured normally in Codex

## Install and run

```bash
python -m pip install -e .
codexpc-connector
```

Windows without installation:

```bat
wrapper.cmd
```

## Filesystem tools

- `read_file` reads text with BOM detection and explicit Unicode decoding.
- `write_file` writes UTF-8 without BOM by default.
- Writes are atomic by default and may use `expected_sha256` to prevent overwriting a file changed by another process.
- `list_dir`, `create_directory`, `copy_path`, and `delete_path` use Codex app-server filesystem RPCs.
- All mutations pass through the allowed-root and protected-write policy.

Useful `write_file` options:

```text
encoding: utf-8 | utf-8-sig | utf-16-le | cp1251 | system
newline: preserve | lf | crlf
overwrite: true | false
create_parents: true | false
atomic: true | false
expected_sha256: optional current file hash
```

Use `write_file` instead of shell redirection for text files. This avoids Windows PowerShell and console code-page ambiguity.

## Process tools

`run_process` and `run_command` are synchronous by default:

```text
run_process(program="git", args=["status"])
-> completed result with exitCode/stdout/stderr
```

For long-running work, set `background=true`:

```text
run_process(..., background=true)
-> job_id
```

Managed job tools:

- `get_job` reads one job without waiting.
- `wait` waits up to 30 seconds per call and retains compatibility with older clients.
- `list_jobs` lists running and recently completed jobs.
- `cancel_job` terminates the operating-system process tree.

Jobs have explicit states:

```text
queued, running, completed, failed, timed_out, cancelled, killed
```

Every process has a timeout. Output is bounded and decoded using UTF-8 first with Windows-compatible fallbacks. Child stdin is isolated from MCP stdio, and child Python processes default to UTF-8 I/O. On Windows, `run_command` supports `auto`, `pwsh`, `powershell`, and `cmd` shells.

## MCP routing

- `mcp_list_servers` and `mcp_list_tools` use `mcpServerStatus/list`.
- `mcp_search_tools` searches the inventory returned by Codex.
- `mcp_call` uses `mcpServer/tool/call`.

## Configuration

Configuration is loaded from:

- Windows: `%LOCALAPPDATA%\CodexPCConnector\config.toml`
- macOS: `~/Library/Application Support/CodexPCConnector/config.toml`
- Linux: `$XDG_STATE_HOME/codexpc-connector/config.toml`

See `config.example.toml`.

Process execution requires `enable_process=true`; shell strings additionally require `enable_shell=true`. These permission switches were not changed in version 0.3.0.

## Verification

```bash
python -m ruff check codexpc_connector scripts tests main.py
python -m unittest discover -s tests -v
python scripts/smoke_processes.py
python scripts/smoke_stdio.py
python scripts/self_check.py
python -m bandit -q -r codexpc_connector
```

Optional coverage:

```bash
python -m pytest --cov=codexpc_connector --cov-branch
```

## Security

This is privileged local software intended for a single trusted user over stdio. Do not expose it directly to a public network. See `SECURITY.md`.

## License

MIT
