# 現行実装仕様

## 1. 目的

本書は、現在の実装を説明する正本仕様である。作業案、移行計画、完了済みの進捗ログは扱わない。

対象は以下とする。

- GUI の画面表示と操作
- Fundamental / Technical の出力
- 機関投資サマリ固定パネル
- 監視銘柄 Fundamental / Technical サマリ
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
- 監視銘柄 Fundamental / Technical サマリ

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
| `TechnicalSummaryRow` / `TechnicalSummaryTable` | 監視銘柄Technicalサマリ出力 |
| `UsMarketSummaryRow` / `UsMarketSummaryTable` | Technical Summary 冒頭のUS Market指標出力 |

### 5.3 UseCase

| UseCase | 責務 |
|---|---|
| `MarketDataService` | 日足、5分足、市況スナップショットを取得・キャッシュし、`MarketDataBundle` を作る |
| `FundamentalAnalysisService` | 株探・yFinance・アナリスト予想を統合し、Fundamental出力に必要な入力を作る |
| `TechnicalAnalysisService` | 日足・5分足から `TechnicalAnalysisResult` を作る |
| `FundamentalSummaryService` | 監視銘柄を順に分析し、サマリ用テーブルを作る |
| `TechnicalSummaryService` | 監視銘柄を順にTechnical分析し、ランク別サマリ用テーブルを作る |
| `UsMarketSummaryService` | yFinanceの日足からUS Market指標の直近値、前日騰落、5日乖離、25日乖離、RSI14を作る |
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

Technical 指標の計算定義は `docs/technical_ranking_spec.md` 第2章を参照する。

**実装要件：**

日足ベースで次を計算する。

- 5日移動平均、前日5日線
- 25日移動平均
- 25日線からの乖離率
- RSI14
- ATR14
- 当日値幅とATR比
- 当日終端位置
- 前日高値更新、前日安値維持
- 前日出来高の20日平均比
- 前日ローソク足型
- 5日、20日、60日の高値/安値と距離

詳細な定義式はすべて `technical_ranking_spec.md` に記載されており、
本書ではリスト形式で概要のみ記載する。

### 5.7 Technical Summary ランク

ランキング分類条件の正本は `docs/technical_ranking_spec.md` とする。
D1 / D2 / D3、VWAP15分維持、D1a / D1b、D3強弱、25日線乖離ラベル、
技術指標の定義、崩れ警戒スコア、ホールド判定、ローソク足型と髭の定義など
すべてのランキング・指標仕様は同書を参照する。

本書ではランキング分類条件の詳細には触れず、実装上の要件のみ記載する。

**実装要件：**

- Technical Summary は A1 / A2 / B1 / B2 / C1 / C2 / D1 / D2 / D3 / E に分類する
- 場中は当日5分足の最新値、大引け後は当日終値を判定価格として使う
- 単一銘柄Technical出力では、D1a / D1b / D1判定保留 / D2 / D3強 / D3 / D3弱 ごとに主判定を切り替える
- 共通短評と詳細行は分けず1行で表示する
- 戦略判定では、深押し指値、前場VWAP回復、後場VWAP回復の各シナリオを詳細分類別に表示する
- ATR14と支持線が取得できる場合は指値帯を価格へ展開し、RRを表示する
- 必要値の欠損時は `指値算出不可` または `RR算出不可` とする

### 5.8 Technical Summary US Market

Technical Summary の冒頭には US Market セクションを表示する。

詳細は `docs/technical_ranking_spec.md` 第14章を参照する。

**実装要件：**

- 対象：`NASDAQ総合`、`SOX指数`、`NVIDIA`、`GRID`、`日経先物`、`銅先物(COMEX)`、`WTI原油`
- 各行は yFinance の日足から直近値、前日騰落、5日移動平均乖離、25日移動平均乖離、RSI14 を計算
- 取得失敗時は Technical Summary 全体の失敗にしない
- 取得できない指標は skipped として理由を保持し、表示可能な指標だけを出力

### 5.9 前日VWAPと後場評価

前日5分足から計算する指標の詳細は `docs/technical_ranking_spec.md` 第3章を参照する。

**実装要件：**

- 前日全体VWAP
- 前日前場VWAP（09:00～11:30）
- 前日後場VWAP（12:30～15:00）
- 前場VWAP維持、後場VWAP維持の判定
- 前日終値の後場VWAP位置
- 後場評価

### 5.10 ローソク足型とヒゲ

ローソク足型とヒゲの判定定義は `docs/technical_ranking_spec.md` 第4章を参照する。

**実装要件：**

- ローソク足型：前日の日足OHLCから `十字` / `小陽線` / `小陰線` / `陽線` / `陰線` / `大陽線` / `大陰線` / `N/A` に分類
- ヒゲ判定：上髭 / 下髭 / ヒゲなし / N/A を判定
- 定義式と判定条件は `technical_ranking_spec.md` を正本とする

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

#### 6.3.1 株探HTML正規化とZipパッケージ

`app/domain/usecases/kabutan_html_normalizer.py` は、ダウンロード済み株探HTMLをCodespacesへ運搬しやすい形へ正規化する。

主な処理は次の通り。

- `<body>` 内HTMLの抽出
- `script`、`style`、`noscript`、`iframe`、HTMLコメントの除去
- `<title>` を4桁コードへ整理
- 出力ファイル名を `7203.html` 形式へ統一
- 正規化結果とスキップ理由を `manifest.json` へ記録

`app/services/kabutan_html_package_service.py` は、正規化済みHTMLと `manifest.json` を `kabutan_html_package.zip` として書庫化する。Package Zip の作成は Tkinter UI で行う。Web UI では Package Zip をアップロード時に検査してパスを保持する。この時点では展開しない。Fundamental解析またはFundamentalサマリが必要になった時だけ、アプリ内部のキャッシュ領域へ展開し、展開後の `html/` を既存の解析処理へ渡す。同じZipが展開済みの場合は展開済みキャッシュを再利用する。展開先はZipのサイズと内容ハッシュから作る署名別ディレクトリとし、固定ディレクトリを毎回削除しない。Web UI はHTML正規化とZip作成を行わない。

Zipの基本構成は次の通り。

```text
kabutan_html_package.zip
  manifest.json
  html/
    7203.html
```

運用手順と未確認事項は `kabutan_html_package_workflow.md` に分離する。

### 6.4 監視銘柄ファイル

`app/data/watchlist_repository.py` が担当する。Markdown / Text から銘柄名と4桁コードを抽出する。

### 6.5 キャッシュ

`app/data/file_cache.py` が `.fundamental_cache` 配下へJSONで保存する。

| 対象 | キー例 | TTL |
|---|---|---:|
| GUI出力 | `gui_output_cache` | 当日分のみ再利用 |
| 株探HTMLフォルダ | `kabutan_last_html_dir` | 長期 |
| 株探Package Zip | `kabutan_last_package_zip` | 長期 |
| 監視銘柄ファイル | `watchlist_last_path` | 長期 |
| 株探業績 | `kabutan_forecast_{code}` | 12時間 |
| yFinance市況 | `yf_{code}` | 12時間 |
| アナリスト予想 | `yf_analyst_{code}` | 12時間 |
| Technical日足 | `tech_daily_{code}_4mo_1d` | 12時間 |
| Technical5分足 | `tech_intraday_{code}_5m_jst` | 5分 |

GUI出力キャッシュは日付が変わると再利用しない。株探HTMLフォルダまたは株探Package Zipを変更した場合はGUI出力キャッシュをクリアする。Web UI 起動時は、キャッシュ済みの監視銘柄ファイル、株探HTMLフォルダ、株探Package Zipを復元する。

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
- TechnicalサマリMarkdown
- Web UI のサマリHTML表示とMarkdown/HTMLダウンロード

関連テストは `tests/` 配下に配置する。
