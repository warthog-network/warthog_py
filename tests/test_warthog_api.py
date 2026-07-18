from unittest.mock import patch

from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.transaction_context import ChainPin
from warthog_py.warthog_api import WarthogApi


def _mock_response(json_body, status=200):
    """Create a mock requests response."""
    from unittest.mock import MagicMock

    response = MagicMock()
    response.status_code = status
    response.json.return_value = json_body
    response.text = ""
    return response


class TestWarthogApi:
    def test_known_nodes_list(self):
        assert isinstance(WarthogApi.known_nodes(), list)
        assert len(WarthogApi.known_nodes()) > 0
        for url in WarthogApi.known_nodes():
            assert url.startswith("http")

    def test_default_base_url_uses_first_known_node(self):
        # No-arg construction picks the first known public testnet node —
        # a sane default so `WarthogApi()` works without configuration.
        api = WarthogApi()
        assert api.base_url == WarthogApi.known_nodes()[0]

    def test_default_can_be_overridden(self):
        api = WarthogApi("http://127.0.0.1:3100")
        assert api.base_url == "http://127.0.0.1:3100"

    def test_create_transaction_context(self):
        head = {
            "code": 0,
            "data": {
                "chainHead": {
                    "pinHash": "a" * 64,
                    "pinHeight": 320,
                }
            },
        }
        with patch("warthog_py.warthog_api.requests.get", return_value=_mock_response(head)):
            api = WarthogApi("http://65.87.7.86:3001")
            ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
            assert isinstance(ctx, ChainPin.__class__) or hasattr(ctx, "chain_pin")
            assert ctx.chain_pin.pin_hash == "a" * 64
            assert ctx.chain_pin.pin_height == 320

    def test_submit_transaction(self):
        api_response = {"code": 0, "data": {"txHash": "deadbeef"}}
        with patch(
            "warthog_py.warthog_api.requests.post",
            return_value=_mock_response(api_response),
        ):
            api = WarthogApi("http://65.87.7.86:3001")
            result = api.submit_transaction({"type": "wartTransfer", "signature65": "ab" * 65})
            assert result["txHash"] == "deadbeef"

    def test_error_response(self):
        err = {"code": 42, "error": "boom"}
        with patch(
            "warthog_py.warthog_api.requests.post", return_value=_mock_response(err)
        ):
            api = WarthogApi("http://65.87.7.86:3001")
            from warthog_py.warthog_api import WarthogApiError

            with __import__("pytest").raises(WarthogApiError) as exc_info:
                api.submit_transaction({})
            assert exc_info.value.code == 42
            assert "boom" in str(exc_info.value)

    def test_network_error(self):
        with patch(
            "warthog_py.warthog_api.requests.get",
            side_effect=__import__("requests").RequestException("conn refused"),
        ):
            api = WarthogApi("http://65.87.7.86:3001")
            from warthog_py.warthog_api import WarthogApiError

            with __import__("pytest").raises(WarthogApiError) as exc_info:
                api.get_chain_head()
            assert exc_info.value.code == -1