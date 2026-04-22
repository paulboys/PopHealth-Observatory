"""Core interface contracts.

Public exports:
- DataProvider
- AnalysisRunner
- ReportGenerator
- IndicatorProvider
- NHANESDataProviderAdapter
- NHANESAnalysisAdapter
- NHANESReportAdapter
- NHANESValidationAdapter
"""

from .nhanes_adapters import NHANESAnalysisAdapter, NHANESDataProviderAdapter
from .nhanes_reporting_adapters import NHANESReportAdapter, NHANESValidationAdapter
from .protocols import AnalysisRunner, DataProvider, IndicatorProvider, ReportGenerator

__all__ = [
    "DataProvider",
    "AnalysisRunner",
    "ReportGenerator",
    "IndicatorProvider",
    "NHANESDataProviderAdapter",
    "NHANESAnalysisAdapter",
    "NHANESReportAdapter",
    "NHANESValidationAdapter",
]
