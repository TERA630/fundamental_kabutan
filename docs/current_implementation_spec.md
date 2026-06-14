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

日足ベースで次を計算する。

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

### 5.7 Technical Summary ランク

ランキング分類条件の正は `docs/technical_summary_ranking_spec.md` とする。
D1 / D2 / D3、VWAP15分維持、D1a / D1b、D3強弱、25日線乖離ラベルの
詳細は同仕様書を参照する。

Technical Summary は A1 / A2 / B1 / B2 / C1 / C2 / D1 / D2 / D3 / E に分類する。
場中は当日5分足の最新値、大引け後は当日終値を判定価格として使う。

D系ランクでは25日線乖離率を必須条件にせず、リスク・リワードの補助ラベルに使う。
D3はVWAP上を15分以上連続維持することを必須とし、出来高比は分類後の強弱表示に使う。
D1は単一銘柄詳細画面で25日線距離が2ATR以内のD1aと、2ATR超のD1bに分ける。
D2は支持線反発候補だけを対象とし、支持線明確割れ、直下1ATR以内の支持線なし、
終端位置40%未満、3日連続安値切り下げ、出来高急増の陰線を除外する。

単一銘柄Technical出力では、D1a / D1b / D1判定保留 / D2 / D3強 / D3 / D3弱ごとに
主判定を切り替え、共通短評と詳細行を分けず1行で表示する。続く戦略判定では、
深押し指値、前場VWAP回復、後場VWAP回復の各シナリオを詳細分類別に表示する。
ATR14と支持線が取得できる場合は指値帯を価格へ展開し、支持線下0.35ATRを損切り、
25日線または直近抵抗線を目標とするRRを表示する。必要値の欠損時は
`指値算出不可` または `RR算出不可` とする。

#### 5.7.1 単一銘柄の崩れ警戒スコア

単一銘柄Technical出力では、25日線の上下にかかわらず崩れ警戒を表示する。次の条件を各1点として合計する。値が欠損して条件を評価できない場合は加点しない。

| 条件 | 点数 |
|---|---:|
| 現在値が25日線未満 | +1 |
| 現在値がVWAP未満 | +1 |
| 直近3営業日の安値切り上げがすべて不成立 | +1 |
| 直近3営業日の高値更新がすべて不成立 | +1 |
| 終端位置が40%未満 | +1 |
| 出来高20日平均比が100%超、かつ陰線または上値失速 | +1 |
| 直下支持線までの距離が0.7ATR超 | +1 |
| 25日線の傾きが低下（5日前の25日線より低い） | +1 |

陰線は `終値 < 始値` かつ実体が `0.15ATR` 以上とする。上値失速は、上ヒゲが当日値幅の45%以上、かつ実体の1.5倍以上とする。

直下支持線は、現在値より下にある25日線、前日安値、20日安値、75日線、60日安値のうち最も近い価格とする。候補がない場合、またはATRを取得できない場合は距離条件を加点しない。

| 合計点 | 表示ラベル（株価ランク別） |
|---:|---|
| 0〜8点 | 以下のランク別ルールにより表示ラベルを決定する（最大スコアは8点）。表示は `崩れ {score}/8：{ラベル}` 形式とする。 |

ランク別ラベル（`崩れ` スコアに基づく）:

- ランク `A*`, `B*`, `D2`, `D3`, `E`:
  - 0〜2点：崩れ軽微
  - 3〜4点：上値重い
  - 5〜6点：崩れ警戒
  - 7〜8点：買い不可
- ランク `C1`:
  - 0〜2点：押し目候補
  - 3〜4点：VWAP回復待ち
  - 5点以上：押し目ではなく崩れ警戒
- ランク `C2`:
  - 0〜2点：軽度崩れ
  - 3〜4点：崩れ警戒
  - 5点以上：買い不可
- ランク `D1`:
  - 0〜2点：戻り良好
  - 3〜4点：25日線奪回待ち
  - 5点以上：戻り売り警戒

表示例: `崩れ 5/8：崩れ警戒`

#### 5.7.2 底打ち初動・ホールド判定

底打ち初動判定は現在値が25日線未満の場合だけ表示し、Technical Summaryランクが `D3` の場合を `成立`、それ以外を `未成立` とする。

ホールド判定は次の条件を使う。25日線近接および支持線が近い状態は `0.7ATR以内` とする。条件が重複する場合は `×`、`△`、`◎`、`○` の順に優先し、どの条件にも完全一致しない場合は `△` とする。

| 判定 | 条件 |
|---|---|
| ◎ | 25日線以上、VWAP以上、終端位置50%以上、出来高20日平均比80%以上、直下支持線まで0.7ATR以内 |
| ○ | 25日線以上または25日線まで0.7ATR以内、VWAP以上、直近3営業日に安値切り上げが1つ以上 |
| △ | VWAP以上だが25日線未満、または終端位置50%未満、または出来高20日平均比80%未満 |
| × | VWAP未満、25日線未満、直近3営業日の安値切り上げがすべて不成立、直下支持線まで0.7ATR超をすべて満たす |

### 5.8 Technical Summary US Market

Technical Summary の冒頭には US Market セクションを表示する。

対象は `NASDAQ総合`、`SOX指数`、`NVIDIA`、`GRID`、`日経先物`、`銅先物(COMEX)`、`WTI原油` とする。各行は yFinance の日足から直近値、前日騰落、5日移動平均乖離、25日移動平均乖離、RSI14 を計算する。

US Market の取得失敗は Technical Summary 全体の失敗にしない。取得できない指標は skipped として理由を保持し、表示可能な指標だけを出力する。

### 5.9 前日VWAPと後場評価

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

前日前場・後場のVWAP維持判定は、単一銘柄Technical出力の冒頭 `需給（VWAP）` 行へ当日判定とまとめて表示する。`■前日評価` には再掲しない。後場評価の表示は分類ラベルのみとし、後場VWAP位置は併記しない。前日高値更新・前日安値維持も `■モメンタム` と重複するため `■前日評価` には表示しない。

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

### 5.10 ローソク足型とヒゲ

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
