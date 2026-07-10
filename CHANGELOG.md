# Changelog

## 0.1.0 - 2026-07-10

### Added

- Dynamic MCP discovery from `codex mcp list --json`.
- Lazy stdio and Streamable HTTP MCP workers with idle shutdown.
- Paginated MCP tool listing, search, generic calls, and legacy gateway compatibility.
- File context reading with hashes and atomic line-based diff patches.
- Atomic guarded writes, SHA-256 checked deletion, bounded downstream output, and background task cancellation.
- Allowed-root path policy and protected system write checks.
- Secret-redacted rotating JSONL logs outside the repository.
- Single-instance process lock.
- Cross-platform packaging, unit tests, self-check, and CI.

### Changed

- Removed hardcoded GitHub, Telegram, and Google Drive MCP configuration.
- Removed tools that exposed global instruction or credential files.
- Arbitrary process and shell execution are disabled by default in public configuration.
