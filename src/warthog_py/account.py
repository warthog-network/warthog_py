"""Wallet account for signing transactions on the Warthog network.

Uses secp256k1 elliptic curve for key management. The address is
derived as ``RIPEMD-160(SHA-256(compressed-public-key))`` with a 4-byte
SHA-256 checksum appended.

Signing follows the BIP-62 / secp256k1 convention: the signature is
returned in **low-s form** (canonical signature) with the recovery id
flipped to match if normalization occurs. This is the same convention
documented in ``docs/developers/integration/wallets.md``.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple

from ecdsa import SECP256k1, SigningKey
from pycoin.ecdsa.secp256k1 import secp256k1_generator

from warthog_py.address import Address
from warthog_py.errors import (
    InvalidPrivateKeyError,
    InvalidSignatureError,
)


@dataclass(frozen=True)
class Account:
    """A secp256k1 wallet account."""

    private_key_hex: str
    public_key_hex: str
    address: Address

    @property
    def private_key(self) -> bytes:
        """Raw 32-byte private key."""
        return bytes.fromhex(self.private_key_hex)

    @property
    def public_key(self) -> bytes:
        """Raw 33-byte compressed public key."""
        return bytes.fromhex(self.public_key_hex)

    @property
    def private_key_int(self) -> int:
        """Private key as a Python int."""
        return int(self.private_key_hex, 16)

    @classmethod
    def from_random(cls) -> "Account":
        """Generate a new random account with a fresh private key."""
        return cls.from_private_key(SigningKey.generate(curve=SECP256k1).to_string())

    @classmethod
    def from_private_key(cls, private_key: bytes) -> "Account":
        """Create an account from a raw 32-byte private key.

        Raises ``InvalidPrivateKeyError`` if the key is not exactly 32 bytes.
        """
        if not isinstance(private_key, (bytes, bytearray)):
            raise InvalidPrivateKeyError(
                f"private key must be bytes or bytearray, got: {type(private_key).__name__}"
            )
        if len(private_key) != 32:
            raise InvalidPrivateKeyError(
                f"private key must be exactly 32 bytes, got {len(private_key)}"
            )

        private_key = bytes(private_key)
        sk = SigningKey.from_string(private_key, curve=SECP256k1)
        vk = sk.get_verifying_key()
        public_compressed = vk.to_string("compressed")
        address = _derive_address(public_compressed)
        return cls(
            private_key_hex=private_key.hex(),
            public_key_hex=public_compressed.hex(),
            address=address,
        )

    @classmethod
    def from_private_key_hex(cls, hex_str: str) -> "Account":
        """Create an account from a 64-character hex private key.

        Raises ``InvalidPrivateKeyError`` on invalid input.
        """
        if not isinstance(hex_str, str) or len(hex_str) != 64:
            raise InvalidPrivateKeyError(
                f"private key hex must be a 64-character string, got: {hex_str!r}"
            )
        try:
            private_key = bytes.fromhex(hex_str)
        except ValueError as e:
            raise InvalidPrivateKeyError(f"invalid hex: {e}") from e
        return cls.from_private_key(private_key)

    @classmethod
    def try_from_private_key_hex(cls, hex_str: str) -> Optional["Account"]:
        try:
            return cls.from_private_key_hex(hex_str)
        except InvalidPrivateKeyError:
            return None

    def sign(self, hash_bytes: bytes) -> Tuple[bytes, bytes, int, str]:
        """Sign a 32-byte hash with the account's private key.

        Returns ``(r, s, recid, signature_hex)`` where ``signature_hex``
        is the 65-byte signature (``r || s || recid``) as 130 hex chars.

        The signature is normalized to **low-s form** (BIP-62). If
        normalization occurs, the recovery id is flipped to maintain
        consistency with the canonical signature.
        """
        if not isinstance(hash_bytes, (bytes, bytearray)):
            raise InvalidSignatureError(
                f"hash must be bytes or bytearray, got: {type(hash_bytes).__name__}"
            )
        if len(hash_bytes) != 32:
            raise InvalidSignatureError(
                f"hash must be exactly 32 bytes, got {len(hash_bytes)}"
            )

        val = int.from_bytes(hash_bytes, "big")
        order = secp256k1_generator.order()

        r, s, recid = secp256k1_generator.sign_with_recid(self.private_key_int, val)

        # Normalize to low-s form
        if s > order // 2:
            s = order - s
            recid ^= 1

        r_bytes = r.to_bytes(32, "big")
        s_bytes = s.to_bytes(32, "big")
        return (
            r_bytes,
            s_bytes,
            recid,
            (r_bytes + s_bytes + bytes([recid])).hex(),
        )


def _derive_address(compressed_pubkey: bytes) -> Address:
    from warthog_py.ripemd160 import ripemd160

    sha = hashlib.sha256(compressed_pubkey).digest()
    ripe = ripemd160(sha)
    return Address.from_raw(ripe.hex())