"""Transaction builder for the legacy node (core/master, core/dev).

That node accepts one kind of transaction, a transfer, so this context
offers one builder. The legacy node reads the amount from ``amountE8``; the
DeFi node reads it from ``wartE8`` and never looks at ``amountE8``, where
that name means the liquidity share count instead.

Obtained via :meth:`warthog_py.legacy_api.WarthogLegacyApi.create_transaction_context`.

All properties (``chain_pin``, ``fee``, ``nonce_id``) can be modified.
When reusing this context for multiple transactions, you MUST change
the ``nonce_id`` for each new transaction to prevent nonce collisions.
The ``chain_pin`` should typically remain unchanged unless you need to
refresh it from the network.
"""

from dataclasses import dataclass, replace
from typing import Any, Dict

from warthog_py.account import Account
from warthog_py.address import Address
from warthog_py.chain_pin import ChainPin
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.transaction_bytes import sign, wart_transfer_bytes
from warthog_py.wart import Wart


@dataclass(frozen=True)
class WarthogLegacyTransactionContext:
    """Transaction context for the legacy node."""

    chain_pin: ChainPin
    fee: RoundedFee
    nonce_id: NonceId

    def with_nonce(self, nonce_id: NonceId) -> "WarthogLegacyTransactionContext":
        """Return a copy with the nonce replaced."""
        return replace(self, nonce_id=nonce_id)

    def with_fee(self, fee: RoundedFee) -> "WarthogLegacyTransactionContext":
        """Return a copy with the fee replaced."""
        return replace(self, fee=fee)

    def transfer_wart(self, account: Account, to_addr: Address, wart: Wart) -> Dict[str, Any]:
        """Build and sign a native WART transfer transaction.

        The payload carries no ``type``. The legacy node has a single
        transaction endpoint that parses one message shape, a transfer, so it
        never looks at a type.
        """
        binary = wart_transfer_bytes(
            self.chain_pin, self.fee, self.nonce_id, to_addr, wart
        )
        return {
            "pinHeight": self.chain_pin.pin_height,
            "nonceId": self.nonce_id.value,
            "feeE8": self.fee.e8,
            "toAddr": to_addr.hex,
            "amountE8": wart.e8,
            "signature65": sign(account, binary),
        }
