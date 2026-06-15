"""Workflow for fetching analysis output for UI modes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class AnalysisOutputResult:
    output: str
    institutional_summary: str


class AnalysisOutputWorkflow:
    def __init__(
        self,
        *,
        fetch_technical_output: Callable[..., str],
        fetch_analysis_output: Callable[..., str],
        fetch_institutional_summary_text: Callable[..., str],
    ):
        self.fetch_technical_output = fetch_technical_output
        self.fetch_analysis_output = fetch_analysis_output
        self.fetch_institutional_summary_text = fetch_institutional_summary_text

    def fetch_output_for_mode(
        self,
        *,
        name: str,
        code4: str,
        mode: str,
        kabutan_html_dir: Path | None = None,
    ) -> AnalysisOutputResult:
        if mode == "technical":
            output = self.fetch_technical_output(name=name, code4=code4)
        else:
            output = self.fetch_analysis_output(
                name=name,
                code4=code4,
                kabutan_html_dir=kabutan_html_dir,
            )

        institutional_summary = self.fetch_institutional_summary_text(
            name=name,
            code4=code4,
            kabutan_html_dir=kabutan_html_dir,
        )
        return AnalysisOutputResult(output=output, institutional_summary=institutional_summary)


__all__ = ["AnalysisOutputResult", "AnalysisOutputWorkflow"]
