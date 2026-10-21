import pytest

from warthog_py.balance import DeFiWartBalance, TokenBalance
from warthog_py.errors import InvalidBalanceError


class TestDeFiWartBalance:
    def test_parses_the_three_amounts_a_node_reports(self):
        data = {
            "wart": {
                "total": {"str": "10.00000000", "E8": 1_000_000_000},
                "locked": {"str": "2.00000000", "E8": 200_000_000},
                "mempool": {"str": "1.00000000", "E8": 100_000_000},
            }
        }
        balance = DeFiWartBalance.parse(data)
        assert balance.total.e8 == 1_000_000_000
        assert balance.locked.e8 == 200_000_000
        assert balance.mempool.e8 == 100_000_000

    def test_free_is_the_total_minus_the_two_locked_parts(self):
        data = {
            "wart": {
                "total": {"str": "10.00000000"},
                "locked": {"str": "2.00000000"},
                "mempool": {"str": "1.00000000"},
            }
        }
        assert DeFiWartBalance.parse(data).free().e8 == 700_000_000

    def test_a_balance_that_does_not_add_up_is_rejected(self):
        data = {
            "wart": {
                "total": {"str": "1.00000000"},
                "locked": {"str": "2.00000000"},
                "mempool": {"str": "0.00000000"},
            }
        }
        with pytest.raises(InvalidBalanceError):
            DeFiWartBalance.parse(data)
        assert DeFiWartBalance.try_parse(data) is None

    def test_a_malformed_payload_is_rejected(self):
        with pytest.raises(InvalidBalanceError):
            DeFiWartBalance.parse({})
        with pytest.raises(InvalidBalanceError):
            DeFiWartBalance.parse({"wart": {"total": {"str": "1.0"}}})
        assert DeFiWartBalance.try_parse({}) is None


class TestTokenBalance:
    def test_parses_the_token_and_the_three_amounts(self):
        data = {
            "token": {"name": "TOK2", "decimals": 4},
            "balance": {
                "total": {"str": "1000.0000", "u64": 10_000_000, "decimals": 4},
                "locked": {"str": "100.0000", "u64": 1_000_000, "decimals": 4},
                "mempool": {"str": "0.0000", "u64": 0, "decimals": 4},
            },
        }
        balance = TokenBalance.parse(data)
        assert balance.name == "TOK2"
        assert balance.decimals.decimals == 4
        assert balance.total.amount == 10_000_000
        assert balance.locked.amount == 1_000_000
        assert balance.mempool.amount == 0

    def test_free_is_the_total_minus_the_two_locked_parts(self):
        data = {
            "token": {"name": "TOK2", "decimals": 4},
            "balance": {
                "total": {"str": "1000.0000", "decimals": 4},
                "locked": {"str": "100.0000", "decimals": 4},
                "mempool": {"str": "50.0000", "decimals": 4},
            },
        }
        assert TokenBalance.parse(data).free().amount == 8_500_000

    def test_a_balance_that_does_not_add_up_is_rejected(self):
        data = {
            "token": {"name": "TOK2", "decimals": 4},
            "balance": {
                "total": {"str": "1.0000", "decimals": 4},
                "locked": {"str": "2.0000", "decimals": 4},
                "mempool": {"str": "0.0000", "decimals": 4},
            },
        }
        with pytest.raises(InvalidBalanceError):
            TokenBalance.parse(data)

    def test_a_malformed_payload_is_rejected(self):
        with pytest.raises(InvalidBalanceError):
            TokenBalance.parse({})
        with pytest.raises(InvalidBalanceError):
            TokenBalance.parse({"token": {"name": "TOK2"}})
        assert TokenBalance.try_parse({}) is None
