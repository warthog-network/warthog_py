"""Represents the number of decimal places for a token.

Valid range: ``0`` to ``18``. WART uses 8 decimal places.
"""

from dataclasses import dataclass

from warthog_py.errors import InvalidDecimalsError

WART = None  # placeholder, set after class definition


@dataclass(frozen=True)
class TokenDecimals:
    """Number of decimal places for a token (0..18)."""

    decimals: int

    @classmethod
    def wart(cls) -> "TokenDecimals":
        """Pre-configured WART decimals (8)."""
        return cls(decimals=8)

    @classmethod
    def liquidity(cls) -> "TokenDecimals":
        """Pre-configured Liquidity decimals (8)."""
        return cls(decimals=8)

    @classmethod
    def new(cls, decimals: int) -> "TokenDecimals":
        """Build a new ``TokenDecimals``.

        Raises ``InvalidDecimalsError`` if ``decimals`` is out of range.
        """
        if not isinstance(decimals, int) or decimals < 0 or decimals > 18:
            raise InvalidDecimalsError(
                f"invalid decimals: {decimals!r} (must be 0..18)"
            )
        return cls(decimals=decimals)