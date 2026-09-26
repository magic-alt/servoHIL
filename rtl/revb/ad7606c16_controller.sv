`timescale 1ns/1ps
`default_nettype none
// AD7606C-16 serial software-mode controller.
// CONFIG address 0x02 uses bits[4:3]=2'b11 (0x18) for eight DOUT lanes.
// Register write: {WEN=0,R/W=0,ADDR[5:0],DATA[7:0]}.
// Register read:  {WEN=0,R/W=1,ADDR[5:0],8'h00}; the following
// all-zero 16-clock frame returns the addressed register on DOUTA and exits
// register mode. DOUT changes on SCLK rising edges; this controller samples
// on falling edges.
// This module proves digital transaction ordering only. It does NOT qualify
// ADC analog settling, calibration, anti-aliasing, board timing or 1 MSPS.
module ad7606c16_controller #(
    parameter integer SCLK_HALF_CYCLES = 5,
    parameter integer RESET_CYCLES = 10,
    parameter integer RESET_SETTLE_CYCLES = 10,
    parameter integer CONVST_CYCLES = 2,
    parameter integer BUSY_TIMEOUT_CYCLES = 10000
)(
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start_init,
    input  wire         sample_request,
    input  wire         adc_busy,
    input  wire [7:0]   adc_dout,
    output reg          adc_reset,
    output reg          adc_convst,
    output reg          adc_cs_n,
    output reg          adc_sclk,
    output reg          adc_sdi,
    output reg          configured,
    output reg          sample_valid,
    output reg [127:0]  sample_words,
    output reg [31:0]   sample_seq,
    output reg [3:0]    fault_code
);
    localparam [7:0] CONFIG_VALUE = 8'h18;
    localparam [15:0] CONFIG_WRITE = {2'b00,6'h02,CONFIG_VALUE};
    localparam [15:0] CONFIG_READ  = {2'b01,6'h02,8'h00};

    localparam [3:0]
        ST_IDLE          = 4'd0,
        ST_RESET_HIGH    = 4'd1,
        ST_RESET_SETTLE  = 4'd2,
        ST_CFG_WRITE     = 4'd3,
        ST_CFG_READ_CMD  = 4'd4,
        ST_CFG_READBACK  = 4'd5,
        ST_READY         = 4'd6,
        ST_CONVST        = 4'd7,
        ST_WAIT_BUSY_HI  = 4'd8,
        ST_WAIT_BUSY_LO  = 4'd9,
        ST_SAMPLE_READ   = 4'd10,
        ST_FAULT         = 4'd11;

    localparam [3:0]
        FAULT_NONE       = 4'd0,
        FAULT_CONFIG     = 4'd1,
        FAULT_BUSY_HIGH  = 4'd2,
        FAULT_BUSY_LOW   = 4'd3;

    reg [3:0] state;
    reg [31:0] count;
    reg [31:0] half_count;
    reg [31:0] busy_count;
    reg [4:0] bit_count;
    reg [15:0] spi_tx;
    reg [15:0] reg_rx;
    reg [127:0] lane_rx;
    reg [127:0] lane_capture;
    integer lane;

`ifndef SYNTHESIS
    initial begin
        if (SCLK_HALF_CYCLES < 1 || RESET_CYCLES < 1 ||
            RESET_SETTLE_CYCLES < 1 || CONVST_CYCLES < 1 ||
            BUSY_TIMEOUT_CYCLES < 2)
            $fatal(1,"AD7606C-16 controller timing parameters invalid");
    end
`endif

    // Start a frame by assigning these registers in the caller state:
    // CS low, SCLK low, SDI=tx[15], spi_tx=tx, bit_count=0, half_count=0.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= ST_IDLE;
            count <= 0;
            half_count <= 0;
            busy_count <= 0;
            bit_count <= 0;
            spi_tx <= 0;
            reg_rx <= 0;
            lane_rx <= 0;
            lane_capture <= 0;
            adc_reset <= 0;
            adc_convst <= 0;
            adc_cs_n <= 1;
            adc_sclk <= 0;
            adc_sdi <= 0;
            configured <= 0;
            sample_valid <= 0;
            sample_words <= 0;
            sample_seq <= 0;
            fault_code <= FAULT_NONE;
        end else begin
            sample_valid <= 0;

            // Explicit initialization/recovery is authoritative and can be
            // requested from READY or FAULT; no automatic retry is performed.
            if (start_init) begin
                state <= ST_RESET_HIGH;
                count <= 0;
                half_count <= 0;
                busy_count <= 0;
                bit_count <= 0;
                adc_reset <= 1;
                adc_convst <= 0;
                adc_cs_n <= 1;
                adc_sclk <= 0;
                adc_sdi <= 0;
                configured <= 0;
                fault_code <= FAULT_NONE;
            end else begin
                case (state)
                    ST_IDLE: begin
                        adc_cs_n <= 1;
                        adc_sclk <= 0;
                        adc_sdi <= 0;
                        adc_convst <= 0;
                    end

                    ST_RESET_HIGH: begin
                        if (count >= RESET_CYCLES-1) begin
                            adc_reset <= 0;
                            count <= 0;
                            state <= ST_RESET_SETTLE;
                        end else count <= count + 1'b1;
                    end

                    ST_RESET_SETTLE: begin
                        if (count >= RESET_SETTLE_CYCLES-1) begin
                            count <= 0;
                            spi_tx <= CONFIG_WRITE;
                            bit_count <= 0;
                            half_count <= 0;
                            reg_rx <= 0;
                            adc_cs_n <= 0;
                            adc_sclk <= 0;
                            adc_sdi <= CONFIG_WRITE[15];
                            state <= ST_CFG_WRITE;
                        end else count <= count + 1'b1;
                    end

                    ST_CFG_WRITE, ST_CFG_READ_CMD, ST_CFG_READBACK, ST_SAMPLE_READ: begin
                        if (half_count >= SCLK_HALF_CYCLES-1) begin
                            half_count <= 0;
                            if (!adc_sclk) begin
                                // DOUT changes after this rising edge.
                                adc_sclk <= 1;
                            end else begin
                                // SDI is latched and DOUT is stable at this edge.
                                adc_sclk <= 0;
                                if (state == ST_CFG_READBACK)
                                    reg_rx <= {reg_rx[14:0],adc_dout[0]};
                                if (state == ST_SAMPLE_READ) begin
                                    lane_capture = lane_rx;
                                    for (lane=0; lane<8; lane=lane+1)
                                        lane_capture[16*lane +: 16] =
                                            {lane_rx[16*lane +: 15],adc_dout[lane]};
                                    lane_rx <= lane_capture;
                                end

                                if (bit_count == 15) begin
                                    adc_cs_n <= 1;
                                    adc_sdi <= 0;
                                    bit_count <= 0;
                                    if (state == ST_CFG_WRITE) begin
                                        spi_tx <= CONFIG_READ;
                                        reg_rx <= 0;
                                        adc_cs_n <= 0;
                                        adc_sdi <= CONFIG_READ[15];
                                        state <= ST_CFG_READ_CMD;
                                    end else if (state == ST_CFG_READ_CMD) begin
                                        // All-zero second frame both obtains
                                        // readback and returns to ADC mode.
                                        spi_tx <= 16'h0000;
                                        reg_rx <= 0;
                                        adc_cs_n <= 0;
                                        adc_sdi <= 0;
                                        state <= ST_CFG_READBACK;
                                    end else if (state == ST_CFG_READBACK) begin
                                        if ({reg_rx[6:0],adc_dout[0]} == CONFIG_VALUE) begin
                                            configured <= 1;
                                            state <= ST_READY;
                                        end else begin
                                            configured <= 0;
                                            fault_code <= FAULT_CONFIG;
                                            state <= ST_FAULT;
                                        end
                                    end else begin
                                        sample_words <= lane_capture;
                                        sample_seq <= sample_seq + 1'b1;
                                        sample_valid <= 1;
                                        state <= ST_READY;
                                    end
                                end else begin
                                    bit_count <= bit_count + 1'b1;
                                    adc_sdi <= spi_tx[14];
                                    spi_tx <= {spi_tx[14:0],1'b0};
                                end
                            end
                        end else half_count <= half_count + 1'b1;
                    end

                    ST_READY: begin
                        adc_cs_n <= 1;
                        adc_sclk <= 0;
                        adc_sdi <= 0;
                        adc_convst <= 0;
                        if (sample_request) begin
                            adc_convst <= 1;
                            count <= 0;
                            state <= ST_CONVST;
                        end
                    end

                    ST_CONVST: begin
                        if (count >= CONVST_CYCLES-1) begin
                            adc_convst <= 0;
                            busy_count <= 0;
                            state <= ST_WAIT_BUSY_HI;
                        end else count <= count + 1'b1;
                    end

                    ST_WAIT_BUSY_HI: begin
                        if (adc_busy) begin
                            busy_count <= 0;
                            state <= ST_WAIT_BUSY_LO;
                        end else if (busy_count >= BUSY_TIMEOUT_CYCLES-1) begin
                            fault_code <= FAULT_BUSY_HIGH;
                            configured <= 0;
                            state <= ST_FAULT;
                        end else busy_count <= busy_count + 1'b1;
                    end

                    ST_WAIT_BUSY_LO: begin
                        if (!adc_busy) begin
                            spi_tx <= 16'h0000;
                            lane_rx <= 0;
                            lane_capture <= 0;
                            bit_count <= 0;
                            half_count <= 0;
                            adc_cs_n <= 0;
                            adc_sclk <= 0;
                            adc_sdi <= 0;
                            state <= ST_SAMPLE_READ;
                        end else if (busy_count >= BUSY_TIMEOUT_CYCLES-1) begin
                            fault_code <= FAULT_BUSY_LOW;
                            configured <= 0;
                            state <= ST_FAULT;
                        end else busy_count <= busy_count + 1'b1;
                    end

                    ST_FAULT: begin
                        adc_cs_n <= 1;
                        adc_sclk <= 0;
                        adc_sdi <= 0;
                        adc_convst <= 0;
                        configured <= 0;
                    end

                    default: begin
                        fault_code <= FAULT_CONFIG;
                        configured <= 0;
                        state <= ST_FAULT;
                    end
                endcase
            end
        end
    end
endmodule
`default_nettype wire
