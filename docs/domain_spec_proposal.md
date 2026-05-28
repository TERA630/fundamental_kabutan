# ドメイン層仕様

最終更新: 2026-05-28

本書は、データ取得後のモデル、UseCase、ドメイン計算、出力Builderの責務を定義する。
表示順・文言・数値表現は `docs/display_spec.md`、rankCF 採点仕様は `docs/rankCF_spec.md` を正とする。

---

## 1. 責務境界

依存方向:

- GUI / Presentation → UseCase → Domain
- Data / Infrastructure は UseCase に注入される Port 実装として接続する。

各層の責務:

| 層 | 主な責務 | 主なファイル |
|----|---------|-------------|
| Data | 監視銘柄読み込み、yFinance取得、株探HTML解析、キャッシュ | `app/data/*.py` |
| Domain Model | 株探・CF・財務・四半期・スコアの入力/結果モデル | `app/domain/models/*.py` |
| Domain Policy | 成長率、CF、財務指標、rankCF などの純計算 | `app/domain/policies/*.py` |
| UseCase | Data Port を呼び出し、分析に必要な入力を組み立てる | `app/domain/usecases/*.py` |
| Builder / Presenter | Domain結果を表示DTOまたは出力テキストへ変換する | `app/domain/builders/*.py`, `app/presenters.py` |
| GUI | 画面部品、イベント、状態、ステータスメッセージ表示 | `app/gui*.py` |

禁止事項:

- Domain / UseCase は `tkinter` などの UI ライブラリを import しない。
- Data層は表示文言を組み立てない。
- 表示仕様上の `N/A` や本文行省略は Presentation / Builder 側で扱い、Domain Policy は `None` などの計算結果で返す。

---

## 2. データソース

### 2.1 yFinance

- 株価
- 時価総額
- PER
- PBR
- ROE
- 業種

### 2.2 株探HTML

- 通期業績
- CF実績
- 財務指標
- 四半期業績
- 実績/予想区分

既定ではローカルHTML優先・Webフォールバックなしとする。

---

## 3. 主要ドメインモデル

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

### 3.3 表示セクションDTO

`app/domain/models/display_sections.py` は、出力テキストの各ブロックを表すDTOを保持する。
DTOは表示に必要な値を運ぶだけで、データ取得やHTML解析を行わない。

---

## 4. UseCase

### 4.1 `FundamentalAnalysisService`

- yFinanceスナップショットと株探HTML行を取得する。
- CF / 成長性 / 財務 / 四半期 / rankCF に必要な入力を構築する。
- `calculate_cf_score()` を呼び、`CfScoringResult` を出力Builderへ渡す。
- J-Quants 由来の `summary_rows` や旧FY/四半期補完モデルには依存しない。

### 4.2 `FetchKabutanForecastUseCase`

- 株探の通期業績行取得をリポジトリへ委譲する。
- HTMLフォルダ指定時はローカルHTMLを優先する。

---

## 5. ドメイン計算ルール

### 5.1 成長率

- 比較系列は年次昇順で構築する。
- 同一年に実績行と予想行が存在する場合、成長率計算では同年予想を除外する。
- 営業利益成長率は `((current - previous) / abs(previous)) * 100`。
- EPS成長率は表示仕様で定めた式に従う。
- 比較元なし、欠損、0除算相当は `None` を返す。

### 5.2 CF経時ブロック

| 指標 | 計算式 |
|------|-------|
| FCF | 営業CF ＋ 投資CF |
| FCFマージン | FCF ÷ 売上高 |
| 営業CFマージン | 営業CF ÷ 売上高 |
| Cash Conversion | 営業CF ÷ 純利益 |
| FCF Yield | FCF ÷ 時価総額 |
| 投資積極性 | `abs(投資CF) ÷ 営業CF` |

分母が `0` または `None`、または必要な入力値が欠損している場合は `None` とする。

### 5.3 PER / 配当利回り

- PERは forecast EPS 由来を優先する。
- forecast EPS が取得不可の場合のみ market PER を使う。
- 配当利回りは株探行の修正1株配当と株価から算出する。

---

## 6. Builder / Presenter

- Builder / Presenter はI/Oを行わない。
- Domain結果を表示DTOまたは出力テキストへ変換する。
- 表示順、見出し、ラベル、`N/A`、本文行省略、内部ログ文言は `docs/display_spec.md` に従う。

---

## 7. 廃止済み方針

- J-Quants由来の財務指標計算モデルは使用しない。
- `summary_rows` は使用しない。
- FY/四半期データを前提にした表示補完は行わない。
- `FundamentalDisplaySnapshot` / `PeriodFundamentalRow` へ寄せる段階移管案は廃止する。

---

## 8. 未完了タスク

なし。
