"""The binary encodings the transaction builders sign.

Both node families sign the same bytes for a WART transfer, so a signature
produced for one is valid for the other. Only the JSON around them differs.
"""

import struct

from warthog_py.address import Address
from warthog_py.chain_pin import ChainPin
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.wart import Wart


def sign(account, binary: bytes) -> str:
    """Sign the binary payload with the account (account hashes internally)."""
    _, _, _, signature_hex = account.sign_bytes(binary)
    return signature_hex


def prefix(pin_height: int, nonce_id: int) -> bytes:
    """Common prefix: ``pinHeight(4) || nonceId(4) || reserved(3)``.

    The 3 reserved bytes sit between the two u32 fields and don't pack
    nicely into ``struct.pack`` alone, so we emit them explicitly.
    """
    return struct.pack(">II", pin_height, nonce_id) + b"\x00\x00\x00"


def u64be(value: int) -> bytes:
    """Big-endian unsigned 64-bit encoding of ``value``."""
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"u64be value must be a non-negative integer, got: {value}")
    return struct.pack(">Q", value)


def address_bytes(address: str) -> bytes:
    """Extract the 20-byte payload (first 40 hex chars) from a 48-char address."""
    return bytes.fromhex(address[:40])


def name_pad5(name: str) -> bytes:
    """Truncate or zero-pad a name to exactly 5 bytes."""
    encoded = name.encode("ascii", errors="replace")[:5]
    return encoded.ljust(5, b"\x00")


def wart_transfer_bytes(
    chain_pin: ChainPin,
    fee: RoundedFee,
    nonce_id: NonceId,
    to_addr: Address,
    wart: Wart,
) -> bytes:
    """The bytes signed for a WART transfer."""
    return (
        bytes.fromhex(chain_pin.pin_hash)
        + prefix(chain_pin.pin_height, nonce_id.value)
        + u64be(fee.e8)
        + address_bytes(to_addr.hex)
        + u64be(wart.e8)
    )
