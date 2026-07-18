"""Transaction fee in rounded WART format (64-bit WART scale).

This is NOT the 16-bit compact representation itself. Instead it is
the result of converting WART to a ``CompactFee`` and then back to the
WART scale. This is a lossy operation: the original WART value cannot
be restored from a ``RoundedFee``. Warthog nodes require rounded values
on the 64-bit WART scale in API calls.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from warthog_py.compact_fee import CompactFee
from warthog_py.errors import InvalidFundsError
from warthog_py.wart import Wart

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class RoundedFee:
    """A transaction fee in rounded WART format."""

    e8: int

    @classmethod
    def from_wart(cls, wart: Wart, ceil: bool) -> "RoundedFee":
        compact = CompactFee.from_wart(wart, ceil)
        rounded = compact.to_wart()
        return cls(e8=rounded.e8)

    @classmethod
    def from_e8(cls, e8: int, ceil: bool) -> "RoundedFee":
        """Create a ``RoundedFee`` from a raw E8 value.

        Raises ``InvalidFundsError`` on negative or out-of-range input.
        """
        wart = Wart.try_from_e8(e8)
        if wart is None:
            raise InvalidFundsError(f"invalid E8 for RoundedFee: {e8!r}")
        return cls.from_wart(wart, ceil)

    @classmethod
    def try_from_e8(cls, e8: int, ceil: bool) -> Optional["RoundedFee"]:
        try:
            return cls.from_e8(e8, ceil)
        except InvalidFundsError:
            return None

    @classmethod
    def min(cls) -> "RoundedFee":
        """Minimum fee (``0.00000001`` WART = ``1`` E8)."""
        return cls.from_e8(0, ceil=False)

    def to_wart(self) -> Wart:
        """Convert to a ``Wart``."""
        return Wart.from_e8(self.e8)