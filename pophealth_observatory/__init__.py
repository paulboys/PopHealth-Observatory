"""Package exports for PopHealth Observatory.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

from .brfss import BRFSSExplorer
from .laboratory_pesticides import get_pesticide_metabolites, get_pesticide_panel, load_pesticide_reference
from .observatory import NHANESExplorer, PopHealthObservatory

# Dynamic version reading from package metadata
try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("pophealth-observatory")
except PackageNotFoundError:
    # Fallback for development environments where package isn't installed
    __version__ = "0.0.0+unknown"

__all__ = [
    "PopHealthObservatory",
    "NHANESExplorer",
    "BRFSSExplorer",
    "get_pesticide_metabolites",
    "get_pesticide_panel",
    "load_pesticide_reference",
    "__version__",
]
