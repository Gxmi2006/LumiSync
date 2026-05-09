"""ASUS Aura / Armoury Crate backend adapter.

The concrete implementation lives beside the backend manager today so startup
probing remains centralized. This module gives contributors a stable import
surface as the backend layer grows.
"""

from lumisync.backends.backend_manager import AuraController

__all__ = ["AuraController"]
