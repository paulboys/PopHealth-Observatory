"""Package-relative path resolution for bundled reference data.

All reference assets live inside the package at ``pophealth_observatory/data/reference/``.
This module provides a single canonical helper so every consumer resolves the
same directory regardless of working directory or install location.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_DATA_REFERENCE_DIR = _PACKAGE_DIR / "data" / "reference"


def get_reference_dir() -> Path:
    """Return the package-internal reference data directory.

    Returns
    -------
    Path
        Absolute path to ``pophealth_observatory/data/reference/``.
    """
    return _DATA_REFERENCE_DIR
