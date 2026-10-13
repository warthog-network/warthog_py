"""Constants used across the warthog_py library."""

from typing import Literal

MAX_U64: int = 0xFFFFFFFFFFFFFFFF
"""Maximum 64-bit unsigned integer (18,446,744,073,709,551,615)."""

MAX_U32: int = 0xFFFFFFFF
"""Maximum 32-bit unsigned integer (4,294,967,295)."""

ApiVersion = Literal["v1", "v2"]
"""Which generation of ``/chain/head`` JSON a node returns.

Both generations serialize the same C++ type, ``Head { ChainHead chainHead;
bool synced; }``. Only the serializer differs:

- **V1** — ``core/master`` and ``core/dev``. A hand-written
  ``to_json(API::Head&)`` flattens ChainHead field-by-field into the top
  level; ``synced`` stays at the root.
  ``{ hash, height, pinHash, pinHeight, ..., synced }``

- **V2** — ``core/defi`` (the DeFi branch). Glaze auto-serialization reflects
  the nested struct, so ChainHead is wrapped; ``synced`` sits beside it.
  ``{ chainHead: { hash, height, pinHash, pinHeight, ... }, synced }``

The two are NOT interchangeable. Both carry the same fields, so validation is
identical. Only the location differs.
"""

API_VERSIONS: tuple = ("v1", "v2")
"""The supported ``/chain/head`` API generations."""