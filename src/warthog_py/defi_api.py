"""Client for the DeFi node (core/defi).

That node speaks the V2 API generation: the chain head comes back nested
under ``chainHead``, and it accepts nine kinds of transaction.

    WarthogDeFiApi()                              # public DeFi node
    WarthogDeFiApi("http://127.0.0.1:3101")       # local core/defi node
"""

from dataclasses import dataclass
from typing import ClassVar

from warthog_py.balance import DeFiWartBalance, TokenBalance
from warthog_py.constants import ApiVersion
from warthog_py.defi_transaction_context import WarthogDeFiTransactionContext
from warthog_py.nonce_id import NonceId
from warthog_py.node_version import NodeVersion
from warthog_py.rounded_fee import RoundedFee
from warthog_py.warthog_api import KNOWN_NODES_DEFI, WarthogApiBase, WarthogApiError


@dataclass
class WarthogDeFiApi(WarthogApiBase):
    """Client for the DeFi node (core/defi).

    The first entry of ``known_nodes_defi()`` is a public DeFi node, which
    serves the V2 API.
    """

    base_url: str = KNOWN_NODES_DEFI[0]
    version: ClassVar[ApiVersion] = "v2"

    def create_transaction_context(
        self, fee: RoundedFee, nonce_id: NonceId
    ) -> WarthogDeFiTransactionContext:
        """Fetch the chain head and build a ``WarthogDeFiTransactionContext``.

        Raises ``WarthogApiError`` or ``InvalidChainHeadError`` on failure.
        """
        head = self.get_chain_head()
        return WarthogDeFiTransactionContext(chain_pin=head.pin, fee=fee, nonce_id=nonce_id)

    def get_wart_balance(self, address: str) -> DeFiWartBalance:
        """Get the WART balance of an account.

        The DeFi node reports the balance three ways: the total, what is
        locked in open limit orders, and what is locked by transactions in the
        mempool.

        Raises ``WarthogApiError`` on failure.
        """
        result = self._request("GET", f"/account/{address}/wart_balance")
        if not result.get("success"):
            raise WarthogApiError(result)

        return DeFiWartBalance.parse(result["data"])

    def get_token_balance(self, address: str, asset_hash: str) -> TokenBalance:
        """Get the balance of a token an account holds.

        Raises ``WarthogApiError`` on failure.
        """
        hash_ = asset_hash.lower()
        if hash_.startswith("0x"):
            hash_ = hash_[2:]

        result = self._request("GET", f"/account/{address}/balance/asset:{hash_}")
        if not result.get("success"):
            raise WarthogApiError(result)

        return TokenBalance.parse(result["data"])

    def get_node_version(self) -> NodeVersion:
        """Get the version of the node.

        The DeFi node serves it on ``/version``, not on ``/tools/version`` like
        the legacy node does. The payload is the same either way.

        Raises ``WarthogApiError`` or ``InvalidNodeVersionError`` on failure.
        """
        return self._fetch_node_version("/version")
