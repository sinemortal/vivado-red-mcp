# Red Pitaya STEMlab 125-14 — FPGA flow

Upstream:
- Red Pitaya FPGA repo: https://github.com/RedPitaya/RedPitaya-FPGA
- Canonical Z10 build: https://github.com/RedPitaya/RedPitaya-FPGA/blob/master/red_pitaya_vivado_Z10.tcl
- Project mode entry: https://github.com/RedPitaya/RedPitaya-FPGA/blob/master/red_pitaya_vivado_project_Z10.tcl
- Hardware docs: https://redpitaya.readthedocs.io/en/latest/developerGuide/hardware/125-14/top.html

## Board summary

- **Part**: `xc7z010clg400-1` (Zynq 7010, dual Cortex-A9 @ 666 MHz, 28 nm Artix-7 PL).
- **Clocks**: 125 MHz LVDS_25 differential from the LTC2145-14 ADC into PL pins `U18/U19`. Drives MMCM/PLL for ADC capture + user PL.
- **ADC**: LTC2145-14, dual-channel 14-bit @ 125 MS/s, LVDS DDR output. Needs ISERDESE2 + IDELAYE2; IDELAYCTRL refclk = 200 MHz (synthesized from the 125 MHz via MMCM).
- **DAC**: AD9767, dual-channel 14-bit @ up to 125 MS/s. SDR LVCMOS25, separate clock from DAC PLL.
- **DDR**: PS-side, 256 MB MT41K128M16JT-125 (DDR3-1066, 16-bit). Configured by PS7 board preset.
- **Connectors**: 16 GPIO on E1/E2 (3.3V LVCMOS), 8 user LEDs, XADC analog (P12/N12 differential), daisy-chain pins, PMOD-like extras on E2.

## Deploy path (no Xilinx cable required)

```bash
scp my_design.bit.bin root@<rp-ip>:/tmp/
ssh root@<rp-ip> 'cat /tmp/my_design.bit.bin > /dev/xdevcfg'
```

The Red Pitaya OS exposes `/dev/xdevcfg` as a sysfs interface to the PCAP
bitstream loader inside the PS. The file must be a **raw binary** (no .bit
header), which is what `write_cfgmem -format bin -interface smapx32 -disablebitswap` produces.

## Canonical synth flags

```tcl
set_property -name {STEPS.SYNTH_DESIGN.ARGS.MORE OPTIONS} \
  -value {-flatten_hierarchy none -bufg 16 -keep_equivalent_registers} \
  [get_runs synth_1]
```

- `-flatten_hierarchy none` keeps the original RTL hierarchy so reports stay readable (cost: a few % QoR).
- `-bufg 16` caps BUFG usage at 16 to leave room for clock_wizard generated clocks.
- `-keep_equivalent_registers` disables register replication for reproducible builds.

## Bundled XDC variants in this server

| Variant | What's inside |
|---|---|
| `leds_min` | 125 MHz LVDS clock + 8 user LEDs only. Use for hello-world projects. |
| `full` | Full peripheral pinout: ADC (clock + 28 LVDS data + OE), DAC (14 data + clk + rst + sel + wrt), PWM (4 channels), XADC analog, E1/E2 expansion (16 pins), daisy-chain TX/RX. |

Paths returned by `get_board_info` are absolute and ready to pass to
`add_constraints`.

## Useful constraints (already in `red_pitaya_125_14_full.xdc`)

```tcl
# Primary 125 MHz LVDS clock
create_clock -name adc_clk -period 8.000 [get_ports adc_clk_p]
set_property IOSTANDARD LVDS_25 [get_ports {adc_clk_p adc_clk_n}]
set_property DIFF_TERM TRUE [get_ports {adc_clk_p adc_clk_n}]

# ADC DDR data — needs ISERDESE2
set_property IOSTANDARD LVDS_25 [get_ports {adc_dat_a_p[*] adc_dat_a_n[*]}]
set_property DIFF_TERM TRUE     [get_ports {adc_dat_a_p[*] adc_dat_a_n[*]}]
```

## Pitfalls specific to Red Pitaya

- ADC samples on **both edges** of the 125 MHz LVDS clock (DDR). Inside the FPGA you usually convert to 250 MHz single-data-rate via `ISERDESE2 -interface_type NETWORKING`. Skipping this gives garbage data.
- DAC is **straight** binary (offset binary). If the ADC is 2's complement, conversion is needed before sending samples out.
- The 200 MHz refclk for `IDELAYCTRL` must be driven by a BUFG; running it from the MMCM directly with no BUFG fails DRC.
- Vivado will fail synth if `adc_dat_a_p[*]` has no DIFF_TERM and you're driving LVDS_25 inputs (`set_property DIFF_TERM TRUE` is mandatory for LVDS_25 in the 7010).
- The on-board 8 LEDs are 3.3V active-high. `set_property IOSTANDARD LVCMOS33` and avoid `SLEW FAST` to prevent EMI.
