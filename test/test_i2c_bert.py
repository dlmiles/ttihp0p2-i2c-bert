#!/usr/bin/python3
#
#
#  Interesting environment settings:
#
#	CI=true		(validates expected production settings, implies ALL=true)
#	ALL=true	Run all tests (not the default profile to help speed up development)
#	DEBUG=true	Enable cocotb debug logging level
#	MONITOR=no-suspend Disables an optimization to suspend the FSM monitors (if active) around parts
#			of the simulation to speed it up.  Keeping them running is only useful to observe
#			the timing of when an FSM changes state (if that is important for diagnostics)
#	PUSH_PULL_MODE=false	false=open-drain
#				true=push-pull
#	SCL_MODE=0	SCL source: 0=RegNext (just 1 register)
#                                   1=MAJ3 (majority voter 3 cell)
#                                   2=3DFF-synchronizer
#                                   3=ANDNOR3-unanimous
#                                   4=5DFF-synchronizer
#                                   5=MAJ5 (majority voter 5)
#                                   6=DIRECT (raw signal)
#                                   7=ANDNOR5-unanimous
#
#			TODO		ANDNOR2-unanimous
#
#	DIVISOR=0	Sample Tick divisor: 0=1:1
#                                            1=1:2
#                                            2=1:4
#                                            3=1:8
#
#  PUSH_PULL_MODE=true make
#  PUSH_PULL_MODE=true GATES=yes make
#
#
# SPDX-FileCopyrightText: Copyright 2023-2024 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#
import os
import sys
import re
import random
import inspect
import numbers
from typing import Any
from collections import namedtuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles
from cocotb.wavedrom import trace
from cocotb.binary import BinaryValue
from cocotb.utils import get_sim_time

from TestBenchConfig import *

from cocotb_stuff import *
from cocotb_stuff.cocotbutil import *
from cocotb_stuff.cocotb_proxy_dut import *
from cocotb_stuff.FSM import *
from cocotb_stuff.I2CController import *
from cocotb_stuff.SignalAccessor import *
from cocotb_stuff.SignalOutput import *
from cocotb_stuff.SimConfig import *
from cocotb_stuff.Monitor import *
from cocotb_stuff.Payload import *



###
###
##################################################################################################################################
###
###


###
###
##################################################################################################################################
###
###

# Signals we are not interested in when enumerating at the top of the log
exclude = [
    r'[\./]_',
    r'[\./]FILLER_',
    r'[\./]PHY_',
    r'[\./]TAP_',
    r'[\./]VGND',
    r'[\./]VNB',
    r'[\./]VPB',
    r'[\./]VPWR',
    r'[\./]pwrgood_',
    r'[\./]ANTENNA_',
    r'[\./]clkbuf_leaf_',
    r'[\./]clknet_leaf_',
    r'[\./]clkbuf_[\d_]+__f_clk',
    r'[\./]clknet_[\d_]+__leaf_clk',
    r'[\./]clkbuf_[\d_]+_clk',
    r'[\./]clknet_[\d_]+_clk',
    r'[\./]net\d+[\./]',
    r'[\./]net\d+$',
    r'[\./]fanout\d+[\./]',
    r'[\./]fanout\d+$',
    r'[\./]input\d+[\./]',
    r'[\./]input\d+$',
    r'[\./]hold\d+[\./]',
    r'[\./]hold\d+$',
    r'[\./]max_cap\d+[\./]',
    r'[\./]max_cap\d+$',
    r'[\./]wire\d+[\./]',
    r'[\./]wire\d+$'
]
EXCLUDE_RE = dict(map(lambda k: (k,re.compile(k)), exclude))

def exclude_re_path(path: str, name: str):
    for v in EXCLUDE_RE.values():
        if v.search(path):
            #print("EXCLUDED={}".format(path))
            return False
    return True

###
# Signals not to touch for ensure_resolvable()
#
# Signals we are not interested in enumerating to assign X with value
ensure_exclude = [
    #r'[\./]_',
    r'[A-Za-z0-9_\$]_[\./]base[\./][A-Za-z0-9_\$]+$',
    r'[\./]FILLER_',
    r'[\./]PHY_',
    r'[\./]TAP_',
    r'[\./]VGND$',
    r'[\./]VNB$',
    r'[\./]VPB$',
    r'[\./]VPWR$',
    r'[\./]HI$',
    r'[\./]LO$',
    r'[\./]CLK$',
    r'[\./]CLK_N$',
    r'[\./]DIODE$',
    r'[\./]GATE$',
    r'[\./]NOTIFIER$',
    r'[\./]RESET$',
    r'[\./]RESET_B$',
    r'[\./]SET$',
    r'[\./]SET_B$',
    r'[\./]SLEEP$',
    r'[\./]UDP_IN$',
    # sky130 candidates to exclude: CLK CLK_N GATE NOTIFIER RESET SET SLEEP UDP_IN
    r'[\./][ABCD][0-9]*$',
    r'[\./][ABCD][0-9]_N*$',
    r'[\./]pwrgood_',
    r'[\./]ANTENNA_',
    r'[\./]clkbuf_leaf_',
    r'[\./]clknet_leaf_',
    r'[\./]clkbuf_[\d_]+_clk',
    r'[\./]clknet_[\d_]+_clk',
    r'[\./]net\d+[\./]',
    r'[\./]net\d+$',
    r'[\./]fanout\d+[\./]',
    r'[\./]fanout\d+$',
    r'[\./]input\d+[\./]',
    r'[\./]input\d+$',
    r'[\./]hold\d+[\./]',
    r'[\./]hold\d+$',
    r'[\./]max_cap\d+[\./]',
    r'[\./]max_cap\d+$',
    r'[\./]wire\d+[\./]',
    r'[\./]wire\d+$',
    # Latches, don't mess with those (as they expect to be zero on powerup)
    r'[\./]i2c_bert\.latched\[\d]+',
    r'[\./]i2c_bert\.powerOnSense[\./]',
    r'[\./]i2c_bert\.powerOnSenseCaptured[\./]'
]
ENSURE_EXCLUDE_RE = dict(map(lambda k: (k,re.compile(k)), ensure_exclude))

def ensure_exclude_re_path(path: str, name: str):
    for v in ENSURE_EXCLUDE_RE.values():
        if v.search(path):
            #print("ENSURE_EXCLUDED={}".format(path))
            return False
    return True



# This is used as detection of gatelevel testing, with a flattened HDL,
#  we can only inspect the external module signals and disable internal signal inspection.
def resolve_GL_TEST():
    gl_test = False
    if 'GL_TEST' in os.environ:
        gl_test = True
    if 'GATES' in os.environ and os.environ['GATES'].casefold() == 'yes':
        gl_test = True
    return gl_test


def resolve_MONITOR_can_suspend():
    can_suspend = True	# default
    if 'MONITOR' in os.environ and os.environ['MONITOR'].casefold() == 'no-suspend':
        can_suspend = False
    return can_suspend


def run_this_test(default_value: bool = True) -> bool:
    if 'CI' in os.environ and os.environ['CI'].casefold() != 'false':
        return True	# always on for CI
    if 'ALL' in os.environ and os.environ['ALL'].casefold() != 'false':
        return True
    return default_value


def resolve_PUSH_PULL_MODE(default_value: bool):
    push_pull_mode = default_value
    if 'PUSH_PULL_MODE' in os.environ and os.environ['PUSH_PULL_MODE'].casefold() != 'false':
        push_pull_mode = True
    return push_pull_mode


def resolve_SCL_MODE(default_value: int):
    scl_mode = default_value
    if 'SCL_MODE' in os.environ and os.environ['SCL_MODE'].casefold() != 'default':
        scl_mode = int(os.environ['SCL_MODE'])
    return scl_mode


def resolve_DIV12(default_value: int):
    div12 = default_value
    if 'DIV12' in os.environ and os.environ['DIV12'].casefold() != 'default':
        div12 = int(os.environ['DIV12'])
    return div12


def resolve_DIVISOR(default_value: int):
    div12 = default_value
    if 'DIVISOR' in os.environ and os.environ['DIVISOR'].casefold() != 'default':
        div12 = int(os.environ['DIVISOR'])
    return div12


def SCL_MODE_description(v: int) -> str:
    if v == 0:
        return 'RegNext'
    elif v == 1:
        return 'MAJ3'
    elif v == 2:
        return '3DFF-synchronizer'
    elif v == 3:
        return 'ANDNOR3-unanimous'
    elif v == 4:
        return '5DFF-synchronizer'
    elif v == 5:
        return 'MAJ5'
    elif v == 6:
        return 'DIRECT'
    elif v == 7:
        return 'ANDNOR5-unanimous'
    else:
        return 'UNKNOWN'


def DIVISOR_description(v: int) -> str:
    if v == 0:
        return '1:1'
    elif v == 1:
        return '1:2'
    elif v == 2:
        return '1:4'
    elif v == 3:
        return '1:8'
    else:
        return 'UNKNOWN'


def CI_matrix():
    ## PUSH_PULL_MODE
    push_pull_mode = [True, False]
    ## SCL_MODE
    scl_mode = range(8)
    ## DIVISOR
    divisor = [0, 0xfff]
    ## CYCLES_PER_BIT
    cycles_per_bit = [3, 6, 10, 11, 12, 25, 50, 100]

    matrix = []
    for a in push_pull_mode:
        for b in scl_mode:
            for c in divisor:
                for d in cycles_per_bit:
                    matrix.append({
                        'PUSH_PULL_MODE': a,
                        'SCL_MODE': b,
                        'DIVISOR': c,
                        'CYCLES_PER_BIT': d
                    })
    return matrix


def resolve_CYCLES_PER_BIT(default_value):
    v = default_value
    if 'CYCLES_PER_BIT' in os.environ and os.environ['CYCLES_PER_BIT'].casefold() != 'default':
        v = int(os.environ['CYCLES_PER_BIT'])

    vv = float(v)
    vv2 = float(v * 2)
    if vv.is_integer():
        cpb = int(vv)
        chb = int(cpb / 2)
        half = False if (cpb % 2) == 0 else True
    elif vv2.is_integer():	# double
        cpb = int(vv)
        chb = int(cpb / 2)
        half = False if (cpb % 2) == 0 else True
    else:
        assert False, f"CYCLES_PER_BIT={CYCLES_PER_BIT} is not supported, needs to be >= 2 and with 0.5 granularity"

    # Is this the best way, maybe there is NamedTuple
    class CFG():
        def __init__(self, cpb, chh, half):
            self._CYCLES_PER_BIT = cpb
            self._CYCLES_PER_HALFBIT = chb
            self._HALF_EDGE = half
            return None

        @property
        def CYCLES_PER_BIT(self):
            return self._CYCLES_PER_BIT

        @property
        def CYCLES_PER_HALFBIT(self):
            return self._CYCLES_PER_HALFBIT

        @property
        def HALF_EDGE(self):
            return self._HALF_EDGE

        def __str__(self):
            return f"CFG(CYCLES_PER_BIT={self.CYCLES_PER_BIT}, CYCLES_PER_HALFBIT={self.CYCLES_PER_HALFBIT}, HALF_EDGE={self.HALF_EDGE})"

    return CFG(cpb, chb, half)


FSM = FSM({
    'phase':  'dut.i2c_bert.myState_1.fsmPhase_stateReg_string',
    'i2c':    'dut.i2c_bert.i2c.fsm_stateReg_string'
})


def frequency_pretty(v) -> str:
    assert type(v) is int or type(v) is float
    if v > 1000000:
        v = round(v / 1000000, 3)
        return f"{v:.3f} Mbps"
    elif v > 1000:
        v = round(v / 1000, 3)
        return f"{v:.3f} Kbps"
    else:
        v = round(v, 3)
        return f"{v:.3f} bps"


def gha_dumpvars(dut):
    dumpvars = ['CI', 'GL_TEST', 'FUNCTIONAL', 'USE_POWER_PINS', 'SIM', 'UNIT_DELAY', 'SIM_BUILD', 'GATES', 'ICARUS_BIN_DIR', 'COCOTB_RESULTS_FILE', 'TESTCASE', 'TOPLEVEL', 'DEBUG', 'LOW_SPEED']
    if 'CI' in os.environ and os.environ['CI'].casefold() != 'false':
        for k in os.environ.keys():
            if k in dumpvars:
                dut._log.info("{}={}".format(k, os.environ[k]))


def bit(byte: int, bitid: int) -> int:
    assert bitid >= 0 and bitid <= 7
    assert (byte & ~0xff) == 0
    mask = 1 << bitid
    return (byte & mask) == mask


def cmd_alu(len4: int = 0, read: bool = False, op_and: bool = False, op_or: bool = False, op_xor: bool = False, op_add: bool = False) -> int:
    v = int((len4 & 0xf) << 4)
    v |= 0x02
    if read:
        v |= 0x01
    if op_and:
        v |= 0x00 << 2
    elif op_or:
        v |= 0x01 << 2
    elif op_xor:
        v |= 0x02 << 2
    elif op_add:
        v |= 0x03 << 2
    return v



@cocotb.test()
async def test_i2c_bert(dut):
    if 'DEBUG' in os.environ and os.environ['DEBUG'] != 'false':
        dut._log.setLevel(cocotb.logging.DEBUG)

    sim_config = SimConfig(dut, cocotb)

    PUSH_PULL_MODE = resolve_PUSH_PULL_MODE(False)
    SCL_MODE = resolve_SCL_MODE(0)
    DIV12 = resolve_DIV12(0)  # (0xfff)
    assert (DIV12 & ~0xfff) == 0
    DIVISOR = resolve_DIVISOR(0)
    assert (DIVISOR & ~0x3) == 0

    TICKS_PER_BIT = 3 #int(CLOCK_FREQUENCY / SCL_CLOCK_FREQUENCY)

    #CYCLES_PER_BIT = 3
    #CYCLES_PER_HALFBIT = 1
    #HALF_EDGE = True

    #CYCLES_PER_BIT = 6
    #CYCLES_PER_HALFBIT = 3
    #HALF_EDGE = False

    #CYCLES_PER_BIT = 8
    #CYCLES_PER_HALFBIT = 4
    #HALF_EDGE = False

    #CYCLES_PER_BIT = 12
    #CYCLES_PER_HALFBIT = 6
    #HALF_EDGE = False

    # This is on edges of 1:8 (we good to refine some aspects)
    #CYCLES_PER_BIT = 24
    #CYCLES_PER_HALFBIT = 12
    #HALF_EDGE = False

    #CYCLES_PER_BIT = 26
    #CYCLES_PER_HALFBIT = 13
    #HALF_EDGE = False

    # 25 chosen at it puts us at 400Kbps for 10MHz (which seems achives "Fast-Mode")
    CFG = resolve_CYCLES_PER_BIT(25)
    dut._log.info(f"{CFG}")
    CYCLES_PER_BIT      = CFG.CYCLES_PER_BIT
    CYCLES_PER_HALFBIT  = CFG.CYCLES_PER_HALFBIT
    HALF_EDGE           = CFG.HALF_EDGE

    # The DUT uses a divider from the master clock at this time
    CLOCK_FREQUENCY = 10000000
    CLOCK_MHZ = CLOCK_FREQUENCY / 1e6
    CLOCK_PERIOD_PS = int(1 / (CLOCK_FREQUENCY * 1e-12)) - 1
    CLOCK_PERIOD_NS = int(1 / (CLOCK_FREQUENCY * 1e-9))

    SCL_CLOCK_FREQUENCY = 1000000

    tb_config = TestBenchConfig(dut, CLOCK_FREQUENCY = CLOCK_FREQUENCY, ALT_CLOCK_FREQUENCY = SCL_CLOCK_FREQUENCY)

    dut._log.info("start")

    #clock = Clock(dut.clk, CLOCK_PERIOD_PS, units="ps")
    clock = Clock(dut.clk, CLOCK_PERIOD_NS, units="ns")
    cocotb.start_soon(clock.start())
    dut._log.info("CLOCK_PERIOD_NS={}".format(CLOCK_PERIOD_NS))
    #dut._log.info("CLOCK_PERIOD_PS={}".format(CLOCK_PERIOD_PS))

    assert design_element_exists(dut, 'clk')
    assert design_element_exists(dut, 'rst_n')
    assert design_element_exists(dut, 'ena')

    gha_dumpvars(dut)

    depth = None
    GL_TEST = resolve_GL_TEST()
    if GL_TEST:
        dut._log.info("GL_TEST={} (detected)".format(GL_TEST))
        #depth = 1

    if GL_TEST:
        dut = ProxyDut(dut)

    report_resolvable(dut, 'initial ', depth=depth, filter=exclude_re_path)

    validate(dut)

    if GL_TEST and 'RANDOM_POLICY' in os.environ:
        await ClockCycles(dut.clk, 1)		## crank it one tick, should assign some non X states
        if os.environ['RANDOM_POLICY'].casefold() == 'zero' or os.environ['RANDOM_POLICY'].casefold() == 'false':
            ensure_resolvable(dut, policy=False, filter=ensure_exclude_re_path)
        elif os.environ['RANDOM_POLICY'].casefold() == 'one' or os.environ['RANDOM_POLICY'].casefold() == 'true':
            ensure_resolvable(dut, policy=True, filter=ensure_exclude_re_path)
        elif os.environ['RANDOM_POLICY'].casefold() == 'random':
            ensure_resolvable(dut, policy='random', filter=ensure_exclude_re_path)
        else:
            assert False, f"RANDOM_POLICY={os.environ['RANDOM_POLICY']} is not supported"
        await ClockCycles(dut.clk, 1)

    await ClockCycles(dut.clk, 1)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0

    await ClockCycles(dut.clk, 6)

    # Latch state setup
    LATCHED_16 = 0xa5
    LATCHED_24 = 0x5a

    dut.ui_in.value = LATCHED_16
    dut.uio_in.value = LATCHED_24
    await ClockCycles(dut.clk, 1)	# need to crank it one for always_latch to work in sim

    dut.ena.value = 1
    await ClockCycles(dut.clk, 4)
    assert dut.ena.value == 1		# validates SIM is behaving as expected

    if not GL_TEST:	# Latch state set
        assert dut.dut.latched_config.latched_ena_ui_in.value == LATCHED_16
        assert dut.dut.latched_config.latched_ena_uio_in.value == LATCHED_24

    # Setup DIVISOR (for powerOnSense test)
    dut.ui_in.value = 0x00 | DIVISOR

    # We waggle this to see if it resolves RANDOM_POLICY=random(iverilog)
    #  where dut.rst_n=0 and dut.dut.rst_n=1 got assigned, need to understand more here
    #  as I would have expected setting dut.rst_n=anyvalue and letting SIM run would
    #  have propagated into dut.dut.rst_n.
    dut.rst_n.value = 0
    if not GL_TEST and False:		## DISABLED ALL ENV
        # TODO I switch to using an _async_reset form of this the todo is to go back to the
        #   original form and manage GL testing concerns
        # sky130_toolbox/glitch_free_clock_mux.v:
        # Uninitialized internal states that depend on each other need to work themselves out.
        dut.dut.i2c_bert.i2c.clockGate.dff01q.value = False
        dut.dut.i2c_bert.i2c.clockGate.dff02q.value = True
        dut.dut.i2c_bert.i2c.clockGate.dff02qn.value = False
        dut.dut.i2c_bert.i2c.clockGate.dff11q.value = False
        dut.dut.i2c_bert.i2c.clockGate.dff12q.value = True
        dut.dut.i2c_bert.i2c.clockGate.dff12qn.value = False
        await ClockCycles(dut.clk, 4)
        dut.dut.i2c_bert.i2c.clockGate.sel.value = not dut.dut.i2c_bert.i2c.clockGate.sel.value
        await ClockCycles(dut.clk, 2)
        dut.dut.i2c_bert.i2c.clockGate.sel.value = not dut.dut.i2c_bert.i2c.clockGate.sel.value
    await ClockCycles(dut.clk, 2)

    POWER_ON_SENSE = bool(random.getrandbits(1))

    dut._log.info(f"Checking #1 powerOnSense state setup {not POWER_ON_SENSE}")
    if GL_TEST:		# so the issue is this X propagates in a bad way and stops the design GL_TEST
        # FIXME make a value using RANDOM_POLICY
        if not POWER_ON_SENSE:
            dut.uio_in.value = BinaryValue('00001000')	# SDA=0 means special power-on condition
        else:
            dut.uio_in.value = BinaryValue('00000000')	# SDA=1 means nomimal power-on condition
    else:
        if not POWER_ON_SENSE:
            dut.uio_in.value = BinaryValue('xxxx1xxx')	# SDA=0 means special power-on condition
        else:
            dut.uio_in.value = BinaryValue('xxxx0xxx')	# SDA=1 means nomimal power-on condition
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)

    # Let the timer.canPowerOnReset fire
    await ClockCycles(dut.clk, (1 << (DIVISOR+2))+CYCLES_PER_BIT+CYCLES_PER_HALFBIT)	# (ticks*4)+BIT+HALFBIT
    dut._log.info(f"Checking #1 powerOnSense state check {str(dut.uio_out.value)} expecting bit7 = {POWER_ON_SENSE}")
    # Validate powerOnSense captured, IHP130_DISABLED_TEST powerOnSense.GATE not seen to fire in gatelevel IHP130
#    if not sim_config.is_verilator:
#        if not POWER_ON_SENSE:
#            assert sim_config.bv_compare_x(str(dut.uio_out.value), '0???????', False, force=GL_TEST), f"uio_out=str(dut.uio_out.value)"
#        else:
#            assert sim_config.bv_compare_x(str(dut.uio_out.value), '1???????', False, force=GL_TEST), f"uio_out=str(dut.uio_out.value)"

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    assert dut.rst_n.value == 0


    # Reset state setup
    v = 0
    # LATCHED is now the same layout as GETCFG
    v = SCL_MODE & 0x7
    if PUSH_PULL_MODE:
        v |= 0x08
    if DIV12 != 0:
        v |= (DIV12 & 0xfff) << 4
    LATCHED_00_08 = v

    LATCHED_00 = LATCHED_00_08 & 0xff 		# 0x34
    LATCHED_08 = (LATCHED_00_08 >> 8) & 0xff	# 0x12

    dut.ui_in.value = LATCHED_00
    dut.uio_in.value = LATCHED_08
    await ClockCycles(dut.clk, 1)	# need to crank it one for always_latch to work in sim

    # Reset state setup
    dut.ui_in.value = 0x00
    dut.uio_in.value = 0x00

    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1)
    assert dut.rst_n.value == 1

    if not GL_TEST:    # Reset state set
        dut.dut.latched_config.latched_rst_n_ui_in.value == LATCHED_00
        dut.dut.latched_config.latched_rst_n_uio_in.value == LATCHED_08

    # Setup DIVISOR
    dut.ui_in.value = 0x00 | DIVISOR

    # Set state a clock or so after start
    await ClockCycles(dut.clk, 1)

    dut._log.info(f"Checking #2 powerOnSense state setup {POWER_ON_SENSE}")
    if GL_TEST:		# so the issue is this X propagates in a bad way and stops the design GL_TEST
        # FIXME make a value using RANDOM_POLICY
        if POWER_ON_SENSE:
            dut.uio_in.value = BinaryValue('00001000')	# SDA=0 means special power-on condition
        else:
            dut.uio_in.value = BinaryValue('00000000')	# SDA=1 means nomimal power-on condition
    else:
        if POWER_ON_SENSE:
            dut.uio_in.value = BinaryValue('xxxx1xxx')	# SDA=0 means special power-on condition
        else:
            dut.uio_in.value = BinaryValue('xxxx0xxx')	# SDA=1 means nomimal power-on condition
    await ClockCycles(dut.clk, (1 << (DIVISOR+2))+CYCLES_PER_BIT+CYCLES_PER_HALFBIT)	# (ticks*4)+BIT+HALFBIT

    dut._log.info(f"Checking #2 powerOnSense state check {str(dut.uio_out.value)} expecting bit7 = {not POWER_ON_SENSE}")

    # Validate powerOnSense captured, IHP130_DISABLED_TEST powerOnSense.GATE not seen to fire in gatelevel IHP130
#    if not sim_config.is_verilator:
#        if POWER_ON_SENSE:
#            assert sim_config.bv_compare_x(str(dut.uio_out.value), '0???????', False, force=GL_TEST), f"uio_out=str(dut.uio_out.value)"
#        else:
#            assert sim_config.bv_compare_x(str(dut.uio_out.value), '1???????', False, force=GL_TEST), f"uio_out=str(dut.uio_out.value)"

    # Let the timer.canPowerOnReset fire
    await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    debug(dut, '001_TEST')


    ctrl = I2CController(dut, CYCLES_PER_BIT = CYCLES_PER_BIT, pp = PUSH_PULL_MODE, GL_TEST = GL_TEST)
    ctrl.try_attach_debug_signals()

    # Verilator VPI hierarchy discovery workaround
    if not GL_TEST and sim_config.is_verilator:
        # Verilator appears to require us to access into the Hierarchy path of items in the form below
        #  before they can be found with discovery APIs.  It appears we only need to access into the
        #  containing object, for the signal siblings to also be found.
        dummy1 = dut.dut.i2c_bert.myState_1.fsmPhase_stateReg_string	# this is the magic: myState_1
        assert design_element_exists(dut, FSM.fsm_signal_path('phase'))

        dummy1 = dut.dut.i2c_bert.i2c.fsm_stateReg_string		# this is the magic: i2c
        assert design_element_exists(dut, FSM.fsm_signal_path('i2c'))

        for hierarchy_path in FSM.values():
            assert design_element_exists(dut, hierarchy_path), f"Verilator signal: {hierarchy_path}"


    fsm_monitors = {}
    if not GL_TEST:
        fsm_monitors['phase'] = FSM.fsm_signal_path('phase')
        fsm_monitors['i2c'] = FSM.fsm_signal_path('i2c')
    MONITOR = Monitor(dut, FSM, fsm_monitors)
    await cocotb.start(MONITOR.build_task())

    # This is a custom capture mechanism of the output encoding
    # Goals:
    #         dumping to a text file and making a comparison with expected output
    #         confirming period where no output occured
    #         confirm / measure output duration of special conditions
    #
    SO = SignalOutput(dut, SIM_SUPPORTS_X = sim_config.SIM_SUPPORTS_X)
    signal_accessor_scl_write = SignalAccessor(dut, 'uio_out', SCL_BITID)	# dut.
    signal_accessor_sda_write = SignalAccessor(dut, 'uio_out', SDA_BITID)	# dut.
    await cocotb.start(SO.register('so', signal_accessor_scl_write, signal_accessor_sda_write))
    # At startup in simulation we see writeEnable asserted and so output
    #SO.assert_resolvable_mode(True)
    #SO.assert_encoded_mode(SO.SE0)
    SO.unregister()		# FIXME

    report_resolvable(dut, depth=depth, filter=exclude_re_path)

    signal_accessor_uio_in = SignalAccessor(dut, 'uio_in')
    signal_accessor_scl = signal_accessor_uio_in.register('uio_in:SCL', SCL_BITID)	# dut.
    signal_accessor_sda = signal_accessor_uio_in.register('uio_in:SDA', SDA_BITID)	# dut.

    #############################################################################################

    ## raw more

    report_resolvable(dut, 'checkpoint001 ', depth=depth, filter=exclude_re_path)

    debug(dut, '001_RAW_READ')

    #CMD_BYTE = 0xb5
    #CMD_BYTE = 0xf1
    CMD_BYTE = 0x01	# CMD_ONE

    ctrl.initialize()
    ctrl.idle()
    await ClockCycles(dut.clk, CYCLES_PER_BIT)

    # PREMABLE
    ctrl.set_sda_scl(True, True)
    await ClockCycles(dut.clk, CYCLES_PER_BIT)

    # PREMABLE (scl toggle test, false START test)
    ctrl.scl = False
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.scl = True
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.scl = False
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.scl = True
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    # FIXME observe FSM is in HUNT and does not change state at any point

    await ClockCycles(dut.clk, CYCLES_PER_BIT)

    # PREMABLE (scl=0, sda toggle test, false START test)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.scl = False	# SCL
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.sda = False
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.sda = True
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.sda = False
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.sda = True
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    ctrl.scl = True	# SCL
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    # FIXME observe FSM is in HUNT and does not change state at any point

    ctrl.idle()
    await ClockCycles(dut.clk, CYCLES_PER_BIT)
    await ClockCycles(dut.clk, CYCLES_PER_BIT)

    # Need to resolve Z state into signal
    ctrl.set_sda_scl(True, True)	# START transition (simulation setup)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    # START
    ctrl.set_sda_scl(False, True)	# START transition (setup)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.sda = False			# START transition
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    # DATA
    ctrl.set_sda_scl(bit(CMD_BYTE, 7), False)	# bit7=1
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 6), False)	# bit6=0
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 5), False)	# bit5=1
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 4), False)	# bit4=1
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 3), False)	# bit3=0
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 2), False)	# bit2=1
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 1), False)	# bit1=0
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(bit(CMD_BYTE, 0), False)	# bit0=0 (WRITE)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.set_sda_scl(None, False)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ## SAMPLE
    if ctrl.sda_oe:
        nack = ctrl.sda_rx
    elif not ctrl._modeIsPP:
        nack = ctrl.PULLUP	# open-drain
    else:
        nack = None
    assert nack is ctrl.ACK

    ctrl.scl = True		## FIXME check SDA still idle
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    # STOP
    ctrl.set_sda_scl(False, False)		# SDA setup to ensure transition
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    ctrl.scl = True
    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.sda = True				# STOP transition
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)
    if HALF_EDGE:
        await FallingEdge(dut.clk)

    if HALF_EDGE:
        await RisingEdge(dut.clk)
    await ClockCycles(dut.clk, CYCLES_PER_HALFBIT)

    ctrl.idle()

    debug(dut, '')
    await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ## cooked mode

    report_resolvable(dut, 'checkpoint002 ', depth=depth, filter=exclude_re_path)

    CAN_ASSERT = True

    debug(dut, '002_COOKED_WRITE')

    await ctrl.send_start()

    await ctrl.send_data(0x00)
    nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
    assert nack is ctrl.ACK

    await ctrl.send_data(0xff)
    nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
    assert nack is ctrl.ACK

    assert await ctrl.check_recv_is_idle()
    await ctrl.send_stop()
    ctrl.idle()
    assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

    debug(dut, '')
    await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    report_resolvable(dut, 'checkpoint090 ', depth=depth, filter=exclude_re_path)

    if run_this_test(True):
        debug(dut, '090_RESET')

        await ctrl.send_start()

        await ctrl.send_data(0xf0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):		# moved above ACK/NACK as it confirms the h/w view of PP/OD
        debug(dut, '100_GETCFG')

        await ctrl.send_start()

        await ctrl.send_data(0xc1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETCFG[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        # GETCFG is now the same layout as LATCHED
        # bit0.2  SCL MODE
        # bit3    PULLUP MODE
        v = SCL_MODE & 0x7	# [2:0]
        if PUSH_PULL_MODE:
            v |= 0x08		# bit3
        assert data == v

        ctrl.sda_idle()
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '110_ACK_wr')

        await ctrl.send_start()

        await ctrl.send_data(0x80)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '120_ACK_rd')

        await ctrl.send_start()

        await ctrl.send_data(0x81)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '130_NACK_wr')

        await ctrl.send_start()

        await ctrl.send_data(0x84)
        nack = await ctrl.recv_ack(ctrl.NACK, CAN_ASSERT)
        assert nack is ctrl.NACK	# NACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '140_NACK_rd')

        await ctrl.send_start()

        await ctrl.send_data(0x85)
        nack = await ctrl.recv_ack(ctrl.NACK, CAN_ASSERT)
        assert nack is ctrl.NACK	# NACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '150_GETLEN')

        await ctrl.send_start()

        await ctrl.send_data(0xd1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETLEN[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0x00

        ctrl.sda_idle()
        debug(dut, '.')
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '160_GETENDS')

        await ctrl.send_start()

        await ctrl.send_data(0xe1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETENDS[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == (DIV12 & 0xff) ^ 0xff # 0x05

        data = await ctrl.recv_data()
        dut._log.info(f"GETENDS[1] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == ((DIV12 & 0xf00) >> 8) ^ 0xf # 0x00

        ctrl.sda_idle()
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    report_resolvable(dut, 'checkpoint430 ', depth=depth, filter=exclude_re_path)

    if run_this_test(True):
        debug(dut, '170_GETLATCH')

        await ctrl.send_start()

        await ctrl.send_data(0xf1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"LATCH[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == LATCHED_00

        data = await ctrl.recv_data()
        dut._log.info(f"LATCH[1] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == LATCHED_08

        data = await ctrl.recv_data()
        dut._log.info(f"LATCH[2] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == LATCHED_16

        data = await ctrl.recv_data()
        dut._log.info(f"LATCH[3] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == LATCHED_24

        ctrl.sda_idle()
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '180_GETLED')

        await ctrl.send_start()

        await ctrl.send_data(0xd1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETLED[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0x00

        ctrl.sda_idle()
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '200_SETDATA')

        await ctrl.send_start()

        await ctrl.send_data(0xf8)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x69
        await ctrl.send_data(data)
        dut._log.info(f"SETDATA[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '205_GETDATA')

        await ctrl.send_start()

        await ctrl.send_data(0xf9)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 1
        for pos in range(maxpos):
            data = await ctrl.recv_data()
            dut._log.info(f"GETDATA[{pos}] = {str(data)}  0x{data:02x}")
            await ctrl.send_ack()
            assert data == 0x69

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '210_SETENDS')

        await ctrl.send_start()

        await ctrl.send_data(0xe0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0xed
        await ctrl.send_data(data)
        dut._log.info(f"SETENDS[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x0f
        await ctrl.send_data(data)
        dut._log.info(f"SETENDS[1] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '215_GETENDS')

        await ctrl.send_start()

        await ctrl.send_data(0xe1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETENDS[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0xed

        data = await ctrl.recv_data()
        dut._log.info(f"GETENDS[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0x0f

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '220_SETLEN')

        await ctrl.send_start()

        await ctrl.send_data(0xd0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x23
        await ctrl.send_data(data)
        dut._log.info(f"SETLEN[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '225_GETLEN')

        await ctrl.send_start()

        await ctrl.send_data(0xd1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETLEN[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0x23

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(False) and False:	# DISABLED ALL ENV
        debug(dut, '229_SETLEN_RESTORE')

        await ctrl.send_start()

        await ctrl.send_data(0xd0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x00
        await ctrl.send_data(data)
        dut._log.info(f"SETLEN[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '230_SETLED')

        await ctrl.send_start()

        await ctrl.send_data(0xf4)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x78	# "t" letter, for TT, or Test!
        await ctrl.send_data(data)
        dut._log.info(f"SETLED[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        expected = data
        data = dut.uo_out.value
        dut._log.info(f"SETLED[0] = uo_out={data}")
        assert expected == data, f"expect != actual  {expected} != {data:#02x}"

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '235_GETLED')

        await ctrl.send_start()

        await ctrl.send_data(0xf5)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETLED[{pos}] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        assert data == 0x78

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)



    if run_this_test(True):
        debug(dut, '240_SETCFG')

        await ctrl.send_start()

        await ctrl.send_data(0xc0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x00
        await ctrl.send_data(data)
        dut._log.info(f"SETCFG[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.NACK, CAN_ASSERT)
        assert nack is ctrl.NACK		## NACK not implemented right now

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '245_GETCFG')

        await ctrl.send_start()

        await ctrl.send_data(0xc1)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"GETCFG[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        ctrl.sda_idle()
        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(False) and False:	# DISABLED ALL ENV
        debug(dut, '249_SETCFG_RESTORE')

        await ctrl.send_start()

        await ctrl.send_data(0xc0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        # GETCFG not the same layout as LATCHED
        # bit0..2  SCL MODE
        # bit3     PULLUP MODE
        v = 0
        v = SCL_MODE & 0x7	# [2:0]
        if PUSH_PULL_MODE:
            v |= 0x08	# bit3
        assert data == v

        data = v
        await ctrl.send_data(data)
        dut._log.info(f"SETCFG[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.NACK, CAN_ASSERT)
        assert nack is ctrl.NACK	## NACK not implemented right now

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    # After disrupting settings issue another reset
    # FIXME ideally go and check and retest the defaults were restored
    if run_this_test(True):
        debug(dut, '299_RESET')

        await ctrl.send_start()

        await ctrl.send_data(0xf0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################


    if run_this_test(True):
        debug(dut, '300_SETDATA')

        await ctrl.send_start()

        await ctrl.send_data(0xf8)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x87
        await ctrl.send_data(data)
        dut._log.info(f"SETDATA[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '300_ALU_ADD')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=False, len4=0, op_add=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x03)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '310_GETSEND')

        await ctrl.send_start()

        await ctrl.send_data(0xfd)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 2
        for pos in range(maxpos):
            data = await ctrl.recv_data()
            dut._log.info(f"SEND[{pos}] = {str(data)}  0x{data:02x}")
            nack = ctrl.ACK if pos != (maxpos - 1) else ctrl.NACK
            await ctrl.send_acknack(nack)
            assert data == (0x87 + 0x03)

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '320_ALU_XOR')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=False, len4=1, op_xor=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x08)	# 0x8a => 0x83
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0xc0)	# 0x83 => 0x43
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '330_GETSEND')

        await ctrl.send_start()

        await ctrl.send_data(0xfd)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 3
        for pos in range(maxpos):
            data = await ctrl.recv_data()
            dut._log.info(f"SEND[{pos}] = {str(data)}  0x{data:02x}")
            nack = ctrl.ACK if pos != (maxpos - 1) else ctrl.NACK
            await ctrl.send_acknack(nack)
            assert data == (0x87 + 0x03) ^ 0x08 ^ 0xc0

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '340_ALU_OR')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=False, len4=2, op_or=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x01)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x02)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x08)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '350_GETSEND')

        await ctrl.send_start()

        await ctrl.send_data(0xfd)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 4
        for pos in range(maxpos):
            data = await ctrl.recv_data()
            dut._log.info(f"SEND[{pos}] = {str(data)}  0x{data:02x}")
            nack = ctrl.ACK if pos != (maxpos - 1) else ctrl.NACK
            await ctrl.send_acknack(nack)
            assert data == ((0x87 + 0x03) ^ 0x08 ^ 0xc0) | 0x01 | 0x02 | 0x08

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '360_ALU_AND')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=False, len4=3, op_and=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0xfe)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0xfd)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0x7f)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        await ctrl.send_data(0xf7)	#
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '370_GETSEND')

        await ctrl.send_start()

        await ctrl.send_data(0xfd)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 5
        for pos in range(maxpos):
            data = await ctrl.recv_data()
            dut._log.info(f"SEND[{pos}] = {str(data)}  0x{data:02x}")
            nack = ctrl.ACK if pos != (maxpos - 1) else ctrl.NACK
            await ctrl.send_acknack(nack)
            assert data == (((0x87 + 0x03) ^ 0x08 ^ 0xc0) | 0x01 | 0x02 | 0x08) & 0xfe & 0xfd & 0x7f & 0xf7

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    ##############################################################################################


    if run_this_test(True):
        debug(dut, '500_ALUR_ADD')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=True, len4=0, op_add=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_ADD[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '510_SETRECV')

        await ctrl.send_start()

        await ctrl.send_data(0xfc)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 2
        for pos in range(maxpos):
            data = 0x30
            await ctrl.send_data(data)
            nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
            dut._log.info(f"RECV[{pos}] = {str(data)}  0x{data:02x}")
            assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '520_ALUR_XOR')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=True, len4=1, op_xor=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_XOR[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_XOR[1] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '530_SETRECV')

        await ctrl.send_start()

        await ctrl.send_data(0xfc)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 3
        for pos in range(maxpos):
            data = 0x30 + pos
            await ctrl.send_data(data)
            nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
            dut._log.info(f"RECV[{pos}] = {str(data)}  0x{data:02x}")
            assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '540_ALUR_OR')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=True, len4=2, op_or=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_OR[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_OR[1] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALU_OR[2] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '550_SETRECV')

        await ctrl.send_start()

        await ctrl.send_data(0xfc)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 4
        for pos in range(maxpos):
            data = 0x30
            await ctrl.send_data(data)
            nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
            dut._log.info(f"RECV[{pos}] = {str(data)}  0x{data:02x}")
            assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '560_ALUR_AND')

        await ctrl.send_start()

        await ctrl.send_data(cmd_alu(read=True, len4=3, op_and=True))
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_AND[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_AND[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_AND[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        data = await ctrl.recv_data()
        dut._log.info(f"ALUR_AND[0] = {str(data)}  0x{data:02x}")
        await ctrl.send_ack()
        ## FIXME assert data == 0x00

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '570_SETRECV')

        await ctrl.send_start()

        await ctrl.send_data(0xfc)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        maxpos = 5
        for pos in range(maxpos):
            data = 0x30
            await ctrl.send_data(data)
            nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
            dut._log.info(f"RECV[{pos}] = {str(data)}  0x{data:02x}")
            assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '580_OUTMUX')

        expected = 0x78 # FIXME check this copied from actual found
        data = dut.uo_out.value
        dut._log.info(f"SETLEDAC[0] = uo_out={data} (before command)")
        assert expected == data, f"expected != actual  {expected} != {data:#02x}"

        current_ui_in = 0x00 | DIVISOR # taken from line 681
        dut.ui_in.value = current_ui_in | 0x80
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4) # hold it for a time to find it in VCD

        expected = 0x4e # FIXME check this copied from actual found
        data = dut.uo_out.value # confirm change occured
        dut._log.info(f"SETLEDAC[0] = uo_out={data} (after command)")
        assert expected == data, f"expected != actual  {expected} != {data:#02x}"

        dut.ui_in.value = current_ui_in
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

        expected = 0x78 # FIXME check this copied from actual found
        data = dut.uo_out.value
        dut._log.info(f"SETLEDAC[0] = uo_out={data} (before command)")
        assert expected == data, f"expected != actual  {expected} != {data:#02x}"


    if run_this_test(True):
        debug(dut, '590_SETLEDAC')

        expected = 0x78 # FIXME check this copied from actual found
        data = dut.uo_out.value
        dut._log.info(f"SETLEDAC[0] = uo_out={data} (before command)")
        assert expected == data, f"expected != actual  {expected} != {data:#02x}"

        await ctrl.send_start()

        await ctrl.send_data(0xc4)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        expected = 0x4e # FIXME check this copied from actual found
        data = dut.uo_out.value # confirm change occured
        dut._log.info(f"SETLEDAC[0] = uo_out={data} (after command)")
        assert expected == data, f"expected != actual  {expected} != {data:#02x}"

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)



    ##############################################################################################

    if run_this_test(True):
        debug(dut, '800_AUTOBAUD')

        await ctrl.send_start()

        await ctrl.send_data(0xcc)
        # FIXME this NACKs as noimpl
        nack = await ctrl.recv_ack(ctrl.NACK, CAN_ASSERT)
        assert nack is ctrl.NACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '850_SETLEN_STRETCH')

        await ctrl.send_start()

        await ctrl.send_data(0xd0)
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        data = 0x80
        await ctrl.send_data(data)
        dut._log.info(f"SETLEN[0] = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack(ctrl.ACK, CAN_ASSERT)
        assert nack is ctrl.ACK

        assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '860_STRETCH_rd')

        await ctrl.send_start()
        await ctrl.send_data(0xc8)

        # copied from ctrl.recv_ack()
        ctrl.set_sda_scl(None, False)           # SDA idle
        await ClockCycles(dut.clk, ctrl.CYCLES_PER_HALFBIT)
        if ctrl.HALFEDGE:
            await FallingEdge(dut.clk)

        # FIXME this ACKs but notested

        # FIXME need to add sense on SCL after we try to rise
        if not GL_TEST:
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'STRETCH', CYCLES_PER_BIT) # need to start observing this earlier to catch it

        # 128 due to SETLEN=0x80
        if not GL_TEST:
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'ACKNACK', 128*CYCLES_PER_BIT) # need to start observing this earlier to catch it
        else:
            await ClockCycles(dut.clk, CYCLES_PER_BIT*128) # SETLEN=0x80
        dut._log.info(f"STRETCH finished")

        # The ACKNACK is deferred when stretching
        nack = ctrl.sda_rx_resolve()
        dut._log.info(f"STRETCH-POST-ACKNACK = {nack} (0=ACK, 1=NACK, expect ACK)")

        ctrl.scl = True

        if ctrl.HALFEDGE:
            await RisingEdge(dut.clk)
        await ClockCycles(dut.clk, ctrl.CYCLES_PER_HALFBIT)

        assert nack is ctrl.ACK

        # Now process the data that exists after

        data = await ctrl.recv_data()
        dut._log.info(f"STRETCH = {str(data)}  0x{data:02x}")
        nack = await ctrl.recv_ack()
        #assert nack is None	## FIXME

        #assert await ctrl.check_recv_is_idle()
        await ctrl.send_stop()
        ctrl.idle()
        #assert await ctrl.check_recv_has_been_idle(CYCLES_PER_BIT*3)

        if not GL_TEST:
            #assert FSM.fsm_state_expected(dut, 'i2c', 'STRETCH')
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', 260*CYCLES_PER_BIT) # need to start obserbing this earlier to catch it

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    ##############################################################################################

    ## FIXME need to cover different kinds of STOP (with/without extra SCL=0)
    ## FIXME need to cover different kinds of START (SDA=0>1 and SCL=0>1 transition, followed by SDA=1>0)
    ## FIXME need to cover different kinds of START (SDA=0>1 then SCL=0>1 transition, followed by SDA=1>0)
    ## FIXME need to cover different kinds of START (SCL=0>1 then SDA=0>1 transition, followed by SDA=1>0)

    # FIXME observe FSM cycle RESET->HUNT

    if run_this_test(True):
        debug(dut, '940_TIMEOUT_START')

        ctrl.idle()

        await ctrl.send_start()
        # FIXME check timeoutError actually occurs (within a reasonable time)

        ctrl.idle()
        await ClockCycles(dut.clk, CYCLES_PER_BIT*12)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        for bitid in range(8):
            debug(dut, f"95{bitid}_TIMEOUT_{bitid}BITS")

            ctrl.idle()

            await ctrl.send_start()
            for loop in range(bitid):
                await ctrl.send_bit(bool(random.getrandbits(1)))

            if not GL_TEST:
                assert FSM.fsm_state_expected(dut, 'i2c', 'RECV')

            # FIXME check timeoutError actually occurs (within a reasonable time)
            await ClockCycles(dut.clk, CYCLES_PER_BIT*165) # FIXME maybe scale with timeout limit, see exit summary 'Timeout Limit'

            if not GL_TEST:        # observe FSM cycle returns to HUNT soon
                assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', CYCLES_PER_BIT)

            ctrl.idle()
            await ClockCycles(dut.clk, CYCLES_PER_BIT*12)

            debug(dut, '')
            await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        for bitid in range(8):
            debug(dut, f"96{bitid}_STOP_{bitid}BITS")

            ctrl.idle()

            await ctrl.send_start()
            for loop in range(bitid):
                await ctrl.send_bit(bool(random.getrandbits(1)))
            await ctrl.send_stop();

            if not GL_TEST:        # observe FSM cycle returns to HUNT soon
                # at 7BITs the transaction is as good as sent, so ACKNACK is the next state
                expected_state = 'HUNT' if(bitid < 7) else 'ACKNACK'
                #assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')	 # CPB <= 4 this fails
                #assert await FSM.fsm_state_expected_within(dut, 'i2c', 'RESET', CYCLES_PER_BIT) # need to start obserbing this earlier to catch it
                assert await FSM.fsm_state_expected_within(dut, 'i2c', expected_state, CYCLES_PER_BIT)

            if bitid >= 7: # need to make it timeout
                await ClockCycles(dut.clk, CYCLES_PER_BIT*165) # FIXME maybe scale with timeout limit, see exit summary 'Timeout Limit'
                if not GL_TEST: # ensure it gets to HUNT state ready for next test
                    assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', CYCLES_PER_BIT)

            ctrl.idle()
            await ClockCycles(dut.clk, CYCLES_PER_BIT*12)

            debug(dut, '')
            await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '970_TIMEOUT_STARTSTOP')

        ctrl.idle()

        await ctrl.send_start()
        if not GL_TEST:
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'RECV', CYCLES_PER_BIT)
        await ctrl.send_stop()
        if not GL_TEST:        # observe FSM cycle returns to HUNT soon
            #assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')	 # CPB <= 4 this fails
            #assert await FSM.fsm_state_expected_within(dut, 'i2c', 'RESET', CYCLES_PER_BIT) # need to start obserbing this earlier to catch it
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', CYCLES_PER_BIT)

        ctrl.idle()
        await ClockCycles(dut.clk, CYCLES_PER_BIT*12)

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '980_STOPTEST1')

        ctrl.idle()
        if not GL_TEST:
            assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')

        await ctrl.send_stop()
        if not GL_TEST:        # observe FSM cycle RESET->HUNT
            #assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')	# CPB <= 4 this fails
            #assert await FSM.fsm_state_expected_within(dut, 'i2c', 'RESET', CYCLES_PER_BIT) # need to start obserbing this earlier to catch it
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', CYCLES_PER_BIT)

        ctrl.idle()

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)


    if run_this_test(True):
        debug(dut, '990_STOPTEST2')

        ctrl.idle()
        if not GL_TEST:
            assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')

        await ctrl.send_stop()
        if not GL_TEST:        # observe FSM cycle RESET->HUNT
            #assert FSM.fsm_state_expected(dut, 'i2c', 'HUNT')	# CPB <= 4 this fails
            #assert await FSM.fsm_state_expected_within(dut, 'i2c', 'RESET', CYCLES_PER_BIT) # need to start obserbing this earlier to catch it
            assert await FSM.fsm_state_expected_within(dut, 'i2c', 'HUNT', CYCLES_PER_BIT)

        ctrl.idle()

        debug(dut, '')
        await ClockCycles(dut.clk, CYCLES_PER_BIT*4)

    ##############################################################################################

    await ClockCycles(dut.clk, 256)

    ##############################################################################################

    if run_this_test(True):
        debug(dut, '990_CMD00_RESET')

    # LATCH reset
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await ClockCycles(dut.clk, 4)

    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 1)

    if not GL_TEST:	# Latch state zeroed?
        assert dut.dut.latched_config.latched_rst_n_ui_in.value == 0x00
        assert dut.dut.latched_config.latched_rst_n_uio_in.value == 0x00

    await ClockCycles(dut.clk, 3)

    dut.ena.value = 0
    await ClockCycles(dut.clk, 1)

    if not GL_TEST:	# Latch state zeroed?
        assert dut.dut.latched_config.latched_ena_ui_in.value == 0x00
        assert dut.dut.latched_config.latched_ena_uio_in.value == 0x00

    await ClockCycles(dut.clk, 3)

    ##############################################################################################

    debug(dut, '999_DONE')


    MONITOR.shutdown()

    await ClockCycles(dut.clk, 32)

    report_resolvable(dut, filter=exclude_re_path)

    sclk_est_1mhz  =  1000000 / CYCLES_PER_BIT
    sclk_est_10mhz = 10000000 / CYCLES_PER_BIT
    sclk_est_25mhz = 25000000 / CYCLES_PER_BIT
    sclk_est_50mhz = 50000000 / CYCLES_PER_BIT
    sclk_est_66mhz = 66000000 / CYCLES_PER_BIT
    timeout_limit  = round(4095 / CYCLES_PER_BIT, 2)
    TIMEOUT = (DIV12 & 0xfff) ^ 0xfff
    timeout_actual = round(TIMEOUT / CYCLES_PER_BIT, 2)

    dut._log.info(f"TEST SCL CONFIGURATION:")
    dut._log.info(f"  CYCLES_PER_BIT     = {CYCLES_PER_BIT}  (timeout limit {timeout_limit:.2f} bits)")
    dut._log.info(f"  CYCLES_PER_HALFBIT = {CYCLES_PER_HALFBIT}")
    dut._log.info(f"  HALF_EDGE          = {HALF_EDGE}")
    dut._log.info(f"  SYS_CLOCK  1 Mhz   = SCLK {frequency_pretty(sclk_est_1mhz)}")
    dut._log.info(f"  SYS_CLOCK 10 Mhz   = SCLK {frequency_pretty(sclk_est_10mhz)}")
    dut._log.info(f"  SYS_CLOCK 25 Mhz   = SCLK {frequency_pretty(sclk_est_25mhz)}")
    dut._log.info(f"  SYS_CLOCK 50 Mhz   = SCLK {frequency_pretty(sclk_est_50mhz)}")
    dut._log.info(f"  SYS_CLOCK 66 Mhz   = SCLK {frequency_pretty(sclk_est_66mhz)}")
    dut._log.info(f"TEST ENV CONFIGURATION:")
    dut._log.info(f"  DIV12              = {DIV12} (0x{DIV12:x}) (as 0x{TIMEOUT:x} timeout {timeout_actual:.2f} bits)")
    dut._log.info(f"  SCL_MODE           = {SCL_MODE} ({SCL_MODE_description(SCL_MODE)})")
    dut._log.info(f"  PUSH_PULL_MODE     = {PUSH_PULL_MODE}")
    dut._log.info(f"  DIVISOR            = {DIVISOR} ({DIVISOR_description(DIVISOR)})")

