"""Compatibility shim for the pre-rebrand package name.

New code should import `lumisync`.
"""

from lumisync import __version__

__all__ = ["__version__"]
