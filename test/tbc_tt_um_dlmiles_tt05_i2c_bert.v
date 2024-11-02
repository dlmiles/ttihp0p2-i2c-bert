//
// SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
// SPDX-License-Identifier: Apache2.0
//
`default_nettype none
`timescale 1ns/1ps

module tb_i2c_bert (
    //input			clk,
    //input			rst_n,	// async (verilator needed reg)
    //input			ena,

    output		[7:0]	uo_out,
    //input		[7:0]	ui_in,

    output		[7:0]	uio_out,
    //input		[7:0]	uio_in,
    output		[7:0]	uio_oe
);
`ifndef SYNTHESIS
    reg [(8*32)-1:0] DEBUG;
    reg DEBUG_wire;
`endif

    reg clk;
    reg rst_n;
    reg ena;

    reg [7:0] ui_in;
    reg [7:0] uio_in;

    initial begin
        //$dumpfile ("tb_i2c_bert.vcd");
        $dumpfile ("tb.vcd");	// Renamed for GHA
`ifdef GL_TEST
        // the internal state of a flattened verilog is not that interesting
        $dumpvars (0, tb_i2c_bert);
`else
        $dumpvars (0, tb_i2c_bert);
`endif
`ifdef TIMING
        #1;
`endif
`ifndef SYNTHESIS
        DEBUG = {8'h44, 8'h45, 8'h42, 8'h55, 8'h47, {27{8'h20}}}; // "DEBUG        "
        DEBUG_wire = 0;
`endif
    end

    wire [7:0] uio_in_loopback;
    // This section was to investigate the highZ and pull-up scenarios
    assign uio_in_loopback = uio_in; // no loopback effect (gpiov2 INP_ENA input-enable)

    tt_um_dlmiles_tt05_i2c_bert dut (
`ifdef USE_POWER_PINS
        .VPWR     ( 1'b1),              //i
        .VGND     ( 1'b0),              //i
`endif
`ifdef USE_POWER_PINS_LEGACY
        .vccd1    ( 1'b1),              //i
        .vssd1    ( 1'b0),              //i
`endif
        .clk      (clk),                //i
        .rst_n    (rst_n),              //i
        .ena      (ena),                //i
        .uo_out   (uo_out),             //o
        .ui_in    (ui_in),              //i
        .uio_out  (uio_out),            //o
        .uio_in   (uio_in_loopback),    //i
        .uio_oe   (uio_oe)              //o
    );

endmodule
