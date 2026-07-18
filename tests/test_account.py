import hashlib

import pytest

from warthog_py.account import Account
from warthog_py.address import Address


PRIVATE_KEY_HEX = "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"


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
        assert account.public_key_hex == (
            "02916a397088159baf27b3ce1271a859e3e6ea27db913a94086423e5867994e705"
        )
        assert account.address.hex == "3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093"

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

    def test_sign(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        digest = hashlib.sha256(b"hello world").digest()
        r, s, recid, signature_hex = account.sign(digest)
        sig_bytes = bytes.fromhex(signature_hex)
        assert len(sig_bytes) == 65
        assert recid in (0, 1, 2, 3)
        # Low-s form: s must be <= order/2
        order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        assert int.from_bytes(s, "big") <= order // 2

    def test_sign_bad_length(self):
        account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
        with pytest.raises(Exception):
            account.sign(b"short")