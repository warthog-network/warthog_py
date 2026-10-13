"""A node's view of the chain head, normalized across API generations.

V1 returns these fields flat and V2 nests them under ``chainHead``; this always
exposes them in one shape. See :data:`warthog_py.constants.ApiVersion`.
"""

from dataclasses import dataclass
from typing import Any, Optional

from warthog_py.chain_pin import ChainPin, chain_head_source
from warthog_py.constants import ApiVersion
from warthog_py.errors import InvalidChainHeadError


@dataclass(frozen=True)
class ChainHead:
    """A node's view of the chain head."""

    pin: ChainPin
    """The most recently proposed pin."""

    hash: str
    """Hash of the block at ``height``."""

    height: int
    """Tip height. Always >= ``pin.pin_height``."""

    synced: bool
    """Whether the node reports itself as synced."""

    @classmethod
    def try_parse(cls, data: Any, version: ApiVersion) -> Optional["ChainHead"]:
        """Extract the chain head from a ``/chain/head`` payload.

        Reads the fields according to the API generation the payload came from.
        Returns ``None`` if the payload does not match ``version``.
        """
        pin = ChainPin.try_parse(data, version)
        src = chain_head_source(data, version)
        if pin is None or src is None:
            return None

        block_hash = src.get("hash")
        height = src.get("height")
        if not isinstance(block_hash, str):
            return None
        # bool is a subclass of int; reject it explicitly.
        if not isinstance(height, int) or isinstance(height, bool) or height < 0:
            return None

        # ``synced`` sits at the root of the payload in both generations.
        synced = isinstance(data, dict) and data.get("synced") is True

        return cls(pin=pin, hash=block_hash, height=height, synced=synced)

    @classmethod
    def parse(cls, data: Any, version: ApiVersion) -> "ChainHead":
        """Like :meth:`try_parse` but raises on invalid input."""
        head = cls.try_parse(data, version)
        if head is None:
            raise InvalidChainHeadError(f"Invalid {version} chain head response")
        return head