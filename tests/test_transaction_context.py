import pytest

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.funds import Funds
from warthog_py.liquidity import Liquidity
from warthog_py.nonce_id import NonceId
from warthog_py.price import Price
from warthog_py.rounded_fee import RoundedFee
from warthog_py.token_decimals import TokenDecimals
from warthog_py.transaction_context import ChainPin, TransactionContext
from warthog_py.wart import Wart


PRIVATE_KEY_HEX = "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"
RECIPIENT_HEX = "0000000000000000000000000000000000000000de47c9b2"
ASSET_HASH = "f45b113119c7f7c000234f1090d5d181ab60b8b24526f1edd2f563aa1ca329f2"


def make_context():
    account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
    recipient = Address.from_hex(RECIPIENT_HEX)
    chain_pin = ChainPin(pin_hash="0" * 64, pin_height=32)
    fee = RoundedFee.min()
    nonce_id = NonceId.from_number(0)
    ctx = TransactionContext(chain_pin=chain_pin, fee=fee, nonce_id=nonce_id)
    return ctx, account, recipient


class TestTransactionContext:
    def test_transfer_wart(self):
        ctx, account, recipient = make_context()
        wart = Wart.from_e8(100_000_000)
        tx = ctx.transfer_wart(account, recipient, wart)
        assert tx["type"] == "wartTransfer"
        assert tx["pinHeight"] == 32
        assert tx["nonceId"] == 0
        assert tx["feeE8"] == 1
        assert tx["toAddr"] == RECIPIENT_HEX
        assert tx["wartE8"] == 100_000_000
        assert len(bytes.fromhex(tx["signature65"])) == 65

    def test_transfer_asset(self):
        ctx, account, recipient = make_context()
        amount = Funds.parse("1000", TokenDecimals.wart())
        tx = ctx.transfer_asset(account, ASSET_HASH, recipient, amount)
        assert tx["type"] == "tokenTransfer"
        assert tx["isLiquidity"] is False
        assert tx["amountU64"] == 100_000_000_000

    def test_transfer_liquidity(self):
        ctx, account, recipient = make_context()
        units = Liquidity.from_e8(100)
        tx = ctx.transfer_liquidity(account, ASSET_HASH, recipient, units)
        assert tx["type"] == "tokenTransfer"
        assert tx["isLiquidity"] is True
        assert tx["amountU64"] == 100

    def test_buy(self):
        ctx, account, _ = make_context()
        wart = Wart.from_e8(100_000_000)
        price = Price.from_number_decimals(1.0, TokenDecimals.new(4), False)
        tx = ctx.buy(account, ASSET_HASH, wart, price)
        assert tx["type"] == "limitSwap"
        assert tx["isBuy"] is True
        assert len(tx["limit"]) == 6

    def test_sell(self):
        ctx, account, _ = make_context()
        amount = Funds.parse("1000", TokenDecimals.new(4))
        price = Price.from_number_decimals(1.0, TokenDecimals.new(4), False)
        tx = ctx.sell(account, ASSET_HASH, amount, price)
        assert tx["type"] == "limitSwap"
        assert tx["isBuy"] is False
        assert tx["amountU64"] == amount.amount

    def test_deposit_liquidity(self):
        ctx, account, _ = make_context()
        token_amount = Funds.parse("1000", TokenDecimals.new(4))
        wart = Wart.from_e8(100_000_000)
        tx = ctx.deposit_liquidity(account, ASSET_HASH, token_amount, wart)
        assert tx["type"] == "liquidityDeposit"
        assert tx["amountU64"] == token_amount.amount

    def test_withdraw_liquidity(self):
        ctx, account, _ = make_context()
        units = Liquidity.from_e8(100)
        tx = ctx.withdraw_liquidity(account, ASSET_HASH, units)
        assert tx["type"] == "liquidityWithdrawal"
        assert tx["amountE8"] == 100

    def test_cancel_transaction(self):
        ctx, account, _ = make_context()
        cancel_nonce_id = NonceId.from_number(1)
        tx = ctx.cancel_transaction(account, 0, cancel_nonce_id)
        assert tx["type"] == "cancelation"
        assert tx["cancelHeight"] == 0
        assert tx["cancelNonceId"] == 1

    def test_create_assets(self):
        ctx, account, _ = make_context()
        dec = TokenDecimals.new(5)
        supply = Funds.parse("10000", dec)
        tx = ctx.create_assets(account, supply, dec, "TOK2")
        assert tx["type"] == "assetCreation"
        assert tx["decimals"] == 5
        assert tx["name"] == "TOK2"

    def test_all_signatures_are_65_bytes(self):
        ctx, account, recipient = make_context()
        wart = Wart.from_e8(100_000_000)
        amount = Funds.parse("1000", TokenDecimals.wart())
        units = Liquidity.from_e8(100)
        price = Price.from_number_decimals(1.0, TokenDecimals.new(4), False)
        token_amount = Funds.parse("1000", TokenDecimals.new(4))
        dec = TokenDecimals.new(5)
        supply = Funds.parse("10000", dec)
        cancel_nonce_id = NonceId.from_number(1)

        txs = [
            ctx.transfer_wart(account, recipient, wart),
            ctx.transfer_asset(account, ASSET_HASH, recipient, amount),
            ctx.transfer_liquidity(account, ASSET_HASH, recipient, units),
            ctx.buy(account, ASSET_HASH, wart, price),
            ctx.sell(account, ASSET_HASH, token_amount, price),
            ctx.deposit_liquidity(account, ASSET_HASH, token_amount, wart),
            ctx.withdraw_liquidity(account, ASSET_HASH, units),
            ctx.cancel_transaction(account, 0, cancel_nonce_id),
            ctx.create_assets(account, supply, dec, "TOK2"),
        ]

        for tx in txs:
            sig_bytes = bytes.fromhex(tx["signature65"])
            assert len(sig_bytes) == 65