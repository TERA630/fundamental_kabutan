"""Web presentation helpers for Fundamental output."""

from __future__ import annotations

from dataclasses import dataclass
import re


TABLE_HEADINGS = {
    "■株価評価・資本効率",
    "■株探 通期業績推移",
    "■キャッシュフロー",
    "■四半期トレンド",
}


@dataclass(frozen=True)
class WebTextBlock:
    kind: str
    text: str


@dataclass(frozen=True)
class WebTableBlock:
    kind: str
    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    note: str | None = None


WebOutputBlock = WebTextBlock | WebTableBlock


def build_fundamental_web_blocks(output: str) -> list[WebOutputBlock]:
    blocks: list[WebOutputBlock] = []
    for section in _split_sections(output):
        if not section:
            continue
        heading = section[0]
        if heading == "■株価評価・資本効率":
            blocks.append(_parse_pipe_table(section, title=heading))
        elif heading == "■株探 通期業績推移":
            blocks.append(_parse_forecast_table(section))
        elif heading == "■キャッシュフロー":
            blocks.append(_parse_pipe_table(section, title=heading, fallback_headers=("年度", "営業CF", "FCF", "投資積極性", "現金残高")))
        elif heading == "■四半期トレンド":
            blocks.append(_parse_quarterly_trend_table(section))
        else:
            blocks.append(WebTextBlock(kind="text", text="\n".join(section).strip()))
    return blocks


def _split_sections(output: str) -> list[list[str]]:
    sections: list[list[str]] = []
    current: list[str] = []
    preface: list[str] = []

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if line.startswith("■"):
            if current:
                sections.append(_trim_blank_lines(current))
            elif preface:
                sections.append(_trim_blank_lines(preface))
                preface = []
            current = [line]
            continue
        if current:
            current.append(line)
        else:
            preface.append(line)

    if current:
        sections.append(_trim_blank_lines(current))
    elif preface:
        sections.append(_trim_blank_lines(preface))
    return [section for section in sections if section]


def _trim_blank_lines(lines: list[str]) -> list[str]:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def _parse_pipe_table(section: list[str], *, title: str, fallback_headers: tuple[str, ...] | None = None) -> WebTableBlock:
    data_lines = [line.strip() for line in section[1:] if line.strip()]
    if not data_lines:
        return WebTableBlock(kind="table", title=title, headers=("項目",), rows=(("N/A",),))

    header_line = data_lines[0]
    headers = _split_pipe_line(header_line)
    rows = tuple(tuple(_split_pipe_line(line)) for line in data_lines[1:])

    if len(headers) == 1 and fallback_headers is not None:
        headers = list(fallback_headers)
    if not rows:
        rows = (("N/A",),)
    return WebTableBlock(kind="table", title=title, headers=tuple(headers), rows=_normalize_rows(tuple(headers), rows))


def _parse_forecast_table(section: list[str]) -> WebTableBlock:
    note = section[1].strip() if len(section) > 1 and section[1].startswith("株探ソース:") else None
    data_lines = [line.strip() for line in section[3 if note else 2 :] if line.strip()]
    headers = ("年度", "売上", "営業益(営業利益率)", "経常益(経常利益率)", "最終益", "1株益", "1株配当")
    rows: list[tuple[str, ...]] = []
    for line in data_lines:
        if line == "データーが取得できません":
            rows.append(("データーが取得できません",))
            continue
        cells = tuple(part for part in re.split(r"\s{2,}", line) if part)
        rows.append(cells if cells else (line,))
    return WebTableBlock(kind="table", title=section[0], headers=headers, rows=_normalize_rows(headers, tuple(rows)), note=note)


def _parse_quarterly_trend_table(section: list[str]) -> WebTableBlock:
    headers = ("四半期", "売上", "営業利益率", "昨年同期比", "修正一株益")
    rows: list[tuple[str, ...]] = []
    for line in section[2:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("N/A"):
            rows.append((stripped,))
            continue
        label, sep, rest = stripped.partition("　")
        values = _split_pipe_line(rest if sep else stripped)
        rows.append((label, *values) if sep else tuple(values))
    if not rows:
        rows.append(("N/A",))
    return WebTableBlock(kind="table", title=section[0], headers=headers, rows=_normalize_rows(headers, tuple(rows)))


def _split_pipe_line(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _normalize_rows(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...]) -> tuple[tuple[str, ...], ...]:
    normalized: list[tuple[str, ...]] = []
    width = len(headers)
    for row in rows:
        if len(row) == width:
            normalized.append(row)
        elif len(row) < width:
            normalized.append((*row, *([""] * (width - len(row)))))
        else:
            normalized.append((*row[: width - 1], " ".join(row[width - 1 :])))
    return tuple(normalized)


__all__ = ["WebOutputBlock", "WebTableBlock", "WebTextBlock", "build_fundamental_web_blocks"]
