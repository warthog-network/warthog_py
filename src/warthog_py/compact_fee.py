"""Warthog's internal 16-bit compact fee representation.

Used for compact storage and transmission of transaction fees within the
protocol. **This is NOT used in transaction submission API — use
``RoundedFee`` instead.**
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from warthog_py.wart import Wart


THRESHOLD = 0x07FF
MIN_11_BIT = 0x0400
MAX_EXPONENT = 15
MAX_MANTISSA = 1023


@dataclass(frozen=True)
class CompactFee:
    """16-bit compact fee: ``(exponent, mantissa)``."""

    exponent: int
    mantissa: int

    @classmethod
    def from_wart(cls, wart: "Wart", ceil: bool) -> "CompactFee":
        """Create a ``CompactFee`` from a ``Wart``.

        ``ceil=True`` rounds up; ``ceil=False`` rounds down.
        """
        if wart.e8 == 0:
            return cls(exponent=0, mantissa=0)

        e, normalized, inexact = _shift_until_under(wart.e8, 10, ceil)
        if ceil and inexact:
            return _apply_ceiling(e, normalized)
        return _finalize(e, normalized)

    def to_wart(self) -> "Wart":
        """Convert to a ``Wart``."""
        from warthog_py.wart import Wart

        if self.exponent < 10:
            shift = 10 - self.exponent
            value = (1024 + self.mantissa) >> shift
        else:
            shift = self.exponent - 10
            value = (1024 + self.mantissa) << shift
        return Wart.from_e8(value)


def _shift_until_under(e8: int, e: int, ceil: bool):
    """Halve ``e8`` until it fits within the 11-bit threshold.

    Returns ``(final_exponent, normalized, inexact?)``.
    """
    if e8 > THRESHOLD:
        inexact = ceil and (e8 & 1) == 1
        final_e, normalized, prev_inexact = _shift_until_under(
            e8 >> 1, e + 1, ceil
        )
        return (final_e, normalized, inexact or prev_inexact)
    return (e, e8, False)


def _apply_ceiling(e: int, e8: int) -> CompactFee:
    rounded = e8 + 1
    if rounded > THRESHOLD:
        new_e = e + 1
        if new_e > MAX_EXPONENT:
            return CompactFee(exponent=MAX_EXPONENT, mantissa=MAX_MANTISSA)
        return _finalize(new_e, rounded >> 1)
    return _finalize(e, rounded)


def _finalize(e: int, e8: int) -> CompactFee:
    final_e, normalized = _normalize(e, e8)
    return CompactFee(exponent=final_e, mantissa=normalized - MIN_11_BIT)


def _normalize(e: int, e8: int):
    if e8 < MIN_11_BIT:
        return _normalize(e - 1, e8 << 1)
    return (e, e8)