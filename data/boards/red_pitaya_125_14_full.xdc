###############################################################################
# Red Pitaya STEMlab 125-14 — full peripheral pinout
#
# Target: Xilinx Zynq xc7z010clg400-1
# Source: RedPitaya/RedPitaya-FPGA, sdc/red_pitaya.xdc (Matej Oblak, 2014)
#   https://github.com/RedPitaya/RedPitaya-FPGA/blob/master/sdc/red_pitaya.xdc
#
# Redistributed under the 3-clause BSD license (see THIRD-PARTY-NOTICES.md):
#   Copyright (c) 2014, Red Pitaya, d.o.o.  All rights reserved.
#
# Bundled with vivado_red_mcp for use with `create_redpitaya_project_rtl`
# (xdc_variant="full"). Top-level port names match the official Red Pitaya
# reference design so user RTL can declare exactly the subset of ports it
# uses — Vivado will flag the unused ones as "no load" warnings (harmless).
#
# Covered:
#   - adc_clk_i / adc_clk_o / adc_cdcs_o  (125 MHz differential input)
#   - adc_dat_i[0..1][13:0]               (14-bit ADC data, 2 channels)
#   - dac_dat_o[13:0], dac_wrt_o, dac_sel_o, dac_clk_o, dac_rst_o
#   - dac_pwm_o[0..3]                     (4-ch PWM DAC)
#   - led_o[7:0]                          (F16 F17 G15 H15 K14 G14 J15 J14)
#   - exp_p_io[7:0], exp_n_io[7:0]        (E1/E2 expansion connector)
#   - daisy_p_o/n_o[1:0], daisy_p_i/n_i[1:0]  (SATA daisy-chain)
#   - vinp_i[4:0], vinn_i[4:0]            (XADC analog inputs)
###############################################################################

############# clocking
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports {adc_clk_i[*]}]
set_property PACKAGE_PIN U19 [get_ports {adc_clk_i[0]}]
set_property PACKAGE_PIN U18 [get_ports {adc_clk_i[1]}]

create_clock -period 8.000 -name adc_clk [get_ports {adc_clk_i[1]}]

set_property IOSTANDARD LVCMOS18 [get_ports {adc_clk_o[*]}]
set_property SLEW FAST            [get_ports {adc_clk_o[*]}]
set_property DRIVE 8              [get_ports {adc_clk_o[*]}]
set_property PACKAGE_PIN N20 [get_ports {adc_clk_o[0]}]
set_property PACKAGE_PIN P20 [get_ports {adc_clk_o[1]}]

set_property IOSTANDARD LVCMOS18 [get_ports adc_cdcs_o]
set_property SLEW FAST            [get_ports adc_cdcs_o]
set_property DRIVE 8              [get_ports adc_cdcs_o]
set_property PACKAGE_PIN V18     [get_ports adc_cdcs_o]

############# ADC data
set_property IOSTANDARD LVCMOS18 [get_ports {adc_dat_i[*][*]}]
set_property IOB TRUE            [get_ports {adc_dat_i[*][*]}]
# adc_dat_i[0] channel A, pins Y17..W14
set_property PACKAGE_PIN Y17 [get_ports {adc_dat_i[0][0]}]
set_property PACKAGE_PIN W16 [get_ports {adc_dat_i[0][1]}]
set_property PACKAGE_PIN Y16 [get_ports {adc_dat_i[0][2]}]
set_property PACKAGE_PIN W15 [get_ports {adc_dat_i[0][3]}]
set_property PACKAGE_PIN W14 [get_ports {adc_dat_i[0][4]}]
set_property PACKAGE_PIN Y14 [get_ports {adc_dat_i[0][5]}]
set_property PACKAGE_PIN W13 [get_ports {adc_dat_i[0][6]}]
set_property PACKAGE_PIN V12 [get_ports {adc_dat_i[0][7]}]
set_property PACKAGE_PIN V13 [get_ports {adc_dat_i[0][8]}]
set_property PACKAGE_PIN T14 [get_ports {adc_dat_i[0][9]}]
set_property PACKAGE_PIN T15 [get_ports {adc_dat_i[0][10]}]
set_property PACKAGE_PIN V15 [get_ports {adc_dat_i[0][11]}]
set_property PACKAGE_PIN T16 [get_ports {adc_dat_i[0][12]}]
set_property PACKAGE_PIN V16 [get_ports {adc_dat_i[0][13]}]
# adc_dat_i[1] channel B
set_property PACKAGE_PIN R18 [get_ports {adc_dat_i[1][0]}]
set_property PACKAGE_PIN P16 [get_ports {adc_dat_i[1][1]}]
set_property PACKAGE_PIN P18 [get_ports {adc_dat_i[1][2]}]
set_property PACKAGE_PIN N17 [get_ports {adc_dat_i[1][3]}]
set_property PACKAGE_PIN R19 [get_ports {adc_dat_i[1][4]}]
set_property PACKAGE_PIN T20 [get_ports {adc_dat_i[1][5]}]
set_property PACKAGE_PIN T19 [get_ports {adc_dat_i[1][6]}]
set_property PACKAGE_PIN U20 [get_ports {adc_dat_i[1][7]}]
set_property PACKAGE_PIN V20 [get_ports {adc_dat_i[1][8]}]
set_property PACKAGE_PIN W20 [get_ports {adc_dat_i[1][9]}]
set_property PACKAGE_PIN W19 [get_ports {adc_dat_i[1][10]}]
set_property PACKAGE_PIN Y19 [get_ports {adc_dat_i[1][11]}]
set_property PACKAGE_PIN W18 [get_ports {adc_dat_i[1][12]}]
set_property PACKAGE_PIN Y18 [get_ports {adc_dat_i[1][13]}]

set_input_delay -clock adc_clk 3.400 [get_ports {adc_dat_i[*][*]}]

############# DAC
set_property IOSTANDARD LVCMOS33 [get_ports {dac_dat_o[*]}]
set_property SLEW SLOW            [get_ports {dac_dat_o[*]}]
set_property DRIVE 8              [get_ports {dac_dat_o[*]}]
set_property PACKAGE_PIN M19 [get_ports {dac_dat_o[0]}]
set_property PACKAGE_PIN M20 [get_ports {dac_dat_o[1]}]
set_property PACKAGE_PIN L19 [get_ports {dac_dat_o[2]}]
set_property PACKAGE_PIN L20 [get_ports {dac_dat_o[3]}]
set_property PACKAGE_PIN K19 [get_ports {dac_dat_o[4]}]
set_property PACKAGE_PIN J19 [get_ports {dac_dat_o[5]}]
set_property PACKAGE_PIN J20 [get_ports {dac_dat_o[6]}]
set_property PACKAGE_PIN H20 [get_ports {dac_dat_o[7]}]
set_property PACKAGE_PIN G19 [get_ports {dac_dat_o[8]}]
set_property PACKAGE_PIN G20 [get_ports {dac_dat_o[9]}]
set_property PACKAGE_PIN F19 [get_ports {dac_dat_o[10]}]
set_property PACKAGE_PIN F20 [get_ports {dac_dat_o[11]}]
set_property PACKAGE_PIN D20 [get_ports {dac_dat_o[12]}]
set_property PACKAGE_PIN D19 [get_ports {dac_dat_o[13]}]

set_property IOSTANDARD LVCMOS33 [get_ports dac_wrt_o]
set_property SLEW FAST            [get_ports dac_wrt_o]
set_property DRIVE 8              [get_ports dac_wrt_o]
set_property PACKAGE_PIN M17     [get_ports dac_wrt_o]

set_property IOSTANDARD LVCMOS33 [get_ports dac_sel_o]
set_property SLEW FAST            [get_ports dac_sel_o]
set_property DRIVE 8              [get_ports dac_sel_o]
set_property PACKAGE_PIN N16     [get_ports dac_sel_o]

set_property IOSTANDARD LVCMOS33 [get_ports dac_clk_o]
set_property SLEW FAST            [get_ports dac_clk_o]
set_property DRIVE 8              [get_ports dac_clk_o]
set_property PACKAGE_PIN M18     [get_ports dac_clk_o]

set_property IOSTANDARD LVCMOS33 [get_ports dac_rst_o]
set_property SLEW FAST            [get_ports dac_rst_o]
set_property DRIVE 8              [get_ports dac_rst_o]
set_property PACKAGE_PIN N15     [get_ports dac_rst_o]

############# PWM DAC
set_property IOSTANDARD LVCMOS18 [get_ports {dac_pwm_o[*]}]
set_property SLEW FAST            [get_ports {dac_pwm_o[*]}]
set_property DRIVE 12             [get_ports {dac_pwm_o[*]}]
set_property IOB TRUE             [get_ports {dac_pwm_o[*]}]
set_property PACKAGE_PIN T10 [get_ports {dac_pwm_o[0]}]
set_property PACKAGE_PIN T11 [get_ports {dac_pwm_o[1]}]
set_property PACKAGE_PIN P15 [get_ports {dac_pwm_o[2]}]
set_property PACKAGE_PIN U13 [get_ports {dac_pwm_o[3]}]

############# LEDs
set_property IOSTANDARD LVCMOS33 [get_ports {led_o[*]}]
set_property SLEW SLOW            [get_ports {led_o[*]}]
set_property DRIVE 4              [get_ports {led_o[*]}]
set_property PACKAGE_PIN F16 [get_ports {led_o[0]}]
set_property PACKAGE_PIN F17 [get_ports {led_o[1]}]
set_property PACKAGE_PIN G15 [get_ports {led_o[2]}]
set_property PACKAGE_PIN H15 [get_ports {led_o[3]}]
set_property PACKAGE_PIN K14 [get_ports {led_o[4]}]
set_property PACKAGE_PIN G14 [get_ports {led_o[5]}]
set_property PACKAGE_PIN J15 [get_ports {led_o[6]}]
set_property PACKAGE_PIN J14 [get_ports {led_o[7]}]

############# Expansion connector (E1, E2)
set_property IOSTANDARD LVCMOS33 [get_ports {exp_p_io[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {exp_n_io[*]}]
set_property SLEW FAST            [get_ports {exp_p_io[*]}]
set_property SLEW FAST            [get_ports {exp_n_io[*]}]
set_property DRIVE 8              [get_ports {exp_p_io[*]}]
set_property DRIVE 8              [get_ports {exp_n_io[*]}]
set_property PACKAGE_PIN G17 [get_ports {exp_p_io[0]}]
set_property PACKAGE_PIN G18 [get_ports {exp_n_io[0]}]
set_property PACKAGE_PIN H16 [get_ports {exp_p_io[1]}]
set_property PACKAGE_PIN H17 [get_ports {exp_n_io[1]}]
set_property PACKAGE_PIN J18 [get_ports {exp_p_io[2]}]
set_property PACKAGE_PIN H18 [get_ports {exp_n_io[2]}]
set_property PACKAGE_PIN K17 [get_ports {exp_p_io[3]}]
set_property PACKAGE_PIN K18 [get_ports {exp_n_io[3]}]
set_property PACKAGE_PIN L14 [get_ports {exp_p_io[4]}]
set_property PACKAGE_PIN L15 [get_ports {exp_n_io[4]}]
set_property PACKAGE_PIN L16 [get_ports {exp_p_io[5]}]
set_property PACKAGE_PIN L17 [get_ports {exp_n_io[5]}]
set_property PACKAGE_PIN K16 [get_ports {exp_p_io[6]}]
set_property PACKAGE_PIN J16 [get_ports {exp_n_io[6]}]
set_property PACKAGE_PIN M14 [get_ports {exp_p_io[7]}]
set_property PACKAGE_PIN M15 [get_ports {exp_n_io[7]}]

############# Daisy-chain (SATA connectors)
set_property IOSTANDARD DIFF_SSTL18_I [get_ports {daisy_p_o[*]}]
set_property IOSTANDARD DIFF_SSTL18_I [get_ports {daisy_n_o[*]}]
set_property IOSTANDARD DIFF_SSTL18_I [get_ports {daisy_p_i[*]}]
set_property IOSTANDARD DIFF_SSTL18_I [get_ports {daisy_n_i[*]}]

create_clock -period 4.000 -name rx_clk [get_ports {daisy_p_i[1]}]

############# XADC analog inputs
set_property IOSTANDARD LVCMOS33 [get_ports {vinp_i[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {vinn_i[*]}]

############# False paths between clock domains
set_false_path -from [get_clocks adc_clk]   -to [get_clocks dac_clk_o]
set_false_path -from [get_clocks adc_clk]   -to [get_clocks dac_clk_1x]
set_false_path -from [get_clocks adc_clk]   -to [get_clocks dac_clk_2x]
set_false_path -from [get_clocks adc_clk]   -to [get_clocks dac_clk_2p]
set_false_path -from [get_clocks clk_fpga_0] -to [get_clocks dac_clk_o]
set_false_path -from [get_clocks clk_fpga_0] -to [get_clocks dac_clk_2x]
