//=============================================================================
// led_blinker_template.v
//
// Minimal Red Pitaya STEMlab 125-14 reference: blinks led_o[0] at ~1 Hz using
// the 125 MHz differential ADC clock (adc_clk_i). Leaves led_o[7:1] driven
// low.
//
// Pair with the bundled constraints file:
//   data/boards/red_pitaya_125_14_leds_min.xdc
//
// Compile with create_redpitaya_project_rtl:
//   create_redpitaya_project_rtl(
//     name="led_blinker_1hz",
//     directory="/tmp/rp_projects",
//     verilog_files=["/path/to/led_blinker_template.v"],
//     top_module="led_blinker",
//     xdc_variant="leds_min"
//   )
//
// 125 MHz / 2^26 ≈ 1.86 Hz toggle rate => ~0.93 Hz full blink cycle. Adjust
// the counter width to tune the rate (e.g. width 27 ≈ 0.47 Hz, width 25 ≈
// 1.86 Hz).
//=============================================================================

`timescale 1ns / 1ps

module led_blinker (
    input  wire        adc_clk_p_i,   // 125 MHz differential clock (+)
    input  wire        adc_clk_n_i,   // 125 MHz differential clock (-)
    output wire [7:0]  led_o          // 8 user LEDs
);

    // Convert differential clock to single-ended
    wire adc_clk;
    IBUFDS #(
        .DIFF_TERM    ("FALSE"),
        .IBUF_LOW_PWR ("FALSE"),
        .IOSTANDARD   ("DIFF_HSTL_I_18")
    ) i_clk_buf (
        .I  (adc_clk_p_i),
        .IB (adc_clk_n_i),
        .O  (adc_clk)
    );

    // Free-running counter
    reg [25:0] counter = 26'd0;
    always @(posedge adc_clk) begin
        counter <= counter + 1'b1;
    end

    // LED0 toggles on MSB; others off
    assign led_o[0]   = counter[25];
    assign led_o[7:1] = 7'b0;

endmodule
