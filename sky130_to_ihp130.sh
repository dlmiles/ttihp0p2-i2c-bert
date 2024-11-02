#!/bin/bash
#
# 
#

VERILOG_FILE="TT05I2CBertTop.v"

cp -f "$VERILOG_FILE" "${VERILOG_FILE}.orig"
# 3-input majority voter
sed -e 's/sky130_fd_sc_hd__maj3/generic__maj3/' -i $VERILOG_FILE
# D-Latch Gate-active-high Reset-active-low Single-output
sed -e 's/sky130_fd_sc_hd__dlrtp/sg13g2_dlhrq/' -i $VERILOG_FILE
diff -u "${VERILOG_FILE}.orig" "${VERILOG_FILE}"
