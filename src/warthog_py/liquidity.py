"""Liquidity pool tokens with 8 decimal places.

Used for liquidity deposit/withdrawal transactions.
``1 unit = 100_000_000 E8``.
"""

from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidFundsError
from warthog_py.funds import Funds
from warthog_py.parsed_funds import ParsedFunds
from warthog_py.token_decimals import TokenDecimals
from warthog_py import MAX_U64


@dataclass(frozen=True)
class Liquidity:
    """Liquidity amount stored as E8."""

    e8: int

    @classmethod
    def parse(cls, string: str) -> "Liquidity":
        """Parse a decimal string to ``Liquidity``.

        Raises ``InvalidFundsError`` on invalid input.
        """
        parsed = ParsedFunds.parse(string)
        return cls.from_parsed_funds(parsed)

    @classmethod
    def try_parse(cls, string: str) -> Optional["Liquidity"]:
        try:
            return cls.parse(string)
        except InvalidFundsError:
            return None

    @classmethod
    def from_parsed_funds(cls, parsed: ParsedFunds) -> "Liquidity":
        funds = Funds.from_parsed_funds(parsed, TokenDecimals.liquidity())
        return cls(e8=funds.amount)

    @classmethod
    def from_e8(cls, e8: int) -> "Liquidity":
        """Create ``Liquidity`` from a raw E8 value.

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
    def try_from_e8(cls, e8: int) -> Optional["Liquidity"]:
        try:
            return cls.from_e8(e8)
        except InvalidFundsError:
            return None