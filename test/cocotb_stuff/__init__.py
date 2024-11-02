#
#
#
#
#
# SPDX-FileCopyrightText: Copyright 2023 Darryl Miles
# SPDX-License-Identifier: Apache2.0
#
#


SCL_BITID		= 2	# bidi: uio_out & uio_in
SDA_BITID		= 3	# bidi: uio_out & uio_in

SCL_BITID_MASK = 1 << SCL_BITID
SDA_BITID_MASK = 1 << SDA_BITID

# This validate the design under test matches values here
def validate(dut) -> bool:
    return True


__all__ = [
    'SCL_BITID',
    'SDA_BITID',

    'SCL_BITID_MASK',
    'SDA_BITID_MASK',

    'validate'
]
