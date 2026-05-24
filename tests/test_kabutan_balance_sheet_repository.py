import pytest

from app.data.kabutan_repository import parse_kabutan_balance_sheet_rows


def test_parse_kabutan_balance_sheet_rows_parses_help_label_headers():
    html = """
    <div id="wrapper_main"><div id="container"><div id="main"><div id="finance_box">
      <table>
        <tr>
          <th>決算期</th>
          <th><span class="help-label">１株<br>純資産</span></th>
          <th><span class="help-label">自己資本<br>比率</span></th>
          <th>総資産<br>(百万円)</th>
          <th>自己資本<br>(百万円)</th>
          <th>剰余金<br>(百万円)</th>
          <th><span class="help-label">有利子<br>負債倍率</span><span class="help-icon"></span></th>
        </tr>
        <tr><th>2025.03</th><td>1,234.5</td><td>45.6</td><td>10,000</td><td>4,560</td><td>2,200</td><td>0.8</td></tr>
      </table>
    </div></div></div></div>
    """

    rows = parse_kabutan_balance_sheet_rows(html)

    assert len(rows) == 1
    assert rows[0].bps == 1234.5
    assert rows[0].equity_ratio == 45.6
    assert rows[0].total_assets == 10000
    assert rows[0].equity == 4560
    assert rows[0].retained_earnings == 2200
    assert rows[0].interest_bearing_debt_multiple == 0.8


def test_parse_kabutan_balance_sheet_rows_fallbacks_to_finance_box_selector():
    html = """
    <div id="finance_box">
      <table>
        <tr><th>決算期</th><th>1株純資産</th><th>自己資本比率</th><th>総資産</th><th>自己資本</th><th>剰余金</th></tr>
        <tr><th>2024.03</th><td>900.0</td><td>41.2</td><td>8,000</td><td>3,200</td><td>1,500</td></tr>
      </table>
    </div>
    """

    rows = parse_kabutan_balance_sheet_rows(html)

    assert len(rows) == 1
    assert rows[0].year == 2024
    assert rows[0].interest_bearing_debt_multiple is None


def test_parse_kabutan_balance_sheet_rows_prioritizes_coverage_then_rows_then_order():
    html = """
    <div id="finance_box">
      <table id="first">
        <tr><th>決算期</th><th>1株純資産</th><th>自己資本比率</th><th>総資産</th><th>自己資本</th></tr>
        <tr><th>2025.03</th><td>1,000</td><td>40.0</td><td>9,999</td><td>3,999</td></tr>
      </table>
      <table id="second">
        <tr><th>決算期</th><th>1株純資産</th><th>自己資本比率</th><th>総資産</th><th>自己資本</th><th>剰余金</th></tr>
        <tr><th>2025.03</th><td>1,111</td><td>44.0</td><td>10,111</td><td>4,444</td><td>2,222</td></tr>
      </table>
    </div>
    """

    rows = parse_kabutan_balance_sheet_rows(html)

    assert len(rows) == 1
    assert rows[0].bps == 1111.0
    assert rows[0].retained_earnings == 2222


def test_parse_kabutan_balance_sheet_rows_fills_none_for_missing_cells():
    html = """
    <div id="finance_box">
      <table>
        <tr><th>決算期</th><th>1株純資産</th><th>自己資本比率</th><th>総資産</th><th>自己資本</th><th>剰余金</th><th>有利子負債倍率</th></tr>
        <tr><th>2025.03</th><td>1,000</td><td>40.0</td><td>9,999</td><td>3,999</td></tr>
      </table>
    </div>
    """

    rows = parse_kabutan_balance_sheet_rows(html)

    assert len(rows) == 1
    assert rows[0].retained_earnings is None
    assert rows[0].interest_bearing_debt_multiple is None


def test_parse_kabutan_balance_sheet_rows_raises_when_no_header():
    html = """
    <div id="finance_box">
      <table>
        <tr><th>決算期</th><th>売上高</th></tr>
        <tr><th>2025.03</th><td>100</td></tr>
      </table>
    </div>
    """

    with pytest.raises(ValueError, match=r"BS\)テーブルのヘッダ"):
        parse_kabutan_balance_sheet_rows(html)
