"""Frexp utility — thin wrapper over Python's built-in ``math.frexp``.

Python's ``math.frexp`` already handles all edge cases (zero, signed
zero, NaN, ±inf) correctly and returns ``(mantissa, exponent)`` such
that ``mantissa * 2 ** exponent == n`` with ``0.5 <= abs(mantissa) < 1``
for any non-zero finite ``n``.
"""

import math
from typing import Tuple, Union

Number = Union[int, float]


def frexp(arg: Number) -> Tuple[float, int]:
    """Decompose ``arg`` into ``(mantissa, exponent)``.

    ``mantissa * 2 ** exponent == arg`` (with edge cases preserved:
    zero, signed zero, NaN, ±inf all come back with exponent 0).
    """
    return math.frexp(arg)