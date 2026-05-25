# 四半期表示仕様（提案）

## 1. 目的
四半期ごとの業績を、以下のような横持ちカラムで安定表示する。

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

## 2. 実装可否
**実装可能**。現行のクリーンアーキテクチャ構成を維持しつつ、
ドメイン層に四半期表示用の Value Object / Policy / UseCase を追加すれば対応できる。

---

## 3. レイヤー別の設計

### 3.1 Domain（純ロジック）

#### 追加モデル案
`app/domain/models/quarterly_financials.py` を拡張、または同階層に専用 VO を追加:

- `QuarterKey`
  - `fiscal_year: int`
  - `quarter_end_month: int | None`（任意月。3/6/9/12 に固定しない）
  - `quarter: Quarter | None`（`fiscal_end_month` 相対で解決）
- `QuarterlyMetricRow`
  - `fiscal_year: int`
  - `quarter_end_month: int | None`
  - `quarter: Quarter`
  - `sales: int | None`
  - `operating_profit: int | None`
  - `ordinary_profit: int | None`
  - `final_profit: int | None`
  - `revised_eps: float | None`
  - `operating_yoy_pct: float | None`
  - `eps_yoy_pct: float | None`
  - `sales_profit_margin_pct: float | None`

#### 追加ポリシー案
`app/domain/policies/quarterly_growth_metrics.py` を中心に、以下を純関数で定義。

1. **前年同期比（営業益）**
   - 対象四半期 `Q(fiscal_year, quarter)` に対して `Q(fiscal_year-1, same quarter)` を比較元にする。
   - `quarter` は決算月相対で解決する（非3月/非12月決算に対応）。
   - `((current - prev) / abs(prev)) * 100`
   - `prev` が `None` または `0` の場合は `None`。

2. **前年同期比（修正1株益）**
   - 上記と同様の比較。

3. **営業損益率（売上損益率カラム）**
   - HTML に営業損益率の値が存在する場合は、その値を優先利用する。
   - HTML に値が無い場合は計算で補完する。
   - 補完式は原則 `operating_profit / sales * 100`。
   - `operating_profit` が欠損の場合のみ `ordinary_profit / sales * 100` を代替採用する。
   - 欠損・0除算時は `None`。

4. **期間ソート**
   - `year ASC, month ASC`。

> 注: 「売上損益損益率」は誤記の可能性があるため、実装名は「売上損益率」へ統一し、
> UIラベルだけは要件に合わせて切替可能にする。

---

### 3.2 UseCase（アプリ固有ルール）

`app/domain/usecases` に四半期表示専用 UseCase を追加:

- `BuildQuarterlyFinancialTableUseCase`
  - 入力:
    - 銘柄コード
    - 取得済み四半期データ列（Repository 取得結果）
  - 処理:
    1. 対象四半期を整列
    2. 前年同期対応を解決
    3. YoY / 売上損益率を計算
    4. `QuarterlyMetricRow` の配列を返却

UseCase は UI 文字列を返さず、**表示に必要な構造化データのみ**返す。

---

### 3.3 Data/Repository（I/O隠蔽）

既存 Repository 層で四半期レコードの取得を提供:

- 取得元が HTML の場合:
  - 四半期テーブルから `year, month, sales, operating_profit, ordinary_profit, final_profit, revised_eps` を抽出。
- 取得元が別 API の場合:
  - 同じドメイン DTO に正規化して返す。

Repository IF 例:

- `QuarterlyFinancialRepository.fetch_quarterly_rows(code4: str) -> tuple[QuarterlyRawRow, ...]`

---

### 3.4 Presentation（ViewModel/Presenter）

`app/presenters.py` または `app/gui_view_model.py` で、UseCase の戻り値を表形式に整形。

- カラム順（要求どおり）:
  1. 売上高
  2. 営業益(前年同期比%)
  3. 経常益
  4. 最終益
  5. 修正1株益(前年同期比%)
  6. 売上損益率

- 行見出し:
  - `YYYY.M`（例: `2025.3`）

- 表示フォーマット:
  - 欠損値: 取得不可は内部値 `N/A` として保持する。
  - 前年同期比（営業益/EPS）の `N/A` は、表示時は空白（ブランク）にする運用を許可する。
  - 比率: `+x.x%` / `-x.x%`
  - 金額: 既存仕様の億円換算ルールに揃えるか、四半期は百万円単位で統一するかを要件確定

---

## 4. 確定仕様（レビュー反映）

1. **対象期間数**
   - 直近5四半期固定で表示する。
   - 取得不可の値は内部表現 `N/A` とする。

2. **前年同期比（営業益/EPS）**
   - 初年度（比較元となる前年同期が無い行）は比較 `N/A`。
   - 表示時は `N/A` を空白（ブランク）にしてよい。

3. **分母の符号**
   - 前年同期比の分母は絶対値 `abs(prev)` を採用する。

4. **営業損益率（売上損益率カラム）**
   - HTML からパースできる場合はその値を優先表示。
   - 計算補完時は `営業益 / 売上`。
   - 営業益が無い場合のみ `経常益 / 売上` を代替利用。

5. **四半期データの種別**
   - 四半期表示は実績のみを対象とする（予想は除外）。

---

## 5. テスト計画（先行して追加推奨）

1. `tests/test_quarterly_growth_metrics.py`
   - 前年同期比の基本ケース
   - 欠損・0除算ケース
   - 負値ケース

2. `tests/test_usecase_financial_metric_rows.py`
   - 行生成順（2025.3 → 2026.3）
   - カラム値のマッピング

3. `tests/test_presenters_kabutan_output.py`
   - 表示文字列のヘッダ順
   - `N/A` と `%` の整形確認

---

## 6. 段階導入案

- **Phase 1**: Domain Policy / UseCase の追加（UI未接続）
- **Phase 2**: Presenter 接続と表示切替
- **Phase 3**: 既存表示との統合、スナップショットテスト固定

