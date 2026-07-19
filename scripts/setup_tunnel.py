#!/usr/bin/env python3
"""Interactive launcher for exposing CodexPC Connector through OpenAI tunnel-client."""

from __future__ import annotations

import getpass
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

TUNNEL_RE = re.compile(r"^tunnel_[0-9a-f]{32}$")


def ask(prompt: str, *, default: str | None = None, required: bool = True) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("This value is required.")


def locate_tunnel_client() -> str:
    found = shutil.which("tunnel-client")
    if found:
        return found
    print("\nError: tunnel-client was not found in PATH.")
    print("Download it from OpenAI Platform > Organization > Tunnels, then reopen the terminal.")
    raise SystemExit(2)


def main() -> int:
    print("CodexPC Connector — interactive tunnel launcher")
    print("Secrets are used only by this process and are not written to disk.\n")

    tunnel_client = locate_tunnel_client()
    organization = ask("Organization name (label only)", required=False)
    profile = ask("Local profile name", default="codexpc")

    while True:
        tunnel_id = ask("Tunnel ID")
        if TUNNEL_RE.fullmatch(tunnel_id):
            break
        print("Expected format: tunnel_ followed by 32 lowercase hexadecimal characters.")

    api_key = getpass.getpass("Runtime API key (hidden): ").strip()
    if not api_key:
        print("Runtime API key is required.")
        return 2

    python_executable = str(Path(sys.executable).resolve())
    mcp_command = f'"{python_executable}" -m codexpc_connector'

    env = os.environ.copy()
    env["CONTROL_PLANE_API_KEY"] = api_key
    env["CONTROL_PLANE_TUNNEL_ID"] = tunnel_id

    print("\nConfiguration")
    if organization:
        print(f"  Organization: {organization}")
    print(f"  Profile:      {profile}")
    print(f"  Tunnel:       {tunnel_id}")
    print(f"  MCP command:  {mcp_command}")
    print("  API key:      hidden, not saved")

    init_command = [
        tunnel_client,
        "init",
        "--sample",
        "sample_mcp_stdio_local",
        "--profile",
        profile,
        "--tunnel-id",
        tunnel_id,
        "--mcp-command",
        mcp_command,
    ]

    print("\nCreating or updating the local tunnel profile...")
    init_result = subprocess.run(init_command, env=env, check=False)
    if init_result.returncode != 0:
        print("Profile creation failed.")
        return init_result.returncode

    print("\nChecking configuration...")
    doctor_result = subprocess.run(
        [tunnel_client, "doctor", "--profile", profile, "--explain"],
        env=env,
        check=False,
    )
    if doctor_result.returncode != 0:
        print("Tunnel diagnostics failed. Review the messages above.")
        return doctor_result.returncode

    print("\nStarting tunnel. Keep this terminal open; press Ctrl+C to stop.\n")
    try:
        return subprocess.run(
            [tunnel_client, "run", "--profile", profile],
            env=env,
            check=False,
        ).returncode
    except KeyboardInterrupt:
        print("\nTunnel stopped.")
        return 130
    finally:
        env.pop("CONTROL_PLANE_API_KEY", None)
        api_key = ""


if __name__ == "__main__":
    raise SystemExit(main())
