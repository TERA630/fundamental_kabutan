# プレゼンテーション層仕様

## 1. 目的

本書は、現行実装におけるプレゼンテーション層の責務と出力仕様を定義する。

プレゼンテーション層は、UseCaseが返すDTOと計算結果を表示用テキストへ変換する。データ取得、HTML解析、採点ロジック、指標計算は持たない。

## 2. 対象ファイル

| ファイル | 責務 |
|---|---|
| `app/presenters.py` | Fundamental出力とrankCF表示セクションの統合 |
| `app/domain/builders/fundamental_output.py` | Fundamental出力Builderの公開口 |
| `app/domain/builders/fundamental_output_impl.py` | Fundamental本文セクションの組み立て |
| `app/domain/builders/kabutan_output.py` | 株探業績、成長性、財務、四半期系セクション作成 |
| `app/domain/builders/analyst_estimates_output.py` | アナリスト予想欄の文字列化 |
| `app/domain/builders/technical_output.py` | Technical出力の文字列化 |
| `app/domain/builders/institutional_summary.py` | 機関投資サマリ固定パネルの文字列化 |
| `app/domain/builders/fundamental_summary.py` | 監視銘柄サマリMarkdownの文字列化 |
| `app/presentation/display_formatter.py` | 表示用フォーマット補助 |

## 3. 共通方針

- 表示上の `N/A`、数値丸め、単位、セクション順、空行、表形式はプレゼンテーション層で扱う。
- ドメイン層から受け取った `None` や欠損値は、表示時に `N/A` へ変換する。
- 表示用Builderは外部APIやファイルを直接読まない。
- 採点や分類の判定はドメイン層で行い、プレゼンテーション層は結果を整形する。
- GUI部品の生成やイベント処理は画面表示層の責務とし、本層には置かない。

## 4. Fundamental 出力

Fundamental 出力は `app/presenters.py` と `app/domain/builders/fundamental_output*.py` が組み立てる。

主な表示順は次の通り。

1. 銘柄ヘッダ
2. 冒頭サマリー
3. バリュエーション
4. rankCF サマリー
5. Quality / Growth スコア詳細
6. アナリスト
7. CF 経時
8. 成長性経時
9. 財務
10. 四半期トレンド
11. 株探業績テーブル

アナリスト欄は yFinance の目標株価、アナリスト人数、今期/来季 EPS 修正人数を表示する。取得できない値は `N/A` とする。

## 5. Fundamental 表示例

Fundamentalタブの表示例は次の通り。

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

■アナリスト
目標株価 {target_mean_price}円(現価格との乖離{target_gap_pct}：アナリスト{analyst_count}人)
今期EPS修正 ↑{current_up} ↓{current_down}
来季EPS修正 ↑{next_up} ↓{next_down}

■株探 通期業績推移
株探ソース: {source}
年度|売上|営業益|経常益|最終益|修正一株益|修正一株配当
{year_label}|{sales}|{operating_profit}|{ordinary_profit}|{net_profit}|{eps}|{dividend}

■キャッシュフロー
年度 | 営業CF | FCF | 投資積極性 | 現金残高
{year_label} | {operating_cf} | {free_cf} | {investment_label} | {cash_balance}

■成長性経時
年度|売上成長率|営業利益成長率|EPS成長率
{year_label}|{sales_growth}|{operating_profit_growth}|{eps_growth}

■財務ブロック
ROE(%)|ROIC(%)|PBR|
{year_label}　{roe}|{roic}|{pbr}

■四半期トレンド
　　　売上|営業利益率|昨年同期比|修正一株益
{quarter_label}　{quarter_sales}|{quarter_operating_margin}|{quarter_yoy}|{quarter_eps}
```

`■株価評価・資本効率` は、年度行から `FCF Yield` 行までを表として扱う。後続の `Quality {quality_score}点 ...`、`[Quality]`、`[Growth]`、`ルール注記:` は表に含めず通常テキストとして表示する。`[Valuation]` 詳細ブロックは `■株価評価・資本効率` と内容が重複するため表示しない。

取得できないブロックまたは値は `N/A` とする。株探通期業績が取得できない場合は、株探ソース行に取得不可理由を表示し、本文に `データーが取得できません` を表示する。

## 6. rankCF 表示

rankCF は `Quality`、`Growth`、`Valuation` の3カテゴリで表示する。総合判定は `S` / `A` / `B` / `C` を使う。

採点ルールそのものはドメイン層の `cf_scoring.py` が持ち、プレゼンテーション層は結果を表示するだけにする。

## 7. Technical 出力

Technical 出力は `app/domain/builders/technical_output.py` が組み立てる。

表示順は次の通り。

1. 銘柄ヘッダ
2. 先頭サマリ
3. 冒頭短評
4. 崩れ警戒、崩れ警戒スコア、底打ち初動判定、ホールド判定
5. `■モメンタム`
6. `■当日位置・レンジ`
7. `■移動平均`
8. `■前日評価`
9. `■支持線`

先頭サマリは、現在値、前日比、終端位置、取得時刻、25日線解離、25日線傾き、VWAP差分、当日出来高の20日平均比、60日レンジ位置を表示する。取得時刻はスクリプト起動時刻ではなく、取得した日中値に紐づく日時を使う。

冒頭短評は、先頭サマリの直後、`■モメンタム` の直前に表示する。表示形式は次の通り。

```text
短評：{区分} {表示名}｜{冒頭コメント}｜{次アクション}
```

例:

```text
短評：D1 戻り途中｜25日線回復待ち。｜後場VWAP維持なら監視継続
```

冒頭短評の判定は domain policy で行い、`app/domain/builders/technical_output.py` は受け取った判定結果を文字列化する。GUI層には判定ロジックを持たない。分類と文言は `docs/Summery_spec.md` の `Technical Summary 冒頭短評` に合わせる。

冒頭短評の直後には次の判定を表示する。崩れ警戒とホールド判定は25日線の上下にかかわらず表示する。底打ち初動判定は現在値が25日線未満の場合だけ表示する。スコアリングと判定条件は `docs/current_implementation_spec.md` の `単一銘柄の崩れ警戒スコア` および `底打ち初動・ホールド判定` を正とする。

```text
崩れ警戒：{低/中/高}
崩れ警戒スコア：{score}点
底打ち初動判定：{未成立/成立}
ホールド判定：{◎/○/△/×}
```

25日線以上の場合は `底打ち初動判定` 行を出力しない。主要値が欠損して判定できない場合は、該当値を `N/A` と表示する。

日中5分足が取得できる場合、先頭サマリには前後場VWAPを追加表示する。現在が前場か後場かの判定は、PC時刻ではなく取得済み5分足の最新バー時刻で行う。既存の前日VWAP分割と同じく、`12:30` 未満を前場、`12:30` 以降を後場とする。

- 最新バーが前場の場合: 前場VWAPのみ表示する。
- 最新バーが後場の場合: 前場VWAPと後場VWAPを表示する。
- 日中5分足が取得できず日足参考値へフォールバックした場合: 前場VWAP、後場VWAPは `N/A` とする。

`■モメンタム` は、3営業日前、2営業日前、前営業日の順に、高値更新、安値切り上げ、3日騰落率、20日平均出来高比を表示する。

## 8. Technical 表示例

Technicalタブの表示例は次の通り。

```text
【銘柄】{name} ({code4})
株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（終端位置{day_close_position}）
取得時刻：{intraday_price_timestamp}
25日線解離：{dev25_pct}({ma25_distance_atr})　傾き：{ma25_slope_symbol}
Vwap：{vwap_diff_price}円({vwap_diff_pct}/{vwap_diff_atr}){vwap_source_suffix}
前場Vwap：{am_vwap}
後場Vwap：{pm_vwap}
当日出来高：20日平均比　{volume_vs_avg20_pct}(前日出来高比　{volume_vs_previous_pct})　{volume_ratio_label}
60日レンジ位置：{recent60_range_position}　{recent60_range_position_label_detail}

短評：{headline_summary}
崩れ警戒：{collapse_risk_level}
崩れ警戒スコア：{collapse_risk_score}点
底打ち初動判定：{bottoming_start_judgement}
ホールド判定：{hold_judgement}

■モメンタム
3日高値更新：{high_breakout_3bd_ago}{high_breakout_2bd_ago}{high_breakout_1bd_ago}
3日安値切り上げ：{low_higher_3bd_ago}{low_higher_2bd_ago}{low_higher_1bd_ago}
3日騰落率　{three_session_change_pct}
3日出来高　{volume_ratio_3bd_ago}→{volume_ratio_2bd_ago}→{volume_ratio_1bd_ago}

■当日位置・レンジ
始値：{open}
高値：{high}
安値：{low}
終値：{close}
当日値幅：{day_range}（ATR比 {day_range_atr} / {day_range_label}）

■移動平均
5日線：{ma5}（乖離 {dev5_pct}）
25日線：{ma25}（乖離 {dev25_pct} / ATR比 {ma25_distance_atr}）
14日ATR：{atr14}

■前日評価
終値 {prev_close}（VWAP {prev_vwap_diff_price}円 / {prev_vwap_diff_pct} / {prev_vwap_diff_atr}）騰落率{prev_change_pct}

前日Vwap(前・後場)　{am_mark}/{pm_mark}  高値更新 {high_mark} / 安値維持 {low_mark}
前日出来高：　20日平均比　{prev_volume_vs_avg20_pct}(前々日比　{prev_volume_change_pct})

後場評価 {previous_pm_evaluation} / VWAP{previous_pm_vwap_position}

前日レンジ {prev_low}-{prev_high}（{prev_range_atr}）　終位置 {prev_close_position}
前日ローソク足型：　{prev_candle_body_label}

■支持線
前日安値：{prev_low}
20日安値：{recent20_low}
60日安値：{recent60_low}
```

実装上の出力は `■支持線` までを本文として返す。

VWAP が日足参考値の場合、`Vwap` 行の末尾に `(日足参考値)` を付ける。日中値の日時が取得できない場合は `取得時刻：N/A` と表示する。日中値が5分足の場合は最新足の日時を使い、日足参考値へフォールバックした場合は日足データの日付と `終値` を使う。

25日線のATR比は25日線からの距離の大きさとして表示する。VWAPのATR比は `latest - vwap` を `atr14` で割った符号付き値として表示する。

前場VWAPと後場VWAPは、日中5分足の `High`、`Low`、`Close` の代表価格 `(High + Low + Close) / 3` に出来高を掛け、対象時間帯の出来高合計で割って算出する。出来高が0または対象時間帯の足が不足する場合は `N/A` とする。前場VWAPは `09:00` 以上 `12:30` 未満、後場VWAPは `12:30` 以降の足を対象にする。表示は価格のみとし、価格フォーマットは既存のVWAP価格表示に合わせる。

後場に入った直後など、後場の出来高付き5分足がまだ存在しない場合、後場VWAPは `N/A` とする。前場のみの時間帯では後場VWAP行を表示しない。

当日出来高の20日平均比は、当日出来高を当日時点の20日平均出来高で割った比率として表示する。あわせて、当日出来高を前営業日出来高で割った騰落率を `前日出来高比` として表示する。`■移動平均` ブロックでは当日出来高の実数は表示しない。

当日出来高の20日平均比には次の評価コメントを付ける。

| 20日平均比 | 表示 |
|---:|---|
| 60%未満 | 出来高薄い |
| 60%以上80%未満 | 出来高やや薄い |
| 80%以上120%未満 | 通常 |
| 120%以上180%未満 | 出来高伴う |
| 180%以上 | 出来高急増 |

60日レンジ位置は、`(現在値 - 60日安値) / (60日高値 - 60日安値) * 100` として表示する。60日高値と60日安値が同値、または必要値が不足する場合は `N/A` とする。

60日レンジ位置には次の判定を付ける。

| 60日レンジ位置 | 表示 |
|---:|---|
| 0%未満 | 60日安値割れ / 見送り |
| 0%以上20%以下 | 安値圏 / 底割れ警戒 |
| 20%超40%以下 | 下位圏 / 反発待ち |
| 40%超60%以下 | 中位圏 / 方向確認 |
| 60%超80%以下 | 上位圏 / 押し目候補 |
| 80%超100%以下 | 高値圏 / 過熱・上値追い警戒 |
| 100%超 | 高値更新 / 飛びつき警戒 |

境界値は上限側に含める。例: `20.0%` は `安値圏 / 底割れ警戒`、`40.0%` は `下位圏 / 反発待ち` とする。

前日出来高の20日平均比は、前営業日の出来高を前営業日時点の20日平均出来高で割った比率として表示する。前々日比は、前営業日の出来高を前々営業日の出来高で割った騰落率として表示する。

`■モメンタム` の各値は次の通り。

- `3日高値更新`: 各対象営業日の高値が、その対象営業日の直前3営業日の高値最大値を上回る場合に `〇`、上回らない場合に `×` とする。
- `3日安値切り上げ`: 各対象営業日の安値が、その対象営業日の直前営業日の安値を上回る場合に `〇`、上回らない場合に `×` とする。
- `3日騰落率`: 3営業日前終値から前営業日終値までの累積騰落率を表示する。
- `3日出来高`: 各対象営業日の出来高を、対象営業日時点の20日平均出来高で割った比率として表示する。

比較対象または分母が不足する場合は、該当値を `N/A` とする。

## 9. 前日評価表示

```text
■前日評価
終値 {prev_close}（VWAP {prev_vwap_diff_price}円 / {prev_vwap_diff_pct} / {prev_vwap_diff_atr}）騰落率{prev_change_pct}

前日Vwap(前・後場)　{am_mark}/{pm_mark}  高値更新 {high_mark} / 安値維持 {low_mark}
前日出来高：　20日平均比　{prev_volume_vs_avg20_pct}(前々日比　{prev_volume_change_pct})

後場評価 {previous_pm_evaluation} / VWAP{previous_pm_vwap_position}

前日レンジ {prev_low}-{prev_high}（{prev_range_atr}）　終位置 {prev_close_position}
前日ローソク足型：　{prev_candle_body_label}
```

ヒゲありの場合のみ、ローソク足型へ `＋上髭` または `＋下髭` を付ける。ヒゲなしの場合は追記しない。

例:

```text
前日ローソク足型：　小陽線
前日ローソク足型：　陰線＋上髭
```

## 10. 機関投資サマリ表示

機関投資サマリ固定パネルの表示形式は次の通り。

```text
機関投資サマリ
時価総額：{market_cap_oku}億円（{market_cap_class}）
流動性：出来高 {volume}（20日平均比 {volume_vs_avg20_pct}） 売買代金 {trading_value_oku}億円
機関投資スコア：{score}/20点　Fundamental Score：{fundamental_score}点（{rank}）　Technical：VWAP {○/×} / 5日線 {○/×} / 25日線 {○/×}
```

VWAP が日足参考値の場合、VWAP判定の後ろに `(日足参考値)` を付ける。

## 11. 監視銘柄 Fundamental サマリ

`fundamental_summery-yyyy-mm-dd.md` は Markdown 表として出力する。

列は次の通り。

```text
銘柄名(銘柄コード), 総合スコア, Quality, Growth, Valuation, 営業利益率, 営業利益3年CAGR, ROIC, Cash conversion, PER, 投資率
```

行は総合スコアの降順で並べる。分析不能な銘柄は除外一覧に載せる。

## 12. Technical 先頭サマリ追加 実装案

今回の追加は単一銘柄の Technical 出力に閉じ、GUI層には表示ロジックを追加しない。計算は domain 層、文字列化は既存の Technical 出力Builderで扱う。

変更候補は次の通り。

| 対象 | 実装内容 |
|---|---|
| `app/domain/models/technical_snapshot.py` | 必要に応じて当日出来高の前日比、詳細な60日レンジ判定の保持先を追加する。ただし小さな差分を優先し、既存値からBuilderで表示計算できるものはモデル追加しない |
| `app/domain/policies/market_history.py` | 本日5分足から前場VWAP、後場VWAP、最新足が前場か後場かを計算する純粋関数を追加し、`build_intraday_vwap_snapshot()` の戻り値へ含める |
| `app/domain/policies/technical_indicators.py` | 当日出来高の前日比を算出する。60日レンジ位置は既存の `recent60_range_position` を使う |
| `app/domain/policies/technical_output_labels.py` もしくは既存policy | 出来高20日平均比コメント、60日レンジ位置コメントを純粋関数として追加する。小規模なら既存のtechnical系policyに追加する |
| `app/domain/builders/technical_output.py` | 先頭サマリに前場/後場VWAP、出来高評価コメント、前日出来高比、60日レンジ位置と判定を表示し、その直後に冒頭短評を表示する |
| `tests/test_market_data_provider_technical.py` | 前場のみ、後場あり、出来高0、日足参考値フォールバック時の前後場VWAPを検証する |
| `tests/test_technical_output.py` | 新しい先頭サマリの表示文字列、N/A表示、前場時に後場VWAPを出さないことを検証する |
| `tests/test_technical_indicators.py` | 当日出来高の前日比、60日レンジ境界値の材料値を検証する |

実装順は次の通り。

1. `market_history.py` に本日前後場VWAP計算を追加し、既存の5分足正規化とセッション抽出を再利用する。
2. 出来高コメント、60日レンジコメントをdomain policyへ追加し、境界値テストを先に書く。
3. `technical_output.py` の先頭サマリ直後に冒頭短評を追加する。
4. `python -m pytest tests/test_market_data_provider_technical.py tests/test_technical_indicators.py tests/test_technical_output.py` で確認する。
