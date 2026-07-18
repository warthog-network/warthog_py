import pytest

from warthog_py.errors import InvalidDecimalsError
from warthog_py.token_decimals import TokenDecimals


class TestTokenDecimals:
    def test_rejects_invalid_decimals(self):
        with pytest.raises(InvalidDecimalsError):
            TokenDecimals.new(-1)
        with pytest.raises(InvalidDecimalsError):
            TokenDecimals.new(19)

    def test_wart_preset(self):
        assert TokenDecimals.wart().decimals == 8

    def test_liquidity_preset(self):
        assert TokenDecimals.liquidity().decimals == 8