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
from collections import namedtuple

import cocotb
from cocotb.triggers import ClockCycles
from cocotb_stuff.FSM import *
from cocotb_stuff.SignalAccessor import *
from cocotb_stuff.SignalOutput import *


## FIXME see if we can register multiple items here (to speed up simulation?) :
##   signal, prefix/label, lambda on change, lambda on print
##  want to have some state changes lookup another signal to print
## fsm_dict = { 'label'  : 'signal.path.here,
##              'label2' : SignalAccessor    }
## signal: str|SignalAccessor
class Monitor():
    def __init__(self, dut, fsm: FSM, fsm_dict: dict) -> None:
        self._dut = dut

        self._states = {}
        self._values = {}

        self.Context = namedtuple('Context', 'prefix accessor signal signal_path')
        self._running = True

        self._active = True

        self._fsm = fsm
        if fsm_dict:
            self.add_and_start(fsm_dict)

        return None

    def add(self, fsm_dict: dict) -> int:
        assert type(fsm_dict) is dict
        assert len(fsm_dict) > 0

        count = 0
        for prefix,signal_or_path in fsm_dict.items():
            signal = signal_or_path
            if isinstance(signal, str):
                signal = SignalAccessor(self._dut, signal)
            if isinstance(signal, SignalAccessor):
                accessor = signal
            else:
                accessor = signal.accessor
            assert isinstance(accessor, SignalAccessor)
            #signal = design_element(self._dut, path)
            #if signal is None:
            #    raise Exception(f"Unable to find signal path: {path}")

            prefix = prefix if(prefix) else signal.path
            ctxt = self.Context(prefix, accessor, signal, signal.path)
            self._states[ctxt.prefix] = ctxt
            count += 1

        return count

    def start(self) -> int:
        count = 0
        # initial state
        for ctxt in self._states.values():
            if ctxt.prefix in self._values:
                continue	# skip already inited

            signal = ctxt.signal
            new_value = signal.value
            new_value_str = str(new_value)
            s = self._fsm.fsm_printable(signal.raw)
            self._dut._log.info("monitor({}) = {} [STARTED]".format(ctxt.prefix, s))
            self._values[ctxt.prefix] = new_value_str
            count += 1

        count = 0
        return count

    def add_and_start(self, fsm_dict: dict) -> int:
        self.add(fsm_dict)
        return self.start()

    def shutdown(self) -> None:
        self._running = False
        self._active = False
        self.report('STOPPED')

    def suspend(self) -> None:
        if self._active and self._running:
            self._running = False
            self.report('SUSPEND')

    async def resume(self) -> None:
        if self._active and not self._running:
            self._running = True
            await cocotb.start(self.build_task())
            self.report('RESUME')

    def report(self, label: str) -> None:
        for ctxt in self._states.values():
            signal = ctxt.signal
            s = self._fsm.fsm_printable(signal.raw)
            self._dut._log.info("monitor({}) = {} [{}]".format(ctxt.prefix, s, label))

    @cocotb.coroutine
    def monitor_coroutine(self) -> None:
        while self._running:
            if not self._running:
                break

            for ctxt in self._states.values():
                old_value_str = self._values.get(ctxt.prefix, None)
                if not old_value_str:
                    continue	# not started

                signal = ctxt.signal
                new_value = signal.value
                new_value_str = str(new_value)
                if new_value_str != old_value_str:
                    s = self._fsm.fsm_printable(signal.raw)
                    self._dut._log.info("monitor({}) = {}".format(ctxt.prefix, s))
                    self._values[ctxt.prefix] = new_value_str

            # in generator-based coroutines triggers are yielded
            yield ClockCycles(self._dut.clk, 1)


    def build_task(self) -> cocotb.Task:
        return cocotb.create_task(self.monitor_coroutine())

