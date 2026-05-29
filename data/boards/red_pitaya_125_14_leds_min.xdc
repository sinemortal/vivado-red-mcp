###############################################################################
# Red Pitaya STEMlab 125-14 — minimal LED-only constraints
#
# Target: Xilinx Zynq xc7z010clg400-1
# Use case: hello-world / LED-blinker projects that only need the 125 MHz
#           differential clock input and the 8 user LEDs.
#
# Top-level ports expected by this XDC (declare exactly these in your Verilog):
#
#   module top (
#     input  wire        adc_clk_p_i,   // 125 MHz differential clock (+)
#     input  wire        adc_clk_n_i,   // 125 MHz differential clock (-)
#     output wire [7:0]  led_o          // 8 user LEDs
#   );
#
# Use an IBUFDS primitive inside the module to convert the differential pair
# to a single-ended 125 MHz clock:
#
#   wire adc_clk;
#   IBUFDS i_clk_buf (.I(adc_clk_p_i), .IB(adc_clk_n_i), .O(adc_clk));
#
# Pin assignments match the canonical red_pitaya.xdc (Matej Oblak, 2014).
###############################################################################

# 125 MHz differential ADC clock input
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports adc_clk_p_i]
set_property IOSTANDARD DIFF_HSTL_I_18 [get_ports adc_clk_n_i]
set_property PACKAGE_PIN U18 [get_ports adc_clk_p_i]
set_property PACKAGE_PIN U19 [get_ports adc_clk_n_i]

create_clock -period 8.000 -name adc_clk [get_ports adc_clk_p_i]

# 8 user LEDs
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
