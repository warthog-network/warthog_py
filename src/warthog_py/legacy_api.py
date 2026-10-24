"""Client for the legacy node (core/master, core/dev).

That node speaks the V1 API generation: the chain head comes back flat, and
it accepts one kind of transaction, a transfer.

    WarthogLegacyApi()                              # public main net
    WarthogLegacyApi("http://127.0.0.1:3100")       # local core/master node
"""

from dataclasses import dataclass
from typing import ClassVar

from warthog_py.chain_head import ChainHead
from warthog_py.constants import ApiVersion
from warthog_py.legacy_transaction_context import WarthogLegacyTransactionContext
from warthog_py.nonce_id import NonceId
from warthog_py.node_version import NodeVersion
from warthog_py.rounded_fee import RoundedFee
from warthog_py.wart import Wart
from warthog_py.warthog_api import KNOWN_NODES_LEGACY, WarthogApiBase, WarthogApiError


@dataclass
class WarthogLegacyApi(WarthogApiBase):
    """Client for the legacy node (core/master, core/dev).

    The first entry of ``known_nodes_legacy()`` is a public **main net** node
    (port 3001), which serves the V1 API.
    """

    base_url: str = KNOWN_NODES_LEGACY[0]
    version: ClassVar[ApiVersion] = "v1"

    def create_transaction_context(
        self, fee: RoundedFee, nonce_id: NonceId
    ) -> WarthogLegacyTransactionContext:
        """Fetch the chain head and build a ``WarthogLegacyTransactionContext``.

        Raises ``WarthogApiError`` or ``InvalidChainHeadError`` on failure.
        """
        head = self.get_chain_head()
        return WarthogLegacyTransactionContext(chain_pin=head.pin, fee=fee, nonce_id=nonce_id)

    def get_wart_balance(self, address: str) -> Wart:
        """Get the WART balance of an account.

        The legacy node reports one number: the confirmed balance. It has no
        limit orders, and it does not report what pending transactions lock,
        so there is no split to make.

        Raises ``WarthogApiError`` on failure.
        """
        result = self._request("GET", f"/account/{address}/balance")
        if not result.get("success"):
            raise WarthogApiError(result)

        balance = result["data"].get("balance") if isinstance(result["data"], dict) else None
        if not isinstance(balance, str):
            raise WarthogApiError({"code": -1, "error": "Invalid balance response"})

        return Wart.parse(balance)

    def get_node_version(self) -> NodeVersion:
        """Get the version of the node.

        The legacy node serves it on ``/tools/version``.

        Raises ``WarthogApiError`` or ``InvalidNodeVersionError`` on failure.
        """
        return self._fetch_node_version("/tools/version")
