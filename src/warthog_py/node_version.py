"""The version a node reports about itself.

Every node family reports the same five fields, in the same flat shape:

- ``core/master`` (main net) — ``GET /tools/version``, nlohmann
  ``to_json(PrintNodeVersion&)``
- ``core/dev`` — ``GET /tools/version``, nlohmann ``to_json(PrintNodeVersion&)``
- ``core/defi`` (test net) — ``GET /version``, glaze ``NodeVersion``

So unlike ``/chain/head``, which differs between API generations, the version
payload needs no per-family handling. Only the URL differs, and that is the
caller's business, not the parser's.
"""

from dataclasses import dataclass
from typing import Any, Optional

from warthog_py.errors import InvalidNodeVersionError


@dataclass(frozen=True)
class NodeVersion:
    """The version a node reports about itself."""

    name: str
    """The node's version string, e.g. ``v0.10.3 "dd054a2"``.

    This is the ``CMDLINE_PARSER_VERSION`` macro: the semantic version with a
    ``v`` in front, then the commit hash in quotes.
    """

    major: int
    """Major version."""

    minor: int
    """Minor version."""

    patch: int
    """Patch version."""

    commit: str
    """The commit hash the node was built from."""

    @property
    def version(self) -> str:
        """The version as a dotted triple, e.g. ``0.10.3``.

        This is the numeric form, without the ``v`` prefix and without the
        commit hash. It is what a version comparison wants.
        """
        return f"{self.major}.{self.minor}.{self.patch}"

    @classmethod
    def try_parse(cls, data: Any) -> Optional["NodeVersion"]:
        """Read the version out of a node response.

        Returns ``None`` if the payload is missing a field or a field has the
        wrong type.
        """
        if not isinstance(data, dict):
            return None

        name = data.get("name")
        commit = data.get("commit")
        if not isinstance(name, str) or not isinstance(commit, str):
            return None

        major = data.get("major")
        minor = data.get("minor")
        patch = data.get("patch")
        # bool is a subclass of int; reject it explicitly.
        for value in (major, minor, patch):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return None

        return cls(name=name, major=major, minor=minor, patch=patch, commit=commit)

    @classmethod
    def parse(cls, data: Any) -> "NodeVersion":
        """Like :meth:`try_parse` but raises on invalid input."""
        version = cls.try_parse(data)
        if version is None:
            raise InvalidNodeVersionError("Invalid node version response")
        return version
