from unittest.mock import MagicMock, patch

import pytest

from warthog_py.chain_head import ChainHead
from warthog_py.chain_pin import ChainPin
from warthog_py.defi_api import WarthogDeFiApi
from warthog_py.errors import InvalidChainHeadError
from warthog_py.legacy_api import WarthogLegacyApi
from warthog_py.legacy_transaction_context import WarthogLegacyTransactionContext
from warthog_py.defi_transaction_context import WarthogDeFiTransactionContext
from warthog_py.nonce_id import NonceId
from warthog_py.rounded_fee import RoundedFee
from warthog_py.warthog_api import (
    KNOWN_NODES_DEFI,
    KNOWN_NODES_LEGACY,
    WarthogApiBase,
    WarthogApiError,
)

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
    response = MagicMock()
    response.status_code = status
    response.json.return_value = json_body
    response.text = ""
    return response


class TestKnownNodes:
    def test_the_two_families_have_separate_lists(self):
        assert isinstance(KNOWN_NODES_LEGACY, list)
        assert isinstance(KNOWN_NODES_DEFI, list)
        assert len(KNOWN_NODES_LEGACY) > 0
        assert len(KNOWN_NODES_DEFI) > 0
        assert KNOWN_NODES_LEGACY != KNOWN_NODES_DEFI
        for url in KNOWN_NODES_LEGACY + KNOWN_NODES_DEFI:
            assert url.startswith("http")

    def test_the_base_exposes_both_lists(self):
        assert WarthogApiBase.known_nodes_legacy() == KNOWN_NODES_LEGACY
        assert WarthogApiBase.known_nodes_defi() == KNOWN_NODES_DEFI


class TestLegacyApi:
    def test_default_base_url_uses_first_known_node(self):
        # No-URL construction picks the first known legacy node, which is a
        # main net node on port 3001, so it speaks the V1 API.
        api = WarthogLegacyApi()
        assert api.base_url == KNOWN_NODES_LEGACY[0]
        assert api.version == "v1"

    def test_default_can_be_overridden(self):
        api = WarthogLegacyApi("http://127.0.0.1:3100")
        assert api.base_url == "http://127.0.0.1:3100"

    def test_create_transaction_context(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V1_HEAD)
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
            assert isinstance(ctx, WarthogLegacyTransactionContext)
            assert isinstance(ctx.chain_pin, ChainPin)
            assert ctx.chain_pin.pin_hash == HASH
            assert ctx.chain_pin.pin_height == 320

    def test_get_chain_head_reads_the_flat_shape(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V1_HEAD)
        ):
            head = WarthogLegacyApi().get_chain_head()
            assert isinstance(head, ChainHead)
            assert head.pin == ChainPin(HASH, 320)
            assert head.height == 100
            assert head.synced is True

    def test_get_chain_head_rejects_the_nested_shape(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V2_HEAD)
        ):
            with pytest.raises(InvalidChainHeadError):
                WarthogLegacyApi().get_chain_head()

    def test_get_wart_balance(self):
        body = {"code": 0, "data": {"balance": "10.00000000"}}
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(body)
        ):
            balance = WarthogLegacyApi().get_wart_balance("0" * 40 + "de47c9b2")
            assert balance.e8 == 1_000_000_000


class TestDeFiApi:
    def test_default_base_url_uses_first_known_node(self):
        api = WarthogDeFiApi()
        assert api.base_url == KNOWN_NODES_DEFI[0]
        assert api.version == "v2"

    def test_default_can_be_overridden(self):
        api = WarthogDeFiApi("http://127.0.0.1:3101")
        assert api.base_url == "http://127.0.0.1:3101"

    def test_create_transaction_context(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V2_HEAD)
        ):
            api = WarthogDeFiApi("http://127.0.0.1:3101")
            ctx = api.create_transaction_context(RoundedFee.min(), NonceId.from_number(0))
            assert isinstance(ctx, WarthogDeFiTransactionContext)
            assert ctx.chain_pin.pin_hash == HASH
            assert ctx.chain_pin.pin_height == 320

    def test_get_chain_head_reads_the_nested_shape(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V2_HEAD)
        ):
            head = WarthogDeFiApi().get_chain_head()
            assert isinstance(head, ChainHead)
            assert head.pin == ChainPin(HASH, 320)
            assert head.height == 100
            assert head.synced is True

    def test_get_chain_head_rejects_the_flat_shape(self):
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(V1_HEAD)
        ):
            with pytest.raises(InvalidChainHeadError):
                WarthogDeFiApi().get_chain_head()

    def test_get_wart_balance(self):
        body = {
            "code": 0,
            "data": {
                "wart": {
                    "total": {"str": "10.00000000", "E8": 1_000_000_000},
                    "locked": {"str": "2.00000000", "E8": 200_000_000},
                    "mempool": {"str": "1.00000000", "E8": 100_000_000},
                }
            },
        }
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(body)
        ):
            balance = WarthogDeFiApi().get_wart_balance("0" * 40 + "de47c9b2")
            assert balance.total.e8 == 1_000_000_000
            assert balance.free().e8 == 700_000_000

    def test_get_token_balance(self):
        body = {
            "code": 0,
            "data": {
                "token": {"name": "TOK2", "decimals": 4},
                "balance": {
                    "total": {"str": "1000.0000", "u64": 10_000_000, "decimals": 4},
                    "locked": {"str": "100.0000", "u64": 1_000_000, "decimals": 4},
                    "mempool": {"str": "0.0000", "u64": 0, "decimals": 4},
                },
            },
        }
        with patch(
            "warthog_py.warthog_api.requests.get", return_value=_mock_response(body)
        ):
            balance = WarthogDeFiApi().get_token_balance(
                "0" * 40 + "de47c9b2", "F45B113119C7F7C000234F1090D5D181AB60B8B24526F1EDD2F563AA1CA329F2"
            )
            assert balance.name == "TOK2"
            assert balance.total.amount == 10_000_000
            assert balance.free().amount == 9_000_000


class TestSharedClientBehaviour:
    def test_submit_transaction(self):
        api_response = {"code": 0, "data": {"txHash": "deadbeef"}}
        with patch(
            "warthog_py.warthog_api.requests.post",
            return_value=_mock_response(api_response),
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            result = api.submit_transaction({"signature65": "ab" * 65})
            assert result["txHash"] == "deadbeef"

    def test_submit_transaction_rejects_a_response_without_a_hash(self):
        api_response = {"code": 0, "data": {"notATxHash": "deadbeef"}}
        with patch(
            "warthog_py.warthog_api.requests.post",
            return_value=_mock_response(api_response),
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            with pytest.raises(WarthogApiError) as exc_info:
                api.submit_transaction({"signature65": "ab" * 65})
            assert "Invalid transaction add" in str(exc_info.value)

    def test_submit_transaction_rejects_a_response_that_is_not_a_dict(self):
        api_response = {"code": 0, "data": "deadbeef"}
        with patch(
            "warthog_py.warthog_api.requests.post",
            return_value=_mock_response(api_response),
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            with pytest.raises(WarthogApiError) as exc_info:
                api.submit_transaction({"signature65": "ab" * 65})
            assert "Invalid transaction add" in str(exc_info.value)

    def test_error_response(self):
        err = {"code": 42, "error": "boom"}
        with patch(
            "warthog_py.warthog_api.requests.post", return_value=_mock_response(err)
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            with pytest.raises(WarthogApiError) as exc_info:
                api.submit_transaction({})
            assert exc_info.value.code == 42
            assert "boom" in str(exc_info.value)

    def test_network_error(self):
        import requests

        with patch(
            "warthog_py.warthog_api.requests.get",
            side_effect=requests.RequestException("conn refused"),
        ):
            api = WarthogLegacyApi("http://65.87.7.86:3001")
            with pytest.raises(WarthogApiError) as exc_info:
                api.get_chain_head()
            assert exc_info.value.code == -1
