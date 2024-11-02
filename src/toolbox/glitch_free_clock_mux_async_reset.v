//
// SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
// SPDX-License-Identifier: Apache2.0
//
`default_nettype none
`ifdef TIMESCALE
`timescale 1ns/1ps
`endif
//
//  this is designed to switch 2 different clocks that are intended to run a while.
//  this probably doesn't perform well if you keep switching 'sel' within a
//    few clocks of one of the sources.
//  the circuit is designed to prevent glitches in the 'clk_out' line, by
//   extending the LO state as neccessary to get an edge of the new clk source.
//
//
// REF: https://www.eetimes.com/techniques-to-make-clock-switching-glitch-free/  2003
// REF: YouTube Electronicspedia, Glitch Free Clock Mux, 2022
//
module glitch_free_clock_mux_async_reset (
    output wire			clk_out,
    input  wire			sel,
    input  wire			clk_0,
    input  wire			clk_1,
    input  wire			reset
);

    // No don't do this
    //assign clk_out = sel ? clk_1 : clk_0;

    wire sel_inverted;
`ifdef TIMING
    assign #1 sel_inverted = ~sel;
`else
    assign    sel_inverted = ~sel;
`endif

    // SEL=0 logic area

    wire and01;
    wire and02;
    wire dff01q;
    wire dff02q;
    wire dff02qn;
    wire dff12qn;	// forward reference in feedback loop

`ifdef NOTDEFINED
    generic_keep_and2 and2_and01 (
        .a     (sel_inverted),
        .b     (dff12qn),
        .x     (and01)
    );
`else
    // The logic upstream of DFF.D is not so critical,
    //  so doesn't need a forced topology with (*keep*)
    assign and01 =  sel_inverted & dff12qn;	// sel=0 uses inverted
`endif

    dff_async_reset dff01 (
        .clk   (clk_0),
        .reset (reset),
        .d     (and01),
        .q     (dff01q)
    );

    dffqn_negedge_async_reset dff02 (
        .clk   (clk_0),
        .reset (reset),
        .d     (dff01q),
        .q     (dff02q),
        .qn    (dff02qn)
    );

    // This exists to force a specific transistor topology and prevent
    //   optimizer providing an equivalent by coalescing function into
    //   a combined cell, this seems important for all logic upstream
    //   of clk_out.
    generic_keep_and2 and2_and02 ( // critical topology
        .A     (dff02q),
        .B     (clk_0),
        .X     (and02)
    );
    //assign and02 = dff02q & clk_0;

    // SEL=1 logic area

    wire and11;
    wire and12;
    wire dff11q;
    wire dff12q;

`ifdef NODEFINED
    generic_keep_and2 and2_and11 (
        .A     (sel),
        .B     (dff02qn),
        .X     (and11)
    );
`else
    // The logic upstream of DFF.D is not so critical,
    //  so doesn't need a forced topology with (*keep*)
    assign and11 = sel & dff02qn;		// sel=1 uses non-inverted
`endif
///    assign and11 = ~sel & dff11qn;  // REMOVE THIS LINE

    dff_async_reset dff11 (
        .clk   (clk_1),
        .reset (reset),
        .d     (and11),
        .q     (dff11q)
    );

    dffqn_negedge_async_reset dff12 (
        .clk   (clk_1),
        .reset (reset),
        .d     (dff11q),
        .q     (dff12q),
        .qn    (dff12qn)
    );

    generic_keep_and2 and2_and12 ( // critical topology
        .A     (dff12q),
        .B     (clk_1),
        .X     (and12)
    );
    //assign and12 = dff12q & clk_1;

    // Combine AND clock-gated outputs

    generic_keep_or2 or2_clk_out ( // critical topology
        .A     (and02),
        .B     (and12),
        .X     (clk_out)
    );
    //assign clk_out = and02 | and12;

endmodule
