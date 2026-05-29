# Vivado MCP Server — Red Pitaya edition

A Model Context Protocol (MCP) server that enables AI assistants like Claude to
directly drive AMD/Xilinx Vivado, **and take a Red Pitaya STEMlab 125-14
(Zynq xc7z010) design from a natural-language description all the way to a
bitstream running on the board** — synthesis, implementation, `.bit.bin`
generation, and SSH deploy, with no Vivado GUI.

This is what sets it apart from other Vivado MCP servers: first-class Red Pitaya
support (bundled board XDC, the canonical RedPitaya-FPGA PS+PL backbone, and
on-board deployment), not just generic Vivado control.

> Forked from [coreyhahn/vivado_mcp](https://github.com/coreyhahn/vivado_mcp) and
> heavily extended: a modular `tools/` registry, Block Design / IP Integrator,
> Hardware Manager, advanced reports, the Red Pitaya RTL + PS+PL flows, and SSH
> deploy.

## Features

- **Session Management**: Start/stop persistent Vivado TCL sessions (avoids 30s startup per command)
- **Project Management**: Open/close Vivado projects (.xpr files)
- **Design Flow**: Run synthesis, implementation, and bitstream generation
- **Reports & Analysis**: Get timing summaries, utilization reports, and design analysis
- **Design Queries**: Explore hierarchy, ports, nets, and cells
- **Simulation**: Control Vivado's integrated simulator (xsim)
- **Red Pitaya end-to-end**: Create RTL or PS+PL projects, build, and deploy the bitstream to the board over SSH
- **Raw TCL**: Execute arbitrary Vivado TCL commands for advanced operations

## Requirements

- Python 3.10+
- AMD/Xilinx Vivado installed — **developed and validated against Vivado 2020.1**
  (the version the Red Pitaya STEMlab 125-14 toolchain targets). Generic Vivado
  tools work on newer versions too, but the Red Pitaya flows assume 2020.1.
- Vivado must be in your PATH, or specify the full path when starting a session
- **Linux/macOS**: uses `pexpect` (installed automatically)
- **Windows**: uses a `pywinpty` (ConPTY) shim (installed automatically). `vivado.bat` must be
  reachable on `PATH` — source `C:\Xilinx\Vivado\<version>\settings64.bat` in
  the shell that launches `vivado-mcp`, or pass an absolute path to
  `start_session`.

## Installation

### From GitHub

```bash
git clone https://github.com/sinemortal/vivado-mcp.git
cd vivado-mcp
pip install -e .
```

### Configure Claude Code

Add to your Claude Code MCP configuration (`~/.claude/claude_desktop_config.json` or project-level `.mcp.json`):

```json
{
  "mcpServers": {
    "vivado": {
      "command": "vivado-mcp"
    }
  }
}
```

Or if you want to specify the Python interpreter:

```json
{
  "mcpServers": {
    "vivado": {
      "command": "python",
      "args": ["-m", "vivado_mcp"]
    }
  }
}
```

## Usage

Once configured, Claude can interact with Vivado through natural language. Example workflow:

1. **Start Vivado session**: "Start a Vivado session"
2. **Open project**: "Open my project at /path/to/project.xpr"
3. **Run synthesis**: "Synthesize the design"
4. **Check timing**: "What's the timing summary? Is timing met?"
5. **Check utilization**: "Show me the resource utilization"
6. **Close session**: "Stop the Vivado session"

## Red Pitaya quick start

This fork adds first-class support for creating Red Pitaya STEMlab 125-14
projects from scratch — no .xpr template or Vivado GUI needed. Describe your
design in chat and Claude will call **one** composite tool that runs the
whole flow (create → add sources → add XDC → synth → impl → bitstream → `.bin`).

See **[USAGE.md](USAGE.md)** for Italian prompt examples and the step-by-step
low-level flow.

New tools added for this use case:

- `create_project` — create a Vivado project on disk (defaults to
  `xc7z010clg400-1`)
- `add_sources` / `add_constraints` — attach HDL and XDC files to the project
- `list_boards` / `get_board_info` — browse bundled board metadata and get
  absolute paths to the vendored XDC files (no Vivado session needed)
- `generate_cfgmem` — convert a `.bit` to the `.bit.bin` that the Red Pitaya
  expects at `/dev/xdevcfg`
- `get_synthesis_errors_parsed` — structured error list from a failed run
- **`create_redpitaya_project_rtl`** — composite that runs the whole RTL
  flow end-to-end and returns `{bit_path, bin_path, timing_summary, utilization}`

Bundled data under `data/boards/`:
- `red_pitaya_125_14_full.xdc` — complete peripheral pinout (ADC, DAC, LEDs,
  expansion connector, XADC), from `RedPitaya/RedPitaya-FPGA` sdc/
- `red_pitaya_125_14_leds_min.xdc` — minimal constraints (125 MHz differential
  clock + 8 user LEDs) for hello-world projects
- `red_pitaya_125_14_info.json` — part number, LED count, default synth flags

## Available Tools

### Session Management
- `start_session` - Start a persistent Vivado TCL session
- `stop_session` - Stop the Vivado session
- `session_status` - Get session statistics

### Project Management
- `open_project` - Open a Vivado project (.xpr)
- `close_project` - Close the current project
- `get_project_info` - Get project information (part, directory, etc.)

### Design Flow
- `run_synthesis` - Run synthesis
- `run_implementation` - Run place and route
- `generate_bitstream` - Generate bitstream

### Reports & Analysis
- `get_timing_summary` - Get timing summary (WNS, TNS, WHS, THS)
- `get_timing_paths` - Get detailed timing paths for failing/critical paths
- `get_utilization` - Get resource utilization (LUTs, FFs, BRAMs, DSPs)
- `get_clocks` - Get clock information
- `get_messages` - Get synthesis/implementation messages

### Design Queries
- `get_design_hierarchy` - Get module/instance hierarchy
- `get_ports` - Get top-level ports
- `get_nets` - Search for nets
- `get_cells` - Search for cells/instances

### Simulation
- `launch_simulation` - Launch behavioral/post-synth/post-impl simulation
- `run_simulation` - Run simulation for specified time
- `restart_simulation` - Restart from time 0
- `close_simulation` - Close the simulator
- `get_simulation_time` - Get current simulation time
- `get_signal_value` - Get a signal's current value
- `get_signal_values` - Get multiple signal values by pattern
- `add_signals_to_wave` - Add signals to waveform viewer
- `set_simulation_top` - Set the testbench module
- `get_simulation_objects` - List signals in a scope
- `get_scopes` - List hierarchy scopes
- `step_simulation` - Step simulation
- `add_breakpoint` - Add signal breakpoint
- `remove_breakpoints` - Remove all breakpoints

### Block Design (IP Integrator) — Zynq / AXI
- `create_block_design` - Create a new block design and make it current
- `save_bd_design` / `close_bd_design` - Persist or close the BD
- `list_bd_cells` - List cells in the current BD
- `add_ip_to_bd` - Add an IP core (VLNV) and apply `CONFIG.*` properties
- `connect_bd_net` / `connect_bd_intf_net` - Wire scalar / AXI pins
- `auto_connect_axi` - `apply_bd_automation` for AXI master ↔ slave
- `apply_ps7_preset` - Apply Zynq PS7 board automation (FIXED_IO/DDR/clocks)
- `validate_block_design` - Run DRC on the BD
- `assign_bd_address` - Auto-assign AXI address ranges
- `regenerate_bd_layout` - Refresh BD layout before save
- `generate_bd_wrapper` - `make_wrapper` + add to fileset + set as top

### IP Catalog
- `create_ip` - Create an IP from the Xilinx catalog
- `configure_ip` - Apply `CONFIG.*` to an existing IP
- `generate_ip_target` - Generate synth/simulation output products
- `synth_ip` - Out-of-context synthesis
- `upgrade_ip` - Upgrade IP to latest catalog version
- `report_ip_status` - Audit IP versions in the project

### Hardware Manager (JTAG programming)
- `open_hw_manager` / `close_hw_manager` - Manage HW manager lifecycle
- `connect_hw_server` - Connect to `hw_server` (default localhost:3121)
- `program_device` - Program a `.bit` via the JTAG chain
- `refresh_hw_device` - Re-read JTAG chain state

### Advanced Reports
- `report_power` - Parsed total/dynamic/static power
- `report_drc` - Structured DRC violations grouped by severity
- `report_methodology` - UltraFast methodology checks
- `report_qor_assessment` - Overall QoR score
- `report_clock_interaction` - Cross-clock paths analysis

### RedPitaya PS+PL flow
Build full Processing System + Programmable Logic designs by reusing the canonical
RedPitaya-FPGA backbone (the `systemZ10.tcl` PS7 block design) instead of
reconfiguring the Zynq PS7 from scratch. See `get_vivado_doc redpitaya_ps_pl_flow`.
- `rp_setup_workspace` - Copy a RedPitaya-FPGA repo into an isolated build workspace
- `rp_list_projects` - List `prj/*` projects, flag Z10-capable ones
- `rp_workspace_info` - Report workspace state and which projects are built
- `rp_create_custom_project` - Clone a base project for custom PL logic
- `rp_build_project` - Build a PS+PL project end-to-end (setup → synth → impl →
  bitstream → `.bit.bin`)

### Red Pitaya deploy (SSH)
Push a built bitstream to a live board and run shell commands on it — no Vivado
session required.
- `deploy_to_redpitaya` - SFTP a `.bit.bin` to the board and load it via
  `xdevcfg` (OS 1.04) or `fpgautil` (OS 2.00). Default factory creds `root`/`root`.
- `ssh_redpitaya_exec` - Run an arbitrary command on the Red Pitaya over SSH

### Documentation (offline)
- `list_vivado_docs` - List bundled Vivado documentation topics
- `get_vivado_doc` - Read a topic markdown (`block_design`, `ps7_zynq`,
  `timing_constraints`, `synthesis_strategies`, `simulation_xsim`,
  `red_pitaya_125_14`, `redpitaya_ps_pl_flow`, `tcl_quoting`, `hw_manager`,
  `ip_integrator`, `pitfalls_2020_1`). Each topic embeds the upstream AMD UG URL.

### Advanced
- `run_tcl` / `run_tcl_script` - Execute raw TCL command or source a script
- `generate_full_report` - Generate full reports to file
- `read_report_section` - Read portions of large reports
- `load_board_xdc` - Resolve a bundled board XDC and add to constraints
- `request_feature` - Request new features
- `list_feature_requests` - List submitted requests

## Architecture

```
┌─────────────────┐     MCP Protocol      ┌─────────────────┐
│   Claude Code   │◄────(JSON-RPC)────────►│  Vivado MCP     │
│   (AI Client)   │     over stdio        │    Server       │
└─────────────────┘                       └────────┬────────┘
                                                   │
                                                   │ pexpect
                                                   │ (TCL commands)
                                                   ▼
                                          ┌─────────────────┐
                                          │ Vivado Process  │
                                          │  (TCL mode)     │
                                          └─────────────────┘
```

The server maintains a persistent Vivado process in TCL mode. Commands are sent via pexpect and output is captured by waiting for the Vivado prompt. This avoids the ~30 second startup overhead that would occur if Vivado were launched for each command.

For the design conventions (tool registry pattern, the two Red Pitaya build flows,
Vivado TCL quoting pitfalls), see [`CLAUDE.md`](CLAUDE.md).

## Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Forked from [coreyhahn/vivado_mcp](https://github.com/coreyhahn/vivado_mcp) (MIT)
- Red Pitaya flows build on the [RedPitaya/RedPitaya-FPGA](https://github.com/RedPitaya/RedPitaya-FPGA) backbone
- Developed with [Claude](https://claude.ai) (Anthropic)
- Uses the [Model Context Protocol](https://modelcontextprotocol.io) specification
- Integrates with [AMD/Xilinx Vivado](https://www.xilinx.com/products/design-tools/vivado.html)
