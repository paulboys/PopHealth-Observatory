"""Package exports for PopHealth Observatory.

SPDX-License-Identifier: MIT
Copyright (c) 2025 Paul Boys and PopHealth Observatory contributors
"""

from __future__ import annotations

from importlib import import_module
from typing import Any
from warnings import warn

# Dynamic version reading from package metadata
try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("pophealth-observatory")
except PackageNotFoundError:
    # Fallback for development environments where package isn't installed
    __version__ = "0.0.0+unknown"

# Root-level exports are maintained as backward-compatible shims.
# New code should import from submodules directly (e.g. pophealth_observatory.observatory).
_DEPRECATION_REMOVAL_VERSION = "2.0.0"
_DEPRECATION_REMOVAL_DATE = "2027-06-30"

_DEPRECATED_EXPORTS: dict[str, tuple[str, str]] = {
    "PopHealthObservatory": ("pophealth_observatory.observatory", "PopHealthObservatory"),
    "NHANESExplorer": ("pophealth_observatory.observatory", "NHANESExplorer"),
    "BRFSSExplorer": ("pophealth_observatory.brfss", "BRFSSExplorer"),
    "get_pesticide_metabolites": ("pophealth_observatory.laboratory_pesticides", "get_pesticide_metabolites"),
    "get_pesticide_panel": ("pophealth_observatory.laboratory_pesticides", "get_pesticide_panel"),
    "load_pesticide_reference": ("pophealth_observatory.laboratory_pesticides", "load_pesticide_reference"),
}


def __getattr__(name: str) -> Any:
    if name in _DEPRECATED_EXPORTS:
        module_name, symbol_name = _DEPRECATED_EXPORTS[name]
        replacement_import = f"from {module_name} import {symbol_name}"
        warn(
            (
                f"Importing '{name}' from 'pophealth_observatory' is deprecated and will be removed "
                f"no earlier than {_DEPRECATION_REMOVAL_VERSION} (target date: {_DEPRECATION_REMOVAL_DATE}). "
                f"Use '{replacement_import}' instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )
        module = import_module(module_name)
        value = getattr(module, symbol_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'pophealth_observatory' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_DEPRECATED_EXPORTS.keys()))


__all__ = [*list(_DEPRECATED_EXPORTS.keys()), "__version__"]
