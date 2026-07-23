import hashlib

import pytest

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.errors import InvalidSignatureError


PRIVATE_KEY_HEX = "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"
PUBLIC_KEY_HEX = "02916a397088159baf27b3ce1271a859e3e6ea27db913a94086423e5867994e705"
ADDRESS_HEX = "3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093"


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
