`timescale 1ns/1ps
`default_nettype none
// Synchronous accepted-transaction boundary, not an AXI or CDC adapter.
// At 100 MHz the default half-period gives 5 ms falling-to-falling WDI.
// Plant/I/O pulses mean COMPLETED work, never command submission or a timer.
// Lease renewal must follow an authenticated/validated live host session.
// Each stream accepts an arbitrary first sequence, then exact +1 (mod 2^32).
// Duplicates do not refresh age. Jumps, deadlines and runtime_fault latch off.
// HIL_FAULT_N intentionally is NOT an input: hardware reports fault unarmed,
// so using that status to stop WDI would deadlock watchdog qualification.
// Fault holds WDI at its current level (no synthetic final falling edge).
// Reset may produce an edge; the external two-edge qualifier is still required.
module health_heartbeat #(
    parameter integer HB_HALF_CYCLES = 250000,
    parameter integer PLANT_LIMIT_CYCLES = 10000,
    parameter integer IO_LIMIT_CYCLES = 10000,
    parameter integer LEASE_LIMIT_CYCLES = 1000000
)(
    input  wire clk,
    input  wire rst_n,
    input  wire session_start,
    input  wire arm_request,
    input  wire runtime_fault,
    input  wire plant_valid,
    input  wire [31:0] plant_seq,
    input  wire io_valid,
    input  wire [31:0] io_seq,
    input  wire lease_valid,
    input  wire [31:0] lease_seq,
    output reg hil_wdi,
    output reg hil_arm,
    output wire healthy,
    output reg [7:0] fault_code
);
    reg active, plant_seen, io_seen, lease_seen;
    reg arm_low_seen, previous_arm;
    reg [31:0] last_plant, last_io, last_lease;
    reg [31:0] plant_age, io_age, lease_age, heartbeat_count;
    wire plant_advance = plant_valid && (!plant_seen || plant_seq == last_plant + 32'd1);
    wire io_advance = io_valid && (!io_seen || io_seq == last_io + 32'd1);
    wire lease_advance = lease_valid && (!lease_seen || lease_seq == last_lease + 32'd1);
    wire plant_bad = plant_valid && plant_seen && plant_seq != last_plant && !plant_advance;
    wire io_bad = io_valid && io_seen && io_seq != last_io && !io_advance;
    wire lease_bad = lease_valid && lease_seen && lease_seq != last_lease && !lease_advance;
    wire [7:0] pending_fault = {
        1'b0, lease_bad, io_bad, plant_bad,
        (lease_age >= LEASE_LIMIT_CYCLES-1 && !lease_advance),
        (io_age >= IO_LIMIT_CYCLES-1 && !io_advance),
        (plant_age >= PLANT_LIMIT_CYCLES-1 && !plant_advance),
        runtime_fault
    };
    assign healthy = active && fault_code == 0 && plant_seen && io_seen && lease_seen;

`ifndef SYNTHESIS
    initial begin
        if (HB_HALF_CYCLES < 2 || PLANT_LIMIT_CYCLES < 2 ||
            IO_LIMIT_CYCLES < 2 || LEASE_LIMIT_CYCLES < 2)
            $fatal(1, "health_heartbeat cycle limits must be >=2");
    end
`endif

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0;
            plant_seen <= 0; io_seen <= 0; lease_seen <= 0;
            last_plant <= 0; last_io <= 0; last_lease <= 0;
            plant_age <= 0; io_age <= 0; lease_age <= 0;
            heartbeat_count <= 0; hil_wdi <= 0; hil_arm <= 0;
            fault_code <= 0; arm_low_seen <= 0; previous_arm <= 0;
        end else begin
            previous_arm <= arm_request;
            if (session_start) begin
                hil_arm <= 0; arm_low_seen <= 0; heartbeat_count <= 0;
                // A running healthy session cannot be silently restarted to
                // refresh deadlines. Recovery requires a fault/idle state.
                if (arm_request || runtime_fault || (active && fault_code == 0)) begin
                    fault_code <= fault_code | 8'h80 | {7'b0, runtime_fault};
                    active <= 0;
                end else begin
                    active <= 1; fault_code <= 0;
                    plant_seen <= 0; io_seen <= 0; lease_seen <= 0;
                    last_plant <= 0; last_io <= 0; last_lease <= 0;
                    plant_age <= 0; io_age <= 0; lease_age <= 0;
                end
            end else if (active && fault_code == 0) begin
                if (pending_fault != 0) begin
                    fault_code <= pending_fault;
                    hil_arm <= 0; arm_low_seen <= 0; heartbeat_count <= 0;
                end else begin
                    if (plant_advance) begin
                        plant_seen <= 1; last_plant <= plant_seq; plant_age <= 0;
                    end else if (plant_age < PLANT_LIMIT_CYCLES) plant_age <= plant_age + 1'b1;
                    if (io_advance) begin
                        io_seen <= 1; last_io <= io_seq; io_age <= 0;
                    end else if (io_age < IO_LIMIT_CYCLES) io_age <= io_age + 1'b1;
                    if (lease_advance) begin
                        lease_seen <= 1; last_lease <= lease_seq; lease_age <= 0;
                    end else if (lease_age < LEASE_LIMIT_CYCLES) lease_age <= lease_age + 1'b1;
                    if (healthy) begin
                        if (heartbeat_count == HB_HALF_CYCLES-1) begin
                            heartbeat_count <= 0; hil_wdi <= ~hil_wdi;
                        end else heartbeat_count <= heartbeat_count + 1'b1;
                        if (!arm_request) begin
                            arm_low_seen <= 1; hil_arm <= 0;
                        end else if (arm_low_seen && !previous_arm) hil_arm <= 1;
                    end else begin
                        heartbeat_count <= 0; hil_arm <= 0; arm_low_seen <= 0;
                    end
                end
            end else begin
                hil_arm <= 0; heartbeat_count <= 0; arm_low_seen <= 0;
            end
        end
    end
endmodule
`default_nettype wire
