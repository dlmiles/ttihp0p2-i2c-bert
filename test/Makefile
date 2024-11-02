# Makefile
# See https://docs.cocotb.org/en/stable/quickstart.html for more info

# defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(PWD)/../src
PROJECT_SOURCES  = tt_um.vh
PROJECT_SOURCES += config.vh
PROJECT_SOURCES += top_tt_um_dlmiles_tt05_i2c_bert.v
PROJECT_SOURCES += latched_config.v
PROJECT_SOURCES += toolbox/dffqn_negedge_async_reset.v
PROJECT_SOURCES += toolbox/dff_async_reset.v
PROJECT_SOURCES += toolbox/glitch_free_clock_mux_async_reset.v
PROJECT_SOURCES += pdk_generic/generic_keep_and2.v
PROJECT_SOURCES += pdk_generic/generic_keep_or2.v
PROJECT_SOURCES += pdk_generic/generic_maj3.v
PROJECT_SOURCES += pdk_generic/generic_maj5.v
PROJECT_SOURCES += pdk_generic_sg13g2/sg13g2_dlhrq.v
PROJECT_SOURCES += TT05I2CBertTop.v

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD       = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))
COMPILE_ARGS    += -I$(SRC_DIR)

else

# Gate level simulation:
SIM_BUILD       = sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tbc_tt_um_dlmiles_tt05_i2c_bert.v
VERILOG_SOURCES += $(PWD)/tb_maj3.v
VERILOG_SOURCES += $(PWD)/tb_maj5.v
TOPLEVEL ?= tb_i2c_bert

# MODULE is the basename of the Python test file
MODULE ?= test_i2c_bert

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
