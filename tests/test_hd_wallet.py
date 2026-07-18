import pytest

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.hd_wallet import HDWallet


MNEMONIC = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"


class TestHDWallet:
    def test_from_mnemonic_derives_account(self):
        wallet = HDWallet.from_mnemonic(MNEMONIC)
        account = wallet.derive_account_at_index(0)
        assert len(account.address.hex) == 48
        assert len(account.private_key_hex) == 64
        assert Address.validate(account.address.hex)

    def test_indices_differ(self):
        wallet = HDWallet.from_mnemonic(MNEMONIC)
        a0 = wallet.derive_account_at_index(0)
        a1 = wallet.derive_account_at_index(1)
        assert a0.address.hex != a1.address.hex

    def test_path_and_index_match(self):
        wallet = HDWallet.from_mnemonic(MNEMONIC)
        a_from_index = wallet.derive_account_at_index(0)
        a_from_path = wallet.derive_account_from_path("0/0")
        assert a_from_index.address.hex == a_from_path.address.hex

    def test_m_path_works(self):
        wallet = HDWallet.from_mnemonic(MNEMONIC)
        a = wallet.derive_account_from_path("m/0/0")
        assert isinstance(a, Account)

    def test_invalid_mnemonic_rejected(self):
        with pytest.raises(Exception):
            HDWallet.from_mnemonic("")

    def test_invalid_index_rejected(self):
        wallet = HDWallet.from_mnemonic(MNEMONIC)
        with pytest.raises(Exception):
            wallet.derive_account_at_index(-1)