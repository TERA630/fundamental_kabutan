# 画面・表示仕様

## 1. 目的

本書は、現行実装における GUI 画面、Web UI、および画面へ表示する出力テキストの仕様を定義する。

画面層は UI 部品、ユーザー操作、タブ、ステータス、コピー、保存を担当する。表示用Builderは UseCase が返す DTO と判定結果をテキストまたは HTML に整形する。データ取得、HTML解析、採点・分類・指標計算は持たない。

## 2. 対象ファイル

| ファイル | 責務 |
|---|---|
| `app/gui.py` | Tkinterアプリ本体、イベント連携、状態遷移 |
| `app/gui_view.py` | Widget構築、タブ、テキスト欄、ボタン、固定パネル |
| `app/gui_view_model.py` | ステータスメッセージ生成 |
| `app/gui_state.py` | GUI状態、銘柄選択、出力キャッシュキー |
| `app/gui_controller.py` | GUIイベントからUseCase呼び出しへの仲介 |
| `app/presenters.py` | Fundamental出力とrankCF表示セクションの統合 |
| `app/domain/builders/fundamental_output*.py` | Fundamental本文の組み立て |
| `app/domain/builders/technical_output.py` | 単一銘柄Technical出力の文字列化 |
| `app/domain/builders/institutional_summary.py` | 機関投資サマリ固定パネルの文字列化 |
| `app/domain/builders/*_summary.py` | サマリMarkdownの文字列化 |
| `app/domain/builders/hybrid_evaluation_output.py` | 単一銘柄Hybrid評価の文字列化 |
| `app/presentation/display_formatter.py` | 数値・欠損値などの表示補助 |
| `app/presentation/web_*_summary.py` | サマリのWeb表示用HTML変換 |

## 3. 画面構成

アプリ名は `ファンダメンタル評価 v8（株探/yFinanceベース）`。

画面は次の領域で構成する。

- 監視銘柄ファイル選択
- 株探HTMLフォルダ選択
- 銘柄選択コンボボックス
- `取得` / `Hybrid評価` / `地合評価` / `サマリ出力` / `コピー` / `保存` ボタン
- ステータスメッセージ
- 機関投資サマリ固定パネル
- `Fundamental` / `Technical` タブ
- 各タブのテキスト出力欄

## 4. 操作仕様

- 監視銘柄ファイルは Markdown / Text を読み込む。
- 株探HTMLフォルダは任意で指定できる。指定時は Fundamental でHTML優先取得に使う。
- `取得` は選択中タブに応じて Fundamental または Technical を出力する。
- `Hybrid評価` は選択中銘柄に対して Fundamental と Technical の評価材料を合流し、単一銘柄出力へ追記する。監視銘柄全体のHybrid一覧サマリは生成しない。
- `地合評価` は選択中銘柄にセクタータグがある場合のみ、該当セクターの地合を単一銘柄出力へ追記する。`取得` では自動追記しない。
- `コピー` は選択中タブのテキストをクリップボードへコピーする。
- `保存` は選択中タブのテキストをファイルへ保存する。
- `サマリ出力` は選択中タブに応じて監視銘柄サマリの Markdown ファイルを作成する。Fundamental のファイル名は `fundamental_summary-YYYY-MM-DD.md`、Technical は `technical_summary_MM-DD-HH-MM.md` とする。

## 5. ステータス表示

| 状態 | 表示 |
|---|---|
| 初期 | `監視銘柄ファイルを読み込んでください。` |
| 監視銘柄ロード | `{count}件の監視銘柄を読み込みました。` |
| 監視銘柄復元 | `前回の監視銘柄ファイルを復元しました（{count}件）。` |
| 銘柄選択 | `銘柄を選択しました。取得ボタンを押してください。` |
| 銘柄未選択 | `先に監視銘柄ファイルと銘柄を選んでください。` |
| 銘柄なし | `銘柄が見つかりませんでした。` |
| 取得中 | `取得中: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance` |
| 生成完了 | `生成完了: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance` |
| キャッシュ表示 | `キャッシュ表示: {name} ({code4})` |
| 取得失敗 | `取得に失敗しました。` |
| コピー対象なし | `コピーするテキストがありません。` |
| コピー完了 | `クリップボードにコピーしました。` |
| 保存対象なし | `保存するテキストがありません。` |
| 保存完了 | `保存完了: {path}` |
| 保存失敗 | `保存に失敗しました。` |
| サマリ作成中 | `サマリ作成中です。` |
| サマリ失敗 | `サマリ作成に失敗しました。` |
| Hybrid評価追加 | `Hybrid評価を追加しました。 / 評価時点={evaluation_label}` |
| 地合評価追加 | `地合評価を追加しました。 / 評価時点={evaluation_label}` |
| 株探HTMLフォルダ選択 | `株探HTMLフォルダを設定しました（出力キャッシュをクリア）。` |
| 株探HTMLフォルダ再選択要求 | `株探HTMLフォルダが見つかりません。再選択してください。` |

## 6. 機関投資サマリ固定パネル

固定パネルはタブに関係なく表示する。

初期表示は次の通り。

```text
機関投資サマリ
時価総額：N/A
流動性：N/A
機関投資スコア：N/A
```

取得後の表示形式は次の通り。

```text
機関投資サマリ
時価総額：{market_cap_oku}億円（{market_cap_class}）
流動性：出来高 {volume}（20日平均比 {volume_vs_avg20_pct}） 売買代金 {trading_value_oku}億円
機関投資スコア：{score}/20点　Fundamental Score：{fundamental_score}点（{rank}）　Technical：VWAP {○/×} / 25日線 {○/×}
```

VWAP が日足参考値の場合、VWAP判定の後ろに `(日足参考値)` を付ける。

## 7. キャッシュ表示

- GUI出力キャッシュは当日分のみ再利用する。
- キャッシュヒット時は新規取得せず、選択中タブへ保存済みテキストを表示する。
- 株探HTMLフォルダを変更した場合は、出力キャッシュをクリアする。
- 日付が変わった場合は、GUI出力キャッシュをクリアする。

## 8. サマリ画面の操作

- Web UI のボタン名は `サマリ表示` とする。`Fundamental` / `Technical` のどちらのモードでも利用できる。
- Fundamental モードでは WatchList と株探HTMLフォルダを前提に Fundamental サマリを生成し、HTML 表として画面へ表示する。
- Technical モードでは WatchList を前提に Technical サマリを生成し、ランク別の HTML 表として画面へ表示する。
- Tkinter の `サマリ出力` は、選択中タブに応じた Markdown ファイルを保存する。出力内容とファイル名は `docs/Summery_spec.md` を正とする。

## 9. 出力表示の共通規則

- 表示上の `N/A`、数値丸め、単位、セクション順、空行、表形式は表示用Builderが扱う。
- ドメイン層から受け取った `None` や欠損値は、表示時に `N/A` へ変換する。
- 表示用Builderは外部APIやファイルを直接読まない。採点と分類はドメイン層が行い、Builderは結果を整形する。
- GUI部品の生成とイベント処理は画面層の責務とし、表示用Builderには置かない。
- サマリ画面・サマリファイルの表構造と列定義は `docs/Summery_spec.md` を正とする。

## 10. Fundamental 出力

Fundamental 出力は `app/presenters.py` と `app/domain/builders/fundamental_output*.py` が組み立てる。表示順は、銘柄ヘッダ、冒頭サマリー、バリュエーション、rankCF サマリー、Quality / Growth スコア詳細、アナリスト、CF 経時、成長性経時、財務、四半期トレンド、株探業績テーブルとする。

アナリスト欄は yFinance の目標株価、アナリスト人数、今期・来期 EPS 修正人数を表示する。取得できない値は `N/A` とする。rankCF は `Quality`、`Growth`、`Valuation` の3カテゴリで表示し、総合判定は `S` / `A` / `B` / `C` を使う。採点ルールはドメイン層の `cf_scoring.py` を正とする。

```text
【{name} ({code4})】
株価 {price}円　時価総額 {market_cap_oku}億円（{market_cap_class}）

総合評価 {rank}（{total_score}/100）
{growth_phase} / {per_level} / {roic_level}

■株価評価・資本効率
年度|{year_1}|{year_2}|{year_3}
PER|{per_1}|{per_2}|{per_3}
配当利回り|{dividend_yield_1}|{dividend_yield_2}|{dividend_yield_3}
PBR|{pbr}
ROE|{roe}
ROIC|{roic}
FCF Yield|{fcf_yield}

Quality {quality_score}点 Growth {growth_score}点 Valuation {valuation_score}点

[Quality]
ROIC               {roic_value}({rank})
Cash Conversion    {cash_conversion_value}({rank})
営業CFマージン      {ocf_margin_value}({rank})
営業利益率          {operating_margin_value}({rank})
FCF Ratio          {fcf_ratio_value}({rank})

[Growth]
EPS CAGR           {eps_cagr_value}({rank})
売上CAGR           {sales_cagr_value}({rank})
営業利益CAGR(3y)   {operating_profit_cagr_value}({rank})
```

`■株価評価・資本効率` は年度行から `FCF Yield` 行までを表として扱う。後続のスコア行、`[Quality]`、`[Growth]`、ルール注記は通常テキストとする。`[Valuation]` 詳細ブロックは同表と重複するため表示しない。株探通期業績を取得できない場合は、株探ソース行に理由を、本文に `データーが取得できません` を表示する。

## 11. 単一銘柄 Technical 出力

Technical 出力は `app/domain/builders/technical_output.py` が組み立てる。表示順は、取得時刻、銘柄ヘッダと先頭サマリ、冒頭短評、崩れ警戒・底打ち初動・ホールド判定、戦略判定、`■モメンタム`、`■当日位置・レンジ`、`■重要価格`、`■前日評価` とする。`Hybrid評価` と `地合評価` はボタン押下時だけ、Technical 出力欄の本文末尾へ追記する。

先頭サマリは、取得時刻、銘柄名とコード、現在値、前日比、終端位置、出来高比、25日線乖離、VWAP差分、前後場VWAP位置、60日レンジ位置、リスクリターン、下値、抵抗線、当日前後場VWAP判定を8行に圧縮して表示する。下値は前日安値、25日線、20日安値、60日安値、75日線のうち現在値未満の価格を近い順に最大3価格表示する。抵抗は前日高値、25日線、20日高値、60日高値のうち現在値より上の価格を近い順に表示する。下値と抵抗は同価格のラベルを `/` で併記し、現在値に近い順に `→` で連結する。各下値・抵抗には現在値基準の余地を正のパーセントで併記する。25日線傾きと前後場VWAP価格は先頭サマリへ表示しない。取得時刻には、スクリプト起動時刻ではなく取得した日中値に紐づく日時を使う。

### 11.1 Technical 短評と戦略判定

Technical Summary 一覧の Markdown / Web UI に、短評専用テーブルは表示しない。短評は単一銘柄 Technical 出力だけに表示する。

短評は先頭サマリの直後、`■モメンタム` の直前に次の形式で表示する。

```text
短評：{ランク} {表示名} {位置の説明}
```

例:

```text
短評：A1 位置良好 リターン良好、買い候補
短評：C2 崩れ警戒 監視のみ
```

短評は Technical ランク、ランク表示名、ランク別の位置説明から生成する。判定と文言は domain policy が担い、`technical_output.py` は判定結果を文字列化する。D1 / D2 / D3 の詳細分類は戦略判定の材料として残すが、短評文言には使わない。D / E 系の短評は従来のランク表示名と既存コメントを使う。分類条件、判定優先順位、D系の売買行動および補助ラベルは `docs/technical_ranking_spec.md` を正とする。

短評の後には、将来各条件が成立した場合の行動指針として戦略判定を表示する。これは表示時点で売買シグナルが成立していることを意味しない。D系は詳細分類ごとに評価記号と文言を切り替え、ATR指値帯とRRを可能な範囲で価格へ展開する。必要値が欠損する場合は `指値算出不可` または `RR算出不可` とする。単一銘柄出力は `TechnicalSummaryRow` ではなく `TechnicalAnalysisResult` から同じ domain policy を使って短評を作る。

### 11.2 判定・VWAP表示

短評の直後には次を表示する。崩れ警戒とホールド判定は25日線の上下にかかわらず表示し、底打ち初動判定は現在値が25日線未満の場合だけ表示する。判定条件は `docs/current_implementation_spec.md` の「単一銘柄の崩れ警戒スコア」および「底打ち初動・ホールド判定」を正とする。

```text
崩れ警戒：{低/中/高}（{score}点）
底打ち初動判定：{未成立/成立}
ホールド判定：{◎/○/△/×}
```

主要値が欠損して判定できない場合は該当値を `N/A` とする。日中5分足が取得できる場合、先頭サマリの `需給（VWAP）` 行には現在価格が当日前場・後場それぞれのVWAP以上なら `◯`、未満なら `×`、判定不能なら `N/A` を表示する。同じ行へ前日前場・後場のVWAP維持判定も表示する。前後場VWAPの価格は `■重要価格` に表示する。

前後場の判定にはPC時刻でなく、取得済み5分足の最新バー時刻を使う。`12:30` 未満を前場、以降を後場とする。最新バーが前場なら当日前場だけ、後場なら当日前後場とも表示する。日足参考値へフォールバックした場合、当日は `N/A`、前日前後場は取得結果を表示する。後場に出来高付き5分足がない場合、後場VWAPは `N/A` とする。

### 11.3 Technical 出力形式と数値規則

```text
取得時刻：{intraday_price_timestamp}
【銘柄】{name} ({code4})
　株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（終端位置{day_close_position}） | 出来高比　{volume_vs_avg20_pct}(前日比{volume_vs_previous_pct})
　位置：25日線{dev25_pct}/{ma25_distance_atr} | VWAP{vwap_diff_price}円/{vwap_diff_atr}{vwap_source_suffix} | 前場VWAP{current_am_vwap_position_pct} 後場VWAP{current_pm_vwap_position_pct} | 60日レンジ　{recent60_range_position} |
　リスクリターン：{risk_reward}
　下値：{downside_target_levels_with_room}
　抵抗：{resistance_levels_with_room}
　需給（VWAP）：当日前場／後場　{current_am_mark}／{current_pm_mark}　前日前場／後場　{previous_am_mark}／{previous_pm_mark}

短評：{headline_summary}
崩れ警戒：{collapse_risk_level}（{collapse_risk_score}点）
底打ち初動判定：{bottoming_start_judgement}
ホールド判定：{hold_judgement}
```

実装上の本文は `■前日評価` までを返す。VWAP が日足参考値なら `Vwap` 行の末尾に `(日足参考値)` を付ける。日中値の日時が取得できない場合は `取得時刻：N/A`、日足参考値なら日足データの日付と `終値` を使う。25日線のATR比は25日線からの距離の大きさ、VWAPのATR比は `(latest - vwap) / atr14` の符号付き値とする。前場VWAP・後場VWAP位置は既存互換の現在値基準とし、`(現在値 - 対象VWAP) / 現在値 * 100` で表示する。現在値が対象VWAPより上なら `+`、下なら `-` とする。

リスクリターンは、現在値より下の下値候補と現在値より上の抵抗候補から、現在値に近い有効な1本ずつを選び、`(抵抗 - 現在値) / (現在値 - 下値)` で算出する。ただしRR算出用に限り、現在値からの距離が `0.20ATR` 未満、または `0.3%` 未満の下値・抵抗は近すぎる節目として除外し、次の節目を使う。表示上の下値・抵抗一覧には近すぎる節目も残す。有効な下値または抵抗がない場合は `N/A` とする。

前後場VWAPは日中5分足の代表価格 `(High + Low + Close) / 3` を出来高加重平均して求める。出来高が0または対象時間帯の足が不足する場合は `N/A` とする。前場は `09:00` 以上 `12:30` 未満、後場は `12:30` 以降を対象とする。

当日出来高の20日平均比は当日出来高を当日時点の20日平均出来高で割り、前日比は当日出来高を前営業日出来高で割る。`■重要価格` には当日出来高の実数を表示しない。出来高比の表示は、60%未満を「出来高薄い」、60%以上80%未満を「出来高やや薄い」、80%以上120%未満を「通常」、120%以上180%未満を「出来高伴う」、180%以上を「出来高急増」とする。

60日レンジ位置は `(現在値 - 60日安値) / (60日高値 - 60日安値) * 100` とし、分母が0または必要値が不足すれば `N/A` とする。0%未満は「60日安値割れ / 見送り」、0%以上20%以下は「安値圏 / 底割れ警戒」、20%超40%以下は「下位圏 / 反発待ち」、40%超60%以下は「中位圏 / 方向確認」、60%超80%以下は「上位圏 / 押し目候補」、80%超100%以下は「高値圏 / 過熱・上値追い警戒」、100%超は「高値更新 / 飛びつき警戒」とする。境界値は上限側に含める。

`■モメンタム` は3営業日前、2営業日前、前営業日の順に高値更新、安値切り上げ、3日騰落率、20日平均出来高比を表示する。高値更新は直前3営業日の高値最大値を上回るとき `〇`、安値切り上げは直前営業日の安値を上回るとき `〇` とする。比較対象または分母が不足する場合は `N/A` とする。

`■前日評価` 後場評価は分類ラベルだけを表示し、 ヒゲありの場合のみ、ローソク足型に `＋上髭` または `＋下髭` を付ける。

### 11.4 Hybrid評価表示

単一銘柄画面では、`Hybrid評価` ボタンを押した場合のみ、Technical 出力欄の本文末尾に Hybrid評価を追記する。
Hybrid評価は Fundamental Summary 相当のスコア行と Technical Summary 相当のテクニカル行を選択銘柄1件について作成し、Hybrid分類条件へ渡して表示する。
分類条件に該当しない場合は `分類：該当なし` と表示する。Fundamental総合スコアを作成できない場合は `評価不可` として理由を表示する。

表示例:

```text
■Hybrid評価
分類：F1 高ファンダ深押し反転候補
F：72 / Q：44
理由：F72 / 高値更新1 / 安値切下げ1 / 出来高85%
```

### 11.5 セクター地合表示

単一銘柄 Technical 出力では、`地合評価` ボタンを押した場合のみ、選択銘柄に紐づくセクター地合を本文末尾に追記する。`取得` ボタンでは自動表示しない。
タグなし銘柄、または同セクターの集計結果が作れない場合は表示しない。
セクター地合は単一銘柄の主判定を直接変更せず、同テーマ内の横断的な補助情報として扱う。

表示例:

```text
■セクター地合
半導体材料・装置：強い上昇地合い
　VWAP上 9/12 75% / 終端中央値 78% / 25日線上 10/12 83% / 崩れ中央値 1.5 / 出来高比中央値 68%
　コメント：セクター買い優勢 / 高値圏維持、買い優勢 / 健全
```

複数セクタータグがある銘柄では、該当セクターを複数行で表示する。
