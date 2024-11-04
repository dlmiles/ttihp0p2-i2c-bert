#
#
#
#
# SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#

class TestBenchConfig():
    MODE_FASTER = 0
    MODE_EQUAL = 1
    MODE_SLOWER = 2

    ALT_INTERNAL = 0
    ALT_DIRECT = 1
    ALT_EXTERNAL = 2

    def __init__(self, dut, CLOCK_FREQUENCY: int, ALT_CLOCK_FREQUENCY: int) -> None:
        self._dut = dut
        self.CLOCK_FREQUENCY = CLOCK_FREQUENCY
        self.ALT_CLOCK_FREQUENCY = ALT_CLOCK_FREQUENCY
        return None

    def is_ctrl_clk(self, kind: int = MODE_EQUAL) -> bool:
        if kind & self.MODE_EQUAL:
            return self.CLOCK_FREQUENCY == self.ALT_CLOCK_FREQUENCY
        if kind & self.MODE_FASTER:
            return self.CLOCK_FREQUENCY > self.ALT_CLOCK_FREQUENCY
        if kind & self.MODE_SLOWER:
            return self.CLOCK_FREQUENCY < self.ALT_CLOCK_FREQUENCY
        return False

    @property
    def is_ctrl_clk_equal(self) -> bool:
        return self.is_ctrl_clk(self.MODE_EQUAL)

    @property
    def is_ctrl_clk_faster(self) -> bool:
        return self.is_ctrl_clk(self.MODE_FASTER)

    @property
    def is_ctrl_clk_slower(self) -> bool:
        return self.is_ctrl_clk(self.MODE_SLOWER)

    @property
    def is_phy_clk_source_external(self) -> bool:
        return True

    @property
    def is_phy_clk_source_divider(self) -> int:
        return True


    @property
    def is_phy_clk(self, kind: int = ALT_DIRECT) -> bool:
        return False
