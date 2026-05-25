# 四半期表示仕様（確定）

## 1. 目的
四半期ごとの業績を、以下のカラムで安定表示する。

- 売上高
- 営業益（前年同期比%）
- 経常益
- 最終益
- 修正1株益（前年同期比%）
- 売上損益率

表示イメージ（行＝四半期）:

- 2025.3
- 2025.6
- 2025.9
- 2025.12
- 2026.3

---

## 2. 確定仕様

1. **対象期間数**
   - 直近5四半期固定で表示する。
   - 取得不可の値は内部表現 `N/A` とする。

2. **四半期データの種別**
   - 四半期表示は実績のみを対象とする（予想は除外）。

3. **行ラベル**
   - 行見出しは `YYYY.M`（例: `2025.3`）とする。

4. **表示位置**
   - `■株探 通期業績推移` ブロックの後に `■四半期業績推移` を追加する。

5. **前年同期比（営業益/EPS）**
   - 比較対象は `Q(fiscal_year-1, same quarter)` とする。
   - `quarter` は `fiscal_end_month` 相対で解決する（非3月/非12月決算に対応）。
   - 計算式は `((current - prev) / abs(prev)) * 100`。
   - 初年度（比較元なし）・欠損・0除算は `N/A`。
   - 表示時は前年同期比 `N/A` を空白（ブランク）にする。

6. **売上損益率（営業損益率）**
   - HTML に値がある場合はその値を優先表示。
   - HTML 値がない場合は計算補完する。
     - 原則: `営業益 / 売上 * 100`
     - 営業益が欠損の場合のみ: `経常益 / 売上 * 100`
   - 欠損・0除算時は `N/A`。

7. **絶対値と計算値の欠損表示**
   - 売上/営業益/経常益/最終益/EPS/売上損益率などの絶対値・率は欠損時 `N/A`。
   - YoY などの比較計算値は欠損時に空白表示。

8. **分母の符号**
   - 前年同期比の分母は絶対値 `abs(prev)` を採用する。

---

## 3. レイヤー別責務

### 3.1 Domain（純ロジック）

- `QuarterlyActual`（生データ）
  - `fiscal_year: int`
  - `quarter_end_month: int | None`（任意月）
  - `quarter: Quarter | None`（`fiscal_end_month` 相対で解決）
  - `sales / operating_profit / ordinary_profit / final_profit / revised_eps / operating_margin`

- `QuarterlyMetricRow`（表示向け構造化データ）
  - `fiscal_year / quarter_end_month / quarter`
  - `sales / operating_profit / ordinary_profit / final_profit / revised_eps`
  - `operating_profit_yoy_pct / revised_eps_yoy_pct / operating_margin_pct`

- Domain Policy
  - 前年同期比計算
  - 売上損益率補完
  - 欠損処理

### 3.2 UseCase（アプリ固有ルール）

- `BuildQuarterlyFinancialTableUseCase`
  - 入力: 四半期実績行
  - 処理:
    1. `quarter` 解決
    2. 時系列整列
    3. 直近5四半期抽出
    4. YoY / 売上損益率計算
  - 出力: `tuple[QuarterlyMetricRow, ...]`

### 3.3 Data/Repository（I/O隠蔽）

- 四半期テーブルを HTML から抽出して `QuarterlyActual` へ正規化する。
- `fiscal_end_month` は通期業績テーブル由来を優先して解決する。
  - 通期が取れない場合のみ四半期側の月情報へフォールバックする。

### 3.4 Presentation（ViewModel/Presenter）

- カラム順:
  1. 売上高
  2. 営業益(前年同期比%)
  3. 経常益
  4. 最終益
  5. 修正1株益(前年同期比%)
  6. 売上損益率
- Builder は表示整形のみ担当し、計算・I/Oは行わない。

---

## 4. テスト方針（Phase 3）

1. **スナップショット固定**
   - 四半期ブロックのヘッダ/行フォーマット/空白/N/A の整形を固定化。

2. **境界ケース**
   - 非標準決算月（例: 9月決算）
   - 初年度YoY（比較元なし）
   - 営業益欠損時の経常益フォールバック

3. **統合ケース**
   - 通期ブロック後に四半期ブロックが出ること。
   - 直近5四半期のみ表示されること。

---

## 5. 段階導入ステータス

- **Phase 1**: Domain Policy / UseCase 追加（完了）
- **Phase 2**: Presenter 接続と表示切替（完了）
- **Phase 3-1**: 表示仕様の固定化着手（完了）
- **Phase 3-2/3**: スナップショット網羅拡張・境界ケース固定（進行対象）
