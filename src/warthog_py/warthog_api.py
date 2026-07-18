"""Client for communicating with Warthog nodes."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from warthog_py.errors import WarthogPyError
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.transaction_context import ChainPin, TransactionContext

KNOWN_NODES: List[str] = [
    "http://65.87.7.86:3001",
    "http://185.209.228.16:3001",
    "http://89.117.150.162:3001",
    "http://62.72.44.89:3001",
    "http://217.182.64.43:3001",
    "https://node.wartscan.io",
    "http://dev.node-s.com:3001",
]
"""Known Warthog public nodes (best-effort, may include dead nodes)."""


@dataclass
class WarthogApi:
    """Client for communicating with a Warthog node.

    The default ``base_url`` is the first entry in ``KNOWN_NODES`` (a
    public testnet node). Override it for a local dev node:

        WarthogApi()                              # public testnet
        WarthogApi("http://127.0.0.1:3100")      # local dev
    """

    base_url: str = KNOWN_NODES[0]
    timeout: int = 30

    @staticmethod
    def known_nodes() -> List[str]:
        """Known Warthog public nodes (best-effort, may include dead nodes)."""
        return KNOWN_NODES

    def get_chain_head(self) -> Dict[str, Any]:
        """Fetch the chain head (latest pinned block).

        Returns the parsed ``data`` payload as a dict.

        Raises ``WarthogApiError`` on failure.
        """
        result = self._request("GET", "/chain/head")
        if not result.get("success"):
            raise WarthogApiError(result)
        return result["data"]

    def submit_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a signed transaction to the node.

        Returns the parsed ``data`` payload (e.g. ``{"txHash": "..."}``).

        Raises ``WarthogApiError`` on failure.
        """
        result = self._request("POST", "/transaction/add", body=tx)
        if not result.get("success"):
            raise WarthogApiError(result)
        return result["data"]

    def create_transaction_context(
        self, fee: RoundedFee, nonce_id: NonceId
    ) -> TransactionContext:
        """Fetch the chain head and build a ``TransactionContext``.

        Raises ``WarthogApiError`` on failure.
        """
        head = self.get_chain_head()
        chain_head = head.get("chainHead") or {}
        pin_hash = chain_head["pinHash"]
        pin_height = chain_head["pinHeight"]
        return TransactionContext(
            chain_pin=ChainPin(pin_hash=pin_hash, pin_height=pin_height),
            fee=fee,
            nonce_id=nonce_id,
        )

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
    """Raised when a WarthogApi call fails."""

    def __init__(self, result: Dict[str, Any]):
        self.code = result.get("code", -1)
        self.error_msg = result.get("error", "Unknown error")
        super().__init__(f"Warthog API error [{self.code}]: {self.error_msg}")