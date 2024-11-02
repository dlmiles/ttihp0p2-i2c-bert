# SPDX-FileCopyrightText: Copyright © 2024 Darryl Miles
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from cocotb_stuff import cocotbutil


def bit_count(i: int) -> int:
    count = 0
    while i != 0:
        if (i & 1) != 0:
            count += 1
        i >>= 1
    return count


def set_state(dut, v: int):
    dut.A.value = (v & 0x01) != 0
    dut.B.value = (v & 0x02) != 0
    dut.C.value = (v & 0x04) != 0
    dut.D.value = (v & 0x08) != 0
    dut.E.value = (v & 0x10) != 0
    return None


@cocotb.test()
async def test_maj5(dut):
    dut._log.info("Start")

    cocotbutil.report_resolvable(dut)

    dut.clk.value = 0
    await Timer(40, units='us') # Show X states

    dut.clk.value = 0
    dut.A.value = 0
    dut.B.value = 0
    dut.C.value = 0
    dut.D.value = 0
    dut.E.value = 0
    await Timer(40, units='us') # Show quiescent state

    # Fake clock
    dut._log.info("Clocking")
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    cocotbutil.report_resolvable(dut)

    INPUT_COUNT = 5
    THRESHOLD = int(INPUT_COUNT / 2) + 1
    MAX_LIMIT = 2 ** INPUT_COUNT

    dut._log.info(f"INPUT_COUNT={INPUT_COUNT}")
    dut._log.info(f"THRESHOLD={THRESHOLD}")
    dut._log.info(f"MAX_LIMIT={MAX_LIMIT}")

    for i in range(MAX_LIMIT):
        count = bit_count(i)
        expect = True if count >= THRESHOLD else False

        set_state(dut, i)
        await ClockCycles(dut.clk, 2) # run simtime

        x = dut.X.value
        dut._log.info(f"value = {i:2d} {i:#2} [bitcnt={count:d}], actual = {x}, expect = {expect}")

        assert expect == x, f"expect != actual  {expect} != {x}"

    dut._log.info("Done")
