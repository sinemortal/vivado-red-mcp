# Vivado 2020.1 — pitfalls & quirks

Scripting around Vivado 2020.1 on a Red Pitaya / Zynq workflow. Most of these
items still apply to 2022.x/2023.x but their workarounds may differ.

## Run isolation

Spawned runs (`launch_runs`) execute in a **fresh Tcl interpreter**. Variables
set in the parent shell are NOT visible inside synth_design / opt_design /
place_design / route_design.

To inject Tcl into a step, use the per-step properties:

```tcl
set_property STEPS.SYNTH_DESIGN.TCL.PRE  /path/to/pre_synth.tcl  [get_runs synth_1]
set_property STEPS.SYNTH_DESIGN.TCL.POST /path/to/post_synth.tcl [get_runs synth_1]
set_property STEPS.PLACE_DESIGN.TCL.POST /path/to/post_place.tcl [get_runs impl_1]
set_property STEPS.ROUTE_DESIGN.TCL.POST /path/to/post_route.tcl [get_runs impl_1]
```

Common use cases: custom `read_xdc` ordering, sourcing a write_bitstream.tcl
that produces both .bit and .bit.bin in one impl run.

## `wait_on_run` vs `wait_on_runs`

Both exist in 2020.1. Prefer `wait_on_run <single>` for clarity. Chain stages
with `-to_step`:

```tcl
launch_runs impl_1 -to_step write_bitstream
wait_on_run impl_1
```

This avoids the "launch impl, wait, then launch generate_bitstream, wait
again" double-pass.

## `current_bd_design` is mandatory

After `open_bd_design <file>` you MUST `current_bd_design [get_bd_designs <name>]`
before any `get_bd_cells` / `connect_bd_*` calls. Most failures with
`ERROR: [BD 41-237] No open Block Design` trace back to this.

## `make_wrapper` doesn't add the file

`make_wrapper -files [get_files my.bd] -top` writes a Verilog/VHDL wrapper to
`<proj>/<proj>.srcs/sources_1/bd/<name>/hdl/`. It does NOT add the file to
sources_1 and does NOT set it as top. Two more commands required:

```tcl
add_files -norecurse <wrapper_path>
set_property top <name>_wrapper [current_fileset]
update_compile_order -fileset sources_1
```

## Report column drift

`report_utilization` (and friends) format their tables differently across
Vivado versions. Never rely on column positions — match by header keywords.
The bundled `parse_utilization` accepts both `Slice LUTs` (7-series) and
`CLB LUTs` (UltraScale+) for the same row.

## Tcl quoting traps

See `tcl_quoting.md`. Top three:
1. `{path with spaces}` — braces don't expand `$var`. Use them for paths.
2. `set_property -dict {KEY VAL KEY VAL}` — needs braces, not quotes.
3. `puts {hello $name}` prints `hello $name` literally, not the variable.

## Memory ceiling for `-jobs`

Vivado's parallel impl can OOM on 16 GB hosts for designs >100k LUTs. Cap
jobs at 4 on workstations, 8 on dedicated build hosts.

## Output parsing for run success

Don't grep the run's stdout for "ERROR"; report tables and synth banners
contain that string in benign contexts (`Timing ERROR: 0`). Always verify
via the property:

```tcl
get_property STATUS [get_runs synth_1]
# Expected: "synth_design Complete!" or "Not started"
```

The MCP server's `verify_run_status()` already does this.

## `psutil` requirement

The `get_host_status` tool needs `psutil`. It's pinned in pyproject.toml,
but if you build from a tarball without deps don't be surprised when
`get_host_status` raises ImportError.

## Vivado 2020.1 on modern glibc

If you're on Linux glibc ≥ 2.34, Vivado 2020.1 may fail to load
`libpng12.so.0`. Symlink the system `libpng16.so.16` to it, or install the
EPEL `compat-libpng` package. See AMD AR# 73276.

## Block Design IP version drift

If you save a BD in 2020.1 and reopen in 2020.2+, Vivado pops "IP upgrade
required" for every cell. Either upgrade everything (`upgrade_ip`) or pin the
BD to specific IP versions via `set_property IS_LOCKED TRUE`.

## Paths with spaces — three commands need special care

Vivado 2020.1 has inconsistent argument parsing across commands:

1. **`add_files`** ignores plain Tcl braces on its file args. Wrap the file list in `[list ...]`:
   ```tcl
   # WRONG: splits on the space in "FPGA MCP"
   add_files -fileset sources_1 {C:/foo/FPGA MCP/file.v}
   # CORRECT:
   add_files -fileset sources_1 [list {C:/foo/FPGA MCP/file.v}]
   ```
2. **`set_property -name {PROP WITH SPACE} -value {V}`** requires the explicit `-objects` flag before the target list, otherwise Vivado claims `'-name' specified twice`:
   ```tcl
   set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} \
     -value {-bufg 16} -objects [get_runs synth_1]
   ```
3. **`write_cfgmem -loadbit "up 0x0 <path>"`** has a custom value parser that splits on whitespace inside the quotes, ignoring Tcl braces entirely. The only reliable workaround is to `cd` to the .bit's directory and pass a relative filename:
   ```tcl
   cd {C:/foo/FPGA MCP/run/}
   write_cfgmem -force -format bin -interface smapx32 \
     -disablebitswap -loadbit "up 0x0 design.bit" design.bit.bin
   ```

## Red Pitaya cfgmem nuances

`write_cfgmem -format bin -interface smapx32 -disablebitswap` produces the
raw stream the PCAP loader wants. Forget `-disablebitswap` and the kernel
loader will appear to succeed but the bitstream produces garbage outputs.
