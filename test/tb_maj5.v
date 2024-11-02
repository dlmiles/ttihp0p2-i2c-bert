//
//
//
`default_nettype none
`ifdef TIMESCALE
`timescale 1ns / 1ps
`endif

module tb_maj5 ();

  // Dump the signals to a VCD file. You can view it with gtkwave.
  initial begin
    $dumpfile("tb_maj5.vcd");
    $dumpvars(0, tb_maj5);
`ifdef TIMING
    #1;
`endif
  end

  reg clk;  // dummy clock (combo tests)
  reg A;
  reg B;
  reg C;
  reg D;
  reg E;
  wire X;

  generic__maj5 dut (
    .A  (A),  //i
    .B  (B),  //i
    .C  (C),  //i
    .D  (D),  //i
    .E  (E),  //i
    .X  (X)   //o
  );

  wire notused;
  assign notused = &{clk}; // icarus optimized clk out without this

endmodule
