# 現行実装仕様

## 1. 目的

本書は、現在の実装を説明する正本仕様である。作業案、移行計画、完了済みの進捗ログは扱わない。

対象は以下とする。

- GUI の画面表示と操作
- Fundamental / Technical の出力
- 機関投資サマリ固定パネル
- 監視銘柄 Fundamental サマリ
- Data / Domain / UseCase / Presentation / GUI の責務

## 2. 全体構成

処理の流れは次の順序を基本とする。

`GUI -> Controller -> UseCase -> Domain Policy / Builder -> Data Provider / Repository`

| 層 | 責務 | 主なファイル |
|---|---|---|
| 画面表示 | Tkinter UI、ユーザー操作、タブ、ステータス、コピー、保存 | `app/gui.py`, `app/gui_view.py`, `app/gui_view_model.py`, `app/gui_state.py` |
| プレゼンテーション層 | 出力テキスト、Markdown、表示用セクション、数値表現、N/A表現 | `app/presenters.py`, `app/domain/builders/*.py`, `app/presentation/display_formatter.py` |
| ドメイン層 | DTO、純計算、採点、分類、UseCase orchestration | `app/domain/models/*.py`, `app/domain/policies/*.py`, `app/domain/usecases/*.py` |
| データー層 | yFinance取得、株探HTML解析、監視銘柄読込、JSONキャッシュ | `app/data/*.py` |

## 3. 画面表示案

画面表示の詳細仕様は `screen_spec.md` を正とする。

本層は、Tkinter UI、ユーザー操作、タブ、ステータス、コピー、保存を担当する。データ取得、HTML解析、ドメイン計算、出力テキストの組み立ては持たない。

主な対象は次の通り。

- 画面構成
- 操作仕様
- ステータス表示
- 機関投資サマリ固定パネル
- GUI出力キャッシュ表示

## 4. プレゼンテーション層

プレゼンテーション層の詳細仕様は `presentation_spec.md` を正とする。

本層は、UseCaseが返すDTOと計算結果を表示用テキストへ変換する。データ取得、HTML解析、採点ロジック、指標計算は持たない。

主な対象は次の通り。

- Fundamental 出力
- rankCF 表示
- Technical 出力
- 前日評価表示
- 機関投資サマリ表示
- 監視銘柄 Fundamental サマリ

## 5. ドメイン層

### 5.1 基本責務

ドメイン層はモデル、UseCase、純計算ポリシーを持つ。GUI部品や表示文言、外部APIの直接呼び出しは持たない。

Domain Policy は原則として純粋関数にする。表示用の `N/A` 文字列ではなく、`None` やDTOの値で欠損を表す。

### 5.2 主要モデル

| モデル | 内容 |
|---|---|
| `KabutanForecastRow` | 株探の年度別業績行 |
| `KabutanForecastPair` | 前期実績、今期予想、来期予想などの業績セット |
| `KabutanCashflowRow` | 株探CF行 |
| `KabutanBalanceSheetRow` | 株探財務行 |
| `QuarterlyActual` / `QuarterlyMetricRow` | 四半期実績と表示用メトリクス |
| `MarketSnapshot` | 株価、時価総額、PER、PBR、業種、配当関連 |
| `MarketDataBundle` | 日足、5分足、市況スナップショットをまとめたDTO |
| `TechnicalSnapshot` | Technical表示に必要な価格、移動平均、レンジ、前日評価、節目 |
| `CfScoringInput` / `CfScoringResult` | rankCF の入力と結果 |
| `InstitutionalSummary` | 固定パネル用の機関投資サマリ |
| `FundamentalSummaryRow` / `FundamentalSummaryTable` | 監視銘柄サマリ出力 |

### 5.3 UseCase

| UseCase | 責務 |
|---|---|
| `MarketDataService` | 日足、5分足、市況スナップショットを取得・キャッシュし、`MarketDataBundle` を作る |
| `FundamentalAnalysisService` | 株探・yFinance・アナリスト予想を統合し、Fundamental出力に必要な入力を作る |
| `TechnicalAnalysisService` | 日足・5分足から `TechnicalAnalysisResult` を作る |
| `FundamentalSummaryService` | 監視銘柄を順に分析し、サマリ用テーブルを作る |
| `BuildQuarterlyFinancialTableUseCase` | 四半期実績からYoYメトリクスを作る |
| `FetchKabutanForecastUseCase` | 株探業績取得をRepository越しに行う |
| `ResolveKabutanHtmlDirUseCase` / `ResolveWatchlistPathUseCase` | キャッシュ済みパスの有効性を判定する |

### 5.4 Fundamental 計算

主な計算は次の通り。

- 売上、営業利益、EPSなどの成長率
- 営業利益3年CAGR
- PER、配当利回り
- PBR、ROE、ROIC近似
- CFマージン、FCF、FCF Yield、Cash Conversion
- 成長フェーズ分類
- PER水準分類
- ROIC水準分類
- 四半期YoY成長率

### 5.5 rankCF 採点

rankCF は `calculate_cf_score()` で計算する。

| カテゴリ | 主な指標 |
|---|---|
| Quality | ROIC、Cash Conversion、営業CFマージン、営業利益率、FCF Ratio |
| Growth | EPS CAGR、売上CAGR |
| Valuation | FCF Yield、PER |

欠損指標は原則0点として扱う。総合スコアから `S` / `A` / `B` / `C` の判定を作る。

### 5.6 Technical 計算

日足ベースで次を計算する。

- 5日移動平均、25日移動平均
- 5日線・25日線からの乖離率
- RSI14
- ATR14
- 当日値幅とATR比
- 当日終端位置
- 前日高値更新、前日安値維持
- 前日出来高の20日平均比
- 前日ローソク足型
- 5日、20日、60日の高値/安値と距離

### 5.7 前日VWAPと後場評価

前日5分足から次を計算する。

- 前日全体VWAP
- 前日前場VWAP
- 前日後場VWAP
- 前場VWAP維持
- 後場VWAP維持
- 前日終値の後場VWAP位置
- 後場評価

VWAP式:

```text
TypicalPrice = (High + Low + Close) / 3
VWAP = sum(TypicalPrice * Volume) / sum(Volume)
```

前日5分足が取得できない場合、または前場・後場のどちらかが不足する場合、前日VWAP系の値と後場評価は `N/A` とする。前日評価では日足参考VWAPへフォールバックしない。

後場評価は次の優先順位で判定する。

| 優先 | ラベル | 条件 |
|---:|---|---|
| 1 | `N/A` | 必要値欠損、または後場高値 <= 後場安値 |
| 2 | `後場VWAP割` | 終値 <= 後場VWAP |
| 3 | `失速もVWAP維持` | 終値 > 後場VWAP、かつ後場リターン < -1% または終値位置 < 30% |
| 4 | `後場上昇` | 終値 > 後場始値、かつ終値位置 >= 70% |
| 5 | `高値維持` | 終値位置 >= 50%、かつ後場リターンが -1% 以上 1% 以下 |
| 6 | `横ばいVWAP維持` | 終値位置が30%以上50%未満、かつ後場リターンが -1% 以上 1% 以下 |
| 7 | `後場上昇` | 後場リターン > 1% |
| 8 | `横ばいVWAP維持` | 上記以外のVWAP上ケース |

### 5.8 ローソク足型とヒゲ

ローソク足型は前日の日足OHLCから判定する。

| 条件 | ラベル |
|---|---|
| range <= 0 または欠損 | `N/A` |
| 実体比 < 10% または始値 == 終値 | `十字` |
| 実体比 < 30% | `小陽線` / `小陰線` |
| 実体比 < 65% | `陽線` / `陰線` |
| それ以外 | `大陽線` / `大陰線` |

ヒゲ判定は次の通り。

- 上ヒゲ比率が30%以上、かつ実体の1.5倍以上で、下ヒゲより長い場合は `上髭`。
- 下ヒゲ比率が30%以上、かつ実体の1.5倍以上で、上ヒゲより長い場合は `下髭`。
- ヒゲなしの場合は空文字。
- range <= 0 または欠損時は `N/A`。

## 6. データー層

### 6.1 基本責務

データー層は外部データ取得、HTML解析、ファイル読込、永続キャッシュを担当する。ドメイン判定や表示文言の組み立ては行わない。

### 6.2 yFinance

`app/data/market_data_provider.py` が担当する。

| データ | 取得 |
|---|---|
| 日足 | `Ticker.history(period="4mo", interval="1d", auto_adjust=False)` |
| 5分足 | `yf.download(period="5d", interval="5m", auto_adjust=False)` |
| 市況 | `fast_info` と `info` |
| アナリスト予想 | `info` と `eps_revisions` |

日足・5分足は `Open`、`High`、`Low`、`Close`、`Volume` に正規化する。MultiIndex列にも対応する。
5分足のタイムゾーン付きインデックスは `Asia/Tokyo` へ変換してからタイムゾーンを外す。

日中VWAPは、5分足が取得できる場合は5分足から計算する。取得できない場合は日足の `(High + Low + Close) / 3` を日足参考値として使う。

### 6.3 株探HTML

`app/data/kabutan_repository.py` が担当する。

取得・解析対象は次の通り。

- 年度別業績予想・実績
- キャッシュフロー
- 貸借対照表
- 四半期実績

GUIで株探HTMLフォルダが指定されている場合は、対象銘柄のHTMLファイルを優先する。HTMLフォルダが未指定、または対象HTMLがない場合はWeb取得経路を使う。

### 6.4 監視銘柄ファイル

`app/data/watchlist_repository.py` が担当する。Markdown / Text から銘柄名と4桁コードを抽出する。

### 6.5 キャッシュ

`app/data/file_cache.py` が `.fundamental_cache` 配下へJSONで保存する。

| 対象 | キー例 | TTL |
|---|---|---:|
| GUI出力 | `gui_output_cache` | 当日分のみ再利用 |
| 株探HTMLフォルダ | `kabutan_last_html_dir` | 長期 |
| 監視銘柄ファイル | `watchlist_last_path` | 長期 |
| 株探業績 | `kabutan_forecast_{code}` | 12時間 |
| yFinance市況 | `yf_{code}` | 12時間 |
| アナリスト予想 | `yf_analyst_{code}` | 12時間 |
| Technical日足 | `tech_daily_{code}_4mo_1d` | 12時間 |
| Technical5分足 | `tech_intraday_{code}_5m_jst` | 5分 |

GUI出力キャッシュは日付が変わると再利用しない。株探HTMLフォルダを変更した場合はGUI出力キャッシュをクリアする。

## 7. 欠損時の方針

- 任意データの取得失敗は画面全体の失敗にしない。
- 表示できない値は `N/A` とする。
- Fundamental の株探HTMLが取れない場合でも、市況や取得済み情報で可能な範囲を表示する。
- Technical の日中VWAPは、5分足が取れない場合に日足参考値へフォールバックする。
- 前日評価の前日VWAPは、前日5分足が不足する場合に日足参考値へフォールバックしない。
- rankCF の欠損指標は原則0点として扱う。

## 8. 検証方針

主な検証対象は次の通り。

- データ取得正規化とキャッシュ
- 株探HTML解析
- Fundamental計算と表示
- rankCF採点
- Technical指標
- 前日VWAP、前場/後場VWAP、後場評価
- GUI Controllerのタブ別処理
- FundamentalサマリMarkdown

関連テストは `tests/` 配下に配置する。
