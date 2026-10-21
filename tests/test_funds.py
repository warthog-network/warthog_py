import pytest

from warthog_py.errors import InvalidFundsError
from warthog_py.funds import Funds
from warthog_py.parsed_funds import ParsedFunds
from warthog_py.token_decimals import TokenDecimals


class TestFunds:
    def test_parse_valid(self):
        f = Funds.parse("1.123", TokenDecimals.new(4))
        assert f.amount == 11230

    def test_parse_invalid_due_to_decimals(self):
        # 1.123 has 3 decimals, 2-decimal token rejects
        with pytest.raises(InvalidFundsError):
            Funds.parse("1.123", TokenDecimals.new(2))

    def test_from_parsed_funds(self):
        pf = ParsedFunds(val=1123, decimal_places=3)
        f = Funds.from_parsed_funds(pf, TokenDecimals.new(4))
        assert f.amount == 11230

    def test_from_amount(self):
        # The amount is in the token's smallest unit, so it needs no decimals.
        assert Funds.from_amount(11_230).amount == 11_230

    def test_from_amount_rejects_invalid(self):
        with pytest.raises(InvalidFundsError):
            Funds.from_amount(-1)
        with pytest.raises(InvalidFundsError):
            Funds.from_amount(2**64)
        assert Funds.try_from_amount(-1) is None

    # uint64 conversion behavior — these mirror the warthog-ts test_funds.test.ts cases
    # exactly. Each tests one parsed string against decimal-place counts 0/4/12/16.

    def test_from_parsed_funds_for_1_123(self):
        pf = ParsedFunds.parse("1.123")
        # 0 decimals: input has 3 decimals, 0-decimal token rejects
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(0))

        f4 = Funds.from_parsed_funds(pf, TokenDecimals.new(4))
        assert f4.amount == 11230

        f12 = Funds.from_parsed_funds(pf, TokenDecimals.new(12))
        assert f12.amount == 1_123_000_000_000

        f16 = Funds.from_parsed_funds(pf, TokenDecimals.new(16))
        assert f16.amount == 11_230_000_000_000_000

    def test_from_parsed_funds_for_101_123000(self):
        pf = ParsedFunds.parse("101.123000")
        # 0 and 4 decimals reject (input has 6 decimals)
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(0))
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(4))

        f12 = Funds.from_parsed_funds(pf, TokenDecimals.new(12))
        assert f12.amount == 101_123_000_000_000

        f16 = Funds.from_parsed_funds(pf, TokenDecimals.new(16))
        assert f16.amount == 1_011_230_000_000_000_000

    def test_from_parsed_funds_for_101_1230001111(self):
        pf = ParsedFunds.parse("101.1230001111")
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(0))
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(4))

        f12 = Funds.from_parsed_funds(pf, TokenDecimals.new(12))
        assert f12.amount == 101_123_000_111_100

        f16 = Funds.from_parsed_funds(pf, TokenDecimals.new(16))
        assert f16.amount == 1_011_230_001_111_000_000

    def test_from_parsed_funds_for_101_00000000000000(self):
        pf = ParsedFunds.parse("101.00000000000000")
        # 0, 4, 12 decimals reject (input has 14 decimals)
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(0))
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(4))
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(12))

        f16 = Funds.from_parsed_funds(pf, TokenDecimals.new(16))
        assert f16.amount == 1_010_000_000_000_000_000

    def test_from_parsed_funds_for_123123101_001(self):
        pf = ParsedFunds.parse("123123101.001")
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(0))

        f4 = Funds.from_parsed_funds(pf, TokenDecimals.new(4))
        assert f4.amount == 1_231_231_010_010

        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(12))
        with pytest.raises(InvalidFundsError):
            Funds.from_parsed_funds(pf, TokenDecimals.new(16))