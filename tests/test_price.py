import math

import pytest

from warthog_py.errors import InvalidPriceError
from warthog_py.price import Price
from warthog_py.token_decimals import TokenDecimals


class TestPrice:
    def test_from_double_internal_invalid(self):
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(0.0)
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(0)
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(-1.0)
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(-0.5)
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(float("inf"))
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(float("-inf"))
        with pytest.raises(InvalidPriceError):
            Price.from_double_internal(float("nan"))

    def test_try_from_double_internal(self):
        assert Price.try_from_double_internal(0.0) is None
        assert Price.try_from_double_internal(1.5) is not None

    def test_roundtrip_double_raw(self):
        for input_val in [
            0.0000001354,
            0.000001345,
            0.000016574,
            0.00012043,
            0.0011239,
            0.02341,
            0.1812,
            0.5123,
            1.813,
            2.5213,
            16.430,
            194.75,
            1834.5678,
            12_093,
            234_091,
            9_582_389,
            190_123_900,
            9_230_942_914,
        ]:
            price = Price.from_double_internal(input_val)
            output = price.to_double_raw()
            assert abs(1 - output / input_val) * 100 < 0.01

    def test_from_hex_roundtrip(self):
        hex_str = "c0e74d"
        price = Price.from_hex(hex_str)
        assert price.to_hex() == hex_str

    def test_from_hex_wrong_length(self):
        with pytest.raises(InvalidPriceError):
            Price.from_hex("abc")

    def test_from_hex_invalid_hex(self):
        with pytest.raises(InvalidPriceError):
            Price.from_hex("zzzzzz")

    def test_from_hex_invalid_exponent(self):
        # exponent >= 128 is now rejected (consistent with from_mantissa_exponent)
        with pytest.raises(InvalidPriceError):
            Price.from_hex("ffff80")
        with pytest.raises(InvalidPriceError):
            Price.from_hex("ffffff")

    def test_from_mantissa_exponent_valid(self):
        price = Price.from_mantissa_exponent(0x8000, 0)
        assert price.mantissa == 0x8000
        assert price.exponent == 63

    def test_from_mantissa_exponent_invalid(self):
        with pytest.raises(InvalidPriceError):
            Price.from_mantissa_exponent(0x7000, 0)

    def test_from_number_decimals(self):
        price = Price.from_number_decimals(1.5, TokenDecimals.wart(), False)
        assert isinstance(price, Price)

    def test_max(self):
        assert Price.max().mantissa == 0xFFFF
        assert Price.max().exponent == 127