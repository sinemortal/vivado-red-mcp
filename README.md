# vivado-red-mcp — Vivado MCP server, Red Pitaya edition

<!-- mcp-name: io.github.sinemortal/vivado-red-mcp -->

An [MCP](https://modelcontextprotocol.io) server that lets an AI assistant such as
Claude drive **AMD/Xilinx Vivado** directly: create projects, build block designs,
synthesize, implement, simulate, read timing/utilization reports and generate
bitstreams — without opening the Vivado GUI.

It has first-class support for the **Red Pitaya STEMlab 125-14** (Zynq
`xc7z010clg400-1`): you can go from a natural-language description to a
`.bit.bin` running on the board, using either pure RTL or the official
RedPitaya-FPGA PS+PL (ARM + FPGA) backbone, and deploy it over SSH.

> Forked from [coreyhahn/vivado_mcp](https://github.com/coreyhahn/vivado_mcp) and
> heavily extended (93 tools): block design / IP Integrator, IP catalog, Hardware
> Manager, advanced reports, Red Pitaya RTL and PS+PL flows, SSH deploy.

**Current version: 0.5.0** — see [What's new](#whats-new-in-050) and [`CHANGELOG.md`](CHANGELOG.md).

> Not to be confused with the unrelated `vivado-mcp` package on PyPI. This project is
> `vivado-red-mcp`: Python module `vivado_red_mcp`, command `vivado-red-mcp`.

---

## Contents

- [What it can do](#what-it-can-do)
- [Tested with](#tested-with)
- [Requirements](#requirements)
- [Installation](#installation)
- [First steps](#first-steps)
- [Red Pitaya](#red-pitaya)
- [What's new in 0.5.0](#whats-new-in-050)
- [Troubleshooting](#troubleshooting)
- [Available tools](#available-tools)
- [Architecture](#architecture)
- [License](#license)

## What it can do

- **Persistent Vivado session** — one Vivado process in Tcl mode is kept alive, so
  commands don't pay the 20–30 s startup each time.
- **Projects and design flow** — create/open projects, add HDL and XDC files,
  synthesis, implementation, bitstream, run strategies.
- **Block design (IP Integrator)** — ports, IP cores, RTL module cells, nets, PS7
  presets, validation, wrapper generation.
- **Reports** — timing (WNS/TNS/WHS/THS), utilization, clocks, power, DRC,
  methodology, QoR; returned as parsed values, not just raw text.
- **Simulation (xsim)** — behavioral and post-synthesis/implementation, read
  signal values, breakpoints.
- **Red Pitaya** — one-shot RTL build, full PS+PL build from the official
  RedPitaya-FPGA repo, bundled board constraints, `.bit.bin` generation, SSH deploy.
- **Raw Tcl** — anything not covered by a tool can be run as Tcl (multi-line
  scripts supported).

## Tested with

| | Status |
|---|---|
| **Vivado 2026.1, Windows 11** | Validated end-to-end in 0.4.0: session, RTL and PS+PL Red Pitaya builds, reports, behavioral + post-synthesis xsim, block design, RedPitaya-FPGA tutorials (see below) |
| Vivado 2020.1, Linux | Original development target (0.3.x). Not re-tested on 0.4.0 |
| Other Vivado releases | Expected to work (the generic tools use standard Tcl); not tested |
| Red Pitaya board | **STEMlab 125-14 (Z10) only** for the Red Pitaya flows |
| Python | 3.10 – 3.12 |
| MCP Python SDK | **1.x only** (`mcp>=1.0,<2`, pinned automatically) |

The RedPitaya-FPGA tutorials in `prj/Examples` (Led_blink, Knight_rider, Stopwatch,
Frequency_counter) build to a bitstream through the server. Led_blink and
Knight_rider rebuilt from scratch with MCP tools only produce **byte-identical
bitstreams** to the tutorials' own scripts.

## Requirements

1. **Python 3.10+**
2. **AMD Vivado** (the free edition is enough for the Red Pitaya `xc7z010`).
   When installing, you only need *Vivado* and, under devices, *SoCs → Zynq-7000*;
   Vitis Model Composer and DocNav are not needed.
3. **A Vivado license file — also for the free edition on 2025.x/2026.x.**
   Without it Vivado refuses to start (`a valid license was not found`):
   - open the Vivado License Manager (`<Vivado>/bin/vlm.bat` on Windows, `vlm` on Linux);
   - *Obtain License* → on the AMD site tick **Vivado Basic Tier License, Node
     Locked License** (no charge, no expiry) → *Generate Node-Locked License*;
   - host ID: the MAC address of your network card (shown under *View Host
     Information*). The license is tied to the PC, not to the network you use;
   - load the received `Xilinx.lic` with *Load License → Copy License*.
4. **Vivado reachable by the server**, either:
   - on `PATH` (Linux: `source <Vivado>/settings64.sh`; Windows: add
     `<Vivado>\bin` to `PATH`), or
   - by telling Claude the full path, which it passes to `start_session`
     (e.g. `C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat`).

`pexpect` (Linux/macOS) or `pywinpty` (Windows) is installed automatically.

## Installation

### 1. Get the code and install it

```bash
git clone https://github.com/sinemortal/vivado-red-mcp.git
cd vivado-red-mcp
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate
pip install -e .
```

`pip` pins the MCP SDK to 1.x by itself. Do not upgrade `mcp` to 2.x: the server
would not start (`'Server' object has no attribute 'list_tools'`).

### 2. Register it with Claude Code

Once, for all your projects:

```bash
claude mcp add --transport stdio --scope user vivado -- vivado-red-mcp
```

If `vivado-red-mcp` is not on `PATH` when Claude Code starts (typical with a virtual
environment), point to the venv's Python instead:

```bash
# Windows
claude mcp add --transport stdio --scope user vivado -- "C:\path\to\vivado-red-mcp\.venv\Scripts\python.exe" -m vivado_red_mcp
# Linux/macOS
claude mcp add --transport stdio --scope user vivado -- /path/to/vivado-red-mcp/.venv/bin/python -m vivado_red_mcp
```

Or share it with a single project through a `.mcp.json` at the project root:

```json
{
  "mcpServers": {
    "vivado": {
      "type": "stdio",
      "command": "vivado-red-mcp"
    }
  }
}
```

Check it with `claude mcp list`: `vivado` should show as connected.

### 3. Optional: disable the RedPitaya-FPGA auto-download

On startup the server downloads the RedPitaya-FPGA repo (source zip) into its
working directory if it is missing, for the PS+PL flow. Set the
environment variable `VIVADO_MCP_NO_AUTOFETCH=1` to turn this off; the
`rp_fetch_repo` tool can still download it on demand.

## First steps

Talk to Claude in plain language, for example:

1. "Start a Vivado session" (add the path if Vivado is not on `PATH`)
2. "Open my project at `C:/work/my_proj/my_proj.xpr`"
3. "Synthesize and implement it, then tell me if timing is met"
4. "Show me the resource utilization"
5. "Generate the bitstream"
6. "Stop the Vivado session"

Claude picks the tools; you never have to call them by name.

## Red Pitaya

Two flows, depending on whether you need the ARM processor:

| Flow | Tool | Use it for |
|---|---|---|
| **RTL only** (no PS7) | `create_redpitaya_project_rtl` | Logic clocked by the 125 MHz ADC clock: LEDs, counters, expansion-connector GPIO. One call does create → sources → XDC → synth → impl → bitstream → `.bit.bin` |
| **PS + PL** | `rp_fetch_repo` → `rp_setup_workspace` → `rp_build_project` | Designs that need the ARM, DDR or AXI. Reuses the PS7 block design shipped by [RedPitaya-FPGA](https://github.com/RedPitaya/RedPitaya-FPGA) instead of reconfiguring the Zynq by hand |

Example prompt:

> Make an LED blinker at 1 Hz for the Red Pitaya using the 125 MHz ADC clock on
> `led_o[0]`, build it and give me the `.bit.bin`.

To load the result on the board, ask Claude to use `deploy_to_redpitaya` (SSH,
default credentials `root`/`root`; works with OS 1.04 `xdevcfg` and OS 2.00
`fpgautil`), or copy it yourself:

```bash
scp led_blinker.bit.bin root@rp-xxxxxx.local:/tmp/
ssh root@rp-xxxxxx.local 'cat /tmp/led_blinker.bit.bin > /dev/xdevcfg'
```

**PS+PL and the RedPitaya-FPGA repo.** The current upstream `master` targets
Vivado 2025.1; older checkouts targeted 2020.1. Both layouts are supported.
`rp_setup_workspace` copies the repo into a separate workspace and patches only
that copy, so the scripts run on the Vivado you have installed (their exported
block-design/IP scripts otherwise refuse any other release) and without a git
checkout. Your downloaded repo is never modified. Details:
`get_vivado_doc redpitaya_ps_pl_flow`.

**Bundled board data** (`data/boards/`):
- `red_pitaya_125_14_full.xdc` — full pinout (ADC, DAC, LEDs, expansion
  connector, XADC), port names as in the official `red_pitaya_top`
  (`adc_dat_i[ch][bit]`, `dac_dat_o`, `exp_p_io`, …); checked pin by pin against
  upstream `sdc/red_pitaya.xdc`.
- `red_pitaya_125_14_leds_min.xdc` — 125 MHz differential ADC clock + 8 LEDs, for
  hello-world designs.
- `red_pitaya_125_14_info.json` — part number and board metadata.

The RedPitaya tutorials (`prj/Examples`) use different port names
(`adc_dat_a_i`, `adc_clk_p_i`, …) and a PS7 preset (`cfg/red_pitaya.xml`); use
their own `cfg/` files when rebuilding them.

More Italian prompt examples and the step-by-step low-level flow: [`USAGE.md`](USAGE.md).

## What's new in 0.5.0

**Renamed to `vivado-red-mcp`** (package, Python module `vivado_red_mcp`, command
`vivado-red-mcp`), so it no longer clashes with the unrelated `vivado-mcp` package on
PyPI. If you installed an earlier version, reinstall it and re-register it with
Claude Code using the new command (see [Installation](#installation)).

### 0.4.0

**Works on Vivado 2026.1 and with the current RedPitaya-FPGA repo.**

Fixed:
- Server failed to start with MCP SDK 2.x → SDK pinned to 1.x.
- **Simulation never worked when the server was started by Claude Code on
  Windows** (xsim: `Spawn failed`) → fixed.
- Multi-line Tcl sent through `run_tcl` was silently corrupted on Windows → fixed.
- `get_timing_summary` always returned empty values; `get_utilization` misread
  newer reports → both parse current Vivado output.
- Reports right after a build failed with no message (`No open design`) → the
  latest completed run is opened automatically.
- `get_synthesis_errors_parsed` always returned 0 errors → now reads the run logs,
  including failed IP runs.
- `launch_simulation` modes rejected by recent Vivado → fixed.
- `generate_bitstream` timed out after 300 s and didn't check the result → now
  verified, returns the `.bit` path.
- Missing license (or any startup failure) now reports Vivado's own message in
  seconds instead of a generic error after 2 minutes.
- **Bundled `red_pitaya_125_14_full.xdc` had 6 wrong pins** (ADC channel A MSB and
  `dac_dat_o[8..12]`) → corrected.
- PS+PL flow broken by the new RedPitaya-FPGA layout → both layouts supported.

New tools: `create_bd_port`, `add_module_to_bd`, `configure_bd_cell`,
`set_run_strategy`. Full list in [`CHANGELOG.md`](CHANGELOG.md).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `start_session` fails with `valid license was not found` | Vivado 2025.x/2026.x needs a license file even for the free edition — see [Requirements](#requirements) |
| `start_session` cannot find Vivado | Put `<Vivado>/bin` on `PATH` or give Claude the full path of `vivado.bat` / `vivado` |
| Server does not start: `'Server' object has no attribute 'list_tools'` | MCP SDK 2.x installed. Run `pip install "mcp>=1.0,<2"` |
| `claude mcp list` shows `vivado` as failed | `vivado-red-mcp` not on `PATH` for Claude Code: register it with the venv's Python (see [Installation](#2-register-it-with-claude-code)) |
| A RedPitaya example fails synthesis with `red_pitaya_pll ... port does not exist` | Upstream issue in `prj/Examples/Simple_moving_average` (it pulls in `rtl_250`), not in this server |
| Occasional `Could not open 'C' for writing` in an IP run | Intermittent Vivado issue with parallel out-of-context runs; re-run synthesis |
| Long paths on Windows | Keep projects in short paths; Vivado and IP generation hit the 260-character limit |

## Available tools

### Session management
- `start_session` - Start a persistent Vivado Tcl session (optional `vivado_path`)
- `stop_session` - Stop the Vivado session
- `session_status` - Session statistics
- `check_session_health` - Detect a hung/dead session, optionally recover
- `get_host_status` - Host CPU/memory status

### Project management
- `create_project` - Create a project on disk (default part `xc7z010clg400-1`)
- `open_project` / `close_project` - Open or close an `.xpr`
- `get_project_info` - Part, directory, top, …
- `add_sources` / `add_constraints` - Attach HDL and XDC files

### Design flow
- `run_synthesis` - Run synthesis (verified run status)
- `run_implementation` - Run place and route (verified run status)
- `generate_bitstream` - Generate the bitstream (verified status + `.bit` path)
- `set_run_strategy` - Set the synthesis/implementation run strategy

### Reports & analysis
Report tools open the latest completed run automatically if no design is open.
- `get_timing_summary` - WNS, TNS, WHS, THS, pulse width, met / not met
- `get_timing_paths` - Detailed timing paths for failing/critical paths
- `get_utilization` - LUTs, FFs, BRAMs, DSPs, IOs
- `get_clocks` - Clock information
- `get_messages` - Synthesis/implementation messages

### Design queries
- `get_design_hierarchy` - Module/instance hierarchy
- `get_ports` - Top-level ports
- `get_nets` / `get_cells` - Search nets and cells

### Simulation (xsim)
- `set_simulation_top` - Set the testbench module
- `launch_simulation` - Behavioral, post-synthesis or post-implementation
  (functional/timing)
- `run_simulation` / `step_simulation` / `restart_simulation` / `close_simulation`
- `get_simulation_time`
- `get_signal_value` / `get_signal_values` - Read signals
- `get_simulation_objects` / `get_scopes` - Browse the hierarchy
- `add_signals_to_wave`
- `add_breakpoint` / `remove_breakpoints`
- `get_simulation_messages`

### Block design (IP Integrator) — Zynq / AXI
- `create_block_design` - Create a block design and make it current
- `create_bd_port` - Scalar, vector or interface ports
- `add_ip_to_bd` - Add an IP core (VLNV) with `CONFIG.*` properties
- `add_module_to_bd` - Add an RTL module as a module-reference cell
- `configure_bd_cell` - Set `CONFIG.*` on an existing cell (e.g. PS7 board preset import)
- `connect_bd_net` / `connect_bd_intf_net` - Wire pins/ports and AXI interfaces
- `auto_connect_axi` - `apply_bd_automation` for AXI master ↔ slave
- `apply_ps7_preset` - Zynq PS7 automation (FIXED_IO/DDR external)
- `validate_block_design` - Run BD DRC
- `assign_bd_address` - Auto-assign AXI address ranges
- `regenerate_bd_layout` - Tidy the layout
- `save_bd_design` / `close_bd_design` - Persist or close the BD
- `list_bd_cells` - List cells
- `generate_bd_wrapper` - `make_wrapper` + add to fileset + set as top

### IP catalog
- `create_ip` / `configure_ip` - Create and configure catalog IPs
- `generate_ip_target` / `synth_ip` - Output products, out-of-context synthesis
- `upgrade_ip` / `report_ip_status` - Upgrade and audit IP versions

### Hardware Manager (JTAG)
- `open_hw_manager` / `close_hw_manager`
- `connect_hw_server` - Connect to `hw_server` (default `localhost:3121`)
- `program_device` - Program a `.bit` over JTAG
- `refresh_hw_device` - Re-read the JTAG chain

### Advanced reports
- `report_power` - Total/dynamic/static power
- `report_drc` - DRC violations grouped by severity
- `report_methodology` - UltraFast methodology checks
- `report_qor_assessment` - QoR score
- `report_clock_interaction` - Cross-clock paths
- `generate_full_report` / `read_report_section` - Full reports to file, read them in pieces

### Red Pitaya — RTL flow
- `list_boards` / `get_board_info` - Bundled board metadata and XDC paths (no Vivado needed)
- `load_board_xdc` - Add a bundled board XDC to the project
- `create_redpitaya_project_rtl` - One-shot RTL build; returns `bit_path`,
  `bin_path`, parsed `timing_summary` and `utilization`
- `generate_cfgmem` - `.bit` → `.bit.bin` for `/dev/xdevcfg` / `fpgautil`
- `get_synthesis_errors_parsed` - Structured errors from the run logs, including
  failed IP runs

### Red Pitaya — PS+PL flow
- `rp_fetch_repo` - Download RedPitaya-FPGA (source zip, no git needed)
- `rp_setup_workspace` - Isolated, patched copy of the repo to build in
- `rp_list_projects` - List `prj/*` projects, flag the Z10-capable ones
- `rp_workspace_info` - Which projects are already built
- `rp_create_custom_project` - Clone a base project for your own PL logic
- `rp_build_project` - Setup → synth → impl → bitstream → `.bit.bin`, with parsed timing

### Red Pitaya — deploy (SSH, no Vivado needed)
- `deploy_to_redpitaya` - Upload a `.bit.bin` and load it (`xdevcfg` on OS 1.04,
  `fpgautil` on OS 2.00)
- `ssh_redpitaya_exec` - Run a shell command on the board

### Documentation (offline)
- `list_vivado_docs` / `get_vivado_doc` - Bundled topics (`block_design`,
  `ps7_zynq`, `timing_constraints`, `synthesis_strategies`, `simulation_xsim`,
  `red_pitaya_125_14`, `redpitaya_ps_pl_flow`, `tcl_quoting`, `hw_manager`,
  `ip_integrator`, `pitfalls_2020_1`), each with links to the AMD user guides

### Raw Tcl and misc
- `run_tcl` - Run any Tcl command or multi-line script
- `run_tcl_script` - Source a `.tcl` file
- `request_feature` / `list_feature_requests`

## Architecture

```
┌─────────────────┐     MCP (JSON-RPC)     ┌─────────────────┐
│   Claude Code   │◄──────over stdio──────►│  vivado-red-mcp     │
│   (AI client)   │                        │  server         │
└─────────────────┘                        └────────┬────────┘
                                                    │ pexpect (Linux)
                                                    │ pywinpty/ConPTY (Windows)
                                                    ▼
                                           ┌─────────────────┐
                                           │ Vivado process  │
                                           │  (-mode tcl)    │
                                           └─────────────────┘
```

The server keeps one Vivado process in Tcl mode and talks to it through a
pseudo-terminal, using the `Vivado%` prompt to know when a command has finished.
Each tool family lives in its own module under `tools/`; see [`CLAUDE.md`](CLAUDE.md)
for the design conventions and known Vivado Tcl pitfalls.

## Contributing

Issues and pull requests are welcome. There is no automated Vivado test in CI
(it only checks that every tool has a handler); changes to the Vivado-facing code
should be validated against a real Vivado install.

## License

MIT — see [`LICENSE`](LICENSE). Bundled third-party material (Red Pitaya board XDC
files, 3-clause BSD) is listed in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md).

## Acknowledgments

- Forked from [coreyhahn/vivado_mcp](https://github.com/coreyhahn/vivado_mcp) (MIT)
- Red Pitaya flows build on [RedPitaya/RedPitaya-FPGA](https://github.com/RedPitaya/RedPitaya-FPGA)
- Developed with [Claude](https://claude.ai) (Anthropic)
- Uses the [Model Context Protocol](https://modelcontextprotocol.io)
- Integrates with [AMD Vivado](https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado.html)
