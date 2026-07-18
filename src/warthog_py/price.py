"""Represents a swap price in normalized mantissa/exponent format.

- **Mantissa**: 16 bits, must be in ``[0x8000, 0xFFFF]`` (high bit set).
- **Exponent**: 8 bits, stored with offset ``+63`` internally to map to
  ``[0, 127]``.

The price is interpreted as a quotient of base and quote amount
*integers*. When creating or printing a price you must account for the
number of decimals of the involved base asset.
"""

import math
from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidPriceError
from warthog_py.frexp import frexp
from warthog_py.token_decimals import TokenDecimals

MIN_MANTISSA = 0x8000
MAX_MANTISSA = 0xFFFF
MAX_EXPONENT_INTERNAL = 127
MANTISSA_OFFSET = 63
HEX_SIZE = 6


@dataclass(frozen=True)
class Price:
    """Normalized mantissa/exponent price."""

    mantissa: int
    exponent: int

    @classmethod
    def max(cls) -> "Price":
        """Maximum possible price."""
        return cls(mantissa=MAX_MANTISSA, exponent=MAX_EXPONENT_INTERNAL)

    @classmethod
    def from_mantissa_exponent(cls, mantissa: int, exponent: int) -> "Price":
        """Create a ``Price`` from raw mantissa and exponent values.

        ``exponent`` is the raw representation **before** the ``+63``
        adjustment (must be in ``[0, 127]``).

        Raises ``InvalidPriceError`` on invalid input.
        """
        adjusted = exponent + MANTISSA_OFFSET
        if not (isinstance(mantissa, int) and isinstance(adjusted, int)):
            raise InvalidPriceError("mantissa and exponent must be integers")
        if not (MIN_MANTISSA <= mantissa <= MAX_MANTISSA):
            raise InvalidPriceError(f"mantissa {mantissa} out of range")
        if not (0 <= adjusted <= MAX_EXPONENT_INTERNAL):
            raise InvalidPriceError(f"exponent {exponent} (adjusted {adjusted}) out of range")
        return cls(mantissa=mantissa, exponent=adjusted)

    @classmethod
    def try_from_mantissa_exponent(
        cls, mantissa: int, exponent: int
    ) -> Optional["Price"]:
        try:
            return cls.from_mantissa_exponent(mantissa, exponent)
        except InvalidPriceError:
            return None

    @classmethod
    def from_number_decimals(
        cls,
        d: float,
        base_decimals: TokenDecimals,
        ceil: bool = False,
    ) -> "Price":
        """Create a ``Price`` from a decimal number, given the base asset decimals.

        ``ceil=True`` rounds up; ``ceil=False`` (default) rounds down.

        Raises ``InvalidPriceError`` on invalid input.
        """
        adjusted = d * (10 ** (8 - base_decimals.decimals))
        return cls.from_double_internal(adjusted, ceil)

    @classmethod
    def try_from_number_decimals(
        cls,
        d: float,
        base_decimals: TokenDecimals,
        ceil: bool = False,
    ) -> Optional["Price"]:
        try:
            return cls.from_number_decimals(d, base_decimals, ceil)
        except InvalidPriceError:
            return None

    @classmethod
    def from_double_internal(
        cls, d: float, ceil: bool = False
    ) -> "Price":
        """Low-level factory. Library users should prefer ``from_number_decimals``.

        Raises ``InvalidPriceError`` on invalid input.
        """
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            raise InvalidPriceError(f"invalid double: {d!r}")
        d = float(d)
        if d <= 0:
            raise InvalidPriceError(f"price must be positive, got {d}")
        if not math.isfinite(d):
            raise InvalidPriceError(f"price must be finite, got {d}")

        mantissa, exponent = frexp(d)
        mantissa_scaled = math.floor(mantissa * 65_536)
        exact = mantissa * 65_536 == mantissa_scaled

        if ceil and not exact:
            new_mantissa = mantissa_scaled + 1
            if new_mantissa >= 65_536:
                return cls.from_mantissa_exponent(new_mantissa >> 1, exponent + 1)
            return cls.from_mantissa_exponent(new_mantissa, exponent)
        return cls.from_mantissa_exponent(mantissa_scaled, exponent)

    @classmethod
    def try_from_double_internal(
        cls, d: float, ceil: bool = False
    ) -> Optional["Price"]:
        try:
            return cls.from_double_internal(d, ceil)
        except InvalidPriceError:
            return None

    def to_hex(self) -> str:
        """Convert to a 6-character hex string for transaction generation."""
        return f"{self.mantissa:04x}{self.exponent:02x}"

    @classmethod
    def from_hex(cls, hex_str: str) -> "Price":
        """Parse a ``Price`` from a 6-character hex string.

        Raises ``InvalidPriceError`` on invalid input.
        """
        if not isinstance(hex_str, str) or len(hex_str) != HEX_SIZE:
            raise InvalidPriceError(
                f"hex must be a {HEX_SIZE}-character string, got: {hex_str!r}"
            )
        try:
            parsed = int(hex_str, 16)
        except ValueError as e:
            raise InvalidPriceError(f"invalid hex: {e}") from e

        mantissa = parsed >> 8
        exponent = parsed & 0xFF

        if mantissa < MIN_MANTISSA or mantissa > MAX_MANTISSA:
            raise InvalidPriceError(f"mantissa {mantissa} out of normalized range")
        if exponent > MAX_EXPONENT_INTERNAL:
            raise InvalidPriceError(f"exponent {exponent} out of internal range")

        return cls(mantissa=mantissa, exponent=exponent)

    @classmethod
    def try_from_hex(cls, hex_str: str) -> Optional["Price"]:
        try:
            return cls.from_hex(hex_str)
        except InvalidPriceError:
            return None

    def mantissa_exponent2(self) -> int:
        """Base-2 exponent for the mantissa (``exponent - 63 - 16``)."""
        return self.exponent - MANTISSA_OFFSET - 16

    def to_double_raw(self) -> float:
        """Convert to raw double (no decimal adjustment)."""
        return self.mantissa * (2.0 ** self.mantissa_exponent2())

    def to_double_adjusted(self, dec: TokenDecimals) -> float:
        """Convert to double with asset-decimals adjustment."""
        b10e = TokenDecimals.wart().decimals - dec.decimals
        return self.to_double_raw() * (10.0 ** -b10e)