import pytest

from warthog_py.address import Address
from warthog_py.errors import InvalidAddressError


class TestAddress:
    def test_from_hex_valid(self):
        hex_addr = "3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093"
        addr = Address.from_hex(hex_addr)
        assert addr.hex == hex_addr

    def test_from_hex_wrong_length(self):
        with pytest.raises(InvalidAddressError):
            Address.from_hex("abc123")

        with pytest.raises(InvalidAddressError):
            Address.from_hex(
                "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9"
            )

    def test_from_hex_non_hex(self):
        with pytest.raises(InvalidAddressError):
            Address.from_hex("g" * 48)

    def test_from_hex_invalid_checksum(self):
        with pytest.raises(InvalidAddressError):
            Address.from_hex("0" * 40 + "00000000")

    def test_from_raw(self):
        addr = Address.from_raw("0" * 40)
        assert len(addr.hex) == 48

    def test_from_raw_wrong_length(self):
        with pytest.raises(InvalidAddressError):
            Address.from_raw("abc123")

    def test_try_from_hex(self):
        assert Address.try_from_hex("3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093") is not None
        assert Address.try_from_hex("bad") is None

    def test_validate(self):
        assert Address.validate("3661579d61abde5837a8686dc4d65348a2fc61b1fe5f4093")
        bad_checksum = "3661579d61abde5837a8686dc4d65348a2fc61b1" + "00000000"
        assert not Address.validate(bad_checksum)
        assert not Address.validate("abc123")
        assert not Address.validate("g" * 48)