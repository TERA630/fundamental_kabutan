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

---

## 7. 追加提案：成長性ブロック（5.3 / 5.6）をドメイン層で実装する設計

結論：**実装可能**。ただし、表示仕様を安定して満たすために「比較対象行の選定ルール」をValue Objectとして分離する。

### 7.1 追加するドメインルール

1. **成長率計算対象行の前処理（比較系列の確定）**
   - 入力：株探行 `all_rows`（年・実績/予想・EPS・営業利益を含む）
   - ルール：
     - 年次昇順で走査する。
     - 同一年に `実績` と `予想` が共存する場合、**成長率計算の系列には同年予想を含めない**。
     - それ以外の年は、当該年の代表行（通常は実績、実績が無ければ予想）を採用する。
   - 出力：比較系列 `growth_rows`。

2. **営業利益成長率(%)**
   - `op_growth[i] = ((op[i] - op[i-1]) / abs(op[i-1])) * 100`
   - `i=0` は比較元が無いため `N/A`。
   - 前年値欠損・0のときは `N/A`。

3. **EPS成長率(%)（新仕様）**
   - 仕様文をそのまま採用：
     - `eps_growth[i] = (1 - (eps[i] - eps[i-1])) * 100`
   - `i=0` は `N/A`。
   - 前年EPS欠損時は `N/A`。

4. **EPS成長加速率(%)**
   - `eps_accel[i] = eps_growth[i] - eps_growth[i-1]`
   - `i=0` は `N/A`。
   - `eps_growth[i]` または `eps_growth[i-1]` が `N/A` の場合は `N/A`。

5. **成長性ブロック表示順（5.6）**
   1. 営業利益成長率
   2. EPS成長率
   3. EPS成長加速率

### 7.2 ドメイン層の責務分割（クリーンアーキテクチャ準拠）

- `app/domain/policies/growth_rows.py`（新規）
  - 比較系列 `growth_rows` の構築責務のみ。
  - UI/Repository非依存。

- `app/domain/policies/growth_metrics.py`（新規）
  - 営業利益成長率、EPS成長率、EPS成長加速率の純計算。
  - 欠損時 `None` を返す。

- `app/domain/builders/fundamental_output_impl.py`（既存拡張）
  - 上記policyを呼び、表示文字列（`N/A`/`+xx.x%`）へ整形。

### 7.3 追加するValue Object案

- `GrowthPoint`
  - `year: int`
  - `operating_growth_pct: float | None`
  - `eps_growth_pct: float | None`
  - `eps_acceleration_pct: float | None`

- `GrowthBlock`
  - `points: tuple[GrowthPoint, ...]`
  - Builderは `GrowthBlock` を受けて表示行を作るだけにする。

### 7.4 実装時の注意点

- **同年 実績→予想の比較禁止**は、計算関数内部ではなく、必ず比較系列の前処理で保証する。
- 5.3のEPS式は一般的な前年比式と異なるため、domain_specに「仕様固定式」であることを明記する。
- `%`付き表示はBuilder責務、計算値はdomain policyで数値として保持する。

### 7.5 テスト観点（ドメイン中心）

1. 同年に実績/予想があるケースで、同年予想が比較系列から除外されること。
2. 先頭行が常に `N/A` になること。
3. 欠損・0除算相当で `N/A` になること。
4. EPS成長加速率が「当年EPS成長率 - 前年EPS成長率」であること。
5. 成長性ブロックの表示順が仕様通りであること。

### 7.6 段階導入案

- Phase 1: policy関数 + 単体テスト追加（表示は未接続でも可）
- Phase 2: builderへ接続し、成長性ブロック出力を有効化
- Phase 3: スナップショット差分テストで表示フォーマット固定
