# Timing constraints (XDC) — Vivado 2020.1

Upstream:
- UG903 (Using Constraints) — https://docs.amd.com/v/u/2020.1-English/ug903-vivado-using-constraints
- UG949 (UltraFast Design Methodology) — https://www.xilinx.com/support/documentation/sw_manuals/xilinx2020_1/ug949-vivado-design-methodology.pdf

## Order of operations

XDC files inside `constrs_1` are sourced in order. Vivado applies them during
`synth_design` (early/elaboration constraints) and again after `place_design`
(timing exceptions). Mark constraints that are only valid post-synth with
`-quiet` or split them into separate files.

## Clock definitions

```tcl
# Primary clock on input port `clk_p` (125 MHz LVDS, period 8 ns)
create_clock -name adc_clk -period 8.000 [get_ports adc_clk_p]

# Generated clock from MMCM/PLL output (Vivado usually infers these)
create_generated_clock -name fclk_50 \
  -source [get_pins mmcm/CLKIN1] \
  -divide_by 2 [get_pins mmcm/CLKOUT0]

# Virtual clock for IO constraints
create_clock -name virt_adc -period 8.000
```

## I/O constraints

```tcl
# Setup/hold the upstream device imposes on adc_data
set_input_delay -clock virt_adc -max 2.5 [get_ports adc_data*]
set_input_delay -clock virt_adc -min 0.5 [get_ports adc_data*]

# Output skew at DAC pins
set_output_delay -clock virt_dac -max 2.0 [get_ports dac_data*]
set_output_delay -clock virt_dac -min -0.5 [get_ports dac_data*]
```

## Exceptions

```tcl
# Async reset never needs to meet timing
set_false_path -from [get_pins rst_reg/C] -to [all_registers]

# CDC handshake — relaxed by N cycles
set_multicycle_path -setup 2 -from [get_clocks src_clk] -to [get_clocks dst_clk]
set_multicycle_path -hold  1 -from [get_clocks src_clk] -to [get_clocks dst_clk]

# Block timing analysis on dedicated CDC FIFO
set_false_path -through [get_pins cdc_fifo/wr_data*]
```

## Physical / pin constraints

```tcl
set_property PACKAGE_PIN N20  [get_ports led_o[0]]
set_property IOSTANDARD LVCMOS33 [get_ports led_o[0]]
set_property SLEW SLOW [get_ports led_o[0]]
set_property DRIVE 4 [get_ports led_o[0]]
```

For LVDS pairs Vivado wants both halves explicit:

```tcl
set_property PACKAGE_PIN U18 [get_ports adc_clk_p]
set_property PACKAGE_PIN U19 [get_ports adc_clk_n]
set_property IOSTANDARD LVDS_25 [get_ports {adc_clk_p adc_clk_n}]
set_property DIFF_TERM TRUE [get_ports {adc_clk_p adc_clk_n}]
```

## Useful query commands

```tcl
report_clocks
report_clock_networks
report_clock_interaction -delay_type min_max
get_clocks
get_property PERIOD [get_clocks adc_clk]
```

## Pitfalls

- `create_clock -period 8` (no `.000`) is fine — Vivado parses both, but mixing units (`8000ps`) inside the same XDC trips lint.
- Constraints with `[get_pins ...]` evaluated during synthesis can return empty lists if names changed during synth optimization. Wrap in `-quiet` or move to post-synth.
- `set_input_delay -clock <real_clock>` constrains relative to the launching FF clock domain. For source-synchronous I/O always create a virtual clock that mirrors the data clock and reference that.
- `set_false_path` between all clock pairs (`set_false_path -from [all_clocks] -to [all_clocks]`) silences EVERYTHING — never use it.
