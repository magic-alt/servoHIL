`timescale 1ns/1ps
module tb_health_cadence;
  reg clk=0, rst_n=0, session_start=0, arm_request=0, runtime_fault=0;
  reg plant_valid=0, io_valid=0, lease_valid=0;
  reg [31:0] plant_seq=0, io_seq=0, lease_seq=0;
  wire hil_wdi, hil_arm, healthy;
  wire [7:0] fault_code;
  health_heartbeat dut(.*);
  always #5 clk=~clk;
  integer cycle, falls=0;
  time last_fall=0;
  always @(negedge hil_wdi) if (rst_n && healthy) begin
    if (falls && $time-last_fall != 5000000) $fatal(1,"wrong WDI wall-time cadence");
    last_fall=$time; falls=falls+1;
  end
  initial begin
    repeat(3) @(negedge clk);
    rst_n=1; session_start=1;
    @(negedge clk); session_start=0;
    for(cycle=0;cycle<1100000;cycle=cycle+1) begin
      plant_valid=(cycle%50==0); io_valid=plant_valid; lease_valid=(cycle%1000==0);
      if(plant_valid) begin plant_seq=plant_seq+1;io_seq=io_seq+1;end
      if(lease_valid) lease_seq=lease_seq+1;
      @(negedge clk);
      if(fault_code || hil_arm) $fatal(1,"unexpected fault/ARM in disarmed healthy session");
    end
    if(falls!=2) $fatal(1,"expected two falling edges, saw %0d",falls);
    $display("CADENCE_PASS edges=2 interval_ns=5000000");$finish;
  end
  initial begin #12000000;$fatal(1,"cadence timeout");end
endmodule
