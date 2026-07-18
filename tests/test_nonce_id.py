import secrets

import pytest

from warthog_py.constants import MAX_U32
from warthog_py.errors import InvalidNonceError
from warthog_py.nonce_id import NonceId


class TestNonceId:
    def test_validate_valid(self):
        assert NonceId.validate(0)
        assert NonceId.validate(1)
        assert NonceId.validate(MAX_U32)
        assert NonceId.validate(12345)

    def test_validate_invalid(self):
        assert not NonceId.validate(-1)
        assert not NonceId.validate(MAX_U32 + 1)
        assert not NonceId.validate("123")
        assert not NonceId.validate(None)

    def test_from_number(self):
        nonce = NonceId.from_number(12345)
        assert nonce.value == 12345

    def test_from_number_invalid(self):
        with pytest.raises(InvalidNonceError):
            NonceId.from_number(-1)
        with pytest.raises(InvalidNonceError):
            NonceId.from_number(MAX_U32 + 1)

    def test_try_from_number(self):
        assert NonceId.try_from_number(12345) is not None
        assert NonceId.try_from_number(-1) is None

    def test_random_in_range(self):
        for _ in range(20):
            nonce = NonceId.random()
            assert NonceId.validate(nonce.value)