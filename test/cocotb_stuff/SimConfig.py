#
#
#
# SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#
#
import re

class SimConfig():
    def __init__(self, dut, cocotb):
        sim_name = cocotb.SIM_NAME
        self._is_iverilog = re.match(r'Icarus Verilog', sim_name, re.IGNORECASE) is not None
        self._is_verilator = re.match(r'Verilator', sim_name, re.IGNORECASE) is not None
        self._SIM_SUPPORTS_X = self.is_iverilog
        dut._log.info("SimConfig(is_iverilog={}, is_verilator={}, SIM_SUPPORTS_X={})".format(
            self.is_iverilog,
            self.is_verilator,
            self.SIM_SUPPORTS_X
        ))
        return None


    def default_value(self, with_value: bool = None) -> str:
        if with_value is None:
            with_value = False
        return '1' if with_value else '0'

    def bv_replace_x(self, s: str, with_value: bool = None, force: bool = False) -> str:
        if not self._SIM_SUPPORTS_X or force:
            return s.replace('x', self.default_value(with_value))
        return s

    # a="101x10z" s="10?x??z"
    def bv_compare_x(self, a: str, s: str, with_value: bool = None, force: bool = False) -> bool:
        assert type(a) is str and len(a) > 0
        assert type(s) is str and len(s) > 0
        b = self.bv_replace_x(s, with_value, force)
        assert len(a) == len(s), f"length mismatch {a} != {s}  {len(a)} != {len(s)}"
        assert len(a) == len(b), f"length mismatch {a} != {b}  {len(a)} != {len(b)}"
        for i in range(len(a)):
            bitid = len(a) - i - 1
            aa = a[i]
            bb = b[i]
            mm = s[i]
            desc = 'IGNORE' if mm == '?' else 'COMPARE A==B'
            print(f"a={aa} b={bb} m={mm} bit{bitid} {desc}")
            if mm == '?':
                continue
            if aa != bb:
                return False
        print(f"bv_compare_x(a={a}, s={s}, with_value={with_value}, force={force})")
        return True

    @property
    def is_iverilog(self) -> bool:
        return self._is_iverilog

    @property
    def is_verilator(self) -> bool:
        return self._is_verilator

    @property
    def SIM_SUPPORTS_X(self) -> bool:
        return self._SIM_SUPPORTS_X

