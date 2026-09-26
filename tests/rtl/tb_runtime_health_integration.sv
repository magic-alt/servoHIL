`timescale 1ns/1ps
`default_nettype none
module tb_runtime_health_integration;
    reg clk=0,rst_n=0,session_start=0,arm_request=0,runtime_fault=0;
    reg plant_done_valid=0,adc_sample_valid=0,lease_renew_valid=0;
    reg [31:0] plant_done_seq=0,adc_sample_seq=0,lease_renew_seq=0;
    wire hil_wdi,hil_arm,healthy;
    wire [7:0] fault_code;

    runtime_health_integration #(
        .HB_HALF_CYCLES(3),
        .PLANT_LIMIT_CYCLES(8),
        .IO_LIMIT_CYCLES(8),
        .LEASE_LIMIT_CYCLES(12)
    ) dut(
        .clk(clk),.rst_n(rst_n),.session_start(session_start),
        .arm_request(arm_request),.runtime_fault(runtime_fault),
        .plant_done_valid(plant_done_valid),.plant_done_seq(plant_done_seq),
        .adc_sample_valid(adc_sample_valid),.adc_sample_seq(adc_sample_seq),
        .lease_renew_valid(lease_renew_valid),.lease_renew_seq(lease_renew_seq),
        .hil_wdi(hil_wdi),.hil_arm(hil_arm),.healthy(healthy),.fault_code(fault_code)
    );
    always #5 clk=~clk;

    task progress_all;
        begin
            @(negedge clk);
            plant_done_seq=plant_done_seq+1; plant_done_valid=1;
            adc_sample_seq=adc_sample_seq+1; adc_sample_valid=1;
            lease_renew_seq=lease_renew_seq+1; lease_renew_valid=1;
            @(negedge clk);
            plant_done_valid=0; adc_sample_valid=0; lease_renew_valid=0;
        end
    endtask

    integer i;
    initial begin
        repeat(3) @(posedge clk); rst_n=1;
        @(negedge clk); session_start=1;
        @(negedge clk); session_start=0;
        progress_all();
        progress_all();
        if (!healthy) $fatal(1,"completed progress did not establish health");

        // Arm low must be observed before rising.
        repeat(2) begin progress_all(); arm_request=0; end
        arm_request=1; progress_all();
        if (!hil_arm) $fatal(1,"healthy completion stream did not arm");

        // Replaying the same ADC completion sequence does NOT renew I/O.
        adc_sample_valid=1;
        for (i=0;i<10;i=i+1) begin
            @(negedge clk);
            plant_done_seq=plant_done_seq+1; plant_done_valid=1;
            lease_renew_seq=lease_renew_seq+1; lease_renew_valid=1;
            // adc_sample_seq deliberately unchanged.
            @(negedge clk);
            plant_done_valid=0; lease_renew_valid=0;
        end
        adc_sample_valid=0;
        repeat(2) @(posedge clk);
        if (fault_code[2] !== 1'b1) $fatal(1,"replayed ADC completion refreshed IO deadline");
        if (hil_arm) $fatal(1,"faulted completion stream left ARM asserted");
        $display("RUNTIME_INTEGRATION_PASS fault=%h",fault_code);
        $finish;
    end
endmodule
`default_nettype wire
