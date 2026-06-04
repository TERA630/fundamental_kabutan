# Technicalデータ・指標仕様

## 1. 位置づけ

本書は、Technicalタブ、Technical向けyFinanceデータ取得、Technical指標作成の正本仕様である。

- Fundamental表示の出力仕様は `docs/display_spec.md` を正とする。
- Technical表示と機関投資サマリ表示は `docs/display_spec.md` を正とする。
- Domain / UseCase / Builder の責務境界は `docs/domain_spec_proposal.md` を正とする。
- 監視銘柄サマリ出力は `docs/summery_spec.md` を正とする。

## 2. 画面構成

- GUI は Fundamental / Technical をタブで切り替える。
- `取得` ボタンは共通ボタンとし、現在選択中タブに応じて取得処理を切り替える。
- Fundamentalタブ選択時は Fundamental 取得を実行する。
- Technicalタブ選択時は Technical 取得を実行する。
- `コピー` / `保存` は、現在表示中タブの本文のみを対象とする。
- 機関投資サマリ固定パネルの内容は、コピー・保存に含めない。
- 機関投資サマリはタブ切り替えに関係なく常時表示する。

## 3. サマリ出力

- サマリ出力ボタンは、現在選択中モードのみを対象とする。
- Fundamentalタブ選択時は `fundamental_summery-yyyy-mm-dd.md` を作成する。
- Technicalタブ選択時のサマリ出力は未実装とする。
- Technicalタブ選択時にサマリ出力ボタンを押しても、ファイル作成・ステータス変更・エラー表示は行わない。

## 4. Technicalデータ取得

### 4.1 共通

- 外部取得元は `yfinance`。
- yFinance シンボルは `{code4}.T`。
- 数値正規化では `None`、NaN、変換不能値を `None` として扱う。
- 表示層では `None`、NaN、inf を `N/A` とする。
- 任意データの取得失敗は全体を落とさず、取得できる範囲で表示する。

### 4.2 日足価格

| 項目 | 仕様 |
|------|------|
| 取得対象 | `{code4}.T` の日足 |
| 期間 | 4か月相当 |
| 必須列 | `Open`, `High`, `Low`, `Close`, `Volume` |
| 最低件数 | 欠損除去後30件以上 |
| index | timezone除去済みdatetime |

### 4.3 日中足 / VWAP

| 項目 | 仕様 |
|------|------|
| 取得対象 | `{code4}.T` の5分足 |
| 期間 | 1日 |
| 必須列 | `Open`, `High`, `Low`, `Close`, `Volume` |
| 除外条件 | Volume が 0 または欠損の足を除外 |

VWAP:

```text
TypicalPrice = (High + Low + Close) / 3
VWAP = cumsum(TypicalPrice * Volume) / cumsum(Volume)
```

日中足が取得できない場合:

- 現在値、O/H/L、出来高は日足ベースとする。
- `latest_bar_time` は `終値` とする。
- `latest_price_source` は `daily_close` とする。
- VWAP は日足の `(High + Low + Close) / 3` を参考値として使う。
- `vwap_source` は `日足参考値` とする。
- 表示上は VWAP 行の末尾に `(日足参考値)` を付ける。

### 4.4 キャッシュ

- 日中足と日足は別キャッシュキーにする。
- 日足TTLは12時間。
- 日中足TTLは5分。
- Technical取得は株探HTMLフォルダ未設定でも実行できる。

## 5. Technical指標作成

### 5.1 移動平均

| key | 式 |
|-----|----|
| `ma5` | `Close.rolling(5).mean()` |
| `ma25` | `Close.rolling(25).mean()` |
| `ma25_prev5` | 5営業日前の25日移動平均 |
| `dev5` | `latest / ma5 - 1` の百分率 |
| `dev25` | `latest / ma25 - 1` の百分率 |

### 5.2 RSI

期間は14。

```text
delta = Close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
RSI = 100 - 100 / (1 + avg_gain / avg_loss)
```

### 5.3 ATR

期間は14。True Range は以下の最大値。

- `High - Low`
- `abs(High - prev Close)`
- `abs(Low - prev Close)`

```text
ATR14 = TrueRange.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
```

### 5.4 当日レンジ

| key | 式 |
|-----|----|
| `day_change_price` | `latest - prev_close` |
| `day_change_pct` | `latest / prev_close - 1` の百分率 |
| `day_range` | `high - low` |
| `day_range_atr` | `day_range / atr14` |
| `day_close_position` | `(latest - low) / (high - low)` |
| `ma25_distance_atr` | `(latest - ma25) / atr14` |

### 5.5 前日評価

- 前日足は日足履歴の末尾から2本目を使う。
- ローソクは `陽線` / `陰線` / `十字線`。
- 押し判定は `押し` / `崩れ` / `中立` / `判定不可`。
- 前日VWAP維持は、前日終値が表示に使うVWAP以上なら `〇`、下なら `×`、欠損なら `N/A` とする。

### 5.6 節目

当日を含めず `shift(1)` した日足から算出する。

| key | 式 |
|-----|----|
| `recent5_high` | 直近5営業日のHigh最大 |
| `recent20_high` | 直近20営業日のHigh最大 |
| `recent20_low` | 直近20営業日のLow最小 |
| `recent60_high` | 直近60営業日のHigh最大 |
| `recent60_low` | 直近60営業日のLow最小 |
| `recent60_range_position` | `(latest - recent60_low) / (recent60_high - recent60_low)` |

## 6. 表示仕様

Technical出力と機関投資サマリ固定パネルの表示順・文言・数値表現は `docs/display_spec.md` を正とする。

## 7. 実装責務

| 要素 | 責務 |
|------|------|
| `TechnicalSnapshot` | Technical表示に必要な階層DTO |
| `technical_indicators.py` | 日足ベースの移動平均、RSI、ATR、レンジ、前日評価、節目の純計算 |
| `TechnicalAnalysisService` | Data Port と Technical Domain を接続し、Technical分析結果を作成するUseCase |
| `build_technical_output()` | Technical分析結果をテキストへ変換するBuilder |
| `InstitutionalSummary` | 機関投資サマリ表示用DTO |
| `institutional_summary.py` | 機関投資スコア、Technical条件、固定パネル用の純計算 |
