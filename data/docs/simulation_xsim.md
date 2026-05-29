# Simulation with xsim — Vivado 2020.1

Upstream:
- UG900 (Logic Simulation) — https://docs.amd.com/v/u/2020.1-English/ug900-vivado-logic-simulation
- UG937 (Design Suite Tutorial: Logic Simulation)

## Modes

```tcl
launch_simulation -mode behavioral             ;# RTL
launch_simulation -mode post-synthesis -type functional
launch_simulation -mode post-synthesis -type timing
launch_simulation -mode post-implementation -type functional
launch_simulation -mode post-implementation -type timing
```

Behavioral is the only mode that doesn't require synth/impl artifacts.

## Setting up a testbench

```tcl
set_property top tb_top [get_filesets sim_1]
set_property top_lib xil_defaultlib [get_filesets sim_1]
add_files -fileset sim_1 [list /path/to/tb_top.v /path/to/stimuli.v]
update_compile_order -fileset sim_1
```

For SystemVerilog UVM:
```tcl
set_property -name {xsim.compile.xvlog.more_options} \
  -value {-sv -L uvm} [get_filesets sim_1]
```

## Running

```tcl
run 1us          ;# advance 1 microsecond
run -all         ;# until $finish
restart          ;# back to time 0
close_sim
```

## Probing values

```tcl
get_value -radix hex /tb/dut/data_out
get_objects -filter {TYPE == signal} /tb/dut/*
log_wave -recursive *           ;# log everything (huge WDB!)
add_wave /tb/dut/state
```

`get_value` returns the current simulated value as a string. Use `-radix bin|hex|dec|unsigned|ascii`.

## Breakpoints

```tcl
add_bp -posedge /tb/dut/error_flag
add_bp -negedge /tb/clk
remove_bps -all
```

## SAIF for power simulation

```tcl
open_saif /tmp/run.saif
log_saif [get_objects /tb/dut/*]
run -all
close_saif
```

Feed `report_power -input /tmp/run.saif` to get a SAIF-driven power estimate.

## Pitfalls

- `launch_simulation` looks at the *current* simulation set (`sim_1`). If your tb is in a different fileset, set `current_fileset` first.
- xsim is slow on >100k events/s designs; for heavy sim consider exporting to ModelSim/Questa via `export_simulation -simulator questa`.
- `$display` output goes to the xsim console — read via `get_msg_config -count -severity {INFO}` or by redirecting xsim stdout when running outside Vivado.
- After `restart`, all `add_wave` entries are kept, but probes added with `log_wave` are not — re-log them.
