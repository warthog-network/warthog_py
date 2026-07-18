"""RIPEMD-160 wrapper.

Prefers ``pycryptodome`` (which doesn't depend on OpenSSL build flags) and
falls back to ``hashlib.new("ripemd160")`` if ``pycryptodome`` is not
installed.

The full Python ecosystem recommends both libraries; ``pycryptodome``
is documented in our integration guide as a prerequisite.
"""

from typing import Optional

_cached_backend: Optional[str] = None


def _digest_ripemd160(data: bytes) -> bytes:
    """Compute RIPEMD-160 of ``data``. Returns 20 bytes."""
    global _cached_backend

    if _cached_backend is None:
        try:
            from Crypto.Hash import RIPEMD160
            _cached_backend = "pycryptodome"
        except ImportError:
            import hashlib
            _cached_backend = "hashlib"

    if _cached_backend == "pycryptodome":
        from Crypto.Hash import RIPEMD160
        return RIPEMD160.new(data).digest()

    import hashlib
    return hashlib.new("ripemd160", data).digest()


def ripemd160(data: bytes) -> bytes:
    """Public API: compute RIPEMD-160 of ``data``."""
    return _digest_ripemd160(data)