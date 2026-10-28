# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`vivado_red_mcp/` is an MCP (Model Context Protocol) server that exposes AMD/Xilinx
Vivado 2020.1 + Red Pitaya FPGA workflows as tools an AI assistant can drive.
Forked from `coreyhahn/vivado_mcp` and heavily refactored — the original
monolithic `server.py` was split into a `tools/` subpackage and extended with
Block Design, IP catalog, Hardware Manager, advanced reports, RedPitaya
PS+PL flow, and SSH deploy.

Targets: Red Pitaya STEMlab 125-14 (Zynq xc7z010clg400-1). Vivado 2020.1 on
Linux (`settings64.sh`) or Windows (`vivado.bat`); also validated end-to-end on
Vivado 2026.1 (Windows).

## Install & verify

```bash
# From this repo root, editable install
pip install -e .   # pins the MCP SDK to 1.x (mcp>=1.0,<2)

# Console script registered: `vivado-red-mcp` (entry point: vivado_red_mcp:main)
# MCP transport: stdio (JSON-RPC over stdin/stdout)

# Registry consistency check — every declared tool must have a handler:
python -c "from vivado_red_mcp.tools import ALL_TOOLS, ALL_HANDLERS; \
  assert {t.name for t in ALL_TOOLS} == set(ALL_HANDLERS); \
  print(f'{len(ALL_TOOLS)} tools OK')"
```

There is no test suite in the repo; CI only runs the registry check. Validate
changes live against Vivado.

Register with Claude Code (user-global):
```bash
claude mcp add --transport stdio --scope user vivado -- vivado-red-mcp
```

## Architecture

### Tool registry pattern
Every domain lives in its own module under `vivado_red_mcp/tools/`. Each module
exposes two top-level symbols:

```python
TOOLS: list[mcp.types.Tool]                      # schema declarations
HANDLERS: dict[str, Callable[[VivadoSession, dict], dict]]  # impl by name
```

`tools/__init__.py` merges them into `ALL_TOOLS` / `ALL_HANDLERS` and asserts
at import-time that every declared tool has a handler and vice versa — schema
drift becomes a startup error, not a silent runtime failure.

`server.py` is intentionally thin (~80 lines): `list_tools` returns `ALL_TOOLS`,
`call_tool` dispatches via `ALL_HANDLERS`, wraps each dict result in
`TextContent`. To add a tool: write a new module under `tools/`, register it in
`_MODULES` and the `from . import ...` block in `tools/__init__.py`.

### Vivado session
`vivado_session.py` runs a singleton persistent Vivado TCL shell via pexpect
(Linux) or a pywinpty/ConPTY shim (`_vivado_subprocess_shim.py`, Windows).
Spawned lazily by `start_session`. ~30 s cold
start. Output capture is prompt-based (`Vivado%`); error classification in
`classify_output_errors()` distinguishes real TCL errors from report text that
just happens to contain the word "ERROR".

On Windows the child env drops `NoDefaultCurrentDirectoryInExePath`: Claude
Code sets it for its children, and with it Vivado cannot spawn the scripts it
generates by bare name (xsim `compile.bat` → "Spawn failed: file not found").
If Vivado exits during startup (e.g. no license), `start()` returns its output.

Multi-line commands are sent to `run_tcl` as one line that base64-decodes and
`eval`s the script inside `catch` (the console would otherwise drop the
newlines on Windows); a begin marker separates output from the echo, and a
caught error sets `success=False` deterministically.

Report tools go through `tools/_common.py::run_design_cmd`: on "No open
design" it opens the latest completed run (impl_1, else synth_1) and retries,
so reports work right after `run_implementation` / `generate_bitstream`.

Run status verification uses `verify_run_status()` in `parsers.py` — queries
the run's `STATUS`/`PROGRESS` properties as ground truth instead of parsing
launch output.

### Two Red Pitaya build flows — pick the right one
- **RTL-only, no PS7** → `tools/redpitaya.py::create_redpitaya_project_rtl`.
  Pure PL design (counter blinking an LED off the 125 MHz LVDS ADC clock).
  No ARM, no DDR backbone.
- **Full PS + PL** → `tools/redpitaya_repo.py::rp_build_project`. Reuses the
  canonical RedPitaya-FPGA backbone (`prj/<name>/ip/systemZ10.tcl` — a
  `write_bd_tcl` export of the validated PS7 block design with DDR3/MIO/clocks
  pre-configured). Never rebuild the PS7 from scratch with the BD tools — it
  needs ~100 `CONFIG.PCW_*` properties that this project's docs do not encode.

The `rp_*` tools assume a workspace copy of the RedPitaya-FPGA repo
(`rp_setup_workspace` makes one). Builds happen there, the source checkout
stays pristine. Custom designs: `rp_create_custom_project base=barebones`
(or `v0.94`/`axi4lite`) clones a known-good project into the workspace; edit
`prj/<name>/rtl/red_pitaya_top.sv` and call `rp_build_project`.

### Bundled documentation
`vivado_red_mcp/data/docs/*.md` — topical references the MCP server can return
via `get_vivado_doc <topic>`. Topics are listed in `tools/docs.py::KNOWN_TOPICS`.
When you add a topic you must update both `KNOWN_TOPICS` and the description
of the `get_vivado_doc` tool.

**Read `data/docs/pitfalls_2020_1.md` before debugging Vivado quoting issues.**
The recurring offenders, all hit during development:
- `add_files` with paths containing spaces → wrap in `[list {...}]`, plain
  braces are not enough.
- `set_property -name {PROP WITH SPACE} -value {V}` → requires explicit
  `-objects` flag, otherwise Vivado reports `'-name' specified twice`.
- `write_cfgmem -loadbit "up 0x0 <path>"` → custom non-Tcl parser that
  splits on whitespace inside the quotes; only workaround is `cd` to the
  `.bit` directory and pass a relative filename. Shared helper:
  `tools/redpitaya.py::write_cfgmem`.
- `make_wrapper` does NOT add the wrapper to the fileset — parse its
  stdout for the wrapper path, then `add_files -norecurse [list {...}]`
  and `set_property top`.

### Red Pitaya deploy
`tools/deploy.py::deploy_to_redpitaya` SFTPs a `.bit.bin` via paramiko and
loads it. Two methods: `xdevcfg` (OS 1.04 legacy PCAP loader) and `fpgautil`
(OS 2.00 FPGA Manager). The Red Pitaya `fpgautil` binary is at
`/opt/redpitaya/bin/fpgautil`, NOT in the default non-login SSH PATH — the
tool already uses the absolute path. Default factory creds: `root` / `root`.

## Working conventions

- **Don't start a Vivado session for purely host-side or SSH-only operations.**
  Listing boards, reading bundled docs, SSH commands to a Red Pitaya, copying
  files, inspecting JSON metadata — all of these work without `start_session`.
  Cold-starting Vivado costs ~30-120 s and burns RAM.
- **`rp_build_project` calls in the same Vivado session**: each call now does
  `close_project -quiet` for every open project before sourcing the setup TCL.
  This avoids the stale `processing_system7` validation failures that
  otherwise happen when building two RedPitaya projects back-to-back.
- **Synth flags**: `rp_build_project` defaults to no extra synth flags. The
  RedPitaya canonical `-flatten_hierarchy none -bufg 16 -keep_equivalent_registers`
  is for reproducibility, not QoR — it can make timing worse on xc7z010-1.
  Pass them explicitly via `synth_flags=...` only when you want bit-identical
  RedPitaya builds.

## Layout

- `vivado_red_mcp/server.py` — MCP dispatcher (thin).
- `vivado_red_mcp/vivado_session.py` — Vivado pexpect/wexpect session manager.
- `vivado_red_mcp/parsers.py` — timing/utilization/messages/DRC/power parsers + `verify_run_status`, `truncate_response`.
- `vivado_red_mcp/boards.py` — bundled board metadata loader.
- `vivado_red_mcp/reports.py` — `/tmp/vivado_red_mcp` report file cache.
- `vivado_red_mcp/tools/` — domain tool modules + `_common.py` helpers + `__init__.py` registry.
- `vivado_red_mcp/data/boards/` — bundled XDC + JSON metadata for Red Pitaya 125-14.
- `vivado_red_mcp/data/docs/` — markdown topics returned by `get_vivado_doc`.
- `test_runs/` — build outputs from live tests (gitignored).
