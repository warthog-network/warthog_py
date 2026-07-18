import pytest

from warthog_py.errors import InvalidFundsError
from warthog_py.wart import Wart


class TestWart:
    def test_parse_valid(self):
        w = Wart.parse("1.123")
        assert w.e8 == 112_300_000

    def test_parse_too_many_decimals(self):
        with pytest.raises(InvalidFundsError):
            Wart.parse("1.123456789")

    def test_from_e8_valid(self):
        w = Wart.from_e8(100_000_000)
        assert w.e8 == 100_000_000

    def test_from_e8_negative(self):
        with pytest.raises(InvalidFundsError):
            Wart.from_e8(-1)
        with pytest.raises(InvalidFundsError):
            Wart.from_e8(-100_000_000)

    def test_try_from_e8(self):
        assert Wart.try_from_e8(100) is not None
        assert Wart.try_from_e8(-1) is None