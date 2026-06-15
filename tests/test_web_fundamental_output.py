from app.presentation.web_fundamental_output import WebTableBlock, WebTextBlock, build_fundamental_web_blocks
from app.web import build_copy_text


def _table_by_title(output: str, title: str) -> WebTableBlock:
    blocks = build_fundamental_web_blocks(output)
    for block in blocks:
        if isinstance(block, WebTableBlock) and block.title == title:
            return block
    raise AssertionError(f"table block not found: {title}")


def test_build_fundamental_web_blocks_tables_valuation_rows():
    output = """【Test (1234)】

■株価評価・資本効率
年度|2025年(実績)|2026年(予)
PER|20.0倍|18.0倍
PBR|2.00倍|N/A
ROE|20.00%|N/A
ROIC|14.00%|N/A
配当利回り|1.00%|1.20%
FCF Yield|2.00%|N/A
"""

    table = _table_by_title(output, "■株価評価・資本効率")

    assert table.headers == ("年度", "2025年(実績)", "2026年(予)")
    assert ("PER", "20.0倍", "18.0倍") in table.rows
    assert ("FCF Yield", "2.00%", "N/A") in table.rows


def test_build_fundamental_web_blocks_keeps_scoring_text_out_of_valuation_table():
    output = """■株価評価・資本効率
年度|2025年(実績)
PER|20.0倍
PBR|2.00倍
ROE|20.00%
配当利回り|1.00%
FCF Yield|2.00%

Quality 45点 Growth 20点 Valuation 8点

[Quality]
ROIC         18.20%(B)
ルール注記:
- なし
"""

    blocks = build_fundamental_web_blocks(output)
    table = next(block for block in blocks if isinstance(block, WebTableBlock))
    text = next(block for block in blocks if isinstance(block, WebTextBlock))

    assert ("Quality 45点 Growth 20点 Valuation 8点",) not in table.rows
    assert "Quality 45点 Growth 20点 Valuation 8点" in text.text
    assert "ルール注記:" in text.text


def test_build_fundamental_web_blocks_tables_forecast_rows():
    output = """■株探 通期業績推移
株探ソース: HTML
　　　　　　売上　営業益(営業利益率)　経常益(経常利益率)　最終益　1株益　1株配当
2025/03       10.0億       1.0億(10.0%)       0.9億(9.0%)       0.8億     10.0円     20.0円
2026/03(予)   12.0億       1.2億(10.0%)       1.0億(8.3%)       0.9億     12.0円     22.0円
"""

    table = _table_by_title(output, "■株探 通期業績推移")

    assert table.note == "株探ソース: HTML"
    assert table.headers[0] == "年度"
    assert ("2025/03", "10.0億", "1.0億(10.0%)", "0.9億(9.0%)", "0.8億", "10.0円", "20.0円") in table.rows


def test_build_fundamental_web_blocks_tables_cashflow_rows():
    output = """■キャッシュフロー
年度 | 営業CF | FCF | 投資積極性 | 現金残高
2024 | 150 | 80 | 46.7% | 350
2025 | 180 | 100 | 44.4% | 420
"""

    table = _table_by_title(output, "■キャッシュフロー")

    assert table.headers == ("年度", "営業CF", "FCF", "投資積極性", "現金残高")
    assert ("2024", "150", "80", "46.7%", "350") in table.rows


def test_build_fundamental_web_blocks_tables_quarterly_trend_rows():
    output = """■四半期トレンド
　　　売上|営業利益率|昨年同期比|修正一株益
2025.3　10.0億|10.0%|-10%|10.0円
2025.6　N/A|N/A||N/A
"""

    table = _table_by_title(output, "■四半期トレンド")

    assert table.headers == ("四半期", "売上", "営業利益率", "昨年同期比", "修正一株益")
    assert ("2025.3", "10.0億", "10.0%", "-10%", "10.0円") in table.rows
    assert ("2025.6", "N/A", "N/A", "", "N/A") in table.rows


def test_build_copy_text_keeps_plain_output_for_copy_and_download():
    output = "■四半期トレンド\n2025.3　10.0億|10.0%|-10%|10.0円"

    assert build_copy_text("機関投資サマリ", output) == f"機関投資サマリ\n\n{output}"
