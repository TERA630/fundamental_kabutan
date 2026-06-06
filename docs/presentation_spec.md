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
5. Quality / Growth / Valuation スコア詳細
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

[Valuation]
FCF Yield          {fcf_yield_value}({rank})
PER                {per_value}({rank})

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

取得できないブロックまたは値は `N/A` とする。株探通期業績が取得できない場合は、株探ソース行に取得不可理由を表示し、本文に `データーが取得できません` を表示する。

## 6. rankCF 表示

rankCF は `Quality`、`Growth`、`Valuation` の3カテゴリで表示する。総合判定は `S` / `A` / `B` / `C` を使う。

採点ルールそのものはドメイン層の `cf_scoring.py` が持ち、プレゼンテーション層は結果を表示するだけにする。

## 7. Technical 出力

Technical 出力は `app/domain/builders/technical_output.py` が組み立てる。

表示順は次の通り。

1. 銘柄ヘッダ
2. 先頭サマリ
3. `■モメンタム`
4. `■当日位置・レンジ`
5. `■移動平均・出来高`
6. `■前日評価`
7. `■支持線`

先頭サマリは、現在値、前日比、終端位置、取得時刻、25日線解離、25日線傾き、VWAP差分を表示する。取得時刻はスクリプト起動時刻ではなく、取得した日中値に紐づく日時を使う。

`■モメンタム` は、3営業日前、2営業日前、前営業日の順に、高値更新、安値切り上げ、3日騰落率、20日平均出来高比を表示する。

## 8. Technical 表示例

Technicalタブの表示例は次の通り。

```text
【銘柄】{name} ({code4})
株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（終端位置{day_close_position}）
取得時刻：{intraday_price_timestamp}
25日線解離：{dev25_pct}({ma25_distance_atr})　傾き：{ma25_slope_symbol}
Vwap：{vwap_diff_price}円({vwap_diff_pct}/{vwap_diff_atr}){vwap_source_suffix}

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

■移動平均・出来高
5日線：{ma5}（乖離 {dev5_pct}）
25日線：{ma25}（乖離 {dev25_pct} / ATR比 {ma25_distance_atr}）
14日ATR：{atr14}
出来高：{volume}

■前日評価
終値 {prev_close}（VWAP {prev_vwap_diff_price}円 / {prev_vwap_diff_pct} / {prev_vwap_diff_atr}）騰落率{prev_change_pct}

前日Vwap(前・後場)　{am_mark}/{pm_mark}  高値更新 {high_mark} / 安値維持 {low_mark}
前日出来高比　　{prev_volume_vs_avg20_pct}

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
前日出来高比　　{prev_volume_vs_avg20_pct}

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
