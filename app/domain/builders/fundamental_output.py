"""Domain builder for fundamental analysis output text."""

from __future__ import annotations

from typing import Any

from app.domain.builders.fundamental_output_impl import build_fundamental_output_text_impl


def build_fundamental_output_text(
    *,
    name: str,
    code4: str,
    master: dict[str, Any] | None,
    price: float | None,
    market_cap: float | None,
    market_snapshot: dict[str, Any] | None = None,
) -> str:
    """ドメイン層の出力生成エントリポイント。"""
    return build_fundamental_output_text_impl(
        name=name,
        code4=code4,
        master=master,
        price=price,
        market_cap=market_cap,
        market_snapshot=market_snapshot,
    )


__all__ = ["build_fundamental_output_text"]
