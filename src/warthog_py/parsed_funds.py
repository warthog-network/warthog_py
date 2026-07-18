"""Parsed decimal string representation.

Used internally for parsing currency strings into integer + decimal count.
"""

from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidFundsError
from warthog_py.constants import MAX_U64

MAX_DIGITS = 20


@dataclass(frozen=True)
class ParsedFunds:
    """A parsed decimal string: integer value + decimal-place count."""

    val: int
    decimal_places: int

    @classmethod
    def parse(cls, s: str) -> "ParsedFunds":
        """Parse a decimal string into a ``ParsedFunds``.

        Raises ``InvalidFundsError`` on invalid input.
        """
        if not isinstance(s, str):
            raise InvalidFundsError(f"input must be a string, got: {type(s).__name__}")

        digits = []
        digits_after_dot = 0
        dot_found = False

        for ch in s:
            if "0" <= ch <= "9":
                if len(digits) >= MAX_DIGITS:
                    raise InvalidFundsError(
                        f"too many digits (max {MAX_DIGITS})"
                    )
                digits.append(ch)
                if dot_found:
                    digits_after_dot += 1
            elif ch == ".":
                if dot_found:
                    raise InvalidFundsError("multiple dots in input")
                dot_found = True
            else:
                raise InvalidFundsError(f"invalid character: {ch!r}")

        if not digits:
            raise InvalidFundsError("empty input")

        val = int("".join(digits))
        if val > MAX_U64:
            raise InvalidFundsError(f"value {val} exceeds MAX_U64")

        return cls(val=val, decimal_places=digits_after_dot)

    @classmethod
    def try_parse(cls, s: str) -> Optional["ParsedFunds"]:
        """Like ``parse`` but returns ``None`` instead of raising."""
        try:
            return cls.parse(s)
        except InvalidFundsError:
            return None