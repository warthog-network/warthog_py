"""Transaction nonce (32-bit unsigned integer).

Every transaction requires a unique nonce to prevent replay attacks.
Valid range: ``[0, 0xFFFFFFFF]`` (``0`` to ``4_294_967_295``).
"""

from dataclasses import dataclass
from typing import Optional

from warthog_py.errors import InvalidNonceError

MAX_U32: int = 0xFFFFFFFF


@dataclass(frozen=True)
class NonceId:
    """A 32-bit transaction nonce."""

    value: int

    @staticmethod
    def validate(value: int) -> bool:
        """Return ``True`` if ``value`` is a valid 32-bit unsigned integer."""
        return isinstance(value, int) and 0 <= value <= MAX_U32

    @classmethod
    def from_number(cls, value: int) -> "NonceId":
        """Create a ``NonceId`` from a number.

        Raises ``InvalidNonceError`` on out-of-range values.
        """
        if not cls.validate(value):
            raise InvalidNonceError(f"invalid nonce: {value!r} (must be 0..{MAX_U32})")
        return cls(value=value)

    @classmethod
    def try_from_number(cls, value: int) -> Optional["NonceId"]:
        """Like ``from_number`` but returns ``None`` instead of raising."""
        try:
            return cls.from_number(value)
        except InvalidNonceError:
            return None

    @classmethod
    def random(cls) -> "NonceId":
        """Generate a random ``NonceId`` in the valid 32-bit range."""
        import secrets

        return cls(value=secrets.randbelow(MAX_U32 + 1))