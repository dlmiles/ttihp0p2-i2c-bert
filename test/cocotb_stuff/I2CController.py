#
#
#
#
#
#
#
#
# SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

from cocotb_stuff import *
from cocotb.utils import get_sim_time
from cocotb_stuff.cocotbutil import *
from cocotb_stuff.SignalAccessor import *

class I2CController():
    SIGNAL_LIST = [
        'SCL_ie', 'SCL_od', 'SCL_pp', 'SCL_og', 'SCL_pg', 'SCL_os', 'SCL_ps',
        'SDA_ie', 'SDA_od', 'SDA_pp', 'SDA_og', 'SDA_pg', 'SDA_os', 'SDA_ps'
    ]
    PULLUP = True
    HIZ = 'z'
    PREFIX = "dut.debug_"

    # Line state constants
    ACK = False
    NACK = True

    def __init__(self, dut, CYCLES_PER_BIT: int, pp: bool = False, GL_TEST: bool = False):
        self._dut = dut
        self.GL_TEST = GL_TEST

        self.CYCLES_PER_BIT = CYCLES_PER_BIT
        self.HALFEDGE = CYCLES_PER_BIT % 2 != 0
        self.CYCLES_PER_HALFBIT = int(CYCLES_PER_BIT / 2)

        self._dut._log.info(f"I2CController(CYCLES_PER_BIT={self.CYCLES_PER_BIT}, HALFEDGE={self.HALFEDGE}, CYCLES_PER_HALFBIT={self.CYCLES_PER_HALFBIT})")

        self._sa_uio_in = SignalAccessor(dut, 'uio_in')	# FIXME pull from shared registry ?
        # This is a broken idea (over VPI) use self._sdascl
        #self._scl = self._sa.register('uio_in:SCL', SCL_BITID)
        #self._sda = self._sa.register('uio_in:SDA', SDA_BITID)
        self._sdascl = self._sa_uio_in.register('uio_in', SCL_BITID, SDA_BITID)

        # uio_out: This is output from peer, and input/receiver side for us
        self._sa_uio_out = SignalAccessor(dut, 'uio_out')	# FIXME pull from shared registry ?
        self._sdascl_out = self._sa_uio_out.register('uio_out', SCL_BITID, SDA_BITID)
        # uio_oe: This is peer OE
        self._sa_uio_oe = SignalAccessor(dut, 'uio_oe')	# FIXME pull from shared registry ?
        self._sdascl_oe = self._sa_uio_oe.register('uio_oe', SCL_BITID, SDA_BITID)

        self._scl_state = self.PULLUP
        self._sda_state = self.PULLUP

        self._scl_idle = True
        self._sda_idle = True

        self._modeIsPP = pp

        self._haveSclIe     = False
        self._haveSclLineOD = False
        self._haveSclLinePP = False
        self._haveSclLineOG = False
        self._haveSclLinePG = False
        self._haveSclLineOS = False
        self._haveSclLinePS = False

        self._haveSdaIe     = False
        self._haveSdaLineOD = False
        self._haveSdaLinePP = False
        self._haveSdaLineOG = False
        self._haveSdaLinePG = False
        self._haveSdaLineOS = False
        self._haveSdaLinePS = False

        self._check_recv_idle_start = False


    def try_attach_debug_signals(self) -> bool:
        self._haveSclIe     = design_element_exists(self._dut, self.PREFIX + "SCL_ie")
        self._haveSclLineOD = design_element_exists(self._dut, self.PREFIX + "SCL_od")
        self._haveSclLinePP = design_element_exists(self._dut, self.PREFIX + "SCL_pp")
        self._haveSclLineOG = design_element_exists(self._dut, self.PREFIX + "SCL_og")
        self._haveSclLinePG = design_element_exists(self._dut, self.PREFIX + "SCL_pg")
        self._haveSclLineOS = design_element_exists(self._dut, self.PREFIX + "SCL_os")
        self._haveSclLinePS = design_element_exists(self._dut, self.PREFIX + "SCL_ps")

        self._haveSdaIe     = design_element_exists(self._dut, self.PREFIX + "SDA_ie")
        self._haveSdaLineOD = design_element_exists(self._dut, self.PREFIX + "SDA_od")
        self._haveSdaLinePP = design_element_exists(self._dut, self.PREFIX + "SDA_pp")
        self._haveSdaLineOG = design_element_exists(self._dut, self.PREFIX + "SDA_og")
        self._haveSdaLinePG = design_element_exists(self._dut, self.PREFIX + "SDA_pg")
        self._haveSdaLineOS = design_element_exists(self._dut, self.PREFIX + "SDA_os")
        self._haveSdaLinePS = design_element_exists(self._dut, self.PREFIX + "SDA_ps")

        self.report()

        self.idle()

        # We shall just work return value off these two signals
        return self._haveSclIe or self._haveSdaIe


    def report(self):
        for n in self.SIGNAL_LIST:
            self._dut._log.info("{}{} = {}".format(self.PREFIX, n, design_element_exists(self._dut, self.PREFIX + n)))


    def initialize(self, PP: bool = None) -> None:
        self.scl = self._scl_state
        self.sda = self._sda_state

        if type(PP) is bool:
            print(f"initialize(PP={PP})")
            self._modeIsPP = PP


    async def cycles_after_setup(self):
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
        if self.HALFEDGE:
            await FallingEdge(self._dut.clk)


    async def cycles_after_hold(self):
        if self.HALFEDGE:
            await RisingEdge(self._dut.clk)
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)


    async def send_start(self):
        assert self.sda
        assert self.scl

        if self._sda_idle or self._scl_idle:
            # Probably not needed as line state is like this already but it looks better on VCD
            self.set_sda_scl(True, True)
            await self.cycles_after_hold()
            #await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)

        self.set_sda_scl(False, True)	# START transition (setup)
        await self.cycles_after_setup()

        self.sda = False		# START transition
        await self.cycles_after_hold()


    async def send_stop(self) -> None:
        assert self.scl
        self.set_sda_scl(False, False)	# SDA setup for STOP transition
        await self.cycles_after_setup()

        self.scl = True
        await self.cycles_after_hold()

        self.sda = True			# STOP condition
        await self.cycles_after_setup()


    async def send_data(self, byte: int) -> None:
        for bitid in reversed(range(8)):
            m = 1 << bitid
            bf = True if((byte & m) != 0) else False

            self.set_sda_scl(bf, False)       # bitN
            await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
            if self.HALFEDGE:
                await FallingEdge(self._dut.clk)

            self.scl = True
            if self.HALFEDGE:
                await RisingEdge(self._dut.clk)
            await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)


    # no_pullup this disables any pullup interpretion of line state
    # tx_overlay this concerns if our TX situation is visible to the return value
    def sda_rx_resolve(self, no_pullup: bool = False, tx_overlay: bool = False) -> bool:
        if tx_overlay and not self._sda_idle:
            v = self._sda_state	# not idle, TX will overide any RX value (because we can't RX when we TX)
        elif self.sda_oe:
            v = self.sda_rx
        elif not self._modeIsPP and not no_pullup:
            v = self.PULLUP	# open-drain
        else:
            v = None
        return v


    async def recv_ack(self, expect: bool = None, can_assert: bool = False) -> bool:
        assert self.scl

        self.set_sda_scl(None, False)		# SDA idle
        # FIXME inject noise here (all 1 until last, all 0 until last, random until last,
        #  random for a bit, then all 1 until last - this seems realistic, noise during transition, then settle, then sample
        #  we would expect filtering to take effect
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
        if self.HALFEDGE:
            await FallingEdge(self._dut.clk)

        nack = self.sda_rx_resolve()

        self.scl = True

        if self.HALFEDGE:
            await RisingEdge(self._dut.clk)
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)

        # Ok we try to perform a bit of a diagnostic as the ACK/NACK part seems an
        #  important thing and tricky to understand what the corrective action is
        #  and which side is at fault
        if expect is not None:
            expect_s = 'NACK' if expect is self.NACK else 'ACK'
            nack_s = 'NACK' if nack is self.NACK else 'ACK'

            warn = False
            need_assert = False

            desc = ""
            if not self._sda_idle:
                desc = f"WARN: TB is still driving SDA IE=1 so can not rx DUT"
                warn = True
            elif not self.sda_oe and self._modeIsPP:
                desc = f"WARN: DUT has not set SDA OE to drive line (mode=PP)"
                warn = True
            elif self.sda_oe and not self.sda_rx is self.ACK:
                desc = f"DUT is driving ACK state"
            elif self.sda_oe and self.sda_rx is self.NACK:
                if self._modeIsPP:
                    desc = f"DUT is driving NACK state"
                else:
                    desc = f"WARN: DUT is driving NACK state, but in open-drain it should use pull-up and set OE=0 (mode=OD)"
                    warn = True

            ie = not self._sda_idle
            if self._haveSdaIe:
                ie = str(self._dut.dut.debug_SDA_ie.value)

            # We only report one issue (the one to fix first)
            if expect is not nack:
                self._dut._log.warning(f"recv_ack(expect={expect}[{expect_s}]) EXPECT FAILED actual={nack}[{nack_s}] oe={self.sda_oe} rx={self.sda_rx} ie={ie} ({desc})")
                need_assert = True
            elif not self._modeIsPP and self.sda_oe and self.sda_rx is self.NACK:
                self._dut._log.warning(f"recv_ack(expect={expect}[{expect_s}]) OPEN-DRAIN FAILED oe={self.sda_oe} rx={self.sda_rx} ie={ie} ({desc})")
                need_assert = True
            elif warn:
                self._dut._log.warning(f"recv_ack(expect={expect}[{expect_s}]) WARNING actual={nack}[{nack_s}] oe={self.sda_oe} rx={self.sda_rx} ie={ie} ({desc}))")

            if not self.GL_TEST:	# FIXME reinstante this
                if can_assert and need_assert:
                    assert False, f"recv_ack(expect={expect}[{expect_s}]) but line state is {nack}[{nack_s}]"

        return nack


    async def recv_data(self, bit_count: int = 8) -> int:
        assert bit_count > 0
        assert self.scl
        value = 0
        for bitid in reversed(range(bit_count)):
            bit_mask = 1 << bitid

            self.set_sda_scl(None, False)       # idle SDA
            await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
            if self.HALFEDGE:
                await FallingEdge(self._dut.clk)

            self.scl = True
            ## FIXME check driver etc... perform diagnostic, reuse recv_nack() logic ?
            bit_value = self.sda_rx_resolve()
            if bit_value:
                value |= bit_mask

            if self.HALFEDGE:
                await RisingEdge(self._dut.clk)
            await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
        return value


    async def send_bit(self, bit: bool = False, idle_exit: bool = False) -> None:
        assert self.scl

        self.set_sda_scl(bit, False)
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)
        if self.HALFEDGE:
            await FallingEdge(self._dut.clk)

        self.scl = True
        if self.HALFEDGE:
            await RisingEdge(self._dut.clk)
        if idle_exit:
            self.sda_idle()
        await ClockCycles(self._dut.clk, self.CYCLES_PER_HALFBIT)


    async def send_ack(self) -> None:
        await self.send_bit(False, idle_exit = True)


    async def send_nack(self) -> None:
        await self.send_bit(True, idle_exit = True)


    async def send_acknack(self, nack: bool = False) -> None:
        await self.send_bit(nack, idle_exit = True)


    async def check_recv_is_idle(self, cycles: int = 0, no_warn: bool = False) -> bool:
        start_sim_time = get_sim_time()
        self._check_recv_idle_start = start_sim_time

        # warn if we are not idle on our side ?
        if not no_warn and not self._sda_idle:
            self._dut._log.warning(f"check_recv_is_idle(cycles={cycles}, no_warn={no_warn}) but SDA has not set TX idle (HiZ)")

        self._dut._log.warning(f"check_recv_is_idle(cycles={cycles}, no_warn={no_warn}) start={start_sim_time}")

        # signal scl_oe
        if self.sda_oe:
            self._dut._log.warning(f"check_recv_is_idle(cycles={cycles}, no_warn={no_warn}) SDA OE={self.sda_oe} dut should be idle")
            return False
        for i in range(cycles):
            await ClockCycles(self._dut.clk, 1)
            if self.sda_oe:
                self._dut._log.warning(f"check_recv_is_idle(cycles={cycles}, no_warn={no_warn}) SDA OE={self.sda_oe} dut should be idle")
                return False

        ## FIXME enable the background task to monitor
        #task = self.task_ensure_started()
        #task.enable = True

        return True


    async def check_recv_has_been_idle(self, cycles: int = 0, no_warn: bool = False) -> bool:
        assert self._check_recv_idle_start is not None

        # warn if we are not idle on our side ?
        if not no_warn and not self._sda_idle:
            self._dut._log.warning(f"check_recv_has_been_idle(cycles={cycles}, no_warn={no_warn}) but SDA has not set TX idle (HiZ)")

        start_sim_time = self._check_recv_idle_start
        self._check_recv_idle_start = None	# reset

        ## FIXME enable the background task to monitor
        #self.task_disable_if_started()

        # signal scl_oe
        if self.sda_oe:
            return False
        while True:
            # FIXME compute this from cycles from clk?
            NS = 90000	# 6 * 10
            now = get_sim_time()
            left = (start_sim_time + (cycles * NS)) - now
            limit = 600000 * self.CYCLES_PER_BIT
            assert left <= limit, f"left too large at {left}"
            self._dut._log.warning(f"check_recv_has_been_idle(cycles={cycles}, no_warn={no_warn}) {now} - {start_sim_time} = {left}")
            if left <= 0:
                break

            await ClockCycles(self._dut.clk, 1)
            if self.sda_oe:
                return False

        return True


    def scl_idle(self, v: bool = None) -> bool:
        if self._haveSclIe:
            bf = v is not None and ( v is not self.PULLUP or self._modeIsPP )
            self._dut._log.info(f"scl_idle({v})  pp={self._modeIsPP}  bf={bf}")
            self._dut.dut.debug_SCL_ie.value = bf
        self._scl_idle = v is None
        return v


    def sda_idle(self, v: bool = None) -> bool:
        if self._haveSdaIe:
            bf = v is not None and ( v is not self.PULLUP or self._modeIsPP )
            self._dut._log.info(f"sda_idle({v})  pp={self._modeIsPP}  bf={bf}")
            self._dut.dut.debug_SDA_ie.value = bf
        self._sda_idle = v is None
        return v


    def idle(self) -> None:
        self.set_sda_scl(None, None)


    @property
    def scl_raw(self) -> bool:
        return self._scl_state


    @scl_raw.setter
    def scl_raw(self, v: bool) -> None:
        assert type(v) is bool or v is None
        self._scl_state = v if v is not None else self.PULLUP
        sda = self.sda_resolve()
        self._sdascl.value = self.resolve_bits_state_str(sda, v)


    @property
    def sda_raw(self) -> bool:
        return self._sda_state


    @sda_raw.setter
    def sda_raw(self, v: bool) -> None:
        assert type(v) is bool or v is None
        self._sda_state = v if v is not None else self.PULLUP
        scl = self.scl_resolve()
        self._sdascl.value = self.resolve_bits_state_str(v, scl)


    @property
    def scl(self) -> bool:
        return self._scl_state

    @scl.setter
    def scl(self, v: bool) -> None:
        assert type(v) is bool or v is None
        self.scl_idle(v)
        self.scl_raw = v

    @property
    def sda(self) -> bool:
        return self._sda_state

    @sda.setter
    def sda(self, v: bool) -> None:
        assert type(v) is bool or v is None
        self.sda_idle(v)
        if v is not None:
            self.sda_raw = v

    @property
    def sda_rx(self) -> bool:
        if not self._sdascl_out.raw.value.is_resolvable:
            #nv = False	# FIXME pickup RANDOM_POLICY
            x = str(self._sdascl_out.raw.value)[-4:-2]	# "xxxx01xx" => "01" SDA SCL
            my_sda = x[0]		# bit3 is 1st char
            if my_sda == 'x':
                # FIXME try insert here: assert not PUSH_PULL_MODE
                assert not self._modeIsPP, f"PUSH_PULL_MODE={self._modeIsPP}"	# only open-drain allowed this fixup
                nv = True	# FIXME is this open-drain mode ?
                # FIXME is this warning old now? remove it ?
                self._dut._log.warning(f"GL_TEST={self.GL_TEST} I2CController.sda_rx() = {str(self._sdascl_out.raw.value)} [IS_NOT_RESOLABLE maybe due to OPEN-DRAIN] x={x} my_sda={my_sda} using {nv}")
                my_sda = '1'
            assert my_sda == '0' or my_sda == '1', f"my_sda={str(self._sdascl_out.raw.value)}"
            nv = True if my_sda == '1' else False
            return nv
        return self._sdascl_out.value & 2 != 0


    @property
    def sda_oe(self) -> bool:
        if not self._sdascl_oe.raw.value.is_resolvable:
            #nv = False	# FIXME pickup RANDOM_POLICY
            x = str(self._sdascl_oe.raw.value)[-4:-2]	# "xxxx01xx" => "01" SDA SCL
            my_sda_oe = x[0]		# bit3 is 1st char
            if my_sda_oe == 'x':
                assert False	# never happens ?  yes it does
                nv = False	# FIXME is good default
                # FIXME is this warning old now? remove it ?
                self._dut._log.warning(f"GL_TEST={self.GL_TEST} I2CController.sda_oe() = {str(self._sdascl_oe.raw.value)} [IS_NOT_RESOLABLE] x={x} my_sda_oe={my_sda_oe} using {nv}")
                my_sda_oe = '1'
            assert my_sda_oe == '0' or my_sda_oe == '1', f"my_sda_oe={str(self._sdascl_oe.raw.value)}"
            nv = True if my_sda_oe == '1' else False
            return nv
        return self._sdascl_oe.value & 2 != 0


    def scl_resolve(self, v: bool = None, with_idle: bool = True) -> bool:
        assert type(v) is bool or v is None
        if v is None:
            if self._scl_idle and with_idle:
                return None
            return self._scl_state
        if not with_idle:
            return self._scl_state
        return v


    def sda_resolve(self, v: bool = None, with_idle: bool = True) -> bool:
        assert type(v) is bool or v is None
        if v is None:
            if self._sda_idle and with_idle:
                return None
            return self._sda_state
        if not with_idle:
            return self._sda_state
        return v


    def resolve_bits(self, sda: bool, scl: bool) -> int:
        assert type(sda) is bool
        assert type(scl) is bool
        if scl:
            if sda:
                return SCL_BITID_MASK|SDA_BITID_MASK
            else:
                return SCL_BITID_MASK
        else:
            if sda:
                return SDA_BITID_MASK
            else:
                return 0


    def resolve_bits_zerobased(self, sda: bool, scl: bool) -> int:
        # SCL_BITID is the min(SCL_BITID, SDA_BITID)
        x = self.resolve_bits(scl, sda)
        x_z = x >> SCL_BITID
        #print(f"resolve_bits(sda={sda}, scl={scl}) = {x} {x_z}")
        return self.resolve_bits(sda, scl) >> SCL_BITID


    def resolve_bit_state_str(self, bf: bool, when_none: str = None) -> str:
        assert type(when_none) is str or when_none is None
        if bf is None:
            if when_none is None:
                if not self.GL_TEST:
                    return self.HIZ
                # GL_TEST: Does not work with Z here, it propagates into gates
                # So we default to PP=False, OD=True(pullup)
                bf = False if self._modeIsPP else self.PULLUP
             #return when_none
        return '1' if bf else '0'


    def resolve_bits_state_str(self, sda: bool, scl: bool, when_none: str = None) -> str:
        assert type(sda) is bool or sda is None
        assert type(scl) is bool or scl is None
        assert type(when_none) is str or when_none is None
        scl_c = self.resolve_bit_state_str(scl, when_none)
        sda_c = self.resolve_bit_state_str(sda, when_none)
        return sda_c + scl_c


    def set_sda_scl(self, sda: bool = None, scl: bool = None, with_idle: bool = True) -> None:
        assert type(sda) is bool or sda is None
        assert type(scl) is bool or scl is None
        self.sda_idle(sda)
        self.scl_idle(scl)
        sda = self.sda_resolve(sda, with_idle)
        scl = self.scl_resolve(scl, with_idle)
        self.set_sda_raw_and_scl_raw(sda, scl)


    def set_sda(self, sda: bool = None, with_idle: bool = True) -> None:
        assert type(sda) is bool or sda is None
        self.sda_idle(sda)
        sda = self.sda_resolve(sda, with_idle)
        scl = self.scl_resolve()
        self.set_sda_raw_and_scl_raw(sda, scl)


    def set_scl(self, scl: bool = None, with_idle: bool = True) -> None:
        assert type(scl) is bool or scl is None
        self.scl_idle(scl)
        sda = self.sda_resolve()
        scl = self.scl_resolve(scl, with_idle)
        self.set_sda_raw_and_scl_raw(sda, scl)


    def set_sda_raw_and_scl_raw(self, sda: bool = None, scl: bool = None) -> None:
        assert type(sda) is bool or sda is None
        assert type(scl) is bool or scl is None

        self._sda_state = sda if sda is not None else self.PULLUP
        self._scl_state = scl if scl is not None else self.PULLUP

        #v = self.resolve_bits_zerobased(sda, scl)
        v = self.resolve_bits_state_str(sda, scl)
        #print(f"resolve_bits_zerobased(sda={sda}, scl={scl}) = {v}")
        self._sdascl.value = v


