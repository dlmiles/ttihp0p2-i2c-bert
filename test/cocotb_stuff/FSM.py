#
#
#
#
#
# SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#
#
import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import ClockCycles

from .cocotbutil import *






class FSM():
    def __init__(self, fsm):
        self._fsm = fsm


    def values(self):
        return self._fsm.values()


    def fsm_signal_path(self, label: str) -> str:
        if label in self._fsm:
            return self._fsm[label]
        raise Exception(f"Unable to find fsm_signal: {label}")


    def fsm_state(self, dut, label: str) -> str:
        path = self.fsm_signal_path(label)

        signal = design_element(dut, path)
        if signal is None:
            raise Exception(f"Unable to find signal path: {path}")

        return self.fsm_printable(signal)


    # signal: NonHierarchyObject|BinaryValue
    def fsm_printable(self, signal) -> str:
        is_string = False
        if isinstance(signal, cocotb.handle.NonHierarchyObject):
            is_string = signal._path.endswith('_string')
            value = signal.value
        assert isinstance(value, BinaryValue)
        if value.is_resolvable and is_string: # and signal._path.endswith('_string'):
            # Convert to string
            return value.buff.decode('ascii').rstrip()
        else:
            return str(value)


    def fsm_state_expected(self, dut, label: str, expected: str) -> bool:
        state = self.fsm_state(dut, label)
        assert state == expected, f"fsm_state({label}) in state {state} expected state {expected}"
        return True


    async def fsm_state_expected_within(self, dut, label: str, expected: str, cycles: int = None, can_raise: bool = True) -> bool:
        assert cycles is None or cycles >= 0

        if cycles is None:
            cycles = 10000

        for i in range(cycles):
            state = self.fsm_state(dut, label)
            if state == expected:
                if i > 0:
                    dut._log.info("fsm_state_expected_within({}, expected={}, cycles={}) took {} cycles".format(label, expected, cycles, i))
                return self.fsm_state_expected(dut, label, expected)
            await ClockCycles(dut.clk, 1)

        if can_raise:
            state = self.fsm_state(dut, label)
            raise Exception(f"fsm_state({label}) == {expected} not achieved after {cycles} cycles (current state: {state})")

        return False


