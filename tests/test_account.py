import hashlib

import pytest

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.errors import InvalidSignatureError


PRIVATE_KEY_HEX = "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"
PUBLIC_KEY_HEX = "02916a397088159baf27b3ce1271a859e3e6ea27db913a94086423e5867994e705"
ADDRESS_HEX = "3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093"

# Pinned RFC 6979 vectors, shared with warthog-ts and warthog_ex so that all
# three SDKs assert the same bytes for the same key and message. The third
# vector uses a message whose SHA-256 digest starts with a zero byte, which is
# the input class where a faulty nonce truncation produces a signature that is
# nearly, but not exactly, correct.
PINNED_VECTORS = [
    {
        "name": "plain message",
        "message": b"hello",
        "digest": "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        "r": "dbeafb9b24ddf7d24c0bf82f078bf2ecc068654eb4873e3c74814543dd65ef49",
        "s": "711681c2dc77d895a78aea9485189758226f9cefd8091b830961c3f09ef80f90",
        "recid": 1,
    },
    {
        "name": "empty message",
        "message": b"",
        "digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "r": "ce84cb32ec1c4aca7e8794124303ff7bc0de08864aee6acbf66df1ce757a7b82",
        "s": "3f0a1154a8e8ba7fff32ea3fadd883fa10cc532d41f5d60def06dd9d963c5e02",
        "recid": 0,
    },
    {
        "name": "message with a leading zero digest byte",
        "message": b"warthog-leading-zero-264",
        "digest": "0049704e969839bd144391b75529b632f76923764a850381952da58ed342f067",
        "r": "0ddfd65fe9031ede0e40df065b5a686b29907058e2d15d9c9b2418194464d99b",
        "s": "63e40acfb3f62dab3eb0b4a93d857a52c1227be852fad81335eab417da39f694",
        "recid": 0,
    },
]


class TestAccount:
    def test_from_random(self):
        account = Account.from_random()
        assert len(account.private_key_hex) == 64
        assert len(account.public_key_hex) == 66
        assert len(account.address.hex) == 48
        assert Address.validate(account.address.hex)

    def test_from_private_key_hex_known(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        assert account.private_key_hex == PRIVATE_KEY_HEX
        assert account.public_key_hex == PUBLIC_KEY_HEX
        assert account.address.hex == ADDRESS_HEX

    def test_from_private_key_known(self):
        account = Account.from_private_key(bytes.fromhex(PRIVATE_KEY_HEX))
        assert account.private_key_hex == PRIVATE_KEY_HEX

    def test_from_private_key_bad_length(self):
        with pytest.raises(Exception):
            Account.from_private_key(b"too_short")

    def test_try_from_private_key_hex(self):
        assert Account.try_from_private_key_hex(PRIVATE_KEY_HEX) is not None
        assert Account.try_from_private_key_hex("not_hex") is None
        assert Account.try_from_private_key_hex("a") is None

    def test_sign_bytes_returns_valid_signature(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        r, s, recid, signature_hex = account.sign_bytes(b"hello")
        sig_bytes = bytes.fromhex(signature_hex)
        assert len(sig_bytes) == 65
        assert len(r) == 32
        assert len(s) == 32
        assert recid in (0, 1, 2, 3)
        # Low-s form
        order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        assert int.from_bytes(s, "big") <= order // 2

    def test_sign_bytes_deterministic(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig1 = account.sign_bytes(b"hello")
        sig2 = account.sign_bytes(b"hello")
        assert sig1 == sig2

    def test_sign_bytes_string_equals_bytes(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        assert account.sign_bytes("hello") == account.sign_bytes(b"hello")

    def test_sign_bytes_empty_input(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        r, s, recid, signature_hex = account.sign_bytes(b"")
        assert len(signature_hex) == 130
        assert recid in (0, 1, 2, 3)

    def test_sign_bytes_rejects_invalid_input(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        with pytest.raises(InvalidSignatureError):
            account.sign_bytes(12345)
        with pytest.raises(InvalidSignatureError):
            account.sign_bytes(None)

    def test_recover_public_key_round_trips(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        recovered = Account.recover_public_key(b"hello", sig)
        assert recovered == bytes.fromhex(PUBLIC_KEY_HEX)

    def test_recover_public_key_accepts_hex_string(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        _, _, _, signature_hex = account.sign_bytes(b"hello")
        recovered = Account.recover_public_key(b"hello", signature_hex)
        assert recovered == bytes.fromhex(PUBLIC_KEY_HEX)

    def test_recover_public_key_accepts_3tuple(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        r, s, recid, _ = account.sign_bytes(b"hello")
        recovered = Account.recover_public_key(b"hello", (r, s, recid))
        assert recovered == bytes.fromhex(PUBLIC_KEY_HEX)

    def test_recover_public_key_string_input(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        # Recover via str message (same as bytes "hello")
        recovered = Account.recover_public_key("hello", sig)
        assert recovered == bytes.fromhex(PUBLIC_KEY_HEX)

    def test_recover_public_key_tampered_message(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        recovered = Account.recover_public_key(b"hellp", sig)
        assert recovered != bytes.fromhex(PUBLIC_KEY_HEX)

    def test_recover_public_key_recid_sensitive(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        r, s, recid, _ = account.sign_bytes(b"hello")
        flipped_recid = recid ^ 1
        # May raise or return a different key, depending on whether the flipped
        # recid corresponds to a valid point on the curve.
        try:
            recovered = Account.recover_public_key(b"hello", (r, s, flipped_recid))
            assert recovered != bytes.fromhex(PUBLIC_KEY_HEX)
        except InvalidSignatureError:
            pass

    def test_recover_public_key_invalid_signature(self):
        with pytest.raises(InvalidSignatureError):
            Account.recover_public_key(b"hello", "abcd")
        with pytest.raises(InvalidSignatureError):
            Account.recover_public_key(b"hello", "z" * 130)
        with pytest.raises(InvalidSignatureError):
            Account.recover_public_key(b"hello", (b"bad", b"bad", 5))

    def test_try_recover_public_key(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        assert Account.try_recover_public_key(b"hello", sig) is not None
        assert Account.try_recover_public_key(b"hello", "abcd") is None

    def test_recover_address_round_trips(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        recovered = Account.recover_address(b"hello", sig)
        assert recovered.hex == ADDRESS_HEX

    def test_recover_address_tampered_message(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        recovered = Account.recover_address(b"hellp", sig)
        assert recovered.hex != ADDRESS_HEX

    def test_try_recover_address(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        sig = account.sign_bytes(b"hello")
        assert Account.try_recover_address(b"hello", sig) is not None
        assert Account.try_recover_address(b"hello", "abcd") is None

    def test_hashlib_sha256_unchanged(self):
        # Sanity: the SHA-256 hashing path used by sign_bytes matches
        # a manual hashlib.sha256(message).digest() invocation.
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        message = b"hello"
        r_a, s_a, recid_a, _ = account.sign_bytes(message)
        # Sign the digest manually via the internal helper
        r_b, s_b, recid_b, _ = account._sign_hash(hashlib.sha256(message).digest())
        assert (r_a, s_a, recid_a) == (r_b, s_b, recid_b)

    def test_pinned_vectors_hash_to_their_digest(self):
        for vector in PINNED_VECTORS:
            digest = hashlib.sha256(vector["message"]).hexdigest()
            assert digest == vector["digest"], vector["name"]

    def test_sign_bytes_matches_pinned_rfc6979_vectors(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)

        for vector in PINNED_VECTORS:
            r, s, recid, signature_hex = account.sign_bytes(vector["message"])

            assert r.hex() == vector["r"], vector["name"]
            assert s.hex() == vector["s"], vector["name"]
            assert recid == vector["recid"], vector["name"]
            assert signature_hex == (
                vector["r"] + vector["s"] + f"{vector['recid']:02x}"
            ), vector["name"]

    def test_recover_public_key_matches_pinned_rfc6979_vectors(self):
        for vector in PINNED_VECTORS:
            signature_hex = vector["r"] + vector["s"] + f"{vector['recid']:02x}"
            recovered = Account.recover_public_key(vector["message"], signature_hex)

            assert recovered == bytes.fromhex(PUBLIC_KEY_HEX), vector["name"]
