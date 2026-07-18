"""BIP-44 hierarchical deterministic wallet for Warthog.

Uses the derivation path ``m/44'/2070'/0'`` for Warthog accounts
(coin type ``2070`` is registered to Warthog).
"""

from bip32 import BIP32
from mnemonic import Mnemonic

from warthog_py.account import Account

PURPOSE = 44
COIN_TYPE = 2070
ACCOUNT = 0


class HDWallet:
    """BIP-44 HD wallet for Warthog."""

    def __init__(self, root_node: BIP32):
        self._root_node = root_node

    @classmethod
    def from_mnemonic(cls, mnemonic: str) -> "HDWallet":
        """Create an ``HDWallet`` from a BIP-39 mnemonic phrase.

        Accepts 12, 15, 18, 21, or 24 words.
        """
        if not isinstance(mnemonic, str) or not mnemonic.strip():
            raise ValueError("mnemonic must be a non-empty string")

        m = Mnemonic("english")
        seed = m.to_seed(mnemonic.strip(), passphrase="")

        # Derive root at m/44'/2070'/0' using hardened notation: 'h' or "'"
        root = BIP32.from_seed(seed)
        path = f"m/{PURPOSE}h/{COIN_TYPE}h/{ACCOUNT}h"
        return cls(root)

    def derive_account_at_index(self, index: int) -> Account:
        """Derive an account at the given index using path ``0/{index}``."""
        if not isinstance(index, int) or index < 0:
            raise ValueError(f"index must be a non-negative integer, got: {index}")
        return self.derive_account_from_path(f"0/{index}")

    def derive_account_from_path(self, path: str) -> Account:
        """Derive an account from a custom relative path.

        A leading ``m/`` is optional — pass either ``"0/0"`` or
        ``"m/0/0"``.
        """
        full_path = _ensure_master_prefix(path)
        privkey = self._root_node.get_privkey_from_path(full_path)
        return Account.from_private_key(privkey)


def _ensure_master_prefix(path: str) -> str:
    if path.startswith("m/") or path.startswith("M/"):
        return path
    return "m/" + path