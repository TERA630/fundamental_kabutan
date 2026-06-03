# 株価取得・指標作成・表示エンジン移植仕様書

## 1. 位置づけ

本書を、プログラムの株価取得・指標作成・表示エンジン追加に関する正本仕様とする。


## 1．2 作業目標

　1．　GUIに、Technical / Fundamental の切り替えボックスを作り後述のイメージで画面表示を切り替えられるようにする。
　2．　サマリ作成は現在選択中モードのみを対象とする。Fundamental表示時は `fundamental_summery-yyyy-mm-dd.md` を作成する。Technical表示時のサマリ作成は現段階では未実装とし、ボタン押下時も何もしない。
　3．　機関投資評価サマリを新設する。　時価総額、流動性(売買代金)　...
　4．　画面イメージは下記の通り

　　　　------------------------------------
　　　　取得日時　株価(前日比、前日%)　終端位置｛高値圏/安値圏/中間｝：xx.x%　　60日レンジ　{高値圏/安値圏/中間}：xx.x%
　　　　{上昇トレンド/下降トレンド/横ばい}
　　　　------------------------------------
　　　　機関投資サマリ(常時表示)
　　　　時価総額：xxxx.x　億円({超大型/大型主役/中型主役/小型})
　　　　流動性：　出来高　xxxxx.x株　(20日平均：＋xx%)　　売買代金
　　　　機関投資スコア　xx点　Fundamental Score　xx点({S/A/B/C})　Technical：Vwap × 25日線〇
　　　　------------------------------------
　　　　Technical　/　　Fundamental切り替え
　

## 2. 対象ファイル

| ファイル | 役割 |
|---|---|
| `stock_constants.py` | 表示文言、評価ラベル、しきい値、市況シンボル、文字コード、診断カテゴリ |
| `stock_types.py` | Python向け `TypedDict`、階層snapshot型、flatからstructuredへの変換 |
| `stock_logging.py` | 取得ログを `Logs/stock_snapshot.log` に残す設定 |
| `data_layer.py` | yfinanceから外部データを取得し、Python値へ正規化 |
| `domain_layer.py` | 指標算出、評価ラベル作成、flat/structured snapshot API |
| `presentation_layer.py` | flat snapshotを固定フォーマットの日本語テキストへ変換 |
| `technical_snap.py` | Tkinter GUI |
| `tests/test_domain_and_data.py` | 外部APIに依存しない固定データテスト |
| `Samples/` | 移植比較用サンプル |

## 3. 公開API

### 3.1 現行互換API

```python
from domain_layer import StockInput, get_stock_snapshot

flat = get_stock_snapshot(StockInput(name="トヨタ自動車", code="7203"))
```

`get_stock_snapshot()` は現行表示層と互換性があるflat辞書を返す。

### 3.2 移植推奨API

```python
from domain_layer import StockInput, get_structured_stock_snapshot

snapshot = get_structured_stock_snapshot(StockInput(name="トヨタ自動車", code="7203"))
```

`get_structured_stock_snapshot()` は保守性重視の階層snapshotを返す。Python移植先ではこのAPIを優先して使う。

### 3.3 表示API

```python
from presentation_layer import render_stock_block

text = render_stock_block(flat, include_market=True, market_block=market_block)
```

現行表示層はflat snapshotを入力とする。structured snapshotを直接表示する場合は、移植先で専用rendererを作る。

## 4. 入力仕様

### 4.1 銘柄入力

| 項目 | 型 | 内容 |
|---|---|---|
| `name` | string | 表示用銘柄名 |
| `code` | string | 東証4桁コード。例: `7203` |

yfinanceの株価取得シンボルは `{code}.T` とする。

### 4.2 監視銘柄ファイル

`presentation_layer.load_watchlist()` はMarkdownまたはテキストから銘柄を抽出する。

- 想定形式: `銘柄名 (1234)` または箇条書き内の同等表記
- コードは4桁数字のみ対象
- 同一コードが複数回出た場合は初出のみ採用
- 抽出できない場合は `ERROR_MESSAGES["watchlist_parse_failed"]`
- 通常読み込みはUTF-8、BOM付きUTF-8は `utf-8-sig` fallback

## 5. データ取得仕様

### 5.1 共通

- 外部取得元は `yfinance`
- 数値正規化は `safe_float()`
- `None`、NaN、変換不能値は `None`
- 表示層では `None`、NaN、inf を `N/A`
- 任意データの取得失敗は全体を落とさず `diagnostics` に記録
- 日足価格が不足する場合のみ `error = "価格データ不足"`
- 取得処理の実行時刻は `acquired_at`
- 取得した現在値が何時点の価格かは `latest_price_timestamp`
- 価格の由来は `latest_price_source`

### 5.2 日足価格

| 項目 | 仕様 |
|---|---|
| 関数 | `fetch_history(symbol, period="4mo", interval="1d")` |
| API | `yf.Ticker(symbol).history(auto_adjust=False)` |
| 現行利用 | `{code}.T`, `period="4mo"` |
| 必須列 | `Open`, `High`, `Low`, `Close`, `Volume` |
| 最低件数 | 欠損除去後30件以上 |
| index | timezone除去済みdatetime |

### 5.3 日中足/VWAP

| 項目 | 仕様 |
|---|---|
| 関数 | `fetch_intraday_vwap(code, interval="5m")` |
| API | `yf.download("{code}.T", period="1d", interval="5m", auto_adjust=False)` |
| 必須列 | `Open`, `High`, `Low`, `Close`, `Volume` |
| 除外条件 | Volumeが0または欠損の足を除外 |

VWAP:

```text
TypicalPrice = (High + Low + Close) / 3
VWAP = cumsum(TypicalPrice * Volume) / cumsum(Volume)
```

日中足が取れない場合:

- 現在値、O/H/L、出来高は日足ベース
- `latest_bar_time` は `終値`
- `latest_price_source` は `daily_close`
- `latest_price_timestamp` は `{日足日付} 終値`
- VWAPは日足の `(High + Low + Close) / 3`
- `vwap_source` は `日足参考値`
- `vwap_timestamp` は `{日足日付} 終値`
- `diagnostics` に `field="intraday"` を記録

日中足が取れた場合:

- VWAPは本日5分足の価格と出来高から計算
- `vwap_source` は `本日5分足`
- `vwap_timestamp` は `{日足日付} {latest_bar_time}`

### 5.4 市況

| 表示名 | yfinance symbol |
|---|---|
| WTI | `CL=F` |
| 銅 | `HG=F` |
| NASDAQ | `^IXIC` |

取得仕様:

- `fetch_history(symbol, period="10d")`
- 終値2本未満なら `latest=None`, `change_pct=None`, `trend="N/A"`
- 騰落率は `latest / prev_close - 1`
- 5日移動平均が取れる場合のみ `grade_trend()`

### 5.5 PER/EPS

関数: `fetch_valuation_snapshot(code)`

| key | 取得元/算出 |
|---|---|
| `eps_actual` | `ticker.info["trailingEps"]` |
| `eps_fy0` | `get_earnings_estimate()` の `0y / avg`。なければ `forwardEps` |
| `eps_fy1` | `get_earnings_estimate()` の `+1y / avg` |
| `per_actual` | `ticker.info["trailingPE"]` |
| `per_forward` | `ticker.info["forwardPE"]` |

ドメイン層:

- `per_fy0 = latest / eps_fy0`
- `eps_fy0` がない場合は `per_forward`
- `per_fy1 = latest / eps_fy1`
- EPSが `None` または0以下の場合、算出PERは `None`

### 5.6 収益性

関数: `fetch_profitability_snapshot(code)`

| key | 取得元/算出 |
|---|---|
| `roe_actual` | `ticker.info["returnOnEquity"]`。1以下なら百分率へ変換 |
| `op_margin_actual` | 年次損益計算書の `Operating Income / Total Revenue * 100` |
| `op_growth_actual` | `最新Operating Income / 前期Operating Income - 1` の百分率 |

今期末予想営業利益率は、現状のyfinance標準取得では営業利益予想値を安定取得できないため、表示・ドメインsnapshotの対象外とする。

年次損益計算書は `ticker.income_stmt` を優先し、空なら `ticker.financials` をfallbackとする。

行名:

- 営業利益: `Operating Income`, `OperatingIncome`
- 売上高: `Total Revenue`, `TotalRevenue`, `Revenue`

## 6. 指標作成仕様

### 6.1 移動平均

| key | 式 |
|---|---|
| `ma5` | `Close.rolling(5).mean()` |
| `ma25` | `Close.rolling(25).mean()` |
| `ma25_prev5` | 5営業日前の25日移動平均。30件以上の場合のみ |
| `dev5` | `latest / ma5 - 1` の百分率 |
| `dev25` | `latest / ma25 - 1` の百分率 |

### 6.2 RSI

期間は14。

```text
delta = Close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
RSI = 100 - 100 / (1 + avg_gain / avg_loss)
```

### 6.3 ATR

期間は14。True Rangeは以下の最大値。

- `High - Low`
- `abs(High - prev Close)`
- `abs(Low - prev Close)`

```text
ATR14 = TrueRange.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
```

### 6.4 当日レンジ

| key | 式 |
|---|---|
| `day_change_price` | `latest - prev_close` |
| `day_change_pct` | `latest / prev_close - 1` の百分率 |
| `day_range` | `high - low` |
| `day_range_atr` | `day_range / atr14` |
| `day_close_position` | `(latest - low) / (high - low)` |
| `ma25_distance` | `latest - ma25` |
| `ma25_distance_atr` | `(latest - ma25) / atr14` |

### 6.5 前日評価

前日足は日足履歴の末尾から2本目を使う。

| key | 式 |
|---|---|
| `prev_change_pct` | `prev_close / prev_prev_close - 1` の百分率 |
| `prev_range` | `prev_high - prev_low` |
| `prev_range_atr` | `prev_range / atr14` |
| `prev_close_position` | `(prev_close - prev_low) / (prev_high - prev_low)` |
| `prev_vol_ratio` | `prev_volume / prev_vol_avg20 - 1` の百分率 |

ローソク:

| 条件 | ラベル |
|---|---|
| `close > open` | 陽線 |
| `close < open` | 陰線 |
| その他 | 十字線 |

形状:

| 条件 | ラベル |
|---|---|
| 日中値幅が0以下 | 小動き |
| 実体 / 値幅 >= 0.65 | 実体大きめ |
| 下ヒゲ / 値幅 >= 0.40 かつ 下ヒゲ >= 実体 * 1.5 | 下ヒゲ長め |
| 上ヒゲ / 値幅 >= 0.40 かつ 上ヒゲ >= 実体 * 1.5 | 上ヒゲ長め |
| 実体 / 値幅 <= 0.20 | 小動き・十字線気味 |
| その他 | 通常足 |

押し判定:

| 条件 | ラベル |
|---|---|
| `prev_range_atr` または `prev_close_position` 欠損 | 判定不可 |
| `prev_range_atr >= 1.30` かつ `close_position <= 0.30` かつ `prev_vol_ratio >= 20` | 崩れ |
| `prev_range_atr >= 1.50` かつ `close_position <= 0.40` | 崩れ |
| `0.50 <= prev_range_atr <= 1.20` かつ `close_position >= 0.45` かつ `prev_vol_ratio <= 20` | 押し |
| その他 | 中立 |

### 6.6 節目

当日を含めず `shift(1)` した日足から算出する。

| key | 式 |
|---|---|
| `recent5_high` | 直近5営業日のHigh最大 |
| `recent20_high` | 直近20営業日のHigh最大 |
| `recent60_high` | 直近60営業日のHigh最大 |
| `recent60_low` | 直近60営業日のLow最小 |
| `recent*_high_distance` | `latest - recent*_high` |
| `recent*_high_distance_pct` | `latest / recent*_high - 1` の百分率 |
| `recent60_range_position` | `(latest - recent60_low) / (recent60_high - recent60_low)` |

## 7. ラベル仕様

| 種別 | 条件 | ラベル |
|---|---|---|
| 値幅ATR比 | `< 0.5` | 浅い値幅 |
| 値幅ATR比 | `< 1.0` | 通常値幅 |
| 値幅ATR比 | `< 1.5` | 大きめ |
| 値幅ATR比 | `>= 1.5` | 急拡大 |
| 終端位置 | `>= 0.60` | 高値圏で終了 |
| 終端位置 | `>= 0.30` | 中段で終了 |
| 終端位置 | `< 0.30` | 安値圏で終了 |
| 60日レンジ | `>= 0.60` | 高値圏 |
| 60日レンジ | `>= 0.30` | 中段 |
| 60日レンジ | `< 0.30` | 安値圏 |
| トレンド | `latest > ma5 > ma25` かつ `ma25 > ma25_prev5` | 上昇トレンド |
| トレンド | `latest < ma5 < ma25` | 下落トレンド |
| トレンド | その他 | もみ合い / 戻り局面 |

欠損、NaN、infの場合は `N/A`。

## 8. Snapshot仕様

### 8.1 flat snapshot

`get_stock_snapshot()` は現行表示互換のflat辞書を返す。主な分類は以下。

| 分類 | key例 |
|---|---|
| 銘柄 | `name`, `code`, `date`, `acquired_at`, `error`, `diagnostics` |
| 先頭サマリ | `summary_trend_symbol`, `summary_trend_label` |
| 当日価格 | `latest_bar_time`, `latest_price_source`, `latest_price_timestamp`, `open`, `high`, `low`, `latest`, `day_change_price`, `day_change_pct`, `volume` |
| VWAP | `vwap`, `vwap_diff`, `vwap_source`, `vwap_timestamp` |
| テクニカル | `ma5`, `dev5`, `ma25`, `dev25`, `rsi`, `atr14`, `trend` |
| 前日 | `prev_close`, `prev_candle`, `prev_wick_shape`, `prev_evaluation` |
| 節目 | `recent5_high`, `recent20_high`, `recent60_high`, `recent60_low` |
| PER/EPS | `per_actual`, `per_fy0`, `per_fy1`, `eps_actual`, `eps_fy0`, `eps_fy1` |
| 収益性 | `roe_actual`, `op_margin_actual`, `op_growth_actual` |

### 8.2 structured snapshot

`get_structured_stock_snapshot()` は `stock_types.StructuredStockSnapshot` を返す。

| key | 内容 |
|---|---|
| `identity` | 銘柄名、コード、取得日、エラー |
| `summary` | 先頭サマリ用のトレンド記号、短縮ラベル |
| `price` | 当日価格、現在値、出来高、価格時点、価格ソース |
| `vwap` | VWAP、VWAP差分率、VWAP由来、VWAP時点 |
| `technical` | MA、RSI、ATR、トレンド |
| `range` | 当日レンジ、終端位置、25日線距離 |
| `previous_session` | 前日価格、ローソク、押し判定、総合評価 |
| `breakline` | 直近高値、60日レンジ |
| `valuation` | PER/EPS |
| `profitability` | ROE、営業利益率、営業成長率 |
| `diagnostics` | 内部診断情報 |

flatからstructuredへの変換は `stock_types.to_structured_snapshot()`。

## 9. Diagnostics/ログ仕様

`get_stock_snapshot()` と `get_structured_stock_snapshot()` は診断情報を `diagnostics` に持つ。

形式:

```python
{
    "category": "外部API失敗",
    "field": "valuation",
    "message": "valuation unavailable",
}
```

カテゴリ:

- 外部API失敗
- データ欠損
- 列名変更/列不足
- ゼロ除算
- 取得対象外

診断情報は表示テキストには出さず、`domain_layer` loggerへwarning出力する。

通常の取得成功/失敗ログも `domain_layer` loggerへinfo出力する。GUI起動時は `technical_snap.py` が `setup_stock_logging()` を呼び、`Logs/stock_snapshot.log` に以下を残す。

- 銘柄名
- コード
- 取得処理時刻 `acquired_at`
- 現在値 `latest`
- 価格ソース `latest_price_source`
- 価格時点 `latest_price_timestamp`
- VWAP由来 `vwap_source`
- VWAP時点 `vwap_timestamp`
- エラー有無
- diagnostics件数

## 10. 表示仕様

### 10.1 基本整形

| 関数 | 仕様 |
|---|---|
| `fmt_price` | `1,234.56`。欠損は `N/A` |
| `fmt_price_current` | 1000以上は小数なし、1000未満は小数1桁 |
| `fmt_price_diff` | 符号付き、カンマ、小数2桁 |
| `fmt_pct` | 符号付き、小数2桁、`%` |
| `fmt_pct_plain` | 符号なし、小数1桁、`%` |
| `fmt_pct_jp` | 符号付き、小数2桁、`％` |
| `fmt_pct_no_sign_jp` | 符号なし、小数2桁、`％` |
| `fmt_volume` | カンマ区切り整数 + `株` |
| `fmt_multiple` | 小数2桁 + `倍` |
| `fmt_per` | 小数1桁 + `倍` |
| `fmt_eps` | 小数なし + `円` |

### 10.2 先頭サマリ

目的は、銘柄ごとの現在位置、短期方向、25日線傾き、VWAP・25日線からの距離、RSI、60日レンジ位置を冒頭で一目確認できるようにすること。

表示位置は銘柄見出しの直後、既存の `■当日位置・レンジ` より前とする。既存の詳細ブロックは削除せず、先頭サマリは詳細ブロックの要約として追加する。

取得した株価の時点は `latest_price_timestamp` として保持するが、先頭サマリには表示しない。日中足が取得できた場合は `{日足日付} {HH:MM}`、日中足が取得できない場合は `{日足日付} 終値` を内部値として保持する。

表示テンプレート:

```text
【銘柄】{name} ({code4})
株価：{latest}円（前日比{day_change_price}円：{day_change_pct}）（当日{day_close_position_zone}{day_close_position}）
トレンド：{trend_label}　　　25日線傾き：{ma25_slope_symbol}

Vwap：{vwap_diff_price}円（{vwap_diff_pct}、{vwap_diff_atr}ATR）
位置：25日線 {dev25}（{ma25_distance_atr}ATR）
前日高値：{prev_high}　前日安値：{prev_low}　　　　{previous_high_evaluation}
5日高値 {recent5_high_distance_pct}　20日高値まで：{recent20_high_remaining_pct} 　　60日レンジ位置 {recent60_range_position}（{recent60_range_zone}）
RSI：{rsi}
```

項目仕様:

| 表示項目 | snapshot key / 算出 | 表示仕様 |
|---|---|---|
| 銘柄 | `name`, `code4` | `【銘柄】{name} ({code4})` |
| 時点 | `latest_price_timestamp` | 内部値として保持する。先頭サマリには表示しない。スクリプト実行時刻は使わない |
| 株価 | `latest` | `株価：{latest}円`。価格は `fmt_price_current()` + `円` |
| 前日比 | `day_change_price`, `day_change_pct` | `（前日比{day_change_price}円：{day_change_pct}）`。価格差は符号付き円、率は符号付き・小数1桁の `%` |
| 終端位置 | `day_close_position`, `day_close_position_label` | `（当日{zone}{position}%）`。zoneは既存ラベルから `高値圏` / `中間` / `安値圏` に短縮する |
| トレンド | `trend` | `上昇` / `もみあい` / `下落` の短縮ラベルで表示 |
| 25日線傾き | `ma25`, `ma25_prev5` | `ma25 > ma25_prev5` なら `↑`、同値なら `→`、下なら `↓`、欠損なら `N/A` |
| Vwap | `latest - vwap`, `vwap_diff_pct`, `vwap_diff_atr` | 価格差、乖離率、ATR比を表示する |
| 位置 | `dev25`, `ma25_distance_atr` | 25日線乖離率とATR比を表示する |
| 前日評価 | `prev_high`, `prev_low`, `latest` | 前日高値・安値と、前日高値突破 / 前日レンジ / 前日安値割れ評価を表示する |
| RSI | `rsi` | 小数1桁 |
| 60日線レンジ位置 | `recent60_range_position`, `recent60_range_zone` | `recent60_range_position * 100` を小数1桁の `%`。ゾーンラベルを括弧で併記 |

トレンド短縮ラベル:

| 元ラベル | 先頭サマリ表示 |
|---|---|
| 上昇トレンド | 上昇 |
| 下落トレンド | 下落 |
| もみ合い / 戻り局面 | もみあい |

終端位置ラベルは既存ラベルを維持する。

| 元ラベル | 先頭サマリ表示 |
|---|---|
| 高値圏で終了 | 高値圏で終了 |
| 中段で終了 | 中段で終了 |
| 安値圏で終了 | 安値圏で終了 |

欠損時:

- 数値が欠損、NaN、infの場合は該当箇所を `N/A` とする。
- Vwapが欠損する場合は `Vwap　：　N/A` とし、価格差も表示しない。
- 25日線またはATRが欠損する場合は、取得できる値だけ表示し、不足部分を `N/A` とする。
- 60日レンジの高値・安値が同値、または算出不能の場合は `60日レンジ位置 N/A` とする。

例:

```text
【銘柄】　コムシス
株価：5,452円（前日比+60.00円：+1.1%）（当日高値圏84.4%）
トレンド：もみあい　　　25日線傾き：↑

Vwap：+42.00円（+0.8%、0.50ATR）
位置：25日線 -1.7%（-0.50ATR）
前日高値：5,338.00　前日安値：5,210.00　　　　前日高値突破：+2.1%
5日高値 -0.2%　20日高値まで：12.1% 　　60日レンジ位置 43.8%（中段）
RSI：49.3
```

Vwapの価格差は、既存の `latest - vwap` と同じ符号にする。つまり現在値がVWAPより下ならマイナス。

### 10.3 前日評価ブロック

表示テンプレート:

```text
■前日評価
前日騰落率：{prev_change_pct}

前日Vwap維持：{〇/×/N/A}
ローソク：{candle} / {wick_shape}
押し判定：{pullback}
```

`previous_high_evaluation` は現在値 `latest` と前日高値・前日安値から以下で判定する。

| 条件 | 表示 |
|---|---|
| `latest > prev_high` | `前日高値突破：{latest / prev_high - 1}` |
| `prev_low <= latest <= prev_high` | `前日レンジ：{(latest - prev_low) / (prev_high - prev_low)}（{高値圏/中間/安値圏}）` |
| `latest < prev_low` | `前日安値：{latest / prev_low - 1}` |

前日VWAP維持は、前日終値が表示に使うVWAP以上なら `〇`、下なら `×`、欠損なら `N/A` とする。

### 10.4 節目・ブレイクライン / 支持線ブロック

節目・ブレイクラインは先頭サマリに統合し、独立した `■節目・ブレイクライン` ブロックは表示しない。

```text
5日高値 {recent5_high_distance_pct}　20日高値まで：{recent20_high_remaining_pct} 　　60日レンジ位置 {recent60_range_position}（{recent60_range_zone}）
```

高値までの距離は、現在値が高値未満なら既存の高値距離率の絶対値を小数1桁で表示する。現在値が高値以上なら `突破 {+x.x%}` と表示する。

支持線は最後に表示する。

```text
■支持線
前日安値：{prev_low}
20日安値：{recent20_low}
60日安値：{recent60_low}
```

### 10.5 移動平均・出来高ブロック

先頭サマリへの移動に伴い、既存の `■当日テクニカル` は `■移動平均・出来高` に改名する。`VWAP` と `RSI` の行は削除する。

`■移動平均・出来高` に表示する項目:

- 5日線
- 25日線
- 14日ATR
- 出来高

`VWAP`、`RSI` は先頭サマリのみで表示する。算出自体はsnapshotに残し、表示責務だけを先頭サマリへ移す。

25日線の `距離` は表示しない。25日線行は以下の形式とする。

```text
25日線：{ma25}（乖離 {dev25} / ATR比 {ma25_distance_atr}倍）
出来高：20日平均出来高比 {volume_vs_avg20_pct}　（{volume}株）
```

### 10.6 ファンダメンタルブロック

`■ファンダメンタル` に表示する項目:

- ROE
- 営業利益率
- 営業成長率

配当利回りは表示しない。ドメイン・structured snapshotにも配当利回り項目は持たせない。

### 10.7 表示順

1. `【銘柄】{name} ({code})`
2. 先頭サマリ
3. `■当日位置・レンジ`
4. PER/EPS
5. `■移動平均・出来高`
6. `■前日評価`
7. `■ファンダメンタル`
8. `■支持線`
9. 任意で `■市況`

`■流れ` ブロックと `■節目・ブレイクライン` ブロックは先頭サマリと情報が重複するため表示しない。

### 10.8 市況ブロック

市況ブロックはチェック有効時のみ末尾に追加する。表示順は WTI、銅、NASDAQ。

```text
{name}：{latest}（{change_pct} / {trend}）
```

## 11. テスト仕様

テストは `tests/test_domain_and_data.py` に集約する。外部APIに依存しない固定データを使う。

実行:

```powershell
python -m unittest discover -s tests -v
```

検証対象:

- 日中VWAP
- ATR14
- RSI14
- 終端位置
- 値幅ATR比ラベル
- 前日押し判定
- トレンド判定
- PER/EPS fallback
- 欠損時の `N/A`
- 任意データ取得失敗時のdiagnostics
- flatからstructuredへの変換
- `get_structured_stock_snapshot()`
- 先頭サマリの表示順、トレンド短縮ラベル、終端位置の既存ラベル維持、欠損時の `N/A`
- `■移動平均・出来高` に改名され、`VWAP`、`RSI`、25日線の `距離` が表示されていないこと
- `■ファンダメンタル` に配当利回りが表示されず、structured snapshotにも配当項目がないこと

## 12. Samples仕様

保存先は `Samples/`。

各銘柄について以下を保存する。

- `{code}_snapshot.json`: flat snapshot
- `{code}_structured.json`: structured snapshot
- `{code}_render.txt`: 市況ブロック込み表示テキスト
- `README.md`: 取得日時、銘柄、注意事項

現在のサンプル銘柄:

- トヨタ自動車 (7203)
- 北川電機 (6327)
- 東京エレクトロン (8035)
- オムロン (6645)
- 三菱商事 (8058)

## 13. 移植時の注意点

- `latest` は日中足が取れた場合は日中足終値、取れない場合は日足終値。
- `date` は日足最終日の年月日であり、日中足の営業日とは完全一致しない可能性がある。
- `latest_bar_time` は日中足取得時は `HH:MM`、未取得時は `終値`。
- `latest_price_timestamp` は日中足取得時は `{日足日付} {HH:MM}`、未取得時は `{日足日付} 終値`。
- `latest_price_source` は日中足なら `intraday_5m`、日足終値代替なら `daily_close`。
- 直近高値は当日を除外している。
- 今期末予想営業利益率は現行仕様の対象外。取得できない値を `N/A` として表示し続けるより、表示・ドメインから削除する。
- `vwap_source` は日中足由来なら `本日5分足`、日足代替なら `日足参考値`。
- `vwap_timestamp` は日中足由来なら `{日足日付} {HH:MM}`、日足代替なら `{日足日付} 終値`。
- 先頭サマリのVwap表示は、`vwap_diff` と `latest - vwap` を使う。詳細ブロック側にはVWAP行を表示しない。
- structured snapshotは移植用の推奨形式。現行表示層はflat snapshotを使う。

## 14. 現行GUIへの統合仕様

本節は、既存 `fundmental_kabutan` GUIへTechnical表示エンジンと機関投資サマリを統合するための決定事項を定義する。

### 14.1 画面構成

- 機関投資サマリは、画面上の固定パネルとして常時表示する。
- Technical / Fundamental の切り替えはタブで実装する。
- `取得` ボタンは共通ボタンとし、現在選択中のタブに応じて取得処理を切り替える。
  - Fundamentalタブ選択時: 現行Fundamental取得を実行する。
  - Technicalタブ選択時: Technical取得を実行する。
- `コピー` / `保存` は、現在表示中タブの本文のみを対象とする。
  - 機関投資サマリ固定パネルの内容は、コピー・保存には含めない。
- Fundamentalタブの本文表示は現行出力を維持する。
- Technicalタブの本文表示は本書 10章のTechnical表示仕様を採用する。

### 14.2 サマリ出力

- サマリ出力ボタンは、現在選択中モードのみを対象とする。
- Fundamentalタブ選択時は、既存仕様に合わせて小文字の `fundamental_summery-yyyy-mm-dd.md` を作成する。
- Technicalタブ選択時のサマリ出力は現段階では未実装とする。
  - Technicalタブ選択時にサマリ出力ボタンを押しても、ファイル作成・ステータス変更・エラー表示は行わない。

### 14.3 機関投資サマリ固定パネル

表示項目:

```text
機関投資サマリ
時価総額：xxxx.x億円（{超大型/大型主役/中型主役/小型}）
流動性：出来高 xxxxx株（20日平均比 {+/-xx.x%}） 売買代金 xxxx.x億円
機関投資スコア：xx/20点　Fundamental Score：xx点（{S/A/B/C}）　Technical：VWAP {○/×} / 5日線 {○/×} / 25日線 {○/×}
```

責務:

- 機関投資サマリは、Technical / Fundamental のタブ切り替えに関係なく常時表示する。
- Fundamental Score は rankCF の総合スコアを使う。
- Technical条件は、機関投資スコアには加点しない。
- Fundamental Score と Technical条件は、機関投資スコアとは別表示とする。

### 14.4 機関投資スコア

満点は20点とする。

#### 時価総額（5点）

| 条件 | 点数 |
|------|------|
| 3兆円以上 | 5 |
| 1兆円以上3兆円未満 | 4 |
| 5000億円以上1兆円未満 | 3 |
| 2000億円以上5000億円未満 | 2 |
| 1000億円以上2000億円未満 | 1 |
| 1000億円未満、または欠損 | 0 |

#### 売買代金（5点）

売買代金は `終値 × 出来高` で算出する。

| 条件 | 点数 |
|------|------|
| 100億円以上 | 5 |
| 50億円以上100億円未満 | 4 |
| 20億円以上50億円未満 | 3 |
| 10億円以上20億円未満 | 2 |
| 5億円以上10億円未満 | 1 |
| 5億円未満、または欠損 | 0 |

出来高20日平均比は `当日出来高 ÷ 20日平均出来高 - 1` の百分率で算出する。

#### ROIC（5点）

| 条件 | 点数 |
|------|------|
| 15%以上 | 5 |
| 10%以上15%未満 | 4 |
| 8%以上10%未満 | 3 |
| 5%以上8%未満 | 2 |
| 3%以上5%未満 | 1 |
| 3%未満、または欠損 | 0 |

#### EPS CAGR（5点）

| 条件 | 点数 |
|------|------|
| 20%以上 | 5 |
| 10%以上20%未満 | 4 |
| 5%以上10%未満 | 3 |
| 0%以上5%未満 | 2 |
| -5%以上0%未満 | 1 |
| -5%未満、または欠損 | 0 |

### 14.5 Technical条件表示

- Technical条件は、VWAP、5日線、25日線に対する現在値の位置で判定する。
- 現在値が対象値より上なら `○`、下なら `×` と表示する。
- 対象値が欠損している場合は `N/A` と表示する。
- VWAPが日中足から取得できない場合は日足参考値へフォールバックし、表示上は末尾に `(日足参考値)` を付ける。

### 14.6 データ取得・キャッシュ

- yFinance取得は既存 `app/data/market_data_provider.py` に統合する。
- 日中足VWAP取得に失敗した場合は、日足の `(High + Low + Close) / 3` を参考値として使う。
- 日中足と日足は別キャッシュキーにする。
- 日中足は短TTL、日足は長TTLとする。
  - 具体的なTTL秒数は実装フェーズで決定する。

### 14.7 API方針

- flat snapshot互換APIは現段階では作成しない。
- Technical実装では、既存アプリの `app/domain` 構造に合わせたDTO / UseCase / Builderを優先する。
- 既存移植元ファイルのコピー方針は、本仕様段階では確定しない。
  - 実装フェーズで、既存ファイルをそのままコピーするか、既存アプリ構造へ分解して移植するかを改めて検討する。

## 15. 統合実装Phase案

### Phase 1: 統合仕様整理

**状態: 完了（2026-05-30）**

- 機関投資サマリ固定パネル、Technical / Fundamentalタブ、共通取得ボタン、サマリ出力挙動を定義する。
- 機関投資スコア、Technical条件表示、データ取得・キャッシュ方針を定義する。

### Phase 2: 機関投資サマリDTO / Policy

**状態: 未着手**

- 機関投資サマリ表示に必要なDTOを追加する。
- 時価総額、売買代金、ROIC、EPS CAGRのスコアリングPolicyを追加する。
- Technical条件表示用の判定Policyを追加する。

### Phase 3: Technicalドメイン実装

**状態: 未着手**

- 日足、日中足、VWAP、移動平均、RSI、ATR、レンジ、節目のTechnical DTO / Policy / UseCaseを追加する。
- flat snapshot互換APIは作らない。

### Phase 4: yFinance Data Port拡張

**状態: 未着手**

- 既存 `market_data_provider.py` に日足履歴、日中足、VWAP取得に必要な関数を統合する。
- 日中足・日足のキャッシュキーとTTLを分離する。

### Phase 5: GUIタブ統合

**状態: 未着手**

- Fundamental / Technical をタブ表示にする。
- 共通取得ボタンが選択中タブのUseCaseを呼ぶようにする。
- 機関投資サマリ固定パネルを本文表示とは別に配置する。

### Phase 6: サマリ出力分岐

**状態: 未着手**

- Fundamentalタブ選択時のみ、既存 `fundamental_summery-yyyy-mm-dd.md` を作成する。
- Technicalタブ選択時は、サマリ出力ボタン押下時に何もしない。

## 16. PR分割案

Technicalドメインは既存 `app/domain` 構造に分解して実装する。
移植元ファイルのコピー方針は、本節では確定せず、Data取得や表示移植の実装フェーズで改めて検討する。

### PR-1: 機関投資サマリDTO / Policy

**状態: 完了（2026-05-31）**

目的:

- 外部取得やGUIに依存しない、機関投資サマリの純ドメイン計算を追加する。

対象:

- `app/domain/models/institutional_summary.py`
- `app/domain/policies/institutional_summary.py`
- `tests/test_institutional_summary.py`

実装内容:

- 時価総額、売買代金、ROIC、EPS CAGRの機関投資スコアを算出する。
- 売買代金は `終値 × 出来高` で算出する。
- 出来高20日平均比は `当日出来高 ÷ 20日平均出来高 - 1` の百分率で算出する。
- Technical条件は、現在値がVWAP、5日線、25日線より上なら `○`、下なら `×`、欠損なら `N/A` とする。
- 機関投資スコアにはFundamental ScoreとTechnical条件を加点しない。

### PR-2: Technical Snapshot DTO / Indicator Policy

**状態: 完了（2026-05-31）**

目的:

- Technical画面表示に必要なsnapshot DTOと、日足ベースのTechnical指標計算を追加する。

対象案:

- `app/domain/models/technical_snapshot.py`
- `app/domain/policies/technical_indicators.py`
- `tests/test_technical_indicators.py`

実装内容:

- 移動平均、RSI、ATR、当日レンジ、前日評価、節目の純計算を追加する。
- flat snapshot互換APIは作成しない。
- `TechnicalSnapshot` は表示に必要な階層DTOとして保持する。
- Data取得やGUI結合は本PRでは行わない。

### PR-3: yFinance Data Port拡張

**状態: 完了（2026-05-31）**

目的:

- 既存 `app/data/market_data_provider.py` にTechnical取得に必要な日足・日中足取得を統合する。

実装内容:

- 日足履歴取得、日中足取得、VWAPフォールバックを追加する。
- 日中足と日足のキャッシュキー・TTLを分離する。
- 日足TTLは12時間、日中足TTLは5分とする。
- DataFrameの永続キャッシュ接続は後続UseCase実装時に行う。本PRではキャッシュキー生成関数とTTL定数をData Portで公開する。
- `yf.download()` のMultiIndex列は単一銘柄向けに正規化する。
- 日中足VWAPが取得できない場合は、日足最終行の `(High + Low + Close) / 3` を `日足参考値` として返す。

### PR-4: Technical UseCase / Builder

**状態: 完了（2026-05-31）**

目的:

- Data PortとTechnicalドメインを接続し、Technical画面本文を生成する。

対象案:

- `app/domain/usecases/technical_analysis.py`
- `app/domain/builders/technical_output.py`
- `tests/test_usecase_technical_analysis.py`
- `tests/test_technical_output.py`

実装内容:

- PR3のData Portから日足・日中足を取得し、PR2のTechnical Policyで `TechnicalSnapshot` を作成する。
- 日足・日中足は別キャッシュキーで保存する。
- 日中足が取得できない場合は日足参考値VWAPへフォールバックする。
- Technical画面本文をBuilderでMarkdown風テキストへ変換する。
- GUIタブ統合は本PRでは行わない。

### PR-5: GUI統合

**状態: 完了（2026-05-31）**

目的:

- 機関投資サマリ固定パネル、Fundamental / Technicalタブ、共通取得ボタンをGUIへ統合する。

実装内容:

- Fundamentalタブは現行出力を維持する。
- TechnicalタブはTechnical UseCaseを呼ぶ。
- コピー・保存は固定パネルを含めず、現在タブ本文だけを対象にする。
- Technicalタブ選択時のサマリ出力は何もしない。
- 機関投資サマリ固定パネルはタブ本文とは別に表示する。
- `取得` ボタンは、現在選択中タブに応じてFundamental / Technicalの取得処理を切り替える。
- Technical取得は株探HTMLフォルダ未設定でも実行できる。
- Fundamental取得は従来どおり株探HTMLフォルダを要求する。
- 機関投資サマリは取得時に更新する。
- Fundamental Scoreに必要な株探データがない場合は、固定パネル内のFundamental Scoreを `N/A` とする。
