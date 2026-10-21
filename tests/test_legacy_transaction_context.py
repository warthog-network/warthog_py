from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.chain_pin import ChainPin
from warthog_py.legacy_transaction_context import WarthogLegacyTransactionContext
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.wart import Wart

PRIVATE_KEY_HEX = "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"
RECIPIENT_HEX = "0000000000000000000000000000000000000000de47c9b2"


def make_context():
    account = Account.from_private_key_hex(PRIVATE_KEY_HEX)
    recipient = Address.from_hex(RECIPIENT_HEX)
    chain_pin = ChainPin(pin_hash="0" * 64, pin_height=32)
    fee = RoundedFee.min()
    nonce_id = NonceId.from_number(0)
    ctx = WarthogLegacyTransactionContext(
        chain_pin=chain_pin, fee=fee, nonce_id=nonce_id
    )
    return ctx, account, recipient


class TestLegacyTransactionContext:
    def test_transfer_wart(self):
        ctx, account, recipient = make_context()
        wart = Wart.from_e8(100_000_000)
        tx = ctx.transfer_wart(account, recipient, wart)
        assert tx["pinHeight"] == 32
        assert tx["nonceId"] == 0
        assert tx["feeE8"] == 1
        assert tx["toAddr"] == RECIPIENT_HEX
        assert tx["amountE8"] == 100_000_000
        assert len(bytes.fromhex(tx["signature65"])) == 65

    def test_the_payload_carries_no_type(self):
        # The legacy node has a single transaction endpoint that parses one
        # message shape, a transfer, so it never looks at a type.
        ctx, account, recipient = make_context()
        wart = Wart.from_e8(100_000_000)
        tx = ctx.transfer_wart(account, recipient, wart)
        assert "type" not in tx
        assert "wartE8" not in tx

    def test_the_legacy_context_has_no_defi_only_builders(self):
        # The two node families are separate APIs, so a legacy context cannot
        # build a limit swap: the method does not exist on it.
        assert not hasattr(WarthogLegacyTransactionContext, "transfer_asset")
        assert not hasattr(WarthogLegacyTransactionContext, "buy")
        assert not hasattr(WarthogLegacyTransactionContext, "deposit_liquidity")

    def test_with_nonce_returns_a_copy(self):
        ctx, _, _ = make_context()
        updated = ctx.with_nonce(NonceId.from_number(1))
        assert updated.nonce_id.value == 1
        assert ctx.nonce_id.value == 0
