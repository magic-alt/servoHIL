`timescale 1ns/1ps
module tb_health_heartbeat;
  parameter integer HALF = 25, PLANT_LIMIT = 11, IO_LIMIT = 13, LEASE_LIMIT = 31;
  reg clk=0, rst_n=0, session_start=0, arm_request=0, runtime_fault=0;
  reg plant_valid=0, io_valid=0, lease_valid=0;
  reg [31:0] plant_seq=0, io_seq=0, lease_seq=0;
  wire hil_wdi, hil_arm, healthy;
  wire [7:0] fault_code;
  always #5 clk=~clk;
  health_heartbeat #(.HB_HALF_CYCLES(HALF), .PLANT_LIMIT_CYCLES(PLANT_LIMIT),
    .IO_LIMIT_CYCLES(IO_LIMIT), .LEASE_LIMIT_CYCLES(LEASE_LIMIT)) dut(.*);
  string input_path, output_path;
  integer fd, out, count, index=0;
  integer s, a, f, p, i, l;
  reg [31:0] ps, isq, ls;
  initial begin
    if (!$value$plusargs("input=%s",input_path)) $fatal(1,"missing input path");
    if (!$value$plusargs("output=%s",output_path)) $fatal(1,"missing output path");
    fd=$fopen(input_path,"r"); out=$fopen(output_path,"w");
    if (!fd || !out) $fatal(1,"cannot open vector files");
    repeat(3) @(negedge clk);
    rst_n=1;
    while (!$feof(fd)) begin
      count=$fscanf(fd,"%d %d %d %d %h %d %h %d %h\n",s,a,f,p,ps,i,isq,l,ls);
      if(count!=9) $fatal(1,"malformed vector %0d",index);
      @(negedge clk);
      session_start=s[0]; arm_request=a[0]; runtime_fault=f[0];
      plant_valid=p[0]; plant_seq=ps; io_valid=i[0]; io_seq=isq;
      lease_valid=l[0]; lease_seq=ls;
      @(posedge clk); #1;
      $fdisplay(out,"%0d %0d %0d %0d %0d",index,hil_wdi,hil_arm,healthy,fault_code);
      index=index+1;
    end
    $fclose(fd); $fclose(out); $display("HEALTH_VECTORS_PASS count=%0d",index); $finish;
  end
  initial begin #10000000; $fatal(1,"simulation timeout"); end
endmodule
