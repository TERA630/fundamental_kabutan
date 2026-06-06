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
3. `■当日位置・レンジ`
4. `■移動平均・出来高`
5. `■前日評価`
6. `■支持線`
7. `■上値節目`

先頭サマリは、現在値、前日比、終端位置、VWAP差分、5日線、25日線、前日高値/安値、RSI、20日平均出来高比を表示する。

## 8. Technical 表示例

Technicalタブの表示例は次の通り。

```text
【銘柄】{name} ({code4})
株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（終端位置{day_close_position}）
Vwap：{vwap_diff}円（{vwap_diff_pct}、{vwap_diff_atr}）
5日線：{ma5}（乖離 {dev5_pct}）　25日線：{ma25}（乖離 {dev25_pct} / ATR比 {ma25_distance_atr}）
前日高値：{prev_high}　前日安値：{prev_low}　　　　{previous_high_evaluation}
RSI：{rsi14}　20日平均出来高比：{volume_vs_avg20}
5日高値 {recent5_high_distance_pct}　20日高値まで：{recent20_high_remaining_pct} 　　60日レンジ位置 {recent60_range_position}（{recent60_range_position_label}）

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

実装上の出力は `■支持線` までを本文として返す。先頭サマリ内の `5日高値`、`20日高値まで`、`60日レンジ位置` が上値節目の役割を担う。

VWAP が日足参考値の場合、`Vwap` 行の末尾に `(日足参考値)` を付ける。

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

## 12. Technical 先頭サマリ改定案

### 12.1 目的

Technical タブ冒頭の株価サマリは、スクリプト実行時点ではなく、実際に取得した日中値の鮮度を読み取れる形式へ変更する。

また、冒頭で判断したい 25日線からの位置、VWAP からの位置、直近3営業日のモメンタムを先頭サマリ内に集約する。

### 12.2 取得時刻

株価行の直下に、取得した日中値の日時を表示する。

```text
取得時刻：{intraday_datetime}
```

- `intraday_datetime` は、取得した日中値に紐づく日時を表示する。
- スクリプト起動時刻、GUI操作時刻、整形処理時刻は表示しない。
- 日中値の日時が取得できない場合は `取得時刻：N/A` と表示する。
- 日中値が5分足の場合は最新足の日時を使う。
- 日中値が日足参考値へフォールバックした場合は、日足データの日付を使い、必要に応じて既存の `(日足参考値)` 表示を併用する。

### 12.3 先頭サマリ表示形式

改定後の先頭サマリは次の形式を基本とする。

```text
【銘柄】{name} ({code4})
株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（終端位置{day_close_position}）
取得時刻：{intraday_datetime}
25日線解離：{dev25_pct}({ma25_distance_atr})　傾き：{ma25_slope_symbol}
Vwap：{vwap_diff_price}円({vwap_diff_pct}/{vwap_diff_atr}){vwap_source_suffix}

■モメンタム
3日高値更新：{mark_3bd_ago}{mark_2bd_ago}{mark_1bd_ago}
3日安値切り上げ：{mark_3bd_ago}{mark_2bd_ago}{mark_1bd_ago}
3日騰落率　{three_day_change_pct}
3日出来高　{volume_ratio_3bd_ago}→{volume_ratio_2bd_ago}→{volume_ratio_1bd_ago}
```

例:

```text
株価：7,120円（前日比+85.00円：+1.2%）（終端位置78.4%）
取得時刻：2026-06-05 14:55
25日線解離：+2.7%(0.45ATR)　傾き：↑
Vwap：-43.7円(-0.6%/-0.11ATR)

■モメンタム
3日高値更新：〇×〇
3日安値切り上げ：〇××
3日騰落率　+2.3%
3日出来高　68%→47%→128%
```

### 12.4 フォーマット規則

- `25日線解離` は現行の `dev25_pct` を使う。表記名はユーザー表示上の指定に合わせて `解離` とする。
- `ma25_distance_atr` は25日線からの距離の大きさとして表示する。例: `0.45ATR`。
- `傾き` は現行の `ma25_slope_symbol` と同じく `↑` / `↓` / `→` / `N/A` を使う。
- `Vwap` の価格差は現価格 `latest - vwap` を円で表示する。
- `Vwap` の割合は `(latest / vwap - 1) * 100` を表示する。
- `Vwap` の ATR 比は `vwap_diff_price / atr14` を符号付きで表示する。例: `-0.11ATR`。
- `Vwap` が日足参考値の場合は現行どおり `Vwap` 行末に `(日足参考値)` を付ける。
- 価格差、パーセント、ATR 比は欠損時に `N/A` とする。
- 符号はプラス値に `+`、マイナス値に `-` を付ける。
- 全角の `＋`、`－` は使わず、既存フォーマッタに合わせて半角 `+`、`-` を使う。

### 12.5 直近3営業日モメンタム

`■モメンタム` は、3営業日前、2営業日前、前営業日の順に左から表示する。

#### 3日高値更新

各対象営業日の高値が、その対象営業日の直前3営業日の高値最大値を上回る場合に `〇`、上回らない場合に `×` とする。

比較対象データが不足する場合は、該当位置を `N/A` とする。

#### 3日安値切り上げ

各対象営業日の安値が、その対象営業日の直前営業日の安値を上回る場合に `〇`、上回らない場合に `×` とする。

比較対象データが不足する場合は、該当位置を `N/A` とする。

#### 3日騰落率

`3日騰落率` は、3営業日前終値から前営業日終値までの累積騰落率を表示する。

```text
three_day_change_pct = (前営業日終値 / 3営業日前終値 - 1) * 100
```

必要な終値が不足する場合は `N/A` とする。

#### 3日出来高

`3日出来高` は、3営業日前、2営業日前、前営業日の各出来高を20日平均出来高で割った比率として表示する。

```text
volume_ratio = 対象営業日の出来高 / 対象営業日時点の20日平均出来高 * 100
```

分母が欠損または0の場合は、該当位置を `N/A` とする。

### 12.6 実装時の影響範囲

- `TechnicalSnapshot` へ日中値取得日時、または `TechnicalAnalysisResult` へ取得日時を渡す必要がある。
- 直近3営業日モメンタムは表示専用の値として、UseCase 側で計算済みDTOにしてから Builder へ渡す。
- `technical_output.py` は、計算ロジックを持たず、DTOの値を文字列化する責務に留める。
- 既存の `■前日評価` は残す。`■モメンタム` は先頭サマリの直後、`■当日位置・レンジ` の前に置く。
- 既存テスト `tests/test_technical_output.py` に、取得時刻、25日線解離/VWAP新形式、3営業日モメンタムの期待文字列を追加する。

## 13. コミットごとの作業分割案

1. `technical-analysis: expose intraday timestamp`
   - market data provider で取得した日中値の日時をDTOへ載せる。
   - 5分足取得時と日足参考値フォールバック時の `N/A` 条件をテストする。

2. `technical-analysis: add three-session momentum dto`
   - 3営業日前、2営業日前、前営業日の高値更新、安値切り上げ、騰落率、出来高比をUseCaseで計算する。
   - データ不足時の `N/A` をユニットテストする。

3. `presentation: revise technical opening summary`
   - `technical_output.py` の先頭サマリを改定案の形式へ更新する。
   - 取得時刻、25日線解離、VWAP、`■モメンタム` の表示テストを追加する。

4. `docs: update presentation spec for technical summary`
   - 実装完了後、改定案を正式仕様へ移動し、古い先頭サマリ記述との差分を整理する。
