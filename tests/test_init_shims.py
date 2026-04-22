"""Contract tests for root-level backward-compatible export shims."""

from __future__ import annotations

import importlib
import sys
import warnings

import pytest


def _fresh_root_module():
    """Import a fresh copy of the root package so shim warnings are testable."""
    sys.modules.pop("pophealth_observatory", None)
    return importlib.import_module("pophealth_observatory")


def test_root_nhanesexplorer_shim_warns_and_resolves() -> None:
    pkg = _fresh_root_module()
    assert "NHANESExplorer" not in pkg.__dict__

    with pytest.deprecated_call(match=r"no earlier than 2\.0\.0 \(target date: 2027-06-30\)"):
        shim_cls = pkg.NHANESExplorer

    from pophealth_observatory.observatory import NHANESExplorer

    assert shim_cls is NHANESExplorer


def test_root_function_shim_warns_and_resolves() -> None:
    pkg = _fresh_root_module()
    assert "get_pesticide_panel" not in pkg.__dict__

    with pytest.deprecated_call(
        match=r"Use 'from pophealth_observatory\.laboratory_pesticides import get_pesticide_panel' instead"
    ):
        shim_fn = pkg.get_pesticide_panel

    from pophealth_observatory.laboratory_pesticides import get_pesticide_panel

    assert shim_fn is get_pesticide_panel


def test_unknown_root_attribute_raises_attribute_error() -> None:
    pkg = _fresh_root_module()

    with pytest.raises(AttributeError, match="has no attribute 'DOES_NOT_EXIST'"):
        _ = pkg.DOES_NOT_EXIST


def test_root_shim_warning_emitted_once_after_cache() -> None:
    pkg = _fresh_root_module()

    with pytest.deprecated_call(match=r"no earlier than 2\.0\.0 \(target date: 2027-06-30\)"):
        _ = pkg.BRFSSExplorer

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        _ = pkg.BRFSSExplorer

    assert captured == []
