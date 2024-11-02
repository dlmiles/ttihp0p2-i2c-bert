//
// MAJ5 process implementation cell/module mapping
//   5-input majority voter
//
// SPDX-FileCopyrightText: Copyright 2024 Darryl Miles
// SPDX-License-Identifier: Apache2.0
//
// This file exist to provide a default implementation of 'generic__maj5'
//   for PDKs that do not have a specific cell to use.
//
`default_nettype none

module generic__maj5 (
    X,
    A,
    B,
    C,
    D,
    E
);

    // Module ports
    output X;
    input  A;
    input  B;
    input  C;
    input  D;
    input  E;

    wire [4:0] inp;
    assign inp = {E,D,C,B,A};

    wire [9:0] and3;
    assign and3[0] = &{                    inp[2:0]}; //   210
    assign and3[1] = &{          inp[ 3 ], inp[1:0]}; //  3 10
    assign and3[2] = &{inp[4  ],           inp[1:0]}; // 4  10
    assign and3[3] = &{          inp[3:2], inp[  0]}; //  32 0
    assign and3[4] = &{inp[4],   inp[ 2 ], inp[  0]}; // 4 2 0
    assign and3[5] = &{inp[4:3],           inp[  0]}; // 43  0
    assign and3[6] = &{          inp[3:1]          }; //  321
    assign and3[7] = &{inp[4],   inp[2:1]          }; // 4 21
    assign and3[8] = &{inp[4:3], inp[  1]          }; // 43 1
    assign and3[9] = &{inp[4:2]                    }; // 432
    
    wire [1:0] or5;
    assign or5[0] = |{and3[4:0]};
    assign or5[1] = |{and3[9:5]};

    assign X = |or5;

endmodule
