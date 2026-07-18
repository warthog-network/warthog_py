import pytest

from warthog_py.errors import InvalidFundsError
from warthog_py.liquidity import Liquidity


class TestLiquidity:
    def test_parse_valid(self):
        l = Liquidity.parse("1.5")
        assert l.e8 == 150_000_000

    def test_parse_too_many_decimals(self):
        with pytest.raises(InvalidFundsError):
            Liquidity.parse("1.123456789")

    def test_from_e8_valid(self):
        l = Liquidity.from_e8(100)
        assert l.e8 == 100

    def test_from_e8_negative(self):
        with pytest.raises(InvalidFundsError):
            Liquidity.from_e8(-1)
        with pytest.raises(InvalidFundsError):
            Liquidity.from_e8(-100)