"""Transaction builder for creating and signing Warthog transactions.

Obtained via :meth:`warthog_py.WarthogApi.create_transaction_context`.

All properties (``chain_pin``, ``fee``, ``nonce_id``) can be modified.
When reusing this context for multiple transactions, you MUST change
the ``nonce_id`` for each new transaction to prevent nonce collisions.
The ``chain_pin`` should typically remain unchanged unless you need to
refresh it from the network.
"""

import hashlib
import struct
from dataclasses import dataclass, replace
from typing import Any, Dict

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.funds import Funds
from warthog_py.liquidity import Liquidity
from warthog_py.nonce_id import NonceId
from warthog_py.price import Price
from warthog_py.rounded_fee import RoundedFee
from warthog_py.token_decimals import TokenDecimals
from warthog_py.wart import Wart


@dataclass(frozen=True)
class ChainPin:
    """A chain pin: hash + height of the most recently pinned block."""

    pin_hash: str
    pin_height: int


TransactionJson = Dict[str, Any]


@dataclass
class TransactionContext:
    """Mutable transaction context."""

    chain_pin: ChainPin
    fee: RoundedFee
    nonce_id: NonceId

    def with_nonce(self, nonce_id: NonceId) -> "TransactionContext":
        """Return a copy with the nonce replaced."""
        return replace(self, nonce_id=nonce_id)

    def with_fee(self, fee: RoundedFee) -> "TransactionContext":
        """Return a copy with the fee replaced."""
        return replace(self, fee=fee)

    def transfer_wart(self, account: Account, to_addr: Address, wart: Wart) -> TransactionJson:
        """Build and sign a native WART transfer transaction."""
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + _address_bytes(to_addr.hex)
            + _u64be(wart.e8)
        )
        return {
            "type": "wartTransfer",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "toAddr": to_addr.hex,
            "wartE8": wart.e8,
            "signature65": _sign(account, binary),
        }

    def transfer_asset(
        self,
        account: Account,
        asset_hash: str,
        to_addr: Address,
        amount: Funds,
    ) -> TransactionJson:
        """Build and sign an asset transfer transaction."""
        return self._token_transfer_internal(account, asset_hash, False, to_addr, amount.amount)

    def transfer_liquidity(
        self,
        account: Account,
        asset_hash: str,
        to_addr: Address,
        units: Liquidity,
    ) -> TransactionJson:
        """Build and sign a liquidity pool token transfer transaction."""
        return self._token_transfer_internal(account, asset_hash, True, to_addr, units.e8)

    def _token_transfer_internal(
        self,
        account: Account,
        asset_hash: str,
        is_liquidity: bool,
        to_addr: Address,
        amount_e8: int,
    ) -> TransactionJson:
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + (b"\x01" if is_liquidity else b"\x00")
            + _address_bytes(to_addr.hex)
            + _u64be(amount_e8)
        )
        return {
            "type": "tokenTransfer",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "isLiquidity": is_liquidity,
            "toAddr": to_addr.hex,
            "amountU64": amount_e8,
            "signature65": _sign(account, binary),
        }

    def buy(
        self,
        account: Account,
        asset_hash: str,
        wart_amount: Wart,
        limit: Price,
    ) -> TransactionJson:
        """Build and sign a limit buy transaction (spend WART to buy tokens)."""
        return self._limit_swap_internal(account, asset_hash, True, wart_amount.e8, limit)

    def sell(
        self,
        account: Account,
        asset_hash: str,
        token_amount: Funds,
        limit: Price,
    ) -> TransactionJson:
        """Build and sign a limit sell transaction (sell tokens for WART)."""
        return self._limit_swap_internal(account, asset_hash, False, token_amount.amount, limit)

    def _limit_swap_internal(
        self,
        account: Account,
        asset_hash: str,
        is_buy: bool,
        amount_e8: int,
        limit: Price,
    ) -> TransactionJson:
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + (b"\x01" if is_buy else b"\x00")
            + _u64be(amount_e8)
            + bytes.fromhex(limit.to_hex())
        )
        return {
            "type": "limitSwap",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "isBuy": is_buy,
            "amountU64": amount_e8,
            "limit": limit.to_hex(),
            "signature65": _sign(account, binary),
        }

    def deposit_liquidity(
        self,
        account: Account,
        asset_hash: str,
        token_amount: Funds,
        wart: Wart,
    ) -> TransactionJson:
        """Build and sign a liquidity deposit transaction."""
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + _u64be(token_amount.amount)
            + _u64be(wart.e8)
        )
        return {
            "type": "liquidityDeposit",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "amountU64": token_amount.amount,
            "wartE8": wart.e8,
            "signature65": _sign(account, binary),
        }

    def withdraw_liquidity(
        self,
        account: Account,
        asset_hash: str,
        units: Liquidity,
    ) -> TransactionJson:
        """Build and sign a liquidity withdrawal transaction."""
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + _u64be(units.e8)
        )
        return {
            "type": "liquidityWithdrawal",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "amountE8": units.e8,
            "signature65": _sign(account, binary),
        }

    def cancel_transaction(
        self,
        account: Account,
        cancel_height: int,
        cancel_nonce_id: NonceId,
    ) -> TransactionJson:
        """Build and sign a cancelation transaction."""
        if not isinstance(cancel_height, int) or cancel_height < 0:
            raise ValueError(
                f"cancel_height must be a non-negative integer, got: {cancel_height}"
            )

        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + struct.pack(">II", cancel_height, cancel_nonce_id.value)
        )
        return {
            "type": "cancelation",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "cancelHeight": cancel_height,
            "cancelNonceId": cancel_nonce_id.value,
            "signature65": _sign(account, binary),
        }

    def create_assets(
        self,
        account: Account,
        total_supply: Funds,
        decimals: TokenDecimals,
        name: str,
    ) -> TransactionJson:
        """Build and sign an asset creation transaction.

        The ``name`` is truncated or padded to 5 ASCII bytes.
        """
        if not isinstance(name, str):
            raise ValueError(f"name must be a string, got: {type(name).__name__}")

        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + _prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + _u64be(self.fee.e8)
            + _u64be(total_supply.amount)
            + bytes([decimals.decimals])
            + _name_pad5(name)
        )
        return {
            "type": "assetCreation",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "supplyU64": total_supply.amount,
            "decimals": decimals.decimals,
            "name": name,
            "signature65": _sign(account, binary),
        }


def _sign(account: Account, binary: bytes) -> str:
    """SHA-256 the binary payload and sign with the account."""
    digest = hashlib.sha256(binary).digest()
    _, _, _, signature_hex = account.sign(digest)
    return signature_hex


def _prefix(pin_height: int, nonce_id: int) -> bytes:
    """Common prefix: ``pinHeight(4) || nonceId(4) || reserved(3)``.

    The 3 reserved bytes sit between the two u32 fields and don't pack
    nicely into ``struct.pack`` alone, so we emit them explicitly.
    """
    return struct.pack(">II", pin_height, nonce_id) + b"\x00\x00\x00"


def _u64be(value: int) -> bytes:
    """Big-endian unsigned 64-bit encoding of ``value``."""
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"u64be value must be a non-negative integer, got: {value}")
    return struct.pack(">Q", value)


def _address_bytes(address: str) -> bytes:
    """Extract the 20-byte payload (first 40 hex chars) from a 48-char address."""
    return bytes.fromhex(address[:40])


def _name_pad5(name: str) -> bytes:
    """Truncate or zero-pad a name to exactly 5 bytes."""
    encoded = name.encode("ascii", errors="replace")[:5]
    return encoded.ljust(5, b"\x00")