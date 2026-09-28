// Rev.B AXU2CGB I/O DRC harness only.
// This is NOT the functional ServoHIL top and carries no timing/behavior claim.
// It exists solely to keep every contracted package I/O alive for Vivado package-pin/IOSTANDARD DRC.
module servohil_io_drc_top (
    output wire dac_sclk,
    output wire dac_ldac_n,
    output wire dac_cs0_n,
    output wire dac_cs1_n,
    output wire dac_cs2_n,
    output wire dac_cs3_n,
    inout wire dac_sdio0,
    inout wire dac_sdio1,
    inout wire dac_sdio2,
    inout wire dac_sdio3,
    inout wire dac_sdio4,
    inout wire dac_sdio5,
    inout wire dac_sdio6,
    inout wire dac_sdio7,
    input wire dac_alert0_n,
    input wire dac_alert1_n,
    input wire dac_alert2_n,
    input wire dac_alert3_n,
    input wire adc_dout0,
    input wire adc_dout1,
    input wire adc_dout2,
    input wire adc_dout3,
    input wire adc_dout4,
    input wire adc_dout5,
    input wire adc_dout6,
    input wire adc_dout7,
    output wire adc_sclk,
    output wire adc_cs_n,
    output wire adc_sdi,
    output wire adc_convst,
    input wire adc_busy,
    output wire adc_reset,
    input wire pwm_uh,
    input wire pwm_ul,
    input wire pwm_vh,
    input wire pwm_vl,
    input wire pwm_wh,
    input wire pwm_wl,
    inout wire enc0_io0,
    inout wire enc0_io1,
    inout wire enc0_io2,
    inout wire enc0_io3,
    output wire enc0_dir0,
    output wire enc0_dir1,
    inout wire enc1_io0,
    inout wire enc1_io1,
    inout wire enc1_io2,
    inout wire enc1_io3,
    output wire enc1_dir0,
    output wire enc1_dir1,
    inout wire aux_io0,
    inout wire aux_io1,
    inout wire aux_io2,
    inout wire aux_io3,
    inout wire aux_io4,
    inout wire aux_io5,
    output wire rs485_tx,
    input wire rs485_rx,
    output wire rs485_de,
    inout wire mgmt_scl,
    inout wire mgmt_sda,
    output wire hil_arm,
    output wire hil_wdi,
    input wire hil_fault_n
);

    wire contracted_input_activity = ^{dac_alert0_n, dac_alert1_n, dac_alert2_n, dac_alert3_n, adc_dout0, adc_dout1, adc_dout2, adc_dout3, adc_dout4, adc_dout5, adc_dout6, adc_dout7, adc_busy, pwm_uh, pwm_ul, pwm_vh, pwm_vl, pwm_wh, pwm_wl, rs485_rx, hil_fault_n};
    wire contracted_inout_activity = ^{dac_sdio0, dac_sdio1, dac_sdio2, dac_sdio3, dac_sdio4, dac_sdio5, dac_sdio6, dac_sdio7, enc0_io0, enc0_io1, enc0_io2, enc0_io3, enc1_io0, enc1_io1, enc1_io2, enc1_io3, aux_io0, aux_io1, aux_io2, aux_io3, aux_io4, aux_io5, mgmt_scl, mgmt_sda};
    wire io_activity = contracted_input_activity ^ contracted_inout_activity;

    assign dac_sclk = io_activity;
    assign dac_ldac_n = io_activity;
    assign dac_cs0_n = io_activity;
    assign dac_cs1_n = io_activity;
    assign dac_cs2_n = io_activity;
    assign dac_cs3_n = io_activity;
    assign adc_sclk = io_activity;
    assign adc_cs_n = io_activity;
    assign adc_sdi = io_activity;
    assign adc_convst = io_activity;
    assign adc_reset = io_activity;
    assign enc0_dir0 = io_activity;
    assign enc0_dir1 = io_activity;
    assign enc1_dir0 = io_activity;
    assign enc1_dir1 = io_activity;
    assign rs485_tx = io_activity;
    assign rs485_de = io_activity;
    assign hil_arm = io_activity;
    assign hil_wdi = io_activity;

    assign dac_sdio0 = 1'bz;
    assign dac_sdio1 = 1'bz;
    assign dac_sdio2 = 1'bz;
    assign dac_sdio3 = 1'bz;
    assign dac_sdio4 = 1'bz;
    assign dac_sdio5 = 1'bz;
    assign dac_sdio6 = 1'bz;
    assign dac_sdio7 = 1'bz;
    assign enc0_io0 = 1'bz;
    assign enc0_io1 = 1'bz;
    assign enc0_io2 = 1'bz;
    assign enc0_io3 = 1'bz;
    assign enc1_io0 = 1'bz;
    assign enc1_io1 = 1'bz;
    assign enc1_io2 = 1'bz;
    assign enc1_io3 = 1'bz;
    assign aux_io0 = 1'bz;
    assign aux_io1 = 1'bz;
    assign aux_io2 = 1'bz;
    assign aux_io3 = 1'bz;
    assign aux_io4 = 1'bz;
    assign aux_io5 = 1'bz;
    assign mgmt_scl = 1'bz;
    assign mgmt_sda = 1'bz;

endmodule
