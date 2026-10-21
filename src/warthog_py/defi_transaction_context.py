"""Transaction builder for the DeFi node (core/defi).

That node accepts nine kinds of transaction, so this context has all nine
builders. Its WART transfer reads the amount from ``wartE8``, which is where
the DeFi node looks for it; ``amountE8`` means the liquidity share count on
that node.

Obtained via :meth:`warthog_py.defi_api.WarthogDeFiApi.create_transaction_context`.

All properties (``chain_pin``, ``fee``, ``nonce_id``) can be modified.
When reusing this context for multiple transactions, you MUST change
the ``nonce_id`` for each new transaction to prevent nonce collisions.
The ``chain_pin`` should typically remain unchanged unless you need to
refresh it from the network.
"""

import struct
from dataclasses import dataclass, replace
from typing import Any, Dict

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.chain_pin import ChainPin
from warthog_py.funds import Funds
from warthog_py.liquidity import Liquidity
from warthog_py.nonce_id import NonceId
from warthog_py.price import Price
from warthog_py.rounded_fee import RoundedFee
from warthog_py.token_decimals import TokenDecimals
from warthog_py.transaction_bytes import address_bytes, name_pad5, prefix, sign, u64be
from warthog_py.wart import Wart


@dataclass(frozen=True)
class WarthogDeFiTransactionContext:
    """Transaction context for the DeFi node."""

    chain_pin: ChainPin
    fee: RoundedFee
    nonce_id: NonceId

    def with_nonce(self, nonce_id: NonceId) -> "WarthogDeFiTransactionContext":
        """Return a copy with the nonce replaced."""
        return replace(self, nonce_id=nonce_id)

    def with_fee(self, fee: RoundedFee) -> "WarthogDeFiTransactionContext":
        """Return a copy with the fee replaced."""
        return replace(self, fee=fee)

    def transfer_wart(self, account: Account, to_addr: Address, wart: Wart) -> Dict[str, Any]:
        """Build and sign a native WART transfer transaction.

        The amount travels as ``wartE8``. On the DeFi node the name
        ``amountE8`` means the liquidity share count.
        """
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + address_bytes(to_addr.hex)
            + u64be(wart.e8)
        )
        return {
            "type": "wartTransfer",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "toAddr": to_addr.hex,
            "wartE8": wart.e8,
            "signature65": sign(account, binary),
        }

    def transfer_asset(
        self,
        account: Account,
        asset_hash: str,
        to_addr: Address,
        amount: Funds,
    ) -> Dict[str, Any]:
        """Build and sign an asset transfer transaction."""
        return self._token_transfer_internal(account, asset_hash, False, to_addr, amount.amount)

    def transfer_liquidity(
        self,
        account: Account,
        asset_hash: str,
        to_addr: Address,
        units: Liquidity,
    ) -> Dict[str, Any]:
        """Build and sign a liquidity pool token transfer transaction."""
        return self._token_transfer_internal(account, asset_hash, True, to_addr, units.e8)

    def _token_transfer_internal(
        self,
        account: Account,
        asset_hash: str,
        is_liquidity: bool,
        to_addr: Address,
        amount_e8: int,
    ) -> Dict[str, Any]:
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + (b"\x01" if is_liquidity else b"\x00")
            + address_bytes(to_addr.hex)
            + u64be(amount_e8)
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
            "signature65": sign(account, binary),
        }

    def buy(
        self,
        account: Account,
        asset_hash: str,
        wart_amount: Wart,
        limit: Price,
    ) -> Dict[str, Any]:
        """Build and sign a limit buy transaction (spend WART to buy tokens)."""
        return self._limit_swap_internal(account, asset_hash, True, wart_amount.e8, limit)

    def sell(
        self,
        account: Account,
        asset_hash: str,
        token_amount: Funds,
        limit: Price,
    ) -> Dict[str, Any]:
        """Build and sign a limit sell transaction (sell tokens for WART)."""
        return self._limit_swap_internal(account, asset_hash, False, token_amount.amount, limit)

    def _limit_swap_internal(
        self,
        account: Account,
        asset_hash: str,
        is_buy: bool,
        amount_e8: int,
        limit: Price,
    ) -> Dict[str, Any]:
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + (b"\x01" if is_buy else b"\x00")
            + u64be(amount_e8)
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
            "signature65": sign(account, binary),
        }

    def deposit_liquidity(
        self,
        account: Account,
        asset_hash: str,
        token_amount: Funds,
        wart: Wart,
    ) -> Dict[str, Any]:
        """Build and sign a liquidity deposit transaction.

        The amount is the token amount, which the DeFi node reads from
        ``amountU64``. The liquidity share count is what a withdrawal
        carries, in ``amountE8``.
        """
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + u64be(token_amount.amount)
            + u64be(wart.e8)
        )
        return {
            "type": "liquidityDeposit",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "amountU64": token_amount.amount,
            "wartE8": wart.e8,
            "signature65": sign(account, binary),
        }

    def withdraw_liquidity(
        self,
        account: Account,
        asset_hash: str,
        units: Liquidity,
    ) -> Dict[str, Any]:
        """Build and sign a liquidity withdrawal transaction.

        The amount is the liquidity share count, which the DeFi node reads
        from ``amountE8``.
        """
        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + bytes.fromhex(asset_hash)
            + u64be(units.e8)
        )
        return {
            "type": "liquidityWithdrawal",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "assetHash": asset_hash,
            "amountE8": units.e8,
            "signature65": sign(account, binary),
        }

    def cancel_transaction(
        self,
        account: Account,
        cancel_height: int,
        cancel_nonce_id: NonceId,
    ) -> Dict[str, Any]:
        """Build and sign a cancelation transaction."""
        if not isinstance(cancel_height, int) or cancel_height < 0:
            raise ValueError(
                f"cancel_height must be a non-negative integer, got: {cancel_height}"
            )

        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + struct.pack(">II", cancel_height, cancel_nonce_id.value)
        )
        return {
            "type": "cancelation",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "cancelHeight": cancel_height,
            "cancelNonceId": cancel_nonce_id.value,
            "signature65": sign(account, binary),
        }

    def create_assets(
        self,
        account: Account,
        total_supply: Funds,
        decimals: TokenDecimals,
        name: str,
    ) -> Dict[str, Any]:
        """Build and sign an asset creation transaction.

        The ``name`` is truncated or padded to 5 ASCII bytes.
        """
        if not isinstance(name, str):
            raise ValueError(f"name must be a string, got: {type(name).__name__}")

        binary = (
            bytes.fromhex(self.chain_pin.pin_hash)
            + prefix(self.chain_pin.pin_height, self.nonce_id.value)
            + u64be(self.fee.e8)
            + u64be(total_supply.amount)
            + bytes([decimals.decimals])
            + name_pad5(name)
        )
        return {
            "type": "assetCreation",
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "supplyU64": total_supply.amount,
            "decimals": decimals.decimals,
            "name": name,
            "signature65": sign(account, binary),
        }
