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

### 5.4 成長フェーズ分類

冒頭サマリーで表示する `growth_phase` を、売上成長率・営業益成長率・EPS成長率・3年CAGRから判定する。
表示文言は `docs/display_spec.md`、判定ロジックは本節を正とする。

**入力値**

| 入力 | 内容 |
|------|------|
| `sales_growth_current` | 直近期または今期予想の売上成長率 |
| `op_growth_current` | 直近期または今期予想の営業益成長率 |
| `eps_growth_current` | 直近期または今期予想のEPS成長率 |
| `sales_growth_previous` | 前期の売上成長率 |
| `op_growth_previous` | 前期の営業益成長率 |
| `eps_growth_previous` | 前期のEPS成長率 |
| `sales_cagr_3y` | 売上3年CAGR |
| `op_cagr_3y` | 営業益3年CAGR |
| `eps_cagr_3y` | EPS3年CAGR |
| `previous_op` | 前期営業益 |
| `current_op` | 直近期または今期予想の営業益 |
| `previous_eps` | 前期EPS |
| `current_eps` | 直近期または今期予想のEPS |

**基本方針**

- 判定は上から順に行い、最初に一致した分類を採用する。
- 成長率は `%` 単位の値として扱う。
- 判定に必要な値が欠損している条件は不一致として扱い、次の条件へ進む。
- 3年CAGR条件は、原則として売上・営業益・EPSのうち分類に必要な主要指標で判定する。
- どの条件にも一致しない場合は `安定成長` とする。

**判定優先順**

| 優先 | 分類 | 意味 | 判定条件 |
|------|------|------|----------|
| 1 | `業績回復途上` | 赤字・減益からの回復 | 前期営業益成長率または前期EPS成長率が `0%` 未満、または前期営業益・前期EPSのいずれかが赤字で、かつ本年度売上成長率が `0%` 超、営業益が黒字化または `+20%` 以上、EPSが黒字化または `+20%` 以上 |
| 2 | `成長再加速` | 前期鈍化後に再上昇 | 売上成長率が前期比 `+5pt` 以上改善、または営業益成長率・EPS成長率のいずれかが前期比 `+10pt` 以上改善し、かつ3年CAGRが `5%` 以上 |
| 3 | `高成長鈍化後` | まだ高成長だが勢い低下 | 売上成長率が直近 `10%` 以上かつ前期比 `-5pt` 以上鈍化、または営業益成長率・EPS成長率のいずれかが直近 `15%` 以上かつ前期比 `-10pt` 以上鈍化し、かつ3年CAGRが `10%` 以上 |
| 4 | `高成長中` | 売上・利益・EPSすべて強い | 売上成長率 `10%` 以上、営業益成長率 `15%` 以上、EPS成長率 `15%` 以上、3年CAGR `10%` 以上 |
| 5 | `利益改善型` | 売上より利益率改善 | 売上成長率 `5%` 未満、営業益成長率 `10%` 以上、EPS成長率 `10%` 以上、3年CAGR `5%` 以上 |
| 6 | `低成長` | 成熟・横ばい | 売上成長率・営業益成長率・EPS成長率・3年CAGRがすべて `5%` 未満 |
| 7 | `安定成長` | 地味だが堅調、またはその他 | 上記のいずれにも該当しない |

**安定成長の代表条件**

`安定成長` はフォールバック分類だが、以下の条件に一致する場合も明示的に `安定成長` とみなす。

- 売上成長率・営業益成長率・EPS成長率・3年CAGRがすべて `5%` 以上 `10%` 未満。

**業績回復途上の定義**

以下のすべてを満たす場合、`業績回復途上` と判定する。

1. 前期の悪化または赤字がある。
   - `op_growth_previous < 0` または `eps_growth_previous < 0`
   - または `previous_op < 0` または `previous_eps < 0`
2. 本年度売上が増収である。
   - `sales_growth_current > 0`
3. 営業益が黒字化、または強く改善している。
   - 黒字化: `previous_op < 0 and current_op > 0`
   - または強い改善: `op_growth_current >= 20`
4. EPSが黒字化、または強く改善している。
   - 黒字化: `previous_eps < 0 and current_eps > 0`
   - または強い改善: `eps_growth_current >= 20`

閾値を変更する場合は、本節のみを更新し、表示仕様の文言は変更しない。

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
