"""Represents a token amount with a specific number of decimal places."""

from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidFundsError
from warthog_py.parsed_funds import ParsedFunds
from warthog_py.token_decimals import TokenDecimals
from warthog_py.constants import MAX_U64


@dataclass(frozen=True)
class Funds:
    """A token amount with a specific number of decimals."""

    amount: int

    @classmethod
    def parse(cls, string: str, decimals: TokenDecimals) -> "Funds":
        """Parse a decimal string to ``Funds``.

        Raises ``InvalidFundsError`` on invalid input.
        """
        parsed = ParsedFunds.parse(string)
        return cls.from_parsed_funds(parsed, decimals)

    @classmethod
    def try_parse(cls, string: str, decimals: TokenDecimals) -> Optional["Funds"]:
        """Like ``parse`` but returns ``None`` instead of raising."""
        try:
            return cls.parse(string, decimals)
        except InvalidFundsError:
            return None

    @classmethod
    def from_amount(cls, amount: int) -> "Funds":
        """Build ``Funds`` from an integer amount.

        The amount is in the token's smallest unit, so it needs no decimals:
        this is the way to build one from a value a node reported.

        Raises ``InvalidFundsError`` on a negative or overflowing amount.
        """
        if not isinstance(amount, int) or amount < 0:
            raise InvalidFundsError(f"invalid funds amount: {amount!r}")
        if amount > MAX_U64:
            raise InvalidFundsError(
                f"value {amount} overflows the 64-bit unsigned range"
            )
        return cls(amount=amount)

    @classmethod
    def try_from_amount(cls, amount: int) -> Optional["Funds"]:
        """Like ``from_amount`` but returns ``None`` instead of raising."""
        try:
            return cls.from_amount(amount)
        except InvalidFundsError:
            return None

    @classmethod
    def from_parsed_funds(
        cls, parsed: ParsedFunds, decimals: TokenDecimals
    ) -> "Funds":
        """Convert a ``ParsedFunds`` into ``Funds`` at the given decimal precision.

        Raises ``InvalidFundsError`` on invalid input (too many decimals,
        or overflow when scaling to the target precision).
        """
        if parsed.decimal_places > decimals.decimals:
            raise InvalidFundsError(
                f"input has {parsed.decimal_places} decimals but token only supports "
                f"{decimals.decimals}"
            )

        zeros = decimals.decimals - parsed.decimal_places
        # ``10 ** zeros`` is well within Python's arbitrary-precision int for
        # decimals ≤ 18 (the max). Compute the final value and check overflow
        # against MAX_U64 directly — no loop needed.
        multiplier = 10 ** zeros
        if parsed.val > MAX_U64 // multiplier:
            raise InvalidFundsError(
                f"value {parsed.val} overflows when scaling to {decimals.decimals} decimals"
            )

        return cls(amount=parsed.val * multiplier)

    @classmethod
    def try_from_parsed_funds(
        cls, parsed: ParsedFunds, decimals: TokenDecimals
    ) -> Optional["Funds"]:
        """Like ``from_parsed_funds`` but returns ``None`` instead of raising."""
        try:
            return cls.from_parsed_funds(parsed, decimals)
        except InvalidFundsError:
            return None