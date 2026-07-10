# Security Policy

## Threat model

CodexPC Connector can read and modify files, start processes, and proxy tools from MCP servers already trusted by Codex. Treat it as privileged local software.

The connector is designed for a single local user over MCP stdio. It does not expose an unauthenticated TCP/HTTP listener.

## Safe defaults

- Arbitrary process execution is disabled unless `enable_process=true`; shell commands additionally require `enable_shell=true`.
- Paths are resolved before authorization and must remain inside `allowed_roots`.
- Writes to protected operating-system paths require explicit confirmation and normally remain outside allowed roots.
- Directory deletion is not supported.
- Downstream MCP credentials are never returned by discovery tools.
- Logs omit arguments and outputs and redact common credential patterns.
- Global credential/instruction files are not exposed as tools.
- Downstream MCP servers are discovered from Codex, started lazily, and closed after inactivity.

## Network exposure

Do not expose stdio through a public tunnel without authentication, authorization, encryption, request limits, and user-presence confirmation for destructive actions. A tunnel is outside this repository's trust boundary.

## Reporting a vulnerability

Open a private security advisory in the GitHub repository. Do not include live credentials, private files, or exploit output containing personal data in a public issue.

## Supported versions

Security fixes are provided for the latest released minor version.
