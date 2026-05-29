"""IP catalog tools — create_ip, configure_ip, generate_target, synth_ip, upgrade_ip.

References:
  - UG896 (Designing with IP)
  - UG835 §create_ip, §generate_target, §synth_ip, §upgrade_ip, §report_ip_status
"""

from __future__ import annotations

from mcp.types import Tool

from ._common import err, require_args, require_project_open

TOOLS = [
    Tool(
        name="create_ip",
        description=(
            "Create an IP from the Xilinx IP catalog. Generates a .xci file in the "
            "project's IP sources fileset. Use configure_ip + generate_ip_target "
            "afterwards, then run synth_ip if you want out-of-context synthesis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ip_name": {"type": "string", "description": "Catalog name (e.g. 'clk_wiz')"},
                "module_name": {
                    "type": "string",
                    "description": "Instance/module name on disk (e.g. 'clk_wiz_0')",
                },
                "vendor": {"type": "string", "description": "default: xilinx.com"},
                "library": {"type": "string", "description": "default: ip"},
                "version": {"type": "string", "description": "Optional explicit version"},
            },
            "required": ["ip_name", "module_name"],
        },
    ),
    Tool(
        name="configure_ip",
        description="Set CONFIG.* properties on an existing IP via set_property -dict.",
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {"type": "string"},
                "config": {
                    "type": "object",
                    "description": "Dict of CONFIG.* keys to values (e.g. {'CONFIG.PRIM_IN_FREQ': '125'})",
                },
            },
            "required": ["module_name", "config"],
        },
    ),
    Tool(
        name="generate_ip_target",
        description="Generate IP output products (synthesis + simulation by default).",
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {"type": "string"},
                "targets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "default: ['synthesis', 'simulation']",
                },
            },
            "required": ["module_name"],
        },
    ),
    Tool(
        name="synth_ip",
        description="Run out-of-context (OOC) synthesis on an IP.",
        inputSchema={
            "type": "object",
            "properties": {"module_name": {"type": "string"}},
            "required": ["module_name"],
        },
    ),
    Tool(
        name="upgrade_ip",
        description="Upgrade IP version (no-op if already at latest).",
        inputSchema={
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Specific IP to upgrade; if omitted, upgrades all in project",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="report_ip_status",
        description="Get a structured snapshot of the project's IP and their upgrade status.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]


def _create_ip(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "ip_name", "module_name")):
        return e
    ip_name = args["ip_name"]
    module = args["module_name"]
    vendor = args.get("vendor", "xilinx.com")
    library = args.get("library", "ip")
    version = args.get("version")

    cmd = f"create_ip -name {ip_name} -vendor {vendor} -library {library}"
    if version:
        cmd += f" -version {version}"
    cmd += f" -module_name {module}"

    r = session.run_tcl(cmd, timeout_override=120)
    return {"success": r.success, "module_name": module, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _configure_ip(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "module_name", "config")):
        return e
    module = args["module_name"]
    config = args["config"]
    if not isinstance(config, dict) or not config:
        return err("'config' must be a non-empty dict")

    kv = " ".join(f"{k} {{{v}}}" for k, v in config.items())
    r = session.run_tcl(
        f"set_property -dict {{{kv}}} [get_ips {module}]", timeout_override=60
    )
    return {
        "success": r.success,
        "module_name": module,
        "config_applied": len(config),
        "output": r.output,
    }


def _generate_ip_target(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "module_name")):
        return e
    module = args["module_name"]
    targets = args.get("targets") or ["synthesis", "simulation"]
    targets_str = " ".join(targets)
    r = session.run_tcl(
        f"generate_target {{{targets_str}}} [get_files {module}.xci]",
        timeout_override=600,
    )
    return {"success": r.success, "module_name": module, "targets": targets, "output": r.output}


def _synth_ip(session, args):
    if (e := require_project_open(session)):
        return e
    if (e := require_args(args, "module_name")):
        return e
    module = args["module_name"]
    r = session.run_tcl(f"synth_ip [get_ips {module}]", timeout_override=1800)
    return {"success": r.success, "module_name": module, "output": r.output, "elapsed_ms": r.elapsed_ms}


def _upgrade_ip(session, args):
    if (e := require_project_open(session)):
        return e
    module = args.get("module_name")
    target = f"[get_ips {module}]" if module else "[get_ips]"
    r = session.run_tcl(f"upgrade_ip {target}", timeout_override=600)
    return {"success": r.success, "module_name": module, "output": r.output}


def _report_ip_status(session, args):
    if (e := require_project_open(session)):
        return e
    # report_ip_status emits to stdout when -name is omitted
    r = session.run_tcl("report_ip_status", timeout_override=60)
    # Parse simple summary lines
    summary_lines = [ln for ln in r.output.splitlines() if ln.strip()]
    return {
        "success": r.success,
        "lines": summary_lines[:200],
        "elapsed_ms": r.elapsed_ms,
    }


HANDLERS = {
    "create_ip": _create_ip,
    "configure_ip": _configure_ip,
    "generate_ip_target": _generate_ip_target,
    "synth_ip": _synth_ip,
    "upgrade_ip": _upgrade_ip,
    "report_ip_status": _report_ip_status,
}
