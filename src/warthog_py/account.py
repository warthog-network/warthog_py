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
from typing import Optional, Tuple, Union

from ecdsa import SECP256k1, SigningKey
from pycoin.ecdsa.secp256k1 import secp256k1_generator

from warthog_py.address import Address
from warthog_py.errors import (
    InvalidPrivateKeyError,
    InvalidSignatureError,
)

# Signature tuple: (r_bytes, s_bytes, recid, signature_hex)
SignatureTuple = Tuple[bytes, bytes, int, str]

# Either a SignatureTuple, a (r, s, recid) tuple, or a 130-char hex string
SignatureInput = Union[SignatureTuple, Tuple[bytes, bytes, int], str]


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

    def sign_bytes(self, message: Union[bytes, bytearray, str]) -> SignatureTuple:
        """Sign arbitrary bytes with the account's private key.

        The message is hashed with **SHA-256** (the same scheme transaction
        signing uses). Accepts ``bytes``, ``bytearray``, or ``str`` (UTF-8
        encoded).

        Returns ``(r, s, recid, signature_hex)`` where ``signature_hex`` is
        the 65-byte signature (``r || s || recid``) as 130 lowercase hex
        chars.

        The signature is normalized to **low-s form** (BIP-62). If
        normalization occurs, the recovery id is flipped to maintain
        consistency with the canonical signature.

        Raises ``InvalidSignatureError`` if signing fails.
        """
        digest = hashlib.sha256(_to_bytes(message)).digest()
        return self._sign_hash(digest)

    def _sign_hash(self, digest: bytes) -> SignatureTuple:
        """Internal: sign a 32-byte digest with low-s normalization."""
        if not isinstance(digest, (bytes, bytearray)) or len(digest) != 32:
            raise InvalidSignatureError(
                f"digest must be exactly 32 bytes, got {type(digest).__name__} of length {len(digest) if hasattr(digest, '__len__') else '?'}"
            )

        val = int.from_bytes(digest, "big")
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

    @staticmethod
    def recover_public_key(
        message: Union[bytes, bytearray, str],
        signature: SignatureInput,
    ) -> bytes:
        """Recover the compressed public key (33 bytes) that produced the
        given signature for the given message.

        ``signature`` accepts:
        - a 4-tuple ``(r, s, recid, signature_hex)`` (the shape ``sign_bytes`` returns)
        - a 3-tuple ``(r, s, recid)``
        - a 130-char hex string ``r || s || recid``

        Raises ``InvalidSignatureError`` if the signature is malformed or
        recovery fails.
        """
        digest = hashlib.sha256(_to_bytes(message)).digest()
        r, s, recid = _parse_signature(signature)
        pubkey_bytes = _recover_pubkey(digest, r, s, recid)
        if pubkey_bytes is None:
            raise InvalidSignatureError("recovery failed")
        return pubkey_bytes

    @staticmethod
    def try_recover_public_key(
        message: Union[bytes, bytearray, str],
        signature: SignatureInput,
    ) -> Optional[bytes]:
        """Like ``recover_public_key`` but returns ``None`` on failure."""
        try:
            return Account.recover_public_key(message, signature)
        except InvalidSignatureError:
            return None

    @staticmethod
    def recover_address(
        message: Union[bytes, bytearray, str],
        signature: SignatureInput,
    ) -> Address:
        """Recover the Warthog address that produced the given signature.

        Derived from the recovered public key via the same
        ``RIPEMD-160(SHA-256(pubkey)) + 4-byte checksum`` pipeline the
        protocol uses for addresses.

        Raises ``InvalidSignatureError`` on failure.
        """
        pubkey_bytes = Account.recover_public_key(message, signature)
        return _pubkey_to_address(pubkey_bytes)

    @staticmethod
    def try_recover_address(
        message: Union[bytes, bytearray, str],
        signature: SignatureInput,
    ) -> Optional[Address]:
        """Like ``recover_address`` but returns ``None`` on failure."""
        try:
            return Account.recover_address(message, signature)
        except InvalidSignatureError:
            return None


def _to_bytes(message: Union[bytes, bytearray, str]) -> bytes:
    """Convert a message input to bytes. UTF-8 for strings."""
    if isinstance(message, str):
        return message.encode("utf-8")
    if isinstance(message, (bytes, bytearray)):
        return bytes(message)
    raise InvalidSignatureError(
        f"message must be bytes, bytearray, or str, got: {type(message).__name__}"
    )


def _parse_signature(signature: SignatureInput) -> Tuple[int, int, int]:
    """Normalize signature input to ``(r, s, recid)`` as ints."""
    if isinstance(signature, str):
        if len(signature) != 130:
            raise InvalidSignatureError(
                f"signature hex string must be 130 chars, got {len(signature)}"
            )
        try:
            sig_bytes = bytes.fromhex(signature)
        except ValueError as e:
            raise InvalidSignatureError(f"signature is not valid hex: {e}") from e
        r = int.from_bytes(sig_bytes[:32], "big")
        s = int.from_bytes(sig_bytes[32:64], "big")
        recid = sig_bytes[64]
        if recid not in (0, 1, 2, 3):
            raise InvalidSignatureError(
                f"recid must be in {{0, 1, 2, 3}}, got {recid}"
            )
        return r, s, recid

    if isinstance(signature, tuple):
        if len(signature) == 4:
            r_bytes, s_bytes, recid, _ = signature
        elif len(signature) == 3:
            r_bytes, s_bytes, recid = signature
        else:
            raise InvalidSignatureError(
                f"signature tuple must be (r, s, recid) or (r, s, recid, hex), got {len(signature)} elements"
            )

        if not isinstance(r_bytes, (bytes, bytearray)) or len(r_bytes) != 32:
            raise InvalidSignatureError(f"r must be 32 bytes, got {len(r_bytes)}")
        if not isinstance(s_bytes, (bytes, bytearray)) or len(s_bytes) != 32:
            raise InvalidSignatureError(f"s must be 32 bytes, got {len(s_bytes)}")
        if not isinstance(recid, int) or recid not in (0, 1, 2, 3):
            raise InvalidSignatureError(
                f"recid must be int in {{0, 1, 2, 3}}, got {recid!r}"
            )
        return int.from_bytes(r_bytes, "big"), int.from_bytes(s_bytes, "big"), recid

    raise InvalidSignatureError(
        f"signature must be a tuple or 130-char hex string, got: {type(signature).__name__}"
    )


def _recover_pubkey(digest: bytes, r: int, s: int, recid: int) -> Optional[bytes]:
    """Recover a compressed secp256k1 public key from a signature.

    Returns the 33-byte compressed public key, or ``None`` if recovery
    fails (e.g. recid refers to no valid point on the curve).
    """
    order = secp256k1_generator.order()
    is_second_key = recid >> 1
    y_parity = recid & 1

    x = r + (order if is_second_key else 0)

    try:
        points = secp256k1_generator.points_for_x(x)
    except ValueError:
        return None

    # points_for_x returns (p_even, p_odd): index by y parity
    R = points[y_parity]

    inv_r = secp256k1_generator.inverse(r)
    s_over_r = s * inv_r
    minus_e_over_r = -(inv_r * int.from_bytes(digest, "big")) * secp256k1_generator
    try:
        Q = s_over_r * R + minus_e_over_r
    except ValueError:
        return None

    prefix = b"\x02" if Q[1] % 2 == 0 else b"\x03"
    return prefix + Q[0].to_bytes(32, "big")


def _derive_address(compressed_pubkey: bytes) -> Address:
    from warthog_py.ripemd160 import ripemd160

    sha = hashlib.sha256(compressed_pubkey).digest()
    ripe = ripemd160(sha)
    return Address.from_raw(ripe.hex())


def _pubkey_to_address(pubkey_bytes: bytes) -> Address:
    """Derive a Warthog address from a 33-byte compressed public key."""
    from warthog_py.ripemd160 import ripemd160

    sha = hashlib.sha256(pubkey_bytes).digest()
    ripe = ripemd160(sha)
    return Address.from_raw(ripe.hex())
