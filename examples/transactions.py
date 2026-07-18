"""End-to-end example demonstrating all seven Warthog transaction types.

Run with:
    python examples/transactions.py
"""

import sys

sys.path.insert(0, "src")

from warthog_py import (
    Account,
    Address,
    Funds,
    Liquidity,
    NonceId,
    Price,
    RoundedFee,
    TokenDecimals,
    TransactionContext,
    Wart,
    WarthogApi,
)


def main() -> None:
    # Defaults to the first KNOWN_NODES entry (public testnet).
    # Pass an explicit URL for a local dev node, e.g. "http://127.0.0.1:3100".
    api = WarthogApi()

    account = Account.from_random()
    print("Private Key:", account.private_key_hex)
    print("Public Key: ", account.public_key_hex)
    print("Address:    ", account.address.hex)
    print()

    existing = Account.from_private_key_hex(
        "966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0"
    )
    print("Loaded address:", existing.address.hex)
    print()

    # Fetch chain head and build a shared transaction context
    try:
        ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
    except Exception as exc:
        print(f"Skipping live submission: cannot reach node ({exc!r})")
        print("All transaction-builder tests below still run with a dummy context.")
        ctx = TransactionContext(
            chain_pin={"pin_hash": "0" * 64, "pin_height": 1},
            fee=RoundedFee.min(),
            nonce_id=NonceId.from_number(0),
        )

    recipient = Address.from_hex("0000000000000000000000000000000000000000de47c9b2")
    asset = "f45b113119c7f7c000234f1090d5d181ab60b8b24526f1edd2f563aa1ca329f2"
    dec4 = TokenDecimals.new(4)
    price = Price.from_number_decimals(1.0, dec4, False)
    dec5 = TokenDecimals.new(5)
    wart = Wart.from_e8(100_000_000)

    def submit(nonce: int, tx: dict) -> None:
        ctx_ = ctx.with_nonce(NonceId.from_number(nonce))
        # `tx` was built with the original `ctx`; rebuild with the right nonce:
        builder = tx["type"]
        rebuild = {
            "wartTransfer": lambda c: c.transfer_wart(existing, recipient, wart),
            "tokenTransfer": lambda c: (
                c.transfer_asset(existing, asset, recipient, Funds.parse("1000", TokenDecimals.wart()))
                if not tx["isLiquidity"]
                else c.transfer_liquidity(existing, asset, recipient, Liquidity.from_e8(100))
            ),
            "limitSwap": lambda c: (
                c.buy(existing, asset, wart, price) if tx["isBuy"]
                else c.sell(existing, asset, Funds.parse("1000", dec4), price)
            ),
            "liquidityDeposit": lambda c: c.deposit_liquidity(
                existing, asset, Funds.parse("1000", dec4), wart
            ),
            "liquidityWithdrawal": lambda c: c.withdraw_liquidity(
                existing, asset, Liquidity.from_e8(100)
            ),
            "cancelation": lambda c: c.cancel_transaction(
                existing, 0, NonceId.from_number(1)
            ),
            "assetCreation": lambda c: c.create_assets(
                existing, Funds.parse("10000", dec5), dec5, "TOK2"
            ),
        }
        signed = rebuild[builder](ctx_)
        try:
            result = api.submit_transaction(signed)
            print(f"{builder} submitted: {result.get('txHash', result)}")
        except Exception as exc:
            print(f"{builder} failed: {exc}")

    # Build all 7 transaction types to verify nothing is malformed,
    # then attempt to submit each (skips gracefully if node is offline).
    print("Building and submitting all 7 transaction types:\n")
    submit(1, {"type": "wartTransfer"})
    submit(2, {"type": "tokenTransfer", "isLiquidity": False})
    submit(3, {"type": "tokenTransfer", "isLiquidity": True})
    print("Price hex:", price.to_hex())
    submit(5, {"type": "limitSwap", "isBuy": True})
    submit(6, {"type": "limitSwap", "isBuy": False})
    submit(7, {"type": "liquidityDeposit"})
    submit(8, {"type": "liquidityWithdrawal"})
    submit(9, {"type": "cancelation"})
    submit(10, {"type": "assetCreation"})


if __name__ == "__main__":
    main()