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
- 前日5分足は yFinance の5分足を `period="5d"` で取得し、その中から日足履歴の前日取引日に一致するバーを使う。
- 前日5分足が取得できない、または前場・後場の判定に必要なバーが不足する場合、前場/後場VWAP・前日VWAP差分・後場評価は `N/A` とする。日足参考値へのフォールバックは行わない。
- ローソク足型は `大陽線` / `大陰線` / `陽線` / `陰線` / `小陽線` / `小陰線` / `十字`。
- 押し判定は `押し` / `崩れ` / `中立` / `判定不可`。
- 前日出来高比は `前日出来高 / 前日基準の20日平均出来高 * 100` とする。

#### 5.5.1 前日評価リニューアル仕様

テクニカル画面の `■前日評価` は、前日の終値位置・レンジ・出来高・移動平均に加え、前場/後場のVWAP維持と後場評価を同じブロックで読める構成へ寄せる。実装時は、UI層に判定ロジックを置かず、日足・日中足から作る純粋な指標は Domain、データ取得との合成は UseCase、文字列化は Builder に分離する。

表示仕様:

```text
■前日評価
終値 {prev_close}（VWAP {prev_vwap_diff_price}円 / {prev_vwap_diff_pct} / {prev_vwap_diff_atr}ATR）騰落率{prev_change_pct}

前日Vwap(前・後場)　{prev_am_vwap_maintained}/{prev_pm_vwap_maintained}  高値更新 {prev_high_higher} / 安値維持 {prev_low_higher}
前日出来高比　　{prev_volume_vs_avg20_pct}

後場評価 {previous_pm_evaluation} / VWAP{previous_pm_vwap_position}

前日レンジ {prev_low}-{prev_high}（{prev_range_atr}ATR）　終位置 {prev_close_position}
前日ローソク足型：　{prev_candle_body_label}＋{prev_wick_label}
```

フィールド:

| field | 算出元 | 用途 |
|---|---|---|
| `prev_close` / `prev_high` / `prev_low` | 前日の日足 | 終値、前日レンジ |
| `prev_vwap` | 前日5分足の前日全体VWAP | 終値のVWAP差分 |
| `prev_vwap_diff_price` | `prev_close - prev_vwap` | VWAPからの価格差 |
| `prev_vwap_diff_pct` | `prev_close / prev_vwap - 1` の百分率 | VWAPからの乖離率 |
| `prev_vwap_diff_atr` | `prev_vwap_diff_price / atr14` | VWAP差分のATR換算 |
| `prev_am_vwap_maintained` | 前日前場の終端価格と前日前場VWAP | `前日Vwap(前・後場)` の前場側。終端価格がVWAP以上なら `〇`、下なら `×`、欠損なら `N/A` |
| `prev_pm_vwap_maintained` | 前日終値と前日後場VWAP | `前日Vwap(前・後場)` の後場側。終値が後場VWAP以上なら `〇`、下なら `×`、欠損なら `N/A` |
| `previous_pm_vwap_position` | 前日終値と前日後場VWAP | `上` / `下` / `N/A` |
| `previous_pm_evaluation` | 前日後場の `pm_open`, `pm_high`, `pm_low`, `close`, `vwap` | 後場評価ラベル |
| `prev_high_higher` | 前日高値と前々日高値 | 前日高値 > 前々日高値なら `〇`、それ以外は `×`、欠損なら `N/A` |
| `prev_low_higher` | 前日安値と前々日安値 | 前日安値 >= 前々日安値なら `〇`、それ以外は `×`、欠損なら `N/A`。表示ラベルは `安値維持` |
| `prev_volume_vs_avg20_pct` | 前日出来高と前日基準20日平均出来高 | `前日出来高比` |
| `prev_candle_body_label` | 前日の日足OHLC | ローソク足の実体分類 |
| `prev_wick_label` | 前日の日足OHLC | `上髭` / `下髭` / `追加記載なし` |

#### 5.5.2 ローソク足型・ヒゲ判定

入力値は前日の日足 `open`, `high`, `low`, `close` とする。

派生値:

```text
range = high - low
body = abs(close - open)
body_ratio = body / range
upper_wick = high - max(open, close)
lower_wick = min(open, close) - low
upper_wick_ratio = upper_wick / range
lower_wick_ratio = lower_wick / range
```

`range <= 0` または必要値欠損時は、ローソク足型・ヒゲとも `N/A` とする。

ローソク足型:

| 条件 | 陽線系 | 陰線系 |
|---|---|---|
| `body_ratio < 0.10` | `十字` | `十字` |
| `0.10 <= body_ratio < 0.30` | `小陽線` | `小陰線` |
| `0.30 <= body_ratio < 0.65` | `陽線` | `陰線` |
| `0.65 <= body_ratio` | `大陽線` | `大陰線` |

- 陽線系は `close > open`、陰線系は `close < open` とする。
- `close == open` は `十字` とする。

ヒゲ:

| 優先 | ラベル | 条件 |
|---:|---|---|
| 1 | `上髭` | `upper_wick_ratio >= 0.30` かつ `upper_wick >= body * 1.5` かつ `upper_wick > lower_wick` |
| 2 | `下髭` | `lower_wick_ratio >= 0.30` かつ `lower_wick >= body * 1.5` かつ `lower_wick > upper_wick` |
| 3 | `追加記載なし` | 上記以外 |

- 上髭と下髭の条件が同時に成立し、長さが同値の場合は `追加記載なし` とする。

#### 5.5.3 後場評価の判定仕様

入力値は前日の後場開始価格 `pm_open`、後場高値 `pm_high`、後場安値 `pm_low`、終値 `close`、前日VWAP `vwap` とする。

派生値:

```text
pm_return_pct = (close / pm_open - 1) * 100
pm_close_position = (close - pm_low) / (pm_high - pm_low)
```

判定区分は `後場上昇` / `高値維持` / `横ばいVWAP維持` / `失速もVWAP維持` / `後場VWAP割` とする。境界条件と重複を解消するため、実装では上から順に評価する優先順位方式を採用する。

| 優先 | ラベル | 条件案 | 備考 |
|---:|---|---|---|
| 1 | `N/A` | `pm_open`, `pm_high`, `pm_low`, `close`, `vwap` のいずれかが欠損、または `pm_high <= pm_low` | 0値幅では終値位置を定義できない |
| 2 | `後場VWAP割` | `close <= vwap` | `close == vwap` は保守的にVWAP割側へ寄せる |
| 3 | `失速もVWAP維持` | `close > vwap` かつ (`pm_return_pct < -1` または `pm_close_position < 0.30`) | `pm_close_position < 0.30` は横ばい条件と重複し得るため、失速を優先する案 |
| 4 | `後場上昇` | `close > pm_open` かつ `close > vwap` かつ `pm_close_position >= 0.70` | `高値維持` と重複し得るため、上昇を優先する案 |
| 5 | `高値維持` | `close > vwap` かつ `pm_close_position >= 0.50` かつ `-1 <= pm_return_pct <= 1` | 横ばい圏で高値側を維持 |
| 6 | `横ばいVWAP維持` | `close > vwap` かつ `0.30 <= pm_close_position < 0.50` かつ `-1 <= pm_return_pct <= 1` | `pm_close_position < 0.30` は失速へ寄せる |
| 7 | `後場上昇` | `close > vwap` かつ `pm_return_pct > 1` | 後場騰落率が+1%超だが終値位置70%未満の漏れを防ぐフォールバック |
| 8 | `横ばいVWAP維持` | `close > vwap` | 上記に該当しないVWAP上ケースの漏れを防ぐフォールバック |

検証結果:

- 指定条件をそのまま集合として扱うと、`後場上昇` と `高値維持` は、`close > pm_open`、`close > vwap`、`pm_close_position >= 0.70`、かつ `pm_return_pct <= 1` のケースで重複する。
- `横ばいVWAP維持` と `失速もVWAP維持` は、`close > vwap`、`pm_close_position < 0.30`、かつ `-1 <= pm_return_pct <= 1` のケースで重複する。
- `close > vwap`、`pm_return_pct > 1`、かつ `pm_close_position < 0.70` のケースは、指定条件だけではどのラベルにも入らない。
- `close == vwap`、`pm_high == pm_low`、欠損値をどう扱うかは指定条件だけでは未定義である。
- 優先順位方式により、上記の重複と漏れを解消する。

#### 5.5.4 yFinance API回数の見込み

- Technical取得1銘柄あたり、通常は日足履歴1回、5分足履歴1回の合計2リクエストを想定する。
- Fundamental同時取得や機関投資サマリ作成で同じ `MarketDataBundle` を使う経路では、既存どおり日足・5分足を再利用する。
- 5分足取得を `period="1d"` から `period="5d"` に広げても、リクエスト回数は増えない。増えるのはレスポンス内のバー本数である。
- 既存キャッシュTTLは、日足12時間、5分足5分である。短時間に同一銘柄を再取得した場合、5分足は5分間キャッシュされる。
- yFinanceは公式の固定レート上限を公開していないため、厳密な上限保証はできない。通常の手動GUI操作や少数銘柄の連続確認では問題になりにくいが、数十〜数百銘柄を短時間に一括取得する用途ではレート制限・一時失敗の可能性がある。
- レート制限対策が必要になった場合は、5分足TTL延長、銘柄間スリープ、失敗時バックオフ、監視銘柄一括処理時の取得数制限を追加する。

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

## 8. 前日評価リニューアル 作業分割と進捗

本節は、前日評価リニューアル作業中の分割コミット計画と進捗を管理する。実装完了後、必要に応じて進捗ログは整理する。

| Commit | 作業 | 対象 | 進捗 |
|---:|---|---|---|
| 1 | 仕様確定 | `docs/display_spec.md`, `docs/unite_tech_spec.md` | 完了 |
| 2 | 日足ベースの前日評価DTO拡張 | `app/domain/models/technical_snapshot.py`, `app/domain/policies/technical_indicators.py`, `tests/test_technical_indicators.py` | 完了 |
| 3 | 前日5分足から前場/後場VWAP・後場評価を算出 | `app/data/market_data_provider.py`, `app/domain/usecases/technical_analysis.py`, 関連テスト | 完了 |
| 4 | `■前日評価` の表示を新フォーマットへ変更 | `app/domain/builders/technical_output.py`, `tests/test_technical_output.py` | 完了 |
| 5 | 結合確認と仕様進捗更新 | 関連テスト、仕様書の進捗欄 | 完了 |

検証メモ:

- 前日出来高比は `tests/test_technical_indicators.py` で、前日出来高 `1068`、前日基準20日平均出来高 `1058.5` から `1068 / 1058.5 * 100` になることを確認する。
- 前日VWAP、前日前場VWAP、前日後場VWAPは `tests/test_market_data_provider_technical.py` で、5分足の `typical_price = (High + Low + Close) / 3` を出来高加重して算出することを確認する。
- 表示上の前日VWAP差分、前日出来高比、後場評価、VWAP位置は `tests/test_technical_output.py` で確認する。
