"""Warthog's native token (WART) with 8 decimal places.

``1 WART = 100_000_000 E8``.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from warthog_py.errors import InvalidFundsError
from warthog_py.funds import Funds
from warthog_py.parsed_funds import ParsedFunds
from warthog_py.token_decimals import TokenDecimals
from warthog_py.constants import MAX_U64

if TYPE_CHECKING:
    from warthog_py.rounded_fee import RoundedFee


@dataclass(frozen=True)
class Wart:
    """WART amount stored as E8 (1 WART = 100_000_000 E8)."""

    e8: int

    @classmethod
    def parse(cls, string: str) -> "Wart":
        """Parse a decimal string to ``Wart``.

        Raises ``InvalidFundsError`` on invalid input.
        """
        parsed = ParsedFunds.parse(string)
        return cls.from_parsed_funds(parsed)

    @classmethod
    def try_parse(cls, string: str) -> Optional["Wart"]:
        try:
            return cls.parse(string)
        except InvalidFundsError:
            return None

    @classmethod
    def from_parsed_funds(cls, parsed: ParsedFunds) -> "Wart":
        """Convert a ``ParsedFunds`` into ``Wart`` (WART uses 8 decimals).

        Raises ``InvalidFundsError`` on invalid input.
        """
        funds = Funds.from_parsed_funds(parsed, TokenDecimals.wart())
        return cls(e8=funds.amount)

    @classmethod
    def from_e8(cls, e8: int) -> "Wart":
        """Create ``Wart`` from a raw E8 value.

        Raises ``InvalidFundsError`` on negative or out-of-range input.
        """
        if not isinstance(e8, int) or isinstance(e8, bool) or e8 < 0:
            raise InvalidFundsError(
                f"invalid E8: {e8!r} (must be a non-negative integer)"
            )
        if e8 > MAX_U64:
            raise InvalidFundsError(f"E8 {e8} exceeds MAX_U64")
        return cls(e8=e8)

    @classmethod
    def try_from_e8(cls, e8: int) -> Optional["Wart"]:
        try:
            return cls.from_e8(e8)
        except InvalidFundsError:
            return None

    def rounded_fee(self, ceil: bool) -> "RoundedFee":
        """Convert to a ``RoundedFee``.

        Pass ``ceil=True`` to round up, ``ceil=False`` to round down.
        """
        from warthog_py.rounded_fee import RoundedFee

        return RoundedFee.from_wart(self, ceil)