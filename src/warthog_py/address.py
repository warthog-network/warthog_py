"""Warthog address with SHA-256 checksum validation.

Addresses are 20 bytes (40 hex chars) of payload with a 4-byte
(8 hex chars) SHA-256 checksum appended, totaling 48 hex characters.
"""

from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidAddressError

PAYLOAD_SIZE = 20
CHECKSUM_SIZE = 4
HEX_SIZE = (PAYLOAD_SIZE + CHECKSUM_SIZE) * 2


@dataclass(frozen=True)
class Address:
    """A 48-character hex address with a 4-byte SHA-256 checksum."""

    hex: str

    @classmethod
    def from_hex(cls, hex_str: str) -> "Address":
        """Parse and validate a 48-character hex address with checksum.

        Raises ``InvalidAddressError`` on invalid input.
        """
        if not isinstance(hex_str, str) or len(hex_str) != HEX_SIZE:
            raise InvalidAddressError(
                f"address must be a {HEX_SIZE}-character hex string, got: {hex_str!r}"
            )

        try:
            buf = bytes.fromhex(hex_str)
        except ValueError as e:
            raise InvalidAddressError(f"invalid hex characters: {e}") from e

        if len(buf) != 24:
            raise InvalidAddressError(
                f"address must decode to 24 bytes, got {len(buf)}"
            )

        payload = buf[:PAYLOAD_SIZE]
        checksum = buf[PAYLOAD_SIZE:]
        expected = checksum_of(payload)
        if checksum != expected:
            raise InvalidAddressError("invalid checksum")

        return cls(hex=hex_str.lower())

    @classmethod
    def from_raw(cls, raw: str) -> "Address":
        """Create an address from a raw 40-character hex string (20 bytes, no checksum).

        Computes and appends the SHA-256 checksum. Raises ``InvalidAddressError``
        on invalid input.
        """
        if not isinstance(raw, str) or len(raw) != PAYLOAD_SIZE * 2:
            raise InvalidAddressError(
                f"raw address must be a {PAYLOAD_SIZE * 2}-character hex string, got: {raw!r}"
            )

        try:
            payload = bytes.fromhex(raw)
        except ValueError as e:
            raise InvalidAddressError(f"invalid hex characters: {e}") from e

        if len(payload) != PAYLOAD_SIZE:
            raise InvalidAddressError(
                f"raw address must decode to {PAYLOAD_SIZE} bytes, got {len(payload)}"
            )

        checksum = checksum_of(payload)
        return cls(hex=(payload + checksum).hex())

    @classmethod
    def try_from_hex(cls, hex_str: str) -> Optional["Address"]:
        """Like ``from_hex`` but returns ``None`` instead of raising."""
        try:
            return cls.from_hex(hex_str)
        except InvalidAddressError:
            return None

    @classmethod
    def try_from_raw(cls, raw: str) -> Optional["Address"]:
        """Like ``from_raw`` but returns ``None`` instead of raising."""
        try:
            return cls.from_raw(raw)
        except InvalidAddressError:
            return None

    @classmethod
    def validate(cls, address: str) -> bool:
        """Return ``True`` if ``address`` is a valid 48-character hex with checksum."""
        return cls.try_from_hex(address) is not None


def checksum_of(payload: bytes) -> bytes:
    """Compute the SHA-256 checksum of a 20-byte address payload.

    Returns the first 4 bytes of SHA-256(payload) (single hash,
    matching the protocol definition).
    """
    import hashlib

    return hashlib.sha256(payload).digest()[:CHECKSUM_SIZE]