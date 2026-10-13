from unittest.mock import patch

import pytest

from warthog_py.chain_head import ChainHead
from warthog_py.chain_pin import ChainPin
from warthog_py.errors import InvalidChainHeadError
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.warthog_api import WarthogApi

HASH = "a" * 64

V1_HEAD = {
    "code": 0,
    "data": {
        "hash": HASH,
        "height": 100,
        "pinHash": HASH,
        "pinHeight": 320,
        "synced": True,
    },
}

V2_HEAD = {
    "code": 0,
    "data": {
        "chainHead": {
            "hash": HASH,
            "height": 100,
            "pinHash": HASH,
            "pinHeight": 320,
        },
        "synced": True,
    },
}


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
        # No-URL construction picks the first known public node, which is a
        # main net node on port 3001, so it speaks the V1 API.
        api = WarthogApi("v1")
        assert api.base_url == WarthogApi.known_nodes()[0]
        assert api.version == "v1"

    def test_default_can_be_overridden(self):
        api = WarthogApi("v2", "http://127.0.0.1:3200")
        assert api.base_url == "http://127.0.0.1:3200"
        assert api.version == "v2"

    def test_version_is_required_and_validated(self):
        with pytest.raises(TypeError):
            WarthogApi()  # type: ignore[call-arg]
        # The old positional URL form is now a bad generation and must fail
        # loudly rather than mis-parsing every chain head.
        with pytest.raises(ValueError, match="invalid API version"):
            WarthogApi("http://127.0.0.1:3100")
        with pytest.raises(ValueError, match="invalid API version"):
            WarthogApi("v3")

    def test_create_transaction_context_v1(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V1_HEAD)
        ):
            api = WarthogApi("v1", "http://65.87.7.86:3001")
            ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
            assert isinstance(ctx.chain_pin, ChainPin)
            assert ctx.chain_pin.pin_hash == HASH
            assert ctx.chain_pin.pin_height == 320

    def test_create_transaction_context_v2(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V2_HEAD)
        ):
            api = WarthogApi("v2", "http://127.0.0.1:3100")
            ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
            assert ctx.chain_pin.pin_hash == HASH
            assert ctx.chain_pin.pin_height == 320

    def test_get_chain_head_normalizes_both_generations(self):
        for version, payload in (("v1", V1_HEAD), ("v2", V2_HEAD)):
            with patch(
                "warthog_py.warthog_api.requests.get", return_value=_mock_response(payload)
            ):
                api = WarthogApi(version)
                head = api.get_chain_head()
                assert isinstance(head, ChainHead)
                assert head.pin == ChainPin(HASH, 320)
                assert head.hash == HASH
                assert head.height == 100
                assert head.synced is True

    def test_get_chain_head_rejects_the_wrong_generation(self):
        # v1 payload declared as v2, and vice versa. Previously the v1 case
        # raised a bare KeyError from create_transaction_context.
        for version, payload in (("v1", V2_HEAD), ("v2", V1_HEAD)):
            with patch(
                "warthog_py.warthog_api.requests.get", return_value=_mock_response(payload)
            ):
                api = WarthogApi(version)
                with pytest.raises(InvalidChainHeadError):
                    api.get_chain_head()
                with pytest.raises(InvalidChainHeadError):
                    api.create_transaction_context(
                        RoundedFee.min(), NonceId.from_number(0)
                    )

    def test_submit_transaction(self):
        api_response = {"code": 0, "data": {"txHash": "deadbeef"}}
        with patch(
            "warthog_py.warthog_api.requests.post",
            return_value=_mock_response(api_response),
        ):
            api = WarthogApi("v1", "http://65.87.7.86:3001")
            result = api.submit_transaction({"type": "wartTransfer", "signature65": "ab" * 65})
            assert result["txHash"] == "deadbeef"

    def test_error_response(self):
        err = {"code": 42, "error": "boom"}
        with patch(
            "warthog_py.warthog_api.requests.post", return_value=_mock_response(err)
        ):
            api = WarthogApi("v1", "http://65.87.7.86:3001")
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
            api = WarthogApi("v1", "http://65.87.7.86:3001")
            from warthog_py.warthog_api import WarthogApiError

            with __import__("pytest").raises(WarthogApiError) as exc_info:
                api.get_chain_head()
            assert exc_info.value.code == -1