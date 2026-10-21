"""Shared types for the transaction builders.

The two node families accept different transaction sets, so the contexts are
separate classes: :class:`warthog_py.legacy_transaction_context.WarthogLegacyTransactionContext`
for the legacy node (core/master, core/dev) and
:class:`warthog_py.defi_transaction_context.WarthogDeFiTransactionContext` for
the DeFi node (core/defi). A legacy context cannot build a limit swap, because
that builder does not exist on it.

``AnyTransactionContext`` is the union of the two, for calling code that only
sends WART and therefore only needs ``transfer_wart``.
"""

from typing import Any, Dict, Union

from warthog_py.defi_transaction_context import WarthogDeFiTransactionContext
from warthog_py.legacy_transaction_context import WarthogLegacyTransactionContext

TransactionJson = Dict[str, Any]
"""A signed transaction, ready for ``submit_transaction``."""

AnyTransactionContext = Union[
    WarthogLegacyTransactionContext, WarthogDeFiTransactionContext
]
"""Either transaction context. Both have ``transfer_wart``."""

__all__ = ["TransactionJson", "AnyTransactionContext"]
