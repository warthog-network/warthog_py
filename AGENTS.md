# AGENTS.md - Warthog Python Library

## Overview

Warthog is a cryptocurrency. This library provides type-safe primitives for
building and submitting transactions on the Warthog network. It is the
Python port of [`warthog-ts`](https://github.com/warthog-network/warthog-ts) and shares the same wire
format as [`warthog_ex`](https://github.com/warthog-network/warthog_ex).

## Important Constants

- **`MAX_U64`** = `0xffffffffffffffff` (18,446,744,073,709,551,615) — maximum 64-bit unsigned integer. Exposed via `warthog_py.constants.MAX_U64`.
- **`MAX_U32`** = `0xFFFFFFFF` (4,294,967,295) — maximum 32-bit unsigned integer. Exposed via `warthog_py.constants.MAX_U32`.
- **WART decimals** = 8 decimal places (`1 WART = 100_000_000 E8`).

## Error-handling convention

Following standard Python practice, every factory function ships in two
flavors:

- **`name(...)`** — raises a custom exception (e.g. `InvalidAddressError`, `InvalidNonceError`) on invalid input.
- **`try_name(...)`** — returns `None` on invalid input instead of raising.

Predicates that return booleans (`Address.validate`, `NonceId.validate`)
stay as-is. All custom exceptions inherit from
`warthog_py.errors.WarthogPyError`.

Python's `int` is arbitrary precision, so there is no equivalent of
TypeScript's `bigint` — large values are handled natively.

## Built-in Python idioms

We use the standard library where it provides a clean primitive:

- `math.frexp` for Price's mantissa/exponent decomposition (Python handles zero, signed zero, NaN, ±inf correctly).
- `math.isfinite` to validate finite doubles in `Price.from_double_internal`.
- `struct.pack(">Q", n)` / `struct.pack(">II", a, b)` for fixed-width big-endian serialization in `TransactionContext`.
- `hashlib.sha256()` / `pycryptodome.RIPEMD160.new()` for hashing.
- `secrets.randbelow()` for NonceId.random.
- `dataclasses.dataclass(frozen=True)` for immutable value types.
- `requests` for HTTP.

### Things we deliberately don't hand-roll

- **Overflow check**: in `Funds.from_parsed_funds` we compute the final multiplier once (`10 ** zeros`) and check `parsed.val > MAX_U64 // multiplier`. The loop-and-multiply version (in the warthog-ts reference) was replaced because Python's arbitrary-precision `int` makes the single-multiplication version both clearer and faster.
- **Bitwise helpers**: `Price.to_hex` uses `f"{:04x}"` / `f"{:02x}"` instead of `int.to_bytes` + manual hex encoding.
- **`int.bit_count`**, **`math.gcd`**, etc.: not currently needed, but used where applicable per Python idioms.
- **Custom exception hierarchy**: all warthog_py errors inherit from `WarthogPyError`, so callers can catch a single base class if they want to.

## Core Types

### Address
**File:** `src/warthog_py/address.py`

Warthog uses 20-byte addresses with a 4-byte SHA-256 checksum, encoded as
a 48-character hex string.

```python
from warthog_py import Address

addr = Address.from_hex("0000000000000000000000000000000000000000de47c9b2")
addr = Address.try_from_hex("0000000000000000000000000000000000000000de47c9b2")
addr = Address.from_raw("0000000000000000000000000000000000000000")
addr = Address.try_from_raw("0000000000000000000000000000000000000000")
Address.validate("0000000000000000000000000000000000000000de47c9b2")  # True
```

### NonceId
**File:** `src/warthog_py/nonce_id.py`

Every transaction needs a unique nonce (32-bit unsigned integer: 0 to
4,294,967,295).

```python
from warthog_py import NonceId

nonce = NonceId.from_number(12345)
nonce = NonceId.try_from_number(12345)
nonce = NonceId.random()
NonceId.validate(12345)  # True
```

### TokenDecimals
**File:** `src/warthog_py/token_decimals.py`

Represents the number of decimal places for a token (0–18).

```python
from warthog_py import TokenDecimals

td = TokenDecimals.wart()         # 8 decimals
td = TokenDecimals.liquidity()    # 8 decimals
td = TokenDecimals.new(4)         # raises InvalidDecimalsError on out-of-range
```

### ParsedFunds
**File:** `src/warthog_py/parsed_funds.py`

Parses a decimal string into an integer plus a decimal-place count.

```python
from warthog_py import ParsedFunds

parsed = ParsedFunds.parse("123.45")
# parsed.val            # 12345
# parsed.decimal_places # 2
```

### Funds
**File:** `src/warthog_py/funds.py`

Represents a token amount with a specific number of decimal places.

```python
from warthog_py import Funds, TokenDecimals

f = Funds.parse("1.123", TokenDecimals.new(4))
# f.amount # 11230
```

### Wart
**File:** `src/warthog_py/wart.py`

Warthog's native token (8 decimal places).

```python
from warthog_py import Wart

w = Wart.parse("1.5")
w = Wart.try_parse("1.5")
w = Wart.from_e8(150_000_000)
w = Wart.try_from_e8(150_000_000)

# Convert to a RoundedFee
fee = Wart.rounded_fee(w, ceil=False)
```

### Liquidity
**File:** `src/warthog_py/liquidity.py`

Liquidity pool tokens with 8 decimal places. Used for liquidity
deposit/withdrawal transactions.

```python
from warthog_py import Liquidity

l = Liquidity.parse("1.5")
l = Liquidity.from_e8(100)
l = Liquidity.try_from_e8(100)
```

### RoundedFee
**File:** `src/warthog_py/rounded_fee.py`

Transaction fees in rounded WART format (64-bit WART scale).

This is **not** the 16-bit compact representation. It is the result of
converting WART to a `CompactFee` and then back to the WART scale.
This is a lossy operation. Warthog nodes require rounded values on the
64-bit WART scale in API calls.

```python
from warthog_py import RoundedFee, Wart

fee = RoundedFee.min()  # 1 E8 = 0.00000001 WART
fee = RoundedFee.from_e8(1_000, ceil=False)
fee = RoundedFee.try_from_e8(1_000, ceil=False)

wart = RoundedFee.to_wart(fee)
```

### CompactFee
**File:** `src/warthog_py/compact_fee.py`

Warthog's internal 16-bit compact fee representation. Used for compact
storage and transmission within the protocol.

**Note:** This is *not* used in transaction submission API — use
`RoundedFee` instead.

```python
from warthog_py import CompactFee, Wart

cf = CompactFee.from_wart(Wart.parse("1.5"), ceil=False)
wart = CompactFee.to_wart(cf)
```

### Price
**File:** `src/warthog_py/price.py`

Represents a swap price in normalized mantissa/exponent format.

- **Mantissa**: 16 bits, must be in `[0x8000, 0xFFFF]` (high bit set).
- **Exponent**: 8 bits, stored with offset `+63` internally to map to `[0, 127]`.

```python
from warthog_py import Price, TokenDecimals

price = Price.max()

price = Price.from_mantissa_exponent(0x8000, 0)
price = Price.try_from_mantissa_exponent(0x8000, 0)

price = Price.from_hex("c0e74d")
price = Price.try_from_hex("c0e74d")

price = Price.from_number_decimals(1.5, TokenDecimals.wart(), ceil=False)
price = Price.try_from_number_decimals(1.5, TokenDecimals.wart(), ceil=False)

hex_str = Price.to_hex(price)
double = Price.to_double_raw(price)
adjusted = Price.to_double_adjusted(price, TokenDecimals.wart())
```

## Account & Wallets

### Account
**File:** `src/warthog_py/account.py`

Wallet account for signing transactions. Uses secp256k1 elliptic curve.
The address is derived as
`RIPEMD-160(SHA-256(compressed-public-key))` with a 4-byte SHA-256
checksum appended.

Signing follows the **BIP-62 / secp256k1 low-s** convention: the
signature is normalized so that `s ≤ n/2`, and the recovery id is
flipped to match when normalization occurs. This is the same convention
documented in `docs/developers/integration/wallets.md`.

```python
from warthog_py import Account

account = Account.from_random()
account = Account.from_private_key(b"\x00" * 32)  # raises on wrong size
account = Account.from_private_key_hex("966a71a98bb5d13e9116c0dffa3f1a7877e45c6f563897b96cfd5c59bf0803e0")
account = Account.try_from_private_key_hex("...")

# Public dataclass fields
account.private_key_hex
account.public_key_hex
account.address

# Sign arbitrary bytes (UTF-8 string or bytes); SHA-256 happens internally
r, s, recid, sig_hex = account.sign_bytes("hello world")
r, s, recid, sig_hex = account.sign_bytes(b"hello world")

# Recover the public key (33 bytes) that produced a signature.
# signature accepts the (r, s, recid, hex) tuple from sign_bytes,
# the (r, s, recid) tuple, or a 130-char hex string.
pubkey_bytes = Account.recover_public_key("hello world", sig_hex)
pubkey_bytes = Account.try_recover_public_key("hello world", sig_hex)  # None on failure

# Recover the Warthog address that produced a signature.
addr = Account.recover_address("hello world", sig_hex)
addr = Account.try_recover_address("hello world", sig_hex)  # None on failure
```

### HDWallet
**File:** `src/warthog_py/hd_wallet.py`

BIP-44 hierarchical deterministic wallet. Derivation path
`m/44'/2070'/0'/0/{index}` (Warthog coin type `2070`).

```python
from warthog_py import HDWallet

wallet = HDWallet.from_mnemonic("word1 word2 ...")

account = wallet.derive_account_at_index(0)
account = wallet.derive_account_from_path("0/0")
account = wallet.derive_account_from_path("m/0/0")  # leading m/ optional
```

## Transaction Building

### TransactionContext
**File:** `src/warthog_py/transaction_context.py`

Builds and signs transactions. Obtain via
`WarthogApi.create_transaction_context`. The context's `chain_pin`,
`fee`, and `nonce_id` are stored as dataclass fields. Use
`with_nonce(...)` / `with_fee(...)` to produce an updated copy.

```python
from warthog_py import TransactionContext

# WART transfer
tx = context.transfer_wart(account, recipient, wart)

# Asset transfer
tx = context.transfer_asset(account, asset_hash, recipient, funds)

# Liquidity transfer
tx = context.transfer_liquidity(account, asset_hash, recipient, units)

# Buy (spend WART to buy tokens)
tx = context.buy(account, asset_hash, wart_amount, limit)

# Sell (sell tokens for WART)
tx = context.sell(account, asset_hash, token_amount, limit)

# Deposit liquidity
tx = context.deposit_liquidity(account, asset_hash, token_amount, wart)

# Withdraw liquidity
tx = context.withdraw_liquidity(account, asset_hash, units)

# Cancel transaction
tx = context.cancel_transaction(account, cancel_height, cancel_nonce_id)

# Create assets
tx = context.create_assets(account, total_supply, decimals, name)

# Reuse the same context for multiple transactions (must change nonce!)
context2 = context.with_nonce(NonceId.from_number(1))
tx2 = context2.transfer_wart(account, recipient, wart)
```

All return a signed transaction dict (with a `signature65` field)
ready for `WarthogApi.submit_transaction`.

## API Communication

### WarthogApi
**File:** `src/warthog_py/warthog_api.py`

Client for communicating with Warthog nodes. Uses the `requests`
library internally.

```python
from warthog_py import WarthogApi, KNOWN_NODES

# The version declares which /chain/head generation the node speaks and is
# required. The first KNOWN_NODES entry is a public main net node (port 3001),
# which serves the V1 API.
api = WarthogApi("v1")
api = WarthogApi("v2", "http://127.0.0.1:3100")  # local core/defi node

ctx = api.create_transaction_context(fee, nonce)

result = api.submit_transaction(tx)
print(result["txHash"])

head = api.get_chain_head()  # ChainHead, normalized across both generations
head.pin.pin_hash, head.pin.pin_height
head.height
head.synced

WarthogApi.known_nodes()  # list of public node URLs (module static method)
```

Errors raise `warthog_py.warthog_api.WarthogApiError` (a subclass of
`WarthogPyError`) with `.code` and a human-readable message. A chain head that
does not match the declared version raises `warthog_py.errors.InvalidChainHeadError`.

### API generations: V1 vs V2

`/chain/head` returns the same C++ type on every branch, `Head { ChainHead
chainHead; bool synced; }`, but the serializer differs:

- **V1** (`core/master`, `core/dev`): a hand-written `to_json(API::Head&)`
  flattens ChainHead into the top level. `{ hash, height, pinHash, pinHeight, ..., synced }`
- **V2** (`core/defi`): glaze reflects the nesting. `{ chainHead: { hash, height, pinHash, pinHeight, ... }, synced }`

The client is told which one to expect rather than sniffing the payload.
`ChainPin.try_parse()` and `ChainHead.try_parse()` return `None` when the
payload does not match, and `get_chain_head()` raises `InvalidChainHeadError`.

`ChainPin` and `ChainHead` also parse standalone, without a client:

```python
from warthog_py import ChainHead, ChainPin, PIN_HEIGHT_MULTIPLE

head = ChainHead.parse(payload, "v2")
pin = ChainPin.try_parse(payload, "v1")
PIN_HEIGHT_MULTIPLE  # 32
```

## Common Patterns

### Full Transaction Flow

```python
from warthog_py import (
    Account,
    Address,
    RoundedFee,
    Wart,
    NonceId,
    WarthogApi,
)

# 1. Load your account
account = Account.from_private_key_hex("your-private-key-hex")

# 2. Prepare the recipient
recipient = Address.from_hex("0000000000000000000000000000000000000000de47c9b2")

# 3. Connect to the API
api = WarthogApi("v1")  # first KNOWN_NODES entry (a public main net node)

# 4. Create a transaction context (fetches chain pin automatically)
ctx = api.create_transaction_context(RoundedFee.min(), NonceId.random())

# 5. Build and sign a WART transfer
tx = ctx.transfer_wart(account, recipient, Wart.from_e8(100_000_000))

# 6. Submit
result = api.submit_transaction(tx)
print(result["txHash"])
```

## Differences from `warthog-ts`

- **Errors**: TypeScript `null` returns are replaced with `None` (via `try_*`) or a custom exception (e.g. `InvalidAddressError`).
- **Public fields**: `account.address` and `account.private_key_hex` are dataclass fields, not methods.
- **Arbitrary precision**: Python `int` is unbounded, so `bigint` in TS is just `int` here.
- **Bang convention** (Pythonic variant): every factory ships as both `name(...)` (raises) and `try_name(...)` (returns `None`).

## Breaking changes

### 0.2.0 — `/chain/head` V1 API handling

- `WarthogApi` now takes a **required** `version` as its first argument,
  `"v1"` or `"v2"`. `WarthogApi("http://host")` no longer means "URL"; it is
  an invalid version and raises `ValueError`. Use `WarthogApi(version, url)`.
  The reason for the ordering is that Python 3.9 is supported, so
  `dataclasses.field(kw_only=True)` is unavailable.
- `get_chain_head()` returns a `ChainHead` instead of the raw decoded dict.
  Use `head.pin.pin_hash`, `head.pin.pin_height`, `head.height`, `head.synced`.
- `ChainPin` moved from `warthog_py.transaction_context` to `warthog_py.chain_pin`.
  It is still importable as `from warthog_py import ChainPin`.
- The old `create_transaction_context` did `head["pinHash"]` after
  `head.get("chainHead") or {}`, which raised a bare `KeyError` against any
  V1 node. It now works against both generations.

## Testing

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. From the project root:

```bash
# Once: sync dependencies (uv creates .venv/ and installs everything)
uv sync

# Every time: run the tests
uv run pytest

# Or run a specific test file
uv run pytest tests/test_account.py -v
```

`uv sync` reads `pyproject.toml` and installs both runtime dependencies and the `[dependency-groups].dev` test dependencies (pytest). It manages `.venv/` automatically — no manual activation needed; `uv run` invokes Python in the right environment for you.

## Examples

```bash
python examples/transactions.py
```

## Dependencies

- `ecdsa` — secp256k1 key handling
- `mnemonic` — BIP-39 word list
- `bip32` — BIP-32 HD derivation
- `pycoin` — RFC6979 deterministic signing with recovery id (`secp256k1_generator.sign_with_recid`)
- `pycryptodome` — RIPEMD-160 (some Python builds lack OpenSSL RIPEMD-160)
- `requests` — HTTP client

## Quirks

- Python's standard library `hashlib.new("ripemd160")` requires OpenSSL to be built with RIPEMD-160 enabled (rarely the case on minimal Linux installs). We fallback to `pycryptodome`'s `RIPEMD160.new()` which is pure-Python and always available.
- Signing uses `pycoin.ecdsa.secp256k1.secp256k1_generator.sign_with_recid` for RFC6979 deterministic nonce and recovery id in one call. The signature is normalized to low-s form (matching BIP-62).
- `Account.sign_bytes` takes arbitrary bytes (`bytes`/`bytearray`/`str`); it hashes the message internally with SHA-256 (the same scheme transaction signing uses). The recovery methods accept the `(r, s, recid, hex)` tuple from `sign_bytes`, a 3-tuple `(r, s, recid)`, or a 130-char hex string.