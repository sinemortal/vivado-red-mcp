# RedPitaya PS+PL build flow

How the Vivado MCP server builds full **Processing System + Programmable Logic**
designs for the Red Pitaya STEMlab 125-14 (Zynq xc7z010), by reusing the canonical
RedPitaya-FPGA backbone instead of rebuilding the PS7 from scratch.

Upstream:
- RedPitaya-FPGA repo: https://github.com/RedPitaya/RedPitaya-FPGA
- See also `ps7_zynq.md`, `block_design.md` in this doc set.

## Why not build the PS7 from scratch

The Zynq PS7 needs ~100 `CONFIG.PCW_*` properties set exactly right: DDR3 part and
timing, MIO pin assignments (ethernet, UART, SD, USB, I2C), PLL/clock config. Getting
any of these wrong means the board won't boot Linux or DDR fails.

RedPitaya already solved this. Their repo ships `prj/<name>/ip/system.tcl` (legacy
repos: `systemZ10.tcl`) — a `write_bd_tcl` export of a fully-configured,
board-validated PS7 block design. The build script `source`s it verbatim. **That file
is the backbone — known-good.**

## Repo layouts

| | Current upstream `master` | Legacy |
|---|---|---|
| Target Vivado | 2025.1 | 2020.1 |
| Setup script | `red_pitaya_vivado_Z10.tcl` (full build; `DEV_MODE` stops after setup) | `red_pitaya_vivado_project_Z10.tcl` (setup only) |
| Block design | `prj/<name>/ip/system.tcl`, parametrised by the setup script | `prj/<name>/ip/systemZ10.tcl` |
| Vivado project | `prj/<name>/build/redpitaya.xpr` | `prj/<name>/project/redpitaya.xpr` |

`rp_build_project` detects the layout automatically.

### Workspace patches

`rp_setup_workspace` (and `rp_build_project`, for older workspaces) patch the
**workspace copy** — never the source checkout — so the upstream scripts run on the
installed Vivado:

- `set scripts_vivado_version 2025.1` → `[version -short]`, in every `.tcl` of the
  workspace. `write_bd_tcl` (`prj/*/ip/system.tcl`) and `write_ip_tcl`
  (`ip/ip/*/*.tcl`) exports abort on any other Vivado release. The script still checks that every IP VLNV it
  needs exists in the catalog, so a real incompatibility is still reported.
- `set gith [exec git log ...]` → falls back to an all-zero hash. The workspace comes
  from a zip download, not a git clone, so `git log` fails.

## Two flows in this server

| Tool | Use case | PS7? |
|---|---|---|
| `create_redpitaya_project_rtl` | Pure RTL design (LED blinker, counters) driven by the 125 MHz ADC clock. PL only. | No |
| `rp_build_project` | Full PS+PL — ARM + DDR + custom PL logic. Uses the RedPitaya backbone. | Yes |

## The RedPitaya project-mode flow

The setup script (in the repo root) does:

1. `cd prj/<name>`
2. `set_param board.repoPaths [list ../../brd]` — register the Red Pitaya board file
3. `create_project -part xc7z010clg400-1 -force redpitaya ./build` (legacy: `./project`)
4. `set_property verilog_define {Z10 ...}`
5. set globals: `gpio_width 24`, `hp0/1/2/3_clk_freq`
6. `source ip/system.tcl` (legacy: `ip/systemZ10.tcl`) → builds the `system` block design with the PS7
   (DDR3 533 MHz 16-bit, MIO ethernet/UART/SD/USB/I2C, FCLK 125/250/50/200,
   M_AXI_GP0+GP1, EMIO GPIO 24-bit)
7. `generate_target all [get_files system.bd]`
8. `add_files` for RTL (`../../rtl` + project `rtl/`), the BD HDL, and `*.xci`
9. `add_files -fileset constrs_1` for `../../sdc/red_pitaya.xdc` + project `sdc/`
10. `import_files -force; set_property top red_pitaya_top; update_compile_order`
11. **stops** — synthesis/implementation run afterwards

Relative paths (`../../rtl`, `../../sdc`, `../../brd`, `../../ip`) resolve against
`prj/<name>` — so the whole repo tree must be present. That is why `rp_setup_workspace`
copies the entire repo into an isolated workspace.

## MCP tool sequence

```
start_session
rp_setup_workspace   repo_path=<RedPitaya-FPGA checkout>
rp_list_projects     path=<workspace>
rp_build_project     workspace_path=<workspace> project=v0.94
```

`rp_build_project` internally:
- `cd` workspace, sets `argv`/`argc` (adding `DEV_MODE` for the current layout),
  `source`s the setup script
- `launch_runs synth_1` / `impl_1 -to_step write_bitstream` / `wait_on_run`
- `write_cfgmem` → `.bit.bin`

Outputs:
- `.xpr`: `<workspace>/prj/<project>/build/redpitaya.xpr` (legacy: `project/`; openable in the GUI)
- `.bit`: `<workspace>/prj/<project>/build/redpitaya.runs/impl_1/red_pitaya_top.bit`
- `.bit.bin`: alongside the `.bit`

## Adding custom PL logic

`red_pitaya_top.sv` is the integration layer — it instantiates `system system_i`
(the PS7 wrapper) and connects PL application modules. For `barebones` it is 67 lines:
just FIXED_IO + DDR passthrough. The custom-logic flow:

```
rp_create_custom_project workspace_path=<ws> base_project=v0.94 name=my_design
# -> edit prj/my_design/rtl/red_pitaya_top.sv, add custom RTL files
rp_build_project         workspace_path=<ws> project=my_design
```

The PS7 is never touched — it always comes from the repo's block design TCL. Custom logic is PL:
- talk to the ARM via `M_AXI_GP0` (memory-mapped registers), or
- via `EMIO GPIO` (24-bit, simplest), or
- stream to DDR via `S_AXI_HP*` ports.

## Pitfalls

- The workspace must contain the FULL repo tree — `rp_setup_workspace` copies it; do
  not point `rp_build_project` at a partial copy.
- The setup script reads `argv` — `rp_build_project` sets `argv`/`argc`
  before `source` (the plain `run_tcl_script` tool does not).
- Builds run inside the workspace; the pristine Downloads checkout stays untouched.
- v0.94 is the full STEMlab design — synth+impl on the xc7z010 takes ~20-40 min.
  `barebones` (pure PS7) is the fast smoke test (~3-5 min).
- Only the Z10 model is wired up. Z20 / Z20-250 are out of scope.
