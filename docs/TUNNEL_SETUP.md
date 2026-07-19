# Interactive tunnel setup

The launcher connects CodexPC Connector to an existing OpenAI tunnel and stores the runtime API key in the operating system credential vault.

- Windows: **Credential Manager**
- macOS: **Keychain**

The key is entered once on the first launch. Later launches reuse it automatically.

## Run

### Windows

```bat
launch-tunnel.cmd
```

### macOS

```bash
chmod +x launch-tunnel.sh
./launch-tunnel.sh
```

The launcher asks for the organization label, local profile name, and Tunnel ID. The API key is requested only when no saved key exists.

## Replace or remove the saved key

```bash
python scripts/setup_tunnel.py --replace-key
python scripts/setup_tunnel.py --forget-key
```

For a non-default profile, add `--profile NAME`.

## Requirements

- Python 3.11+
- `tunnel-client` available in `PATH`
- Tunnel ID from OpenAI Platform
- Runtime API key with Tunnels Read + Use

The launcher creates or updates the local profile, runs `doctor --explain`, and starts the tunnel with:

```text
python -m codexpc_connector
```

Keep the terminal open while the connector is in use. Press `Ctrl+C` to stop it.

## Security

The key is never written to the repository, shell script, tunnel profile, or plain-text config. Revoke any key that has previously appeared in a script, log, screenshot, or public repository.
