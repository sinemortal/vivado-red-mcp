"""Red Pitaya deploy tools — SCP + SSH execute via paramiko.

Two delivery mechanisms are supported:

- ``xdevcfg`` (default) — works on Red Pitaya OS 1.04 and 2.00. The .bit.bin
  is piped into ``/dev/xdevcfg``, the PCAP loader exposed by the Zynq PS to
  userland. This is the canonical Red Pitaya method.
- ``fpgautil`` — the FPGA-Manager-based loader available on Red Pitaya OS 2.00.
  Mirrors what the Red Pitaya web apps use internally.

Authentication: password-only by default (Red Pitaya ships with ``root/root``).
Pass ``key_filename`` to use an SSH key instead. The connection times out at
``connect_timeout`` seconds (default 10).

No Vivado session required — these tools work purely over the network.
"""

from __future__ import annotations

from pathlib import Path

from mcp.types import Tool

from ._common import err, require_args

TOOLS = [
    Tool(
        name="deploy_to_redpitaya",
        description=(
            "Copy a .bit.bin to a Red Pitaya over SSH/SCP and load it into the "
            "FPGA. Uses /dev/xdevcfg (works on Red Pitaya OS 1.04 + 2.00) or "
            "fpgautil (OS 2.00). No Vivado session required."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "bit_bin_path": {
                    "type": "string",
                    "description": "Absolute path to the local .bit.bin produced by generate_cfgmem",
                },
                "host": {
                    "type": "string",
                    "description": "Red Pitaya IP or hostname (e.g. '192.168.1.100' or 'rp-f0abcd.local')",
                },
                "user": {"type": "string", "description": "SSH user (default: 'root')"},
                "password": {
                    "type": "string",
                    "description": "SSH password (default: 'root' — Red Pitaya factory default)",
                },
                "key_filename": {
                    "type": "string",
                    "description": "Path to an SSH private key. If set, overrides password auth.",
                },
                "port": {"type": "integer", "description": "SSH port (default: 22)"},
                "remote_path": {
                    "type": "string",
                    "description": "Remote .bit.bin path (default: /tmp/<basename>)",
                },
                "method": {
                    "type": "string",
                    "enum": ["xdevcfg", "fpgautil"],
                    "description": "Loader: 'xdevcfg' (default, both OS) or 'fpgautil' (OS 2.00)",
                },
                "connect_timeout": {"type": "integer", "description": "SSH connect timeout in seconds (default: 10)"},
                "keep_remote": {
                    "type": "boolean",
                    "description": "Leave the .bit.bin on the board after loading (default: false → rm)",
                },
            },
            "required": ["bit_bin_path", "host"],
        },
    ),
    Tool(
        name="ssh_redpitaya_exec",
        description=(
            "Run an arbitrary shell command on a Red Pitaya over SSH and return "
            "stdout/stderr/exit code. Useful for status checks, dmesg reads, "
            "manual loader invocations."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "command": {"type": "string", "description": "Shell command to execute"},
                "user": {"type": "string"},
                "password": {"type": "string"},
                "key_filename": {"type": "string"},
                "port": {"type": "integer"},
                "connect_timeout": {"type": "integer"},
                "exec_timeout": {"type": "integer", "description": "Command timeout (default: 30s)"},
            },
            "required": ["host", "command"],
        },
    ),
]


def _connect(args: dict):
    """Open a paramiko SSHClient using args. Returns (client, error_dict_or_None)."""
    try:
        import paramiko  # type: ignore
    except ImportError:
        return None, err(
            "paramiko is not installed. Run: pip install paramiko"
        )

    host = args["host"]
    user = args.get("user", "root")
    port = args.get("port", 22)
    timeout = args.get("connect_timeout", 10)
    key_filename = args.get("key_filename")
    password = args.get("password", "root")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        if key_filename:
            client.connect(
                host,
                port=port,
                username=user,
                key_filename=key_filename,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        else:
            client.connect(
                host,
                port=port,
                username=user,
                password=password,
                timeout=timeout,
                look_for_keys=False,
                allow_agent=False,
            )
    except Exception as ex:  # noqa: BLE001
        return None, err(f"SSH connect failed: {type(ex).__name__}: {ex}", host=host)

    return client, None


def _exec(client, command: str, timeout: int = 30) -> dict:
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    er = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    return {"stdout": out, "stderr": er, "exit_code": rc}


def _deploy_to_redpitaya(session, args):
    if (e := require_args(args, "bit_bin_path", "host")):
        return e

    bit = Path(args["bit_bin_path"])
    if not bit.exists():
        return err(f".bit.bin not found locally: {bit}")
    if not bit.is_file():
        return err(f"Path is not a file: {bit}")

    remote_path = args.get("remote_path") or f"/tmp/{bit.name}"
    method = args.get("method", "xdevcfg")
    keep_remote = args.get("keep_remote", False)

    client, err_d = _connect(args)
    if err_d:
        return err_d

    try:
        # SFTP upload
        sftp = client.open_sftp()
        try:
            sftp.put(str(bit), remote_path)
        finally:
            sftp.close()

        # Verify upload
        verify = _exec(client, f"ls -l {remote_path} && wc -c < {remote_path}")
        if verify["exit_code"] != 0:
            return err(
                "Upload verification failed",
                stderr=verify["stderr"],
                exit_code=verify["exit_code"],
            )

        # Load into FPGA
        if method == "xdevcfg":
            # OS 1.04: PCAP loader (legacy)
            load_cmd = f"cat {remote_path} > /dev/xdevcfg"
        elif method == "fpgautil":
            # OS 2.00: FPGA Manager via fpgautil. Binary lives under
            # /opt/redpitaya/bin/, which is NOT in the default SSH PATH.
            load_cmd = (
                f"/opt/redpitaya/bin/fpgautil -b {remote_path} -f Full"
            )
        else:
            return err(f"Unknown method: {method}")

        load = _exec(client, load_cmd, timeout=60)
        load_ok = load["exit_code"] == 0

        # Cleanup
        cleanup_msg = None
        if not keep_remote and load_ok:
            cu = _exec(client, f"rm -f {remote_path}")
            if cu["exit_code"] != 0:
                cleanup_msg = f"warning: rm failed: {cu['stderr'].strip()}"

        return {
            "success": load_ok,
            "host": args["host"],
            "remote_path": remote_path,
            "method": method,
            "size_bytes": bit.stat().st_size,
            "load_stdout": load["stdout"],
            "load_stderr": load["stderr"],
            "load_exit_code": load["exit_code"],
            "verify_output": verify["stdout"].strip(),
            "cleanup": cleanup_msg,
        }
    finally:
        client.close()


def _ssh_redpitaya_exec(session, args):
    if (e := require_args(args, "host", "command")):
        return e

    client, err_d = _connect(args)
    if err_d:
        return err_d

    try:
        timeout = args.get("exec_timeout", 30)
        result = _exec(client, args["command"], timeout=timeout)
        return {
            "success": result["exit_code"] == 0,
            "host": args["host"],
            "command": args["command"],
            **result,
        }
    finally:
        client.close()


HANDLERS = {
    "deploy_to_redpitaya": _deploy_to_redpitaya,
    "ssh_redpitaya_exec": _ssh_redpitaya_exec,
}
