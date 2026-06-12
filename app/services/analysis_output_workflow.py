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
        save_output_cache_for_today: Callable[[dict[str, str]], None],
        fetch_institutional_summary_text: Callable[..., str],
    ):
        self.fetch_technical_output = fetch_technical_output
        self.fetch_analysis_output = fetch_analysis_output
        self.save_output_cache_for_today = save_output_cache_for_today
        self.fetch_institutional_summary_text = fetch_institutional_summary_text

    def fetch_output_for_mode(
        self,
        *,
        name: str,
        code4: str,
        mode: str,
        output_cache: dict[str, str],
        kabutan_html_dir: Path | None = None,
        output_cache_key: str | None = None,
    ) -> AnalysisOutputResult:
        if mode == "technical":
            output = self.fetch_technical_output(name=name, code4=code4)
        else:
            if output_cache_key is None:
                raise ValueError("output_cache_key is required for fundamental output")
            output = self.fetch_analysis_output(
                name=name,
                code4=code4,
                output_cache=output_cache,
                output_cache_key=output_cache_key,
                kabutan_html_dir=kabutan_html_dir,
            )
            self.save_output_cache_for_today(output_cache)

        institutional_summary = self.fetch_institutional_summary_text(
            name=name,
            code4=code4,
            kabutan_html_dir=kabutan_html_dir,
        )
        return AnalysisOutputResult(output=output, institutional_summary=institutional_summary)


__all__ = ["AnalysisOutputResult", "AnalysisOutputWorkflow"]
