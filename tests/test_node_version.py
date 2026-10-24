import pytest

from warthog_py.errors import InvalidNodeVersionError
from warthog_py.node_version import NodeVersion

PAYLOAD = {
    "name": 'v0.10.3 "dd054a2"',
    "major": 0,
    "minor": 10,
    "patch": 3,
    "commit": "dd054a2",
}


class TestNodeVersionParse:
    def test_reads_the_version_fields(self):
        version = NodeVersion.parse(PAYLOAD)
        assert version.name == 'v0.10.3 "dd054a2"'
        assert version.major == 0
        assert version.minor == 10
        assert version.patch == 3
        assert version.commit == "dd054a2"

    def test_exposes_the_version_as_a_dotted_triple(self):
        assert NodeVersion.parse(PAYLOAD).version == "0.10.3"

    def test_rejects_a_payload_with_a_missing_field(self):
        for field in ("name", "major", "minor", "patch", "commit"):
            payload = {k: v for k, v in PAYLOAD.items() if k != field}
            assert NodeVersion.try_parse(payload) is None

    def test_rejects_a_payload_whose_name_is_not_a_string(self):
        assert NodeVersion.try_parse({**PAYLOAD, "name": 42}) is None

    def test_rejects_a_payload_whose_commit_is_not_a_string(self):
        assert NodeVersion.try_parse({**PAYLOAD, "commit": 42}) is None

    def test_rejects_a_payload_whose_version_numbers_are_not_integers(self):
        assert NodeVersion.try_parse({**PAYLOAD, "major": "0"}) is None
        assert NodeVersion.try_parse({**PAYLOAD, "minor": "10"}) is None
        assert NodeVersion.try_parse({**PAYLOAD, "patch": "3"}) is None

    def test_rejects_a_payload_whose_version_numbers_are_booleans(self):
        # bool is a subclass of int; it must not pass as a version number.
        assert NodeVersion.try_parse({**PAYLOAD, "major": True}) is None

    def test_rejects_a_payload_whose_version_numbers_are_negative(self):
        assert NodeVersion.try_parse({**PAYLOAD, "major": -1}) is None
        assert NodeVersion.try_parse({**PAYLOAD, "minor": -1}) is None
        assert NodeVersion.try_parse({**PAYLOAD, "patch": -1}) is None

    def test_rejects_a_payload_that_is_not_a_dict(self):
        for bad in (None, "garbage", 42, [], ()):
            assert NodeVersion.try_parse(bad) is None

    def test_parse_raises_on_a_malformed_payload(self):
        with pytest.raises(InvalidNodeVersionError):
            NodeVersion.parse({"name": "v0.10.3"})
