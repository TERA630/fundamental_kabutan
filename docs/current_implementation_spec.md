# 現行実装仕様

## 1. 目的

本書は、現在の実装を説明する正本仕様である。作業案、移行計画、完了済みの進捗ログは扱わない。

対象は以下とする。

- GUI の画面表示と操作
- Fundamental / Technical の出力
- 機関投資サマリ固定パネル
- 監視銘柄 Fundamental / Technical サマリ
- 単一銘柄 地合評価
- Data / Domain / UseCase / 画面・表示 の責務

## 2. 全体構成

処理の流れは次の順序を基本とする。

`GUI -> Controller -> UseCase -> Domain Policy / Builder -> Data Provider / Repository`

| 層 | 責務 | 主なファイル |
|---|---|---|
| 画面・表示 | Tkinter / Web UI、ユーザー操作、タブ、ステータス、コピー、保存、出力テキストとHTML整形 | `app/gui*.py`, `app/presenters.py`, `app/domain/builders/*.py`, `app/presentation/*.py` |
| ドメイン層 | DTO、純計算、採点、分類、UseCase orchestration | `app/domain/models/*.py`, `app/domain/policies/*.py`, `app/domain/usecases/*.py` |
| データー層 | yFinance取得、株探HTML解析、監視銘柄読込、JSONキャッシュ | `app/data/*.py` |

## 3. 画面・表示

画面・表示の詳細仕様は `screen_spec.md` を正とする。

本層は、Tkinter / Web UI、ユーザー操作、タブ、ステータス、コピー、保存、出力テキストとHTMLの整形を担当する。データ取得、HTML解析、ドメイン計算は持たない。

主な対象は次の通り。

- 画面構成
- 操作仕様
- ステータス表示
- 機関投資サマリ固定パネル
- GUI出力キャッシュ表示

## 4. ドメイン層

### 4.1 基本責務

ドメイン層はモデル、UseCase、純計算ポリシーを持つ。GUI部品や表示文言、外部APIの直接呼び出しは持たない。

Domain Policy は原則として純粋関数にする。表示用の `N/A` 文字列ではなく、`None` やDTOの値で欠損を表す。

### 4.2 条件判定の実装規約

単一の数値を閾値帯ごとのランク、点数、ラベルへ変換する条件判定は、原則として型付きの `RangeTable` を使う。境界の包含/非包含、欠損時の既定値、帯の優先順位をテーブルに明示し、個別の `if` 連鎖を増やさない。

複数の独立条件を合算する採点、または成立理由を保持する必要がある複合判定には `SignalAtom` を使う。各 Atom は識別子、成立可否、加点、必要に応じたグループ上限を持つ。優先順位を持つ分岐、例外処理、他指標依存の補正は、Atom/RangeTableへ無理に押し込めず Domain Policy で明示する。

### 4.3 主要モデル

| モデル | 内容 |
|---|---|
| `KabutanForecastRow` | 株探の年度別業績行 |
| `KabutanForecastPair` | 前期実績、今期予想、来期予想などの業績セット |
| `KabutanCashflowRow` | 株探CF行 |
| `KabutanBalanceSheetRow` | 株探財務行 |
| `QuarterlyActual` / `QuarterlyMetricRow` | 四半期実績と表示用メトリクス |
| `MarketSnapshot` | 株価、時価総額、PER、PBR、業種、配当関連 |
| `MarketDataBundle` | 日足、5分足、市況スナップショットをまとめたDTO |
| `ManualTechnicalQuote` | 単一銘柄の再解析だけに適用する手入力の当日現在値、高値、安値、VWAP、反映時刻 |
| `TechnicalSnapshot` | Technical表示に必要な価格、移動平均、レンジ、前日評価、節目 |
| `CfScoringInput` / `CfScoringResult` | rankCF の入力と結果 |
| `InstitutionalSummary` | 固定パネル用の機関投資サマリ |
| `FundamentalSummaryRow` / `FundamentalSummaryTable` | 監視銘柄サマリ出力 |
| `TechnicalSummaryRow` / `TechnicalSummaryTable` | 監視銘柄Technicalサマリ出力 |
| `UsMarketSummaryRow` / `UsMarketSummaryTable` | Technical Summary 冒頭のUS Market指標出力 |

### 4.4 UseCase

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

### 4.5 Fundamental 計算

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

### 4.6 rankCF 採点

rankCF は `calculate_cf_score()` で計算する。

| カテゴリ | 主な指標 |
|---|---|
| Quality | ROIC、Cash Conversion、営業CFマージン、営業利益率、FCF Ratio |
| Growth | EPS CAGR、売上CAGR |
| Valuation | FCF Yield、PER |

欠損指標は原則0点として扱う。総合スコアから `S` / `A` / `B` / `C` の判定を作る。

### 4.7 Technical 計算

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

### 4.8 Technical Summary ランク

ランキング分類条件の正本は `docs/technical_ranking_spec.md` とする。
反転補助状態、VWAP15分維持、D1a / D1b、D2弱、D3強弱、
技術指標の定義、崩れ警戒スコア、ホールド判定、ローソク足型と髭の定義など
すべてのランキング・指標仕様は同書を参照する。

本書ではランキング分類条件の詳細には触れず、実装上の要件のみ記載する。

**実装要件：**

- Technical Summary は A1 / A1弱 / A2 / C1 / D1 / B1 / B2 / E の位置ランクに分類する
- Technicalランクと1Y位置評価は、同じ25日線乖離率境界から判定する
- 崩れ警戒と反転状態は位置ランクを上書きせず、補助状態として別に保持する
- 1Y位置評価は25日線乖離率だけで判定し、終端位置による分岐は行わない
- 場中は当日5分足の最新値、大引け後は当日終値を判定価格として使う
- `Focus_theme`、銘柄名キーワード、テーマ性はランキング分類条件に使わない
- 単一銘柄Technical出力では、反転補助状態とD1a / D1b / D1判定保留 / D2 / D2弱 / D3強 / D3 / D3弱に応じて戦略判定を切り替える
- 単一銘柄Technical出力の短評は `位置ランク 状態表示名｜補助状態｜1Y位置評価｜5日線傾き短評` の1行で表示する
- Technical Summary 一覧には `テクニカル状態` と `1Y位置評価` 列を表示する
- 戦略判定では、前場VWAP回復、後場VWAP回復の各シナリオを詳細分類別に表示する
- 旧D1 / D2 / D3 / E判定は、`VWAP回復・確認不足` / `支持線反発候補` / `反転確認` / `反転未確認` の補助状態として維持する

### 4.9 Technical Summary US Market

Technical Summary の冒頭には US Market セクションを表示する。

詳細は `docs/technical_ranking_spec.md` 第14章を参照する。

**実装要件：**

- 対象：`NASDAQ総合`、`SOX指数`、`NVIDIA`、`GRID`、`日経先物`、`銅先物(COMEX)`、`WTI原油`
- 各行は yFinance の日足から直近値、前日騰落、5日移動平均乖離、25日移動平均乖離、RSI14 を計算
- 取得失敗時は Technical Summary 全体の失敗にしない
- 取得できない指標は skipped として理由を保持し、表示可能な指標だけを出力

### 4.10 単一銘柄セクター地合評価

単一銘柄画面では `地合評価` ボタンを押した場合のみ、選択銘柄に紐づくセクター地合を本文末尾へ追記する。
Technical の `取得` ボタンではセクター地合を自動追記しない。
Technical Summary 一覧では、従来どおり US Market セクション後、ランク別テーブル前に `Sector Breadth` を表示する。

**実装要件：**

- 監視銘柄ファイルのセクタータグから対象セクターを決める
- タグなし銘柄、または該当セクターの集計結果が作れない場合は単一銘柄本文へ追記しない
- 単一銘柄のTechnicalランクや戦略判定は変更しない
- 評価時点の指定がある場合は、セクター集計対象銘柄のTechnical行作成にも同じ評価時点を渡す

### 4.11 前日VWAPと後場評価

前日5分足から計算する指標の詳細は `docs/technical_ranking_spec.md` 第3章を参照する。

**実装要件：**

- 前日全体VWAP
- 前日前場VWAP（09:00～11:30）
- 前日後場VWAP（12:30～15:00）
- 前場VWAP維持、後場VWAP維持の判定
- 前日終値の後場VWAP位置
- 後場評価

### 4.12 ローソク足型とヒゲ

ローソク足型とヒゲの判定定義は `docs/technical_ranking_spec.md` 第4章を参照する。

**実装要件：**

- ローソク足型：前日の日足OHLCから `十字` / `小陽線` / `小陰線` / `陽線` / `陰線` / `大陽線` / `大陰線` / `N/A` に分類
- ヒゲ判定：上髭 / 下髭 / ヒゲなし / N/A を判定
- 定義式と判定条件は `technical_ranking_spec.md` を正本とする

## 5. データー層

### 5.1 基本責務

データー層は外部データ取得、HTML解析、ファイル読込、永続キャッシュを担当する。ドメイン判定や表示文言の組み立ては行わない。

### 5.2 yFinance

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

### 5.3 株探HTML

`app/data/kabutan_repository.py` が担当する。

取得・解析対象は次の通り。

- 年度別業績予想・実績
- キャッシュフロー
- 貸借対照表
- 四半期実績

GUIで株探HTMLフォルダが指定されている場合は、対象銘柄のHTMLファイルを優先する。HTMLフォルダが未指定、または対象HTMLがない場合はWeb取得経路を使う。

#### 5.3.1 株探HTML正規化とZipパッケージ

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

### 5.4 監視銘柄ファイル

`app/data/watchlist_repository.py` が担当する。Markdown / Text から銘柄名と4桁コードを抽出する。

### 5.5 キャッシュ

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

## 6. 欠損時の方針

- 任意データの取得失敗は画面全体の失敗にしない。
- 表示できない値は `N/A` とする。
- Fundamental の株探HTMLが取れない場合でも、市況や取得済み情報で可能な範囲を表示する。
- Technical の日中VWAPは、5分足が取れない場合に日足参考値へフォールバックする。
- 前日評価の前日VWAPは、前日5分足が不足する場合に日足参考値へフォールバックしない。
- rankCF の欠損指標は原則0点として扱う。

## 7. 検証方針

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
