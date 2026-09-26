`timescale 1ns/1ps
`default_nettype none
// Completion-only integration seam between the reviewed runtime producers and
// health_heartbeat. Inputs are accepted/completed sequence events in clk domain.
// CDC/AXI adapters must terminate before this module and prove their own event
// transfer semantics. No submission-side activity is accepted here.
module runtime_health_integration #(
    parameter integer HB_HALF_CYCLES = 250000,
    parameter integer PLANT_LIMIT_CYCLES = 10000,
    parameter integer IO_LIMIT_CYCLES = 10000,
    parameter integer LEASE_LIMIT_CYCLES = 1000000
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        session_start,
    input  wire        arm_request,
    input  wire        runtime_fault,
    input  wire        plant_done_valid,
    input  wire [31:0] plant_done_seq,
    input  wire        adc_sample_valid,
    input  wire [31:0] adc_sample_seq,
    input  wire        lease_renew_valid,
    input  wire [31:0] lease_renew_seq,
    output wire        hil_wdi,
    output wire        hil_arm,
    output wire        healthy,
    output wire [7:0]  fault_code
);
    health_heartbeat #(
        .HB_HALF_CYCLES(HB_HALF_CYCLES),
        .PLANT_LIMIT_CYCLES(PLANT_LIMIT_CYCLES),
        .IO_LIMIT_CYCLES(IO_LIMIT_CYCLES),
        .LEASE_LIMIT_CYCLES(LEASE_LIMIT_CYCLES)
    ) u_health (
        .clk(clk),
        .rst_n(rst_n),
        .session_start(session_start),
        .arm_request(arm_request),
        .runtime_fault(runtime_fault),
        .plant_valid(plant_done_valid),
        .plant_seq(plant_done_seq),
        .io_valid(adc_sample_valid),
        .io_seq(adc_sample_seq),
        .lease_valid(lease_renew_valid),
        .lease_seq(lease_renew_seq),
        .hil_wdi(hil_wdi),
        .hil_arm(hil_arm),
        .healthy(healthy),
        .fault_code(fault_code)
    );
endmodule
`default_nettype wire
