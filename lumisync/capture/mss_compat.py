from __future__ import annotations

import mss


def create_mss():
    """Create an MSS screen grabber on both old and new mss releases.

    mss 10 deprecated ``mss.mss`` in favour of ``mss.MSS``; mss 9 only has the
    former. Prefer the new name so users do not see a DeprecationWarning.
    """

    factory = getattr(mss, "MSS", None) or mss.mss
    return factory()
