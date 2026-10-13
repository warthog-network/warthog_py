"""A chain pin: the (height, hash) pair that transactions are built against.

Pin heights are always multiples of 32. A block body stores a 1-byte *relative*
pin and the absolute height is ``relativePin << 5``, so at most 256 distinct
pins exist in a chain. ``core/defi``'s ``PinHeight`` type rejects any height
that is not one of them.

A pin is not a single permanent thing. The chain advances through a sequence of
them, each at a height >= the last. ``/chain/head`` reports the most recently
proposed one, which is what a client needs in order to build a valid
transaction.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from warthog_py.constants import API_VERSIONS, ApiVersion

PIN_HEIGHT_MULTIPLE: int = 32
"""Pin heights are always multiples of 32 (1-byte relative pin)."""


@dataclass(frozen=True)
class ChainPin:
    """A proposed chain pin."""

    pin_hash: str
    pin_height: int

    @staticmethod
    def validate(pin_hash: Any, pin_height: Any) -> bool:
        """Check that a pair of raw values forms a well-formed pin."""
        if not isinstance(pin_hash, str) or len(pin_hash) != 64:
            return False
        # bool is a subclass of int; reject it explicitly.
        if not isinstance(pin_height, int) or isinstance(pin_height, bool):
            return False
        return pin_height >= 0 and pin_height % PIN_HEIGHT_MULTIPLE == 0

    @classmethod
    def try_parse(cls, data: Any, version: ApiVersion) -> Optional["ChainPin"]:
        """Extract the pin from a ``/chain/head`` payload.

        Reads the fields according to the API generation the payload came from.
        Returns ``None`` if the payload does not match ``version``.
        """
        src = chain_head_source(data, version)
        if src is None:
            return None
        pin_hash = src.get("pinHash")
        pin_height = src.get("pinHeight")
        if not cls.validate(pin_hash, pin_height):
            return None
        return cls(pin_hash=pin_hash, pin_height=pin_height)


def chain_head_source(data: Any, version: ApiVersion) -> Optional[Dict[str, Any]]:
    """Locate the ChainHead fields within a ``/chain/head`` payload.

    Both generations serialize the same C++ type, ``Head { ChainHead chainHead;
    bool synced; }``. V1 (``core/master``, ``core/dev``) uses a hand-written
    ``to_json(API::Head&)`` that flattens ChainHead into the top level; V2
    (``core/defi``) uses glaze, which reflects the nesting automatically.

    Returns the ChainHead fields, or ``None`` when the payload is not the
    expected shape.
    """
    if version not in API_VERSIONS:
        return None
    if not isinstance(data, dict):
        return None

    # V1 puts the fields at the top level; V2 wraps them in ``chainHead``.
    src = data if version == "v1" else data.get("chainHead")
    return src if isinstance(src, dict) else None