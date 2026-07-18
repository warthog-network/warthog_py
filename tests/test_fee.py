from warthog_py.compact_fee import CompactFee
from warthog_py.rounded_fee import RoundedFee
from warthog_py.wart import Wart


class TestCompactFee:
    def test_zero_amount(self):
        w = Wart.from_e8(0)
        assert CompactFee.from_wart(w, False) == CompactFee(0, 0)
        assert CompactFee.from_wart(w, False).to_wart().e8 == 1

    def test_one_amount(self):
        w1 = Wart.from_e8(1)
        fee = w1.rounded_fee(False)
        assert fee.e8 == 1


class TestRoundedFee:
    def test_min(self):
        assert RoundedFee.min().e8 == 1

    def test_round_trip(self):
        fee = RoundedFee.from_e8(123_456_789, False)
        assert fee.e8 == fee.to_wart().e8

    def test_rounding_idempotent(self):
        for s in [".00003112", ".00013112", ".00113112", ".0111283", ".32", "5.12354", "10.02031022"]:
            original = Wart.parse(s)

            down = original.rounded_fee(False)
            assert down.e8 <= original.e8
            assert down.e8 == down.to_wart().rounded_fee(False).e8

            up = original.rounded_fee(True)
            assert up.e8 >= original.e8
            assert up.e8 == up.to_wart().rounded_fee(True).e8