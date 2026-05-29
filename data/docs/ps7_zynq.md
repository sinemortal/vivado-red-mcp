# Zynq-7000 PS7 configuration — Red Pitaya and similar

Upstream references:
- UG585 (Zynq-7000 SoC Technical Reference Manual) — https://docs.amd.com/v/u/en-US/ug585-Zynq-7000-TRM
- UG994 §"Re-Customize Processing System for Zynq Devices" — https://docs.amd.com/v/u/2020.1-English/ug994-vivado-ip-subsystems
- UG908 (Programming & Debugging)

## What "PS7" means

The Zynq-7000 has a hard ARM Cortex-A9 dual-core in the **Processing System
(PS)**, exposed to the **Programmable Logic (PL)** through:

- 4 AXI HP (high-performance, master from PL to DDR) ports
- 2 AXI GP (general-purpose master/slave) ports
- 1 AXI ACP (cache-coherent) port
- 4 FCLK programmable clocks from PS to PL (`FCLK_CLK0..3`)
- 4 FCLK_RESET_N synchronous reset outputs
- IRQ_F2P / IRQ_P2F lines

The `processing_system7` IP block represents PS7 and exposes those interfaces
to the block design. The MIO pins (peripherals routed to package pins via PS)
are *not* user-controllable — they are baked into the silicon and routed
through dedicated pads on the package.

## Board-preset path

If a board file ships (`<install>/data/boards/board_files/...`):

```tcl
set_property board_part redpitaya.com:stemlab125_14:part0:1.0 [current_project]
create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 processing_system7_0
apply_bd_automation \
  -rule xilinx.com:bd_rule:processing_system7 \
  -config { make_external "FIXED_IO, DDR" apply_board_preset 1 } \
  [get_bd_cells processing_system7_0]
```

`apply_board_preset 1` sets DDR controller parameters, clock frequencies,
MIO assignments, and ENABLES the peripherals the board exposes. Without a
board preset you must set ~50 CONFIG.PCW_* properties manually.

## Manual config (when no board file)

Essentials when crafting `set_property -dict {...} [get_bd_cells processing_system7_0]`:

- `CONFIG.PCW_USE_M_AXI_GP0 1` — enable AXI GP0 master (PS→PL register access).
- `CONFIG.PCW_USE_S_AXI_HP0 1` — enable AXI HP0 slave (PL→DDR DMA).
- `CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ 50` — FCLK_CLK0 target in MHz.
- `CONFIG.PCW_EN_CLK0_PORT 1` — must be paired with PCW_FPGAn_PERIPHERAL_FREQMHZ.
- `CONFIG.PCW_FCLK_CLK0_BUF TRUE` — BUFG on FCLK_CLK0.
- `CONFIG.PCW_USE_FABRIC_INTERRUPT 1` + `CONFIG.PCW_IRQ_F2P_INTR 1` — PL→PS IRQs.

## Red Pitaya STEMlab 125-14 specifics

- xc7z010clg400-1 (Zynq 7010, dual A9 @ 666 MHz, 28 nm).
- DDR3 256 MB on PS DDR controller (settings: 533 MHz, 16-bit width, MT41K128M16JT-125).
- 125 MHz differential LVDS clock from the ADC drives an MMCM in the PL — **not** the PS FCLK. PS FCLK can still be used for control logic.
- ADC LVDS DDR (LVDS_25 or HSTL_18) must use ISERDESE2 + IDELAYE2 with proper IDELAYCTRL refclk (200 MHz typical).
- The canonical Red Pitaya repo (`RedPitaya/RedPitaya-FPGA`) bundles the board file under `cfg/`. You can either install it into Vivado or skip the board preset and configure PCW_* manually.

## Pitfalls

- Setting `PCW_FPGA0_PERIPHERAL_FREQMHZ` alone does nothing — `PCW_EN_CLK0_PORT` must be 1 in the same `set_property` call.
- `apply_board_preset 1` overrides previous PCW_* settings. Apply preset FIRST, then layer custom overrides on top.
- DDR pins are FIXED_IO and won't appear as routable pins. Don't try to constrain them in XDC.
- The PS7 has no reset input — it self-resets via PS_RESET (driven by the on-board reset chip).
