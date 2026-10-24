"""Shared HTTP plumbing for the node clients.

The two node families are separate APIs, so they get a client each:
:class:`warthog_py.legacy_api.WarthogLegacyApi` for the legacy node
(core/master, core/dev) and :class:`warthog_py.defi_api.WarthogDeFiApi` for
the DeFi node (core/defi). What they genuinely share lives here: the
request plumbing, the chain head fetch and the transaction submission.
"""

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Union

import requests

from warthog_py.chain_head import ChainHead
from warthog_py.constants import ApiVersion
from warthog_py.errors import WarthogPyError
from warthog_py.node_version import NodeVersion
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee

KNOWN_NODES_LEGACY: List[str] = [
    "http://65.87.7.86:3001",
    "http://185.209.228.16:3001",
    "http://89.117.150.162:3001",
    "http://62.72.44.89:3001",
    "http://217.182.64.43:3001",
    "https://node.wartscan.io",
    "http://dev.node-s.com:3001",
]
"""Known legacy nodes (core/master, core/dev). These serve the V1 API."""

KNOWN_NODES_DEFI: List[str] = [
    "http://65.87.7.86:3002/",
    "https://warthog-defitestnet.duckdns.org/",
    "http://104.251.219.14:3001/",
    "http://85.56.145.106:3001/",
    "http://64.44.90.170:3001/",
]
"""Known DeFi nodes (core/defi). These serve the V2 API."""


@dataclass
class WarthogApiBase:
    """Shared HTTP plumbing for the node clients.

    The subclasses are the clients: each one declares which ``/chain/head``
    generation it reads and which transaction set it builds.
    """

    base_url: str
    timeout: int = 30

    version: ClassVar[ApiVersion] = "v1"

    @staticmethod
    def known_nodes_legacy() -> List[str]:
        """Known legacy nodes (core/master, core/dev)."""
        return KNOWN_NODES_LEGACY

    @staticmethod
    def known_nodes_defi() -> List[str]:
        """Known DeFi nodes (core/defi)."""
        return KNOWN_NODES_DEFI

    def get_chain_head(self) -> ChainHead:
        """Fetch the chain head.

        Normalizes the V1 and V2 payload shapes into a single
        :class:`~warthog_py.chain_head.ChainHead`.

        Raises ``WarthogApiError`` on failure, or ``InvalidChainHeadError``
        when the payload does not match this client's generation.
        """
        result = self._request("GET", "/chain/head")
        if not result.get("success"):
            raise WarthogApiError(result)
        return ChainHead.parse(result["data"], self.version)

    def submit_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a signed transaction to the node.

        Returns the parsed ``data`` payload (e.g. ``{"txHash": "..."}``).

        The hash is checked rather than assumed, so a response that does not
        carry one is reported as an error instead of being passed off as a
        success.

        Raises ``WarthogApiError`` on failure.
        """
        result = self._request("POST", "/transaction/add", body=tx)
        if not result.get("success"):
            raise WarthogApiError(result)

        data = result["data"]
        if not isinstance(data, dict) or not isinstance(data.get("txHash"), str):
            raise WarthogApiError({"code": -1, "error": "Invalid transaction add response"})

        return data

    def _fetch_node_version(self, path: str) -> NodeVersion:
        """Fetch the node's version from whichever endpoint serves it.

        Every node family reports the same five fields in the same flat shape,
        so the parsing is shared. Only the path differs, and that is what the
        caller passes in.

        Raises ``WarthogApiError`` or ``InvalidNodeVersionError`` on failure.
        """
        result = self._request("GET", path)
        if not result.get("success"):
            raise WarthogApiError(result)

        return NodeVersion.parse(result["data"])

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Union[str, int]]] = None,
    ) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        if query:
            url += "?" + "&".join(f"{k}={v}" for k, v in query.items())

        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=self.timeout)
            elif method.upper() == "POST":
                response = requests.post(url, json=_encode_bigints(body or {}), timeout=self.timeout)
            else:
                raise ValueError(f"unsupported HTTP method: {method}")
        except requests.RequestException as e:
            return _error_result(repr(e))

        try:
            payload = response.json()
        except ValueError:
            return _error_result(f"non-JSON response (status {response.status_code}): {response.text!r}")

        if payload.get("code") == 0 and "data" in payload:
            return {"success": True, "data": payload["data"]}

        return {
            "success": False,
            "code": payload.get("code", -1),
            "error": payload.get("error") or payload.get("message") or "Unknown error",
        }


def _encode_bigints(obj: Any) -> Any:
    """Recursively convert ints that exceed JSON-safe range into strings."""
    if isinstance(obj, dict):
        return {k: _encode_bigints(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_encode_bigints(v) for v in obj]
    if isinstance(obj, int) and (obj < -(2**53) or obj > 2**53):
        return str(obj)
    return obj


def _error_result(msg: str) -> Dict[str, Any]:
    return {"success": False, "code": -1, "error": msg}


class WarthogApiError(WarthogPyError):
    """Raised when a node client call fails."""

    def __init__(self, result: Dict[str, Any]):
        self.code = result.get("code", -1)
        self.error_msg = result.get("error", "Unknown error")
        super().__init__(f"Warthog API error [{self.code}]: {self.error_msg}")
