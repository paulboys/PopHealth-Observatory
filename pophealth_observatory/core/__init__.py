"""Core interface contracts.

Public exports:
- DataProvider
- AnalysisRunner
- ReportGenerator
- IndicatorProvider
- NHANESDataProviderAdapter
- NHANESAnalysisAdapter
"""

from .nhanes_adapters import NHANESAnalysisAdapter, NHANESDataProviderAdapter
from .protocols import AnalysisRunner, DataProvider, IndicatorProvider, ReportGenerator

__all__ = [
    "DataProvider",
    "AnalysisRunner",
    "ReportGenerator",
    "IndicatorProvider",
    "NHANESDataProviderAdapter",
    "NHANESAnalysisAdapter",
]
