"""Balances as the nodes report them.

The DeFi node reports a balance three ways: what the account owns in total,
what is locked in open limit orders, and what is locked by transactions still
sitting in the mempool. The spendable amount is what is left of the total
after those two.

The legacy node reports one number, the confirmed balance: it has no limit
orders and does not report what pending transactions lock.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from warthog_py.errors import InvalidBalanceError, WarthogPyError
from warthog_py.funds import Funds
from warthog_py.token_decimals import TokenDecimals
from warthog_py.wart import Wart


@dataclass(frozen=True)
class DeFiWartBalance:
    """WART balance of an account on the DeFi node."""

    total: Wart
    """What the account owns."""
    locked: Wart
    """Locked in open limit orders."""
    mempool: Wart
    """Locked by transactions in the mempool."""

    @classmethod
    def parse(cls, data: Dict[str, Any]) -> "DeFiWartBalance":
        """Read a balance out of a ``/account/{address}/wart_balance`` response.

        Raises ``InvalidBalanceError`` if the payload is malformed or the
        three amounts do not add up.
        """
        wart = data.get("wart") if isinstance(data, dict) else None
        if not isinstance(wart, dict):
            raise InvalidBalanceError("balance response has no wart object")

        total = _parse_node_wart(wart.get("total"))
        locked = _parse_node_wart(wart.get("locked"))
        mempool = _parse_node_wart(wart.get("mempool"))
        if total is None or locked is None or mempool is None:
            raise InvalidBalanceError("balance response has a malformed amount")

        # The node computes the spendable amount by subtracting the two
        # locked parts from the total, and asserts the result. A response
        # that does not add up is not a balance we can use.
        if total.e8 < locked.e8 + mempool.e8:
            raise InvalidBalanceError(
                "inconsistent balance: total is less than locked plus mempool"
            )

        return cls(total=total, locked=locked, mempool=mempool)

    @classmethod
    def try_parse(cls, data: Dict[str, Any]) -> Optional["DeFiWartBalance"]:
        """Like ``parse`` but returns ``None`` instead of raising."""
        try:
            return cls.parse(data)
        except InvalidBalanceError:
            return None

    def free(self) -> Wart:
        """The amount that can be spent now: total - locked - mempool.

        Raises ``InvalidBalanceError`` if the balance does not add up, which
        the node also treats as an error rather than a balance.
        """
        free = self.total.e8 - self.locked.e8 - self.mempool.e8
        if free < 0:
            raise InvalidBalanceError(
                "inconsistent balance: total is less than locked plus mempool"
            )
        return Wart.from_e8(free)


@dataclass(frozen=True)
class TokenBalance:
    """Token balance of an account on the DeFi node."""

    name: str
    """Name of the token."""
    decimals: TokenDecimals
    """Number of decimals the token is scaled by."""
    total: Funds
    """What the account owns."""
    locked: Funds
    """Locked in open limit orders."""
    mempool: Funds
    """Locked by transactions in the mempool."""

    @classmethod
    def parse(cls, data: Dict[str, Any]) -> "TokenBalance":
        """Read a balance out of a ``/account/{address}/balance/asset:{hash}`` response.

        Raises ``InvalidBalanceError`` if the payload is malformed or the
        three amounts do not add up.
        """
        if not isinstance(data, dict):
            raise InvalidBalanceError("balance response is not an object")

        token = data.get("token")
        balance = data.get("balance")
        if not isinstance(token, dict) or not isinstance(balance, dict):
            raise InvalidBalanceError("balance response has no token or balance object")

        name = token.get("name")
        decimals = token.get("decimals")
        if not isinstance(name, str) or not isinstance(decimals, int):
            raise InvalidBalanceError("balance response has a malformed token")

        total = _parse_node_funds(balance.get("total"))
        locked = _parse_node_funds(balance.get("locked"))
        mempool = _parse_node_funds(balance.get("mempool"))
        if total is None or locked is None or mempool is None:
            raise InvalidBalanceError("balance response has a malformed amount")

        if total.amount < locked.amount + mempool.amount:
            raise InvalidBalanceError(
                "inconsistent balance: total is less than locked plus mempool"
            )

        try:
            token_decimals = TokenDecimals.new(decimals)
        except WarthogPyError as e:
            raise InvalidBalanceError(f"balance response has invalid decimals: {e}") from e

        return cls(
            name=name,
            decimals=token_decimals,
            total=total,
            locked=locked,
            mempool=mempool,
        )

    @classmethod
    def try_parse(cls, data: Dict[str, Any]) -> Optional["TokenBalance"]:
        """Like ``parse`` but returns ``None`` instead of raising."""
        try:
            return cls.parse(data)
        except InvalidBalanceError:
            return None

    def free(self) -> Funds:
        """The amount that can be spent now: total - locked - mempool.

        Raises ``InvalidBalanceError`` if the balance does not add up, which
        the node also treats as an error rather than a balance.
        """
        free = self.total.amount - self.locked.amount - self.mempool.amount
        if free < 0:
            raise InvalidBalanceError(
                "inconsistent balance: total is less than locked plus mempool"
            )
        return Funds.from_amount(free)


def _parse_node_wart(value: Any) -> Optional[Wart]:
    """Read a WART amount out of a node response.

    The decimal string is used, not the integer: the integer is a JSON
    number, and a balance above 2^53 does not survive that.
    """
    if not isinstance(value, dict):
        return None
    text = value.get("str")
    if not isinstance(text, str):
        return None
    return Wart.try_parse(text)


def _parse_node_funds(value: Any) -> Optional[Funds]:
    """Read a token amount out of a node response.

    The decimal string is used, not the integer, for the same reason as in
    ``_parse_node_wart``.
    """
    if not isinstance(value, dict):
        return None
    text = value.get("str")
    decimals = value.get("decimals")
    if not isinstance(text, str) or not isinstance(decimals, int):
        return None
    try:
        token_decimals = TokenDecimals.new(decimals)
    except WarthogPyError:
        return None
    return Funds.try_parse(text, token_decimals)
