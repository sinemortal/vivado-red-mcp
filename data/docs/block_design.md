# Block Design (IP Integrator) — Vivado 2020.1

Upstream references:
- UG994 (Vivado Design Suite User Guide: Designing IP Subsystems Using IP Integrator) — https://docs.amd.com/v/u/2020.1-English/ug994-vivado-ip-subsystems
- UG895 (Design Suite User Guide: System-Level Design Entry) — https://docs.amd.com/v/u/2020.1-English/ug895-vivado-system-level-design-entry
- UG835 (Tcl Command Reference) — https://www.xilinx.com/content/dam/xilinx/support/documents/sw_manuals/xilinx2020_1/ug835-vivado-tcl-commands.pdf

## Mental model

A *block design* (`.bd`) is a graph of IP cells with typed ports (scalar pins,
AXI4 interface pins, clocks, resets, AXI Streams). Vivado stores it as Tcl
source. The typical flow:

1. `create_bd_design <name>` — creates the .bd and the in-memory design.
2. `current_bd_design [get_bd_designs <name>]` — make it the active one.
3. `create_bd_cell -type ip -vlnv <vlnv> <inst>` — instantiate an IP.
4. `set_property -dict {CONFIG.KEY VAL ...} [get_bd_cells <inst>]` — configure.
5. `connect_bd_net` (scalar) / `connect_bd_intf_net` (interface).
6. `apply_bd_automation` for board-aware wiring (PS7 FIXED_IO/DDR, AXI fabrics).
7. `validate_bd_design` — DRC.
8. `save_bd_design`.
9. `make_wrapper -files [get_files <name>.bd] -top` then `add_files -norecurse <wrapper>` and `set_property top <name>_wrapper [current_fileset]`.

## VLNV format

Every IP is identified by `vendor:library:name:version`. The version field is
optional in `create_bd_cell` — omit it and Vivado picks the newest installed.
Common Zynq-7000 entries:

| IP | VLNV |
|---|---|
| Processing System 7 | `xilinx.com:ip:processing_system7:5.5` |
| AXI Interconnect | `xilinx.com:ip:axi_interconnect:2.1` |
| AXI GPIO | `xilinx.com:ip:axi_gpio:2.0` |
| Clocking Wizard | `xilinx.com:ip:clk_wiz:6.0` |
| AXI Timer | `xilinx.com:ip:axi_timer:2.0` |
| AXI BRAM Controller | `xilinx.com:ip:axi_bram_ctrl:4.1` |
| Concat (xlconcat) | `xilinx.com:ip:xlconcat:2.1` |
| Constant (xlconstant) | `xilinx.com:ip:xlconstant:1.1` |
| AXI Stream FIFO | `xilinx.com:ip:axi_fifo_mm_s:4.2` |

## Connecting pins

- `connect_bd_net [get_bd_pins ps/FCLK_CLK0] [get_bd_pins gpio/s_axi_aclk]`
- `connect_bd_intf_net [get_bd_intf_pins ps/M_AXI_GP0] [get_bd_intf_pins gpio/S_AXI]` — but prefer `apply_bd_automation` for AXI: it inserts an AXI Interconnect and ties clocks/resets automatically.
- External port: `make_bd_pins_external [get_bd_pins gpio/gpio_io_o]` (creates a top-level pin named `gpio_io_o_0`).

## `apply_bd_automation`

Two rules dominate for Zynq + AXI:

```tcl
apply_bd_automation -rule xilinx.com:bd_rule:processing_system7 \
  -config { make_external "FIXED_IO, DDR" apply_board_preset 1 } \
  [get_bd_cells processing_system7_0]

apply_bd_automation -rule xilinx.com:bd_rule:axi4 \
  -config { Master "/processing_system7_0/M_AXI_GP0" Slave "/axi_gpio_0/S_AXI" \
            Clk_master "Auto" Clk_slave "Auto" Clk_xbar "Auto" } \
  [get_bd_intf_pins axi_gpio_0/S_AXI]
```

`apply_board_preset 1` requires the board files installed (Vivado → `set_property board_part …`).

## Validate + wrapper

`validate_bd_design` returns non-zero only on hard ERRORs. CRITICAL WARNINGS
(e.g. unassigned address ranges) leave the design "valid" but typically you
should `assign_bd_address` and re-validate.

`make_wrapper` writes the HDL wrapper to `<proj>/<proj>.srcs/sources_1/bd/<name>/hdl/<name>_wrapper.v` (or `.vhd`). It does **not** add the file to the project — you must call `add_files -norecurse` and `set_property top` yourself.

## Pitfalls (2020.1 specific)

- `current_bd_design` must be set before nearly every `*_bd_*` query. After `open_bd_design <file>` Vivado does NOT auto-make it current.
- `set_property -dict` requires the value list in **braces**, not quotes: `{CONFIG.X 1 CONFIG.Y abc}`. Quoted strings get `$var`-expanded.
- The PS7 cell name must be unique; Vivado-managed scripts assume `processing_system7_0`. Renaming breaks `apply_bd_automation` rule lookups.
- `make_wrapper` returns paths with forward slashes even on Windows; use `{path}` braces when reusing them in Tcl.
