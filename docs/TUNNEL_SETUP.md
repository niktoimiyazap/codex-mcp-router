# Interactive tunnel setup

This launcher connects the local CodexPC Connector to an existing OpenAI tunnel without storing the runtime API key in the repository or in a generated profile.

## Before running

You need:

1. Python 3.11 or newer.
2. CodexPC Connector installed from this repository.
3. `tunnel-client` installed and available in `PATH`.
4. A tunnel ID from OpenAI Platform **Organization → Tunnels**.
5. A runtime API key whose principal has **Tunnels Read + Use**.

The tunnel ID and runtime API key are different values. An admin key is not required to run an existing tunnel.

## Windows

From PowerShell or Command Prompt in the repository directory:

```bat
launch-tunnel.cmd
```

## macOS

From Terminal in the repository directory:

```bash
chmod +x launch-tunnel.sh
./launch-tunnel.sh
```

## Questions asked by the launcher

- **Organization name** — an optional local label; it is not transmitted as authentication.
- **Local profile name** — defaults to `codexpc`.
- **Tunnel ID** — must have the form `tunnel_` plus 32 lowercase hexadecimal characters.
- **Runtime API key** — entered invisibly and used only by the running process.

The launcher creates or updates a local `tunnel-client` profile, runs `doctor --explain`, and starts the tunnel. It binds the tunnel to:

```text
python -m codexpc_connector
```

Keep the terminal open while ChatGPT uses the connector. Press `Ctrl+C` to stop it.

## Security notes

- The runtime key is never written by this launcher.
- Do not commit profiles containing literal keys.
- Prefer `env:CONTROL_PLANE_API_KEY` references in manually written profiles.
- Revoke and replace a key immediately if it appears in a script, shell history, screenshot, log, or public repository.
- Do not use an OpenAI admin key for the long-lived tunnel process.

## Troubleshooting

**`tunnel-client was not found in PATH`**  
Install the supported binary from OpenAI Platform Tunnels management, then reopen the terminal.

**Doctor reports missing permissions**  
The runtime-key principal needs Tunnels Read + Use for the selected tunnel.

**The connector exists but ChatGPT cannot use it**  
Confirm that `doctor` succeeds, the terminal remains open, and the matching connector is enabled in ChatGPT settings.
