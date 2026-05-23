import warnings

from app.data.kabutan_repository import parse_kabutan_cashflow_rows


def test_parse_kabutan_cashflow_rows_extracts_cash_stock_without_whitespace():
    html = """
    <table>
      <tr>
        <th>決算期</th><th>フリーCF<br>(百万円)</th><th>営業CF<br>(百万円)</th><th>投資CF<br>(百万円)</th><th>財務CF<br>(百万円)</th><th>現金等残高<br>(百万円)</th>
      </tr>
      <tr><th>2025.03</th><td>100</td><td>120</td><td>-20</td><td>10</td><td>300</td></tr>
    </table>
    """

    rows = parse_kabutan_cashflow_rows(html)

    assert len(rows) == 1
    assert rows[0].cash_stock == 300


def test_parse_kabutan_cashflow_rows_extracts_cash_stock_with_internal_whitespace():
    html = """
    <table>
      <tr>
        <th>決算期</th><th>フリーCF<br>(百万円)</th><th>営業CF<br>(百万円)</th><th>投資CF<br>(百万円)</th><th>財務CF<br>(百万円)</th><th>現金等 残高<br>(百万円)</th>
      </tr>
      <tr><th>2025.03</th><td>100</td><td>120</td><td>-20</td><td>10</td><td>300</td></tr>
    </table>
    """

    rows = parse_kabutan_cashflow_rows(html)

    assert len(rows) == 1
    assert rows[0].cash_stock == 300


def test_parse_kabutan_cashflow_rows_warns_when_cash_stock_column_missing():
    html = """
    <table>
      <tr>
        <th>決算期</th><th>フリーCF<br>(百万円)</th><th>営業CF<br>(百万円)</th><th>投資CF<br>(百万円)</th><th>財務CF<br>(百万円)</th>
      </tr>
      <tr><th>2025.03</th><td>100</td><td>120</td><td>-20</td><td>10</td></tr>
    </table>
    """

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        rows = parse_kabutan_cashflow_rows(html)

    assert len(rows) == 1
    assert rows[0].cash_stock is None
    assert any("現金等残高列" in str(w.message) for w in captured)
