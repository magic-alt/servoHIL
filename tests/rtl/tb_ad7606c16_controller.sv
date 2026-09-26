`timescale 1ns/1ps
`default_nettype none
module tb_ad7606c16_controller #(
    parameter integer BAD_CONFIG = 0,
    parameter integer NO_BUSY = 0
);
    reg clk=0, rst_n=0, start_init=0, sample_request=0, adc_busy=0;
    reg [7:0] adc_dout=0;
    wire adc_reset, adc_convst, adc_cs_n, adc_sclk, adc_sdi;
    wire configured, sample_valid;
    wire [127:0] sample_words;
    wire [31:0] sample_seq;
    wire [3:0] fault_code;

    ad7606c16_controller #(
        .SCLK_HALF_CYCLES(2),
        .RESET_CYCLES(4),
        .CONVST_CYCLES(2),
        .BUSY_TIMEOUT_CYCLES(40)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start_init(start_init),
        .sample_request(sample_request), .adc_busy(adc_busy), .adc_dout(adc_dout),
        .adc_reset(adc_reset), .adc_convst(adc_convst), .adc_cs_n(adc_cs_n),
        .adc_sclk(adc_sclk), .adc_sdi(adc_sdi),
        .configured(configured), .sample_valid(sample_valid),
        .sample_words(sample_words), .sample_seq(sample_seq), .fault_code(fault_code)
    );

    always #5 clk=~clk;

    integer frame=0;
    integer bitpos=15;
    integer lane;
    reg [15:0] samples [0:7];
    reg [7:0] config_value;

    initial begin
        samples[0]=16'h1111; samples[1]=16'h2222;
        samples[2]=16'h3333; samples[3]=16'h4444;
        samples[4]=16'h5555; samples[5]=16'h6666;
        samples[6]=16'h7777; samples[7]=16'h8888;
        config_value = BAD_CONFIG ? 8'h08 : 8'h18;
    end

    always @(negedge adc_cs_n) begin
        frame = frame + 1;
        bitpos = 15;
    end

    always @(posedge adc_sclk) begin
        adc_dout = 0;
        if (frame == 3) begin
            if (bitpos < 8) adc_dout[0] = config_value[bitpos];
        end else if (frame >= 4) begin
            for (lane=0; lane<8; lane=lane+1)
                adc_dout[lane] = samples[lane][bitpos];
        end
    end

    always @(negedge adc_sclk) begin
        if (!adc_cs_n && bitpos > 0) bitpos = bitpos - 1;
    end

    always @(posedge adc_convst) begin
        if (!NO_BUSY) begin
            adc_busy <= 1;
            fork
                begin
                    repeat(5) @(posedge clk);
                    adc_busy <= 0;
                end
            join_none
        end
    end

    task pulse_init;
        begin
            @(posedge clk); start_init <= 1;
            @(posedge clk); start_init <= 0;
        end
    endtask

    task pulse_sample;
        begin
            @(posedge clk); sample_request <= 1;
            @(posedge clk); sample_request <= 0;
        end
    endtask

    integer timeout;
    initial begin
        repeat(4) @(posedge clk);
        rst_n <= 1;
        pulse_init();

        timeout=0;
        while (!configured && fault_code==0 && timeout<1000) begin
            @(posedge clk); timeout=timeout+1;
        end

        if (BAD_CONFIG) begin
            if (configured || fault_code==0) $fatal(1,"bad CONFIG readback did not fail closed");
            $display("ADC_CONTROLLER_PASS bad_config");
            $finish;
        end
        if (!configured || fault_code!=0) $fatal(1,"configuration did not complete");

        pulse_sample();
        timeout=0;
        while (!sample_valid && fault_code==0 && timeout<1000) begin
            @(posedge clk); timeout=timeout+1;
        end

        if (NO_BUSY) begin
            if (sample_valid || fault_code==0) $fatal(1,"missing BUSY did not time out");
            $display("ADC_CONTROLLER_PASS no_busy");
            $finish;
        end

        if (!sample_valid || fault_code!=0) $fatal(1,"sample did not complete");
        if (sample_seq !== 32'd1) $fatal(1,"sample sequence wrong");
        for (lane=0; lane<8; lane=lane+1)
            if (sample_words[16*lane +: 16] !== samples[lane])
                $fatal(1,"lane %0d mismatch got=%h expected=%h",lane,
                       sample_words[16*lane +: 16],samples[lane]);
        $display("ADC_CONTROLLER_PASS sample_seq=%0d",sample_seq);
        $finish;
    end
endmodule
`default_nettype wire
