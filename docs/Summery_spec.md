# Summary Display Specification

## 1. 概要

本仕様書は、Tkinter GUI と Web UI におけるサマリ表示の動作要件を整理する。

- Tkinter は Fundamental / Technical のサマリ出力を Markdown として生成する。
- Web UI では `サマリ表示` を Web 固有の HTML 表示とし、同等出力を画面上で表現する。
- Web UI の Technical 画面では、監視銘柄をTechnicalランク別に分類したサマリ表を表示する。

## 2. 目的

Web UI におけるサマリ体験を、Tkinter で生成する Markdown 出力と同等の情報量で実装しつつ、Web UI 固有の HTML 表示を提供する。

## 3. 対象範囲

### 3.1 変更対象

- `app/web.py`
- `app/templates/index.html`
- Web UI 用の表示ロジック（`app/presentation/web_fundamental_output.py` など）
- Technical Summary 用のドメインモデル、UseCase、プレゼンテーションロジック
- `docs/fundamental_summary_spec.md`

### 3.2 変更しない対象

- `FundamentalSummaryService` の内部ロジック

## 4. 要件

### 4.1 ボタン名称変更

- Web UI の `app/templates/index.html` で、`/summary` 呼び出しボタンのラベルを `サマリ表示` に変更する。
- 表示モードは `Fundamental` / `Technical` によって切り替えできる。

### 4.2 Web UI Fundamental 画面の挙動

- `Fundamental` モードで `サマリ表示` を押すと、以下の処理を行う。
  1. 現在の WatchList と Kabutan HTML フォルダなどの入力を前提に、`FundamentalSummaryService` を使ってサマリデータを生成する。
  2. 生成されたサマリを `build_fundamental_summary_markdown()` 相当の構造で受け取り、Web表示用に HTML テーブルへ変換する。
  3. Web 画面には Markdown ではなく HTML 表として表示する。

- 表示内容は Tkinter の Markdown 出力イメージと同等とする。
- HTML 表は見出し、横並びセル、集計値、スコアを含む。
- 色付けや強調は可読性を高める範囲で適用する。

### 4.3 Web UI Technical 画面の挙動

- `Technical` モードでも `サマリ表示` ボタンは表示されたままとする。
- Technical モードで `サマリ表示` を押すと、現在の WatchList を前提に Technical Summary を生成する。
- Web 画面にはランク別の HTML テーブルとして表示する。
- 生成結果は Tkinter と同等の Markdown 形式でも保持し、保存・コピー用途で利用できるようにする。

### 4.4 保存設計の提案

#### 4.4.1 Web UI の保存要件

- Web UI における `サマリ表示` は HTML レンダリングを主目的とする。
- 同時に「ファイル保存」も可能にしたいが、保存方式は Web UI の特性を踏まえて設計する。

#### 4.4.2 提案 1：HTML 表示とダウンロード両対応

- `サマリ表示` を押したときに表示する HTML を内部で生成し、画面にレンダリングする。
- 追加で「HTML ダウンロード」ボタンを用意し、同じ HTML 表をファイルとしてダウンロードできるようにする。
- 保存するファイル形式は `summary.html` もしくは `summary.md` で選択可能にすると柔軟。

#### 4.4.3 提案 2：Web UI 側で Markdown も保持してダウンロード

- `FundamentalSummaryService` から Markdown を生成したあと、HTML 表と並行して Markdown データも保持する。
- 画面上は HTML 表として表示しつつ、`ダウンロード` ボタンで Markdown 版を取得できるようにする。
- こうすることで Tkinter の既存出力と同等の形式を保持しつつ、Web 表示と保存を切り分けられる。

#### 4.4.4 推奨

- まずは Web UI に HTML 表表示を実装し、`HTMLダウンロード` を追加する設計が最も自然。
- その後、必要に応じて Markdown ダウンロードも追加するのが段階的で良い。

## 5. 表示仕様

### 5.1 Fundamentals サマリ HTML 表構造

Web UI では以下の構造を想定する。

- `機関投資サマリ` 固定パネルは現在と同じ `state.institutional_summary` で表示継続。
- `サマリ表示` は以下のセクションで構成される。
  - 全体説明文（サマリの対象銘柄と生成日など）
  - 監視銘柄サマリテーブル
  - 災害や取得失敗時は `N/A` を明確表示

- テーブル列は横並びで表示する。
- テーブルは以下の項目を含む。
  - 銘柄名 / コード
  - スコア合計、Quality、Growth、Valuation
  - ROIC、PER、過去数年の売上/利益推移など
- スコアや値の見出し行は強調し、奇数/偶数行は背景色を切り替えて可読性を上げる。

### 5.2 HTML 表の見た目方針

- セルは左寄せ / 右寄せを用途に応じて使い分ける。
- 数値は桁区切り・単位表記を維持する。
- `N/A` は淡いグレーで表示するか、弱い色で目立ちすぎないようにする。
- 表見出しの固定表示は `th` で実装。
- 関連集計値は、表の上部または列のラベルに明示する。

### 5.3 Technical Summary 表示構造

Technical Summary は、監視銘柄を Technical Summary ランクごとに分類し、ランクごとのセクションにテーブル表示する。ランク判定、ランク表示順、60日レンジ判定、前日評価の仕様は `docs/technical_ranking_spec.md` を正とする。

表示順は `docs/technical_summary_ranking_spec.md` の Technical ランク順に従う。各セクション内の銘柄順は、崩れスコアの低い順とする。同点の場合は WatchList の順序を維持する。

Technical Summary の列は次の通り。

| 列 | 内容 |
|---|---|
| 銘柄 | `銘柄名(コード)` |
| 現在値 | `現在値円(前日騰落率)`。前日騰落額は表示しない |
| 3日騰落 | 3営業日前終値から前営業日終値までの騰落率 |
| 当日レンジ | `当日高値-当日安値(当日値幅率:ATR比)` |
| VWAP | `VWAP価格(現在値との乖離率)`。例: `2740円(+1.0%)` |
| 25ME dev | `25日線乖離率(ATR比)` |
| 出来高比 | 当日出来高の20日平均比 |
| 崩れスコア | 崩れ警戒スコアの数値のみ。短評やラベルは表示しない |
| 支持線 | 支持候補のうち現在値より下側で近い2本を `支持線1->支持線2` として表示 |
| 抵抗線 | 抵抗候補のうち現在値より上側で近い2本を `抵抗線1->抵抗線2` として表示 |
| 60D Pos | 60日安値から60日高値までの現在値位置 |

### 5.4 Technical Summary 支持線・抵抗線

支持線・抵抗線は現在値を基準に判定する。

支持候補は次の価格線を使う。

- `25ME`: 25日線
- `PrevL`: 前日安値
- `20D-L`: 20日安値
- `75ME`: 75日線
- `60D-L`: 60日安値

支持線は、欠損値を除外したうえで `価格 < 現在値` の候補を価格の高い順に並べ、現在値の下から近いものを最大2本抽出する。表示では近い順に `支持線1->支持線2` とする。

抵抗候補は次の価格線を使う。

- `PrevH`: 前日高値
- `20D-H`: 20日高値
- `60D-H`: 60日高値
- `25ME`: 25日線

抵抗線は、欠損値を除外したうえで `価格 > 現在値` の候補を価格の低い順に並べ、現在値の上から近いものを最大2本抽出する。表示では近い順に `抵抗線1->抵抗線2` とする。

候補が2本未満の場合は存在する候補のみ表示し、候補がない場合は `N/A` とする。同じ価格の候補が複数ある場合は、初期実装では候補リスト上の先勝ちとする。

### 5.5 Technical Summary 表示例

```markdown
US Market 2026-06-10 00:16

| 指標/銘柄 | 直近値 | 前日騰落 | 5日乖離 | 25日乖離 | RSI |
|---|---:|---:|---:|---:|---:|
| NASDAQ総合 | N/A | -0.85% | -1.9% | -2.3% | 45.38 |

### A1 位置良好

| 銘柄 | 現在値 | 3日騰落 | 当日レンジ | VWAP | 25ME dev | 出来高比 | 崩れスコア | 支持線 | 抵抗線 | 60D Pos |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|
| 信越工業(4063) | 6830円(-0.6%) | -8.8% | 6963-6743(3.2%:0.5ATR) | 6810円(+0.3%) | -8.0%(1.2ATR) | 120% | 2 | PrevL:6743->20D-L:6682 | PrevH:6963->20D-H:7100 | 80% |
```

### 5.6 Technical Summary US Market

Technical Summary の冒頭には、夜間米国指標セクションを表示する。表示位置はランク別銘柄テーブルより前とし、Tkinter の Markdown 出力、Web UI の HTML 表示のどちらにも同じ情報を含める。

見出しは `US Market YYYY-MM-DD HH:MM` とする。日時は取得処理全体の基準時刻を使い、日本時間（JST）で表示する。

表示列は次の通り。

| 列 | 内容 |
|---|---|
| 指標/銘柄 | 指数、先物、ETF、個別銘柄、商品名 |
| 直近値 | 前日終値または直近値の価格水準。取得できない場合は `N/A` |
| 前日騰落 | 前日終値比の騰落率 |
| 5日乖離 | 5日移動平均からの乖離率 |
| 25日乖離 | 25日移動平均からの乖離率 |
| RSI | RSI14 |

初期表示対象は yFinance から取得する。表示名とティッカーの対応は次の通り。

| 表示名 | yFinance ticker | 備考 |
|---|---|---|
| NASDAQ総合 | `^IXIC` | 米国グロース市場の地合い |
| SOX指数 | `^SOX` | 半導体セクター地合い |
| NVIDIA | `NVDA` | AI・半導体の代表銘柄 |
| GRID | `GRID` | First Trust NASDAQ Clean Edge Smart Grid Infrastructure Index Fund |
| 日経先物 | `NKD=F` | yFinance の日経225先物 |
| 銅先物(COMEX) | `HG=F` | yFinance のCOMEX銅先物 |
| WTI原油 | `CL=F` | yFinance のWTI原油先物 |

`GRID` は ETF の `GRID` として扱う。日経先物と銅先物は yFinance で取得する。直近値は価格水準を表示し、取得時刻は日本時間で表示する。

### 5.7 単一銘柄 Technical 短評

Technical Summary 一覧では、冒頭短評のまとめテーブルは表示しない。ランク別テーブルの分類結果を使って確認する。

単一銘柄 Technical 出力では、判断を速くするための短評を表示する。短評は1銘柄につき次の形式で表示する。

```text
{ランク} {表示名} {位置の説明}
```

例:

```text
A1 位置良好 リターン良好、買い候補
C2 崩れ警戒 監視のみ
```

短評はTechnicalランク、ランク表示名、ランク別の位置説明から生成する。判定ロジックと文言は domain 層の純粋関数で行う。Markdown / HTML への整形は builder / presentation 層で行い、GUI層には判定ロジックを書かない。

ランキング分類条件、判定優先順位、D1 / D2 / D3 の売買行動、補助ラベルは
`docs/technical_ranking_spec.md` を正とする。

表示仕様として、25日線以上は順張り押し目・過熱管理、25日線未満は
底打ち確認・戻り売り警戒として見せる。分類ロジックは domain 層の純粋関数に置き、
Markdown / HTML / 単一銘柄出力で共有する。

#### 5.7.1 表示位置

Technical Summary 一覧の Markdown / Web UI には短評専用テーブルを表示しない。短評は単一銘柄 Technical 出力だけに表示する。

#### 5.7.2 単一銘柄 Technical 出力

単一銘柄の Technical 出力にも同じ分類ロジックの短評を表示する。

表示位置は、既存の先頭サマリの直後、`■モメンタム` の直前とする。これにより、価格、25日線、VWAP、出来高、60日レンジの概況を見た直後に、売買判断用の短評を確認できる。

表示形式は次の通り。

```text
短評：{ランク} {表示名} {位置の説明}
```

D1 / D2 / D3の詳細分類は戦略判定の材料として残すが、単一銘柄詳細画面の短評文言には使わない。D / E 系の短評は従来のランク表示名と既存コメントを使う。

```text
短評：A1 位置良好 リターン良好、買い候補
短評：D1 戻り途中 25日線奪回待ち。上値確認中。
```

ランキング一覧上のコードはD1/D2/D3のままとし、D1a/D1bとD3強弱は戦略判定用の内部分類として扱う。

短評の後には、各条件が将来成立した場合の行動指針として戦略判定を表示する。
これは表示時点で売買シグナルが成立していることを意味しない。

```text
戦略判定：
前場深押し○：...
前場VWAP回復◎：...
後場VWAP回復◎：...
```

D系では詳細分類ごとに評価記号と文言を切り替え、ATR指値帯とRRを可能な範囲で
価格へ展開する。必要値が欠損する場合は `指値算出不可` または `RR算出不可` とする。
RR定義、D2からD3への昇格条件、地合い条件の扱いは
`docs/technical_ranking_spec.md` のD系詳細戦略判定を参照する。

単一銘柄 Technical 出力では、ランク別テーブル用の `TechnicalSummaryRow` ではなく、`TechnicalAnalysisResult` から同じ domain policy を使って短評を作る。文字列化は `app/domain/builders/technical_output.py` が担当する。

#### 5.7.3 実装上の変更点

- C2 の表示名は `崩れ警戒` とする。
- B1 の表示名は `過熱後半` とする。
- A1弱 は、A1とC1の間に置く25日線上の押し目候補ランクとして扱う。
- 25日線下でVWAP上の分類は `D1` / `D3` へ分ける。
- `TechnicalSummaryRank` は `B2` / `B1` / `A2` / `A1` / `A1弱` / `C2` / `C1` / `D1` / `D2` / `D3` / `E` を扱う。
- 監視銘柄 Technical Summary と単一銘柄 Technical 出力は、同じ分類・短評生成 policy を共有する。

## 6. 画面操作フロー

### 6.1 Web UI Fundamental モード

1. ユーザーが銘柄と Kabutan HTML フォルダを指定する。
2. `取得` ボタンで出力を生成する（既存機能）。
3. `サマリ表示` ボタンを押す。
4. サマリ生成処理が実行され、画面に HTML テーブルが表示される。
5. 必要なら `ダウンロード` もしくは `HTML保存` によって保存できる。

### 6.2 Web UI Technical モード

1. ユーザーが WatchList を指定する。
2. `Technical` を選択すると `サマリ表示` ボタンが有効になる。
3. `サマリ表示` ボタンを押す。
4. Technical Summary 生成処理が実行され、ランク別の HTML テーブルが表示される。
5. 必要なら Markdown または HTML として保存できる。

### 6.3 Tkinter GUI

- Fundamental の `サマリ出力` は既存どおり Markdown を生成してファイルへ保存する。
- Technical の `サマリ出力` は Technical Summary Markdown を生成してファイルへ保存する。

## 7. 追加設計メモ

- `サマリ表示` には `GET /summary` のような別エンドポイントを使っても良いが、現在の `POST /summary` を流用して差し替えるのが最小変更。
- `WebOutputBlock` に HTML テーブルブロックを追加し、`output_blocks` のレンダリングで扱う方式が既存の Web 表示ロジックと親和性が高い。
- Markdown 生成を再利用し、HTML 変換処理を別関数に切り出すと保守性が高まる。

## 8. Technical Summary 実装案

実装は既存の `TechnicalAnalysisService` と `TechnicalSnapshot` を再利用する。監視銘柄ごとに Technical 解析結果を作り、Technical Summary 用の行モデルへ変換し、ランク別にグルーピングして Markdown / HTML へ整形する。

追加・変更候補は次の通り。

| 対象 | 実装内容 |
|---|---|
| `app/domain/models/technical_summary.py` | `TechnicalSummaryRow`、`TechnicalSummaryTable`、支持線/抵抗線候補モデルを追加 |
| `app/domain/usecases/technical_summary.py` | WatchList を順に解析し、ランク判定、列値計算、支持線/抵抗線抽出、ランク別グルーピングを行う |
| `app/domain/policies/technical_summary.py` | A1/A2/B1/B2/C1/C2/D1/D2/D3/E のランク判定、単一銘柄Technical短評、支持線/抵抗線抽出を純粋関数として実装 |
| `app/domain/policies/technical_indicators.py` | 75日線を計算し、`TechnicalMovingAverageSnapshot` に追加 |
| `app/domain/models/us_market_summary.py` | US Market 行モデルとテーブルモデルを追加 |
| `app/domain/usecases/us_market_summary.py` | yFinance から対象指標を取得し、直近値、前日騰落、5日乖離、25日乖離、RSI14 を計算 |
| `app/domain/builders/technical_summary.py` | Tkinter 保存用 Markdown を生成 |
| `app/presentation/web_technical_summary.py` | Web UI 表示用 HTML テーブルを生成 |
| `app/gui_controller.py` | Technical タブの `サマリ出力` で Technical Summary Markdown を保存 |
| `app/web.py` | Technical モードの `/summary` で Technical Summary HTML を返す |
| `app/templates/index.html` | Technical モードでも `サマリ表示` ボタンを有効化 |
| `app/static/web.css` | 横スクロール、数値右寄せ、ランク見出し、N/A 表示を追加 |
| `tests/` | ランク境界、支持線/抵抗線抽出、Markdown/HTML出力、Web/Tkinter導線のテストを追加 |

データ取得失敗や必要値欠損がある銘柄は、Fundamental Summary と同様に skipped として理由を保持する。行単位の一部欠損は `N/A` 表示とし、分類に必要な現在値、25日線、VWAPが欠損する場合は skipped とする。

## 9. まとめ

- Web UI の `サマリ表示` は `サマリ出力` から名称変更する。
- Web UI Fundamental では Markdown 相当の情報を HTML 表で表示する。
- Web UI Technical ではランク別 Technical Summary を HTML 表で表示する。
- 保存はまず HTML 表のダウンロードを提案し、必要なら Markdown ダウンロードを追加する。
- Tkinter では Fundamental / Technical それぞれの Summary Markdown を保存する。
