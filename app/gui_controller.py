"""Backward-compatible import surface for the shared application service."""

from __future__ import annotations

from app.services.analysis_application_service import (
    AnalysisApplicationService,
    FUNDAMENTAL_SUMMARY_FILENAME_PREFIX,
    TECHNICAL_SUMMARY_FILENAME_PREFIX,
    build_default_fundamental_service,
    build_default_market_data_service,
    build_default_technical_service,
    build_fundamental_summary_filename,
    build_technical_summary_filename,
)

FundamentalGuiController = AnalysisApplicationService

__all__ = [
    "FUNDAMENTAL_SUMMARY_FILENAME_PREFIX",
    "TECHNICAL_SUMMARY_FILENAME_PREFIX",
    "AnalysisApplicationService",
    "FundamentalGuiController",
    "build_default_fundamental_service",
    "build_default_market_data_service",
    "build_default_technical_service",
    "build_fundamental_summary_filename",
    "build_technical_summary_filename",
]
