"""Custom exceptions for the warthog_py library."""


class WarthogPyError(Exception):
    """Base exception for all warthog_py errors."""


class InvalidAddressError(WarthogPyError):
    """Raised when an address hex string fails validation."""


class InvalidNonceError(WarthogPyError):
    """Raised when a nonce value is out of the 32-bit unsigned range."""


class InvalidDecimalsError(WarthogPyError):
    """Raised when a token decimals value is out of [0, 18]."""


class InvalidFundsError(WarthogPyError):
    """Raised when a token amount is invalid (e.g. too many decimals, overflow)."""


class InvalidPriceError(WarthogPyError):
    """Raised when a Price construction produces an out-of-range value."""


class InvalidSignatureError(WarthogPyError):
    """Raised when a secp256k1 signature cannot be produced."""


class InvalidPrivateKeyError(WarthogPyError):
    """Raised when a private key has the wrong size or invalid hex."""


class InvalidChainHeadError(WarthogPyError):
    """Raised when a ``/chain/head`` payload does not match the declared API version."""


class InvalidBalanceError(WarthogPyError):
    """Raised when a node's balance payload is malformed or does not add up."""