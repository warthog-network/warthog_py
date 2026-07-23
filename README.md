# warthog_py

Python library for the [Warthog](https://warthog.network) cryptocurrency.

This is the Python port of [`warthog-ts`](https://github.com/warthog-network/warthog-ts) and provides type-safe primitives for building and submitting transactions on the Warthog network, including the full native DeFi transaction set:

- `wartTransfer`
- `tokenTransfer`
- `assetCreation`
- `limitSwap`
- `liquidityDeposit`
- `liquidityWithdrawal`
- `cancelation`

## Installation

The package is **not yet published to PyPI**. Install it directly from the GitHub repository using [uv](https://docs.astral.sh/uv/):

```bash
uv add "warthog_py @ git+https://github.com/warthog-network/warthog_py.git"
```

Or add it to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "warthog_py @ git+https://github.com/warthog-network/warthog_py.git",
]
```

### Requirements

- Python `>=3.9`
- Dependencies (`ecdsa`, `mnemonic`, `bip32`, `pycoin`, `pycryptodome`, `requests`) are installed automatically by `uv sync`.

## Quick start

```python
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

# 1. Load or generate your account
account = Account.from_private_key_hex("your-private-key-hex")

# 2. Prepare the recipient
recipient = Address.from_hex("0000000000000000000000000000000000000000de47c9b2")

# 3. Connect to a node (defaults to the first KNOWN_NODES entry;
#    pass an explicit URL for a local dev node, e.g. "http://127.0.0.1:3100")
api = WarthogApi()

# 4. Fetch chain head and build a transaction context
ctx = api.create_transaction_context(RoundedFee.min(), NonceId.random())

# 5. Build and sign a WART transfer
tx = ctx.transfer_wart(account, recipient, Wart.from_e8(100_000_000))

# 6. Submit
result = api.submit_transaction(tx)
print(result["txHash"])
```

## Modules

| Module | Purpose |
|---|---|
| `warthog_py.Address` | 20-byte SHA-256-checksummed addresses |
| `warthog_py.NonceId` | 32-bit transaction nonces |
| `warthog_py.TokenDecimals` | Number of decimal places for a token |
| `warthog_py.ParsedFunds` | Parsed decimal strings |
| `warthog_py.Funds` | Token amounts with decimals |
| `warthog_py.Wart` | Native WART token (8 decimals) |
| `warthog_py.Liquidity` | Liquidity pool tokens (8 decimals) |
| `warthog_py.RoundedFee` | Rounded transaction fees |
| `warthog_py.CompactFee` | 16-bit compact fee representation |
| `warthog_py.Price` | Normalized mantissa/exponent prices |
| `warthog_py.Account` | secp256k1 wallet account |
| `warthog_py.HDWallet` | BIP-44 hierarchical deterministic wallet |
| `warthog_py.TransactionContext` | Transaction builder (all 7 types) |
| `warthog_py.WarthogApi` | HTTP client for Warthog nodes |

## Error handling convention

Following standard Python practice, every factory ships in two flavors:

- **`name(...)`** — raises a custom `*Error` on invalid input (`InvalidAddressError`, `InvalidNonceError`, etc.).
- **`try_name(...)`** — returns `None` on invalid input instead of raising.

```python
Address.from_hex("0000000000000000000000000000000000000000de47c9b2")  # raises on invalid
Address.try_from_hex("0000000000000000000000000000000000000000de47c9b2")  # None on invalid
Address.validate("0000000000000000000000000000000000000000de47c9b2")  # bool
```

The custom exception hierarchy lives in `warthog_py.errors`. All exceptions inherit from `WarthogPyError`.

## Testing

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. From the project root:

```bash
# Once: sync dependencies (creates .venv automatically and installs everything)
uv sync

# Every time: run the tests
uv run pytest

```

## Examples

```bash
python examples/transactions.py
```

## Development

To bump the version in `pyproject.toml` (using `uv`'s built-in version command):

```bash
uv version --bump patch    # 0.1.0 -> 0.1.1
uv version --bump minor    # 0.1.0 -> 0.2.0
uv version --bump major    # 0.1.0 -> 1.0.0
```

Use `--no-sync` to skip the venv rebuild:

```bash
uv version --bump patch --no-sync
```

## License

Released under the MIT License.
