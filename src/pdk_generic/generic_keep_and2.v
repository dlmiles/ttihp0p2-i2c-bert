//
// AND2 2-input AND gate.
//
// SPDX-FileCopyrightText: Copyright 2024 Darryl Miles
// SPDX-License-Identifier: Apache2.0
//
// This exists to help force a specific cell topology.
//
`default_nettype none

module generic_keep_and2 (
    X,
    A,
    B
);

    // Module ports
    output wire X;
    input  wire A;
    input  wire B;

`ifdef TECH_SKY130
    (* keep, syn_keep *) sky130_fd_sc_hd__and2_2 and2 (
        .A  (A),    //i
        .B  (B),    //i
        .X  (X)     //o
    );
`elsif TECH_IHP130
    (* keep, syn_keep *) sg13g2_and2_1 and2 (
        .A  (A),    //i
        .B  (B),    //i
        .X  (X)     //o
    );
`else
    assign X = A & B;
`endif

endmodule
