//
// SPDX-FileCopyrightText: Copyright 2023-2024 Darryl Miles
// SPDX-License-Identifier: Apache2.0
//
`default_nettype none

`include "config.vh"

module latched_config (
    output wire [31:0] latched,
    input  wire  [7:0] ui_in,
    input  wire  [7:0] uio_in,
    input  wire        ena,
    input  wire        rst_n
);

`ifdef TECH_FPGA
    // using 3 bits so the project gets the first clock to allow data to flow
    reg [2:0] ena_next;
    initial begin
        // the reset here is the TT reset, not the master reset, we could also have additional
        //  input wire master_rst_n, signal
        ena_next = 3'b0; // FPGA bitstream initialization
    end
    wire ena_filtered; // filtered to remove X and Z and replace with last known state from ena_next[0]
`ifdef XILINX_SIMULATOR
    assign ena_filtered = ($isunknown(ena)) ? ena_next[0] : ena; // SVA ? (ena !== 1'bx && ena !== 1'bz)
`else
    assign ena_filtered = ena;
`endif
    always @(posedge clk) begin
        ena_next <= {ena_next[1:0],ena_filtered};
    end
    wire ena_rise;
    assign ena_rise = ena_next[1] && !ena_next[2];
`endif

    // Here we have phase2 experiment, can we delay ENA enough to capture inputs?
    wire [2:0] ena_delayed;
`ifdef TECH_SKY130
    (* keep , syn_keep *) sky130_fd_sc_hd__dlygate4sd3 ena_delay2 (
       .X(ena_delayed[2]),
       .A(ena_delayed[1])
    );
    (* keep , syn_keep *) sky130_fd_sc_hd__dlygate4sd3 ena_delay1 (
       .X(ena_delayed[1]),
       .A(ena_delayed[0])
    );
    (* keep , syn_keep *) sky130_fd_sc_hd__dlygate4sd3 ena_delay0 (
       .X(ena_delayed[0]),
       .A(ena)
    );
`elsif TECH_IHP130
    (* keep , syn_keep *) sg13g2_dlygate4sd3 ena_delay2 (
       .X(ena_delayed[2]),
       .A(ena_delayed[1])
    );
    (* keep , syn_keep *) sg13g2_dlygate4sd3 ena_delay1 (
       .X(ena_delayed[1]),
       .A(ena_delayed[0])
    );
    (* keep , syn_keep *) sg13g2_dlygate4sd3 ena_delay0 (
       .X(ena_delayed[0]),
       .A(ena)
    );
`else
    assign ena_delayed[2:0] = {3{ena}};
`endif

    // Configuration latch bit experiment (test payload?)
    reg [7:0] latched_ena_uio_in;
`ifdef TECH_FPGA
    always @(posedge clk) begin
        if (ena_rise)
            latched_ena_uio_in <= uio_in;
    end
`else
    always_latch begin
        if (!ena)
            latched_ena_uio_in[1:0] = uio_in[1:0];
    end
    always_latch begin
        if (!ena_delayed[0])
            latched_ena_uio_in[3:2] = uio_in[3:2];
    end
    always_latch begin
        if (!ena_delayed[1])
            latched_ena_uio_in[5:4] = uio_in[5:4];
    end
    always_latch begin
        if (!ena_delayed[2])
            latched_ena_uio_in[7:6] = uio_in[7:6];
    end
`endif

    reg [7:0] latched_ena_ui_in;
`ifdef TECH_FPGA
    always @(posedge clk) begin
        if (ena_rise)
            latched_ena_ui_in <= ui_in;
    end
`else
    always_latch begin
        if (!ena)
            latched_ena_ui_in[1:0] = ui_in[1:0];
    end
    always_latch begin
        if (!ena_delayed[0])
            latched_ena_ui_in[3:2] = ui_in[3:2];
    end
    always_latch begin
        if (!ena_delayed[1])
            latched_ena_ui_in[5:4] = ui_in[5:4];
    end
    always_latch begin
        if (!ena_delayed[2])
            latched_ena_ui_in[7:6] = ui_in[7:6];
    end
`endif

    // Configuration latch bit experiment (configuration?)
    reg [7:0] latched_rst_n_uio_in;
`ifdef TECH_FPGA
    always @(posedge clk) begin
        if (!rst_n)
            latched_rst_n_uio_in <= uio_in;
    end
`else
    always_latch begin
        if (!rst_n)
            latched_rst_n_uio_in = uio_in;
    end
`endif

    reg [7:0] latched_rst_n_ui_in;
`ifdef TECH_FPGA
    always @(posedge clk) begin
        if (!rst_n)
            latched_rst_n_ui_in <= ui_in;
    end
`else
    always_latch begin
        if (!rst_n)
            latched_rst_n_ui_in = ui_in;
    end
`endif

    assign latched = {latched_ena_uio_in, latched_ena_ui_in, latched_rst_n_uio_in, latched_rst_n_ui_in};

endmodule
