import pytest

from warthog_py.chain_head import ChainHead
from warthog_py.chain_pin import PIN_HEIGHT_MULTIPLE, ChainPin, chain_head_source
from warthog_py.errors import InvalidChainHeadError

HASH = "a" * 64

V1_PAYLOAD = {
    "hash": HASH,
    "height": 100,
    "pinHash": HASH,
    "pinHeight": 64,
    "synced": True,
}

V2_PAYLOAD = {
    "chainHead": {
        "hash": HASH,
        "height": 100,
        "pinHash": HASH,
        "pinHeight": 64,
    },
    "synced": True,
}


class TestChainPinValidate:
    def test_accepts_well_formed_pin(self):
        assert ChainPin.validate(HASH, 0)
        assert ChainPin.validate(HASH, 32)
        assert ChainPin.validate(HASH, 320)

    def test_rejects_height_not_multiple_of_32(self):
        assert not ChainPin.validate(HASH, 1)
        assert not ChainPin.validate(HASH, 31)
        assert not ChainPin.validate(HASH, 321)

    def test_rejects_negative_height(self):
        assert not ChainPin.validate(HASH, -32)

    def test_rejects_wrong_hash_length(self):
        assert not ChainPin.validate("a" * 63, 32)
        assert not ChainPin.validate("a" * 65, 32)
        assert not ChainPin.validate("", 32)

    def test_rejects_wrong_types(self):
        assert not ChainPin.validate(123, 32)
        assert not ChainPin.validate(HASH, "32")
        assert not ChainPin.validate(HASH, 32.0)
        assert not ChainPin.validate(None, None)
        # bool is a subclass of int and must not slip through
        assert not ChainPin.validate(HASH, True)


class TestChainPinTryParse:
    def test_reads_v1_from_top_level(self):
        assert ChainPin.try_parse(V1_PAYLOAD, "v1") == ChainPin(HASH, 64)

    def test_reads_v2_from_chain_head(self):
        assert ChainPin.try_parse(V2_PAYLOAD, "v2") == ChainPin(HASH, 64)

    def test_rejects_v2_payload_declared_as_v1(self):
        assert ChainPin.try_parse(V2_PAYLOAD, "v1") is None

    def test_rejects_v1_payload_declared_as_v2(self):
        assert ChainPin.try_parse(V1_PAYLOAD, "v2") is None

    def test_rejects_unknown_version(self):
        assert ChainPin.try_parse(V1_PAYLOAD, "v3") is None

    def test_rejects_non_dict_payload(self):
        assert ChainPin.try_parse(None, "v1") is None
        assert ChainPin.try_parse("chainHead", "v2") is None

    def test_rejects_missing_pin_fields(self):
        assert ChainPin.try_parse({"hash": HASH, "height": 1}, "v1") is None

    def test_rejects_chain_head_that_is_not_a_dict(self):
        assert ChainPin.try_parse({"chainHead": "nope"}, "v2") is None


class TestChainHeadSource:
    def test_v1_returns_the_payload_itself(self):
        assert chain_head_source(V1_PAYLOAD, "v1") is V1_PAYLOAD

    def test_v2_returns_the_nested_mapping(self):
        assert chain_head_source(V2_PAYLOAD, "v2") == V2_PAYLOAD["chainHead"]

    def test_v2_missing_chain_head(self):
        assert chain_head_source(V1_PAYLOAD, "v2") is None

    def test_unknown_version(self):
        assert chain_head_source(V1_PAYLOAD, "v3") is None


class TestChainHeadTryParse:
    def test_normalizes_v1(self):
        head = ChainHead.try_parse(V1_PAYLOAD, "v1")
        assert head == ChainHead(ChainPin(HASH, 64), HASH, 100, True)

    def test_normalizes_v2(self):
        head = ChainHead.try_parse(V2_PAYLOAD, "v2")
        assert head == ChainHead(ChainPin(HASH, 64), HASH, 100, True)

    def test_rejects_cross_generation(self):
        assert ChainHead.try_parse(V2_PAYLOAD, "v1") is None
        assert ChainHead.try_parse(V1_PAYLOAD, "v2") is None

    def test_reads_synced_from_the_root_only(self):
        payload = {
            "chainHead": dict(V2_PAYLOAD["chainHead"], synced=True),
        }
        assert ChainHead.try_parse(payload, "v2").synced is False

    def test_missing_synced_defaults_to_false(self):
        payload = {"chainHead": dict(V2_PAYLOAD["chainHead"])}
        assert ChainHead.try_parse(payload, "v2").synced is False

    def test_rejects_missing_hash(self):
        payload = {"height": 1, "pinHash": HASH, "pinHeight": 0}
        assert ChainHead.try_parse(payload, "v1") is None

    def test_rejects_missing_height(self):
        payload = {"hash": HASH, "pinHash": HASH, "pinHeight": 0}
        assert ChainHead.try_parse(payload, "v1") is None

    def test_rejects_non_integer_height(self):
        payload = {"hash": HASH, "height": "100", "pinHash": HASH, "pinHeight": 0}
        assert ChainHead.try_parse(payload, "v1") is None

    def test_rejects_malformed_pin(self):
        payload = {"hash": HASH, "height": 1, "pinHash": HASH, "pinHeight": 3}
        assert ChainHead.try_parse(payload, "v1") is None


class TestChainHeadParse:
    def test_returns_head(self):
        assert ChainHead.parse(V2_PAYLOAD, "v2").height == 100

    def test_raises_on_mismatch(self):
        with pytest.raises(InvalidChainHeadError, match="Invalid v1"):
            ChainHead.parse(V2_PAYLOAD, "v1")


def test_pin_height_multiple_is_32():
    assert PIN_HEIGHT_MULTIPLE == 32