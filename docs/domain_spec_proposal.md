# ドメイン層仕様提案（現行方針）

## 1. 目的
表示フォーマット（銘柄ヘッダ / 株価・指標 / 株探の通期業績推移）を、
**J-Quants 由来の財務データ構造に依存せず**、現行の取得元に合わせてドメイン層で一貫生成できる状態にする。

---

## 2. 現行データソース

### 2.1 yFinance
- 株価
- 時価総額
- PBR
- ROE
- 業種

### 2.2 株探HTML
- 通期の売上高
- 営業益
- 経常益
- 最終益
- 修正1株益
- 1株配当
- 実績/予想区分

---

## 3. 現行ドメインモデル

### 3.1 `KabutanForecastRow`
株探HTMLから取得した通期業績の1行を表す。

- `period_label: str`
- `year: int`
- `month: int`
- `section: str`（`実績` / `予想`）
- `sales: int | None`
- `operating_profit: int | None`
- `ordinary_profit: int | None`
- `final_profit: int | None`
- `revised_eps: float | None`
- `dividend: float | None`

### 3.2 `KabutanForecastPair`
表示・指標計算に使う複数年分の株探行をまとめる。

- `previous2_actual: KabutanForecastRow | None`
- `previous_actual: KabutanForecastRow | None`
- `current_actual: KabutanForecastRow | None`
- `current_forecast: KabutanForecastRow`
- `next_forecast: KabutanForecastRow | None`
- `all_rows: tuple[KabutanForecastRow, ...]`

---

## 4. ユースケース方針

### 4.1 `FundamentalAnalysisService`
責務：yFinanceスナップショットと株探HTML行を取得し、Presenterへ渡す。

- yFinance値は `fetch_yfinance_snapshot` から取得する。
- 株探業績は `FetchKabutanForecastUseCase` / `KabutanForecastRepository` から取得する。
- J-Quants の `summary_rows`、FY/四半期データ、J-Quants形式の財務指標計算には依存しない。

### 4.2 `FetchKabutanForecastUseCase`
責務：株探の通期業績行取得をリポジトリへ委譲する。

- HTMLフォルダ指定時はローカルHTMLを優先する。
- 既定ではWebフォールバックを行わない。

---

## 5. 出力生成方針

### 5.1 基本出力
`build_fundamental_output_text` は、銘柄名・株価・時価総額・PBR・ROE・業種と、株探行から算出したPER/配当利回りを生成する。

### 5.2 株探セクション
`build_kabutan_forecast_output` は、株探の通期業績推移セクションを生成する。

- BuilderはI/O（HTTP、ファイル読込）を行わない。
- 表示整形はBuilderに閉じ込める。
- 欠損値は表示時に `N/A` または仕様上の欠損メッセージへ変換する。

---

## 6. 廃止済み方針
- J-Quants由来の財務指標計算モデルは使用しない。
- `summary_rows` は使用しない。
- FY/四半期データを前提にした表示補完は行わない。
- `FundamentalDisplaySnapshot` / `PeriodFundamentalRow` へ寄せる段階移管案は廃止する。
