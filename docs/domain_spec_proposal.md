# ドメイン層仕様提案（株探表示寄せ）

## 1. 目的
表示フォーマット（銘柄ヘッダ / 株価・指標 / 実績＋今期来期予想テーブル）を、
**データ取得ロジックと分離してドメイン層で一貫生成できる状態**にする。

---

## 2. 責務分離（ドメイン層内）

### 2.1 モデル（`app/domain/models`）
表示に必要な意味的データを保持し、文字列整形は持たない。

#### `StockProfile`
- `code4: str`
- `name: str`
- `industry_name: str | None`
- `market_cap_billion_yen: float | None`
- `size_class_label: str | None` 例: `中型主役`

#### `PriceSnapshot`
- `price_yen: float | None`
- `as_of_date: date | None`

#### `ValuationMetrics`
- `per: float | None`
- `eps_yen: float | None`
- `dividend_yield_pct: float | None`

#### `PeriodFundamentalRow`
- `period_kind: Literal["actual", "forecast"]`
- `fiscal_year: int`
- `sales_hundred_million_yen: float | None`
- `operating_profit_hundred_million_yen: float | None`
- `ordinary_profit_hundred_million_yen: float | None`
- `final_profit_hundred_million_yen: float | None`
- `eps_yen: float | None`
- `dividend_yen: float | None`
- `operating_margin_pct: float | None`
- `ordinary_margin_pct: float | None`
- `operating_growth_yoy_pct: float | None`

#### `FundamentalDisplaySnapshot`
- `profile: StockProfile`
- `price: PriceSnapshot`
- `metrics_2025_actual: ValuationMetrics | None`
- `metrics_2026_forecast: ValuationMetrics | None`
- `metrics_2027_forecast: ValuationMetrics | None`
- `rows: tuple[PeriodFundamentalRow, ...]`  
  （表示順で 2023実績, 2024実績, 2025実績, 2026予想, 2027予想）

---

### 2.2 リポジトリ境界（`app/domain/usecases/*.py`のProtocol）
取得責務はPortに閉じ込める。

#### `FundamentalRepositoryPort`
- `fetch_fundamental_rows(code4: str, years: tuple[int, ...]) -> list[PeriodFundamentalRowSource]`
- `fetch_stock_profile(code4: str) -> StockProfileSource`

#### `MarketRepositoryPort`
- `fetch_price_snapshot(code4: str) -> PriceSnapshot`

#### `ValuationRepositoryPort`
- `fetch_valuation_metrics(code4: str, fiscal_year: int, kind: str) -> ValuationMetrics`

> 命名ポリシーに合わせ、取得は `fetch_*` で統一。

---

### 2.3 ユースケース（`app/domain/usecases`）

#### `BuildFundamentalDisplaySnapshotUseCase`
責務：複数リポジトリから取得し、表示可能なドメインスナップショットを作る。

- 入力: `code4: str`, `base_year: int`
- 出力: `FundamentalDisplaySnapshot`
- 手順:
  1. `fetch_stock_profile`
  2. `fetch_price_snapshot`
  3. `fetch_fundamental_rows`（実績3年＋予想2年）
  4. `calc_*` で率系を補完（営業利益率、経常利益率、前年比営業成長率）
  5. 評価指標 `fetch_valuation_metrics` を年別セット

#### `CalculateFundamentalMetricsUseCase`（分離案）
責務：数値計算のみ（純関数寄り）。

- `calc_operating_margin_pct(row)`
- `calc_ordinary_margin_pct(row)`
- `calc_operating_growth_yoy_pct(current, previous)`
- `calc_per_times(price_yen, revised_eps_yen)`
- `calc_dividend_yield_pct(price_yen, revised_dividend_yen)`

#### 年次評価指標の算出方針
- 実績・今期予想・来期予想の各 `PeriodFundamentalRow` を基点に `ValuationMetrics` を算出する。
- `ValuationMetrics.per` と `ValuationMetrics.dividend_yield_pct` は、外部API値ではなくドメイン計算値を優先する。
- 行データ欠損時は `None` を保持し、Builderで `N/A` 表示する。

#### `GradeCompanyScaleUseCase`（任意）
責務：時価総額→サイズラベル判定。

- `grade_company_scale(market_cap_billion_yen) -> str | None`

---

### 2.4 出力生成（Builder）
表示文言組み立てはBuilderに限定し、ユースケースは構造化データまで。

#### `build_fundamental_display_text(snapshot: FundamentalDisplaySnapshot) -> str`
- ヘッダブロック（銘柄名、コード、業種、時価総額）
- 株価ブロック
- 指標ブロック（2025実績 / 2026期末予想 / 2027来季予想）
  - `PER：{base_year}年実績 ... ／ {base_year+1}年末予想 ... ／ {base_year+2}年来期予想 ...`
  - `配当利回り：{base_year}年実績 ... ／ {base_year+1}年末予想 ... ／ {base_year+2}年来季予想 ...`
- 実績・予想テーブル

> 命名ポリシーに合わせ、出力生成は `build_*`。

---

## 3. 例外・欠損の扱い
- モデル上は欠損を `None` に統一。
- Builderでのみ `N/A` へ変換。
- 年次行が不足した場合でも `rows` は存在する行だけ保持し、
  GUI側で固定行補完が必要ならPresenter/GUIViewModelで実施。

---

## 4. 既存実装への段階的適用
1. 既存 `KabutanForecastRow` を `PeriodFundamentalRow` に寄せる（互換期間は変換関数で吸収）。
2. `FetchKabutanForecastUseCase` は取得専用に残し、
   新規 `BuildFundamentalDisplaySnapshotUseCase` で統合。
3. `app/domain/builders/kabutan_output.py` から表示整形責務を
   新Builder（`build_fundamental_display_text`）へ段階移管。

---

## 5. 受け入れ基準（ドメイン層）
- ユースケースはGUI依存（Tkinterや文字色など）を持たない。
- BuilderはI/O（HTTP、ファイル読込）を行わない。
- `fetch_*`, `calc_*`, `grade_*`, `build_*` 命名が守られている。
- 同一入力スナップショットに対して、Builder出力は決定的である。
