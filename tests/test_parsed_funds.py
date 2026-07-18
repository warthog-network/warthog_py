import pytest

from warthog_py.constants import MAX_U64
from warthog_py.errors import InvalidFundsError
from warthog_py.parsed_funds import ParsedFunds


class TestParsedFunds:
    def test_parse_1_123(self):
        pf = ParsedFunds.parse("1.123")
        assert pf.val == 1123
        assert pf.decimal_places == 3

    def test_parse_101_123000(self):
        pf = ParsedFunds.parse("101.123000")
        assert pf.val == 101_123_000
        assert pf.decimal_places == 6

    def test_parse_101_1230001111(self):
        pf = ParsedFunds.parse("101.1230001111")
        assert pf.val == 1_011_230_001_111
        assert pf.decimal_places == 10

    def test_parse_101_00000000000000(self):
        pf = ParsedFunds.parse("101.00000000000000")
        assert pf.val == 10_100_000_000_000_000
        assert pf.decimal_places == 14

    def test_parse_123123101_001(self):
        pf = ParsedFunds.parse("123123101.001")
        assert pf.val == 123_123_101_001
        assert pf.decimal_places == 3

    def test_parse_invalid_inputs(self):
        for s in ["", ".", "abc", "1.1.1"]:
            with pytest.raises(InvalidFundsError):
                ParsedFunds.parse(s)

        # 21 digits — exceeds MAX_DIGITS=20
        with pytest.raises(InvalidFundsError):
            ParsedFunds.parse("1" * 21)

        # 20 digits but value > MAX_U64
        with pytest.raises(InvalidFundsError):
            ParsedFunds.parse(str(MAX_U64 + 1))

    def test_try_parse(self):
        assert ParsedFunds.try_parse("123") is not None
        assert ParsedFunds.try_parse("") is None