# Fundamental画面 yFinanceアナリスト予想 仕様

## 目的

Fundamental画面に、yFinanceから取得できるアナリスト目標株価とEPS修正人数を表示する。
EPS trendは表示対象から外し、EPS revisionsは過去30日のみを表示する。

## 取得元

- 対象シンボルは既存yFinance取得と同じ `{code4}.T` とする。
- 目標株価とアナリスト人数は `ticker.info` から取得する。
  - `targetMeanPrice`
  - `numberOfAnalystOpinions`
- EPS修正人数は `ticker.eps_revisions` のPandas DataFrameから取得する。
  - 互換性のため、属性名が `eps_revisons` の場合もフォールバックとして参照する。

## 表示対象

- 四半期行 `0q`, `+1q` は表示しない。
- 年度末行のみ表示する。
  - `0y`: 今期末
  - `+1y`: 来季末
- EPS revisionsは過去30日のみ表示する。
  - `upLast30days`: 上方修正人数
  - `downLast30days`: 下方修正人数
- 7日修正人数は取得・DTO保持・表示の対象外とする。
- 目標株価乖離率は `(targetMeanPrice - 現在株価) / 現在株価 * 100` で算出し、符号付き1桁小数の%で表示する。

## 表示形式

```text
■アナリスト
目標株価 {targetMeanPrice}円(現価格との乖離{targetGapPct}%：アナリスト{numberOfAnalystOpinions}人)
今期EPS修正 ↑{currentYearUpLast30days} ↓{currentYearDownLast30days}
来季EPS修正 ↑{nextYearUpLast30days} ↓{nextYearDownLast30days}
```

## 欠損時の扱い

- ブロックは常に表示する。
- 取得失敗、対象行なし、対象列なし、値変換不可の場合は該当値を `N/A` と表示する。
- yFinance取得失敗は画面全体の失敗にしない。

## 実装方針

- `app.domain.models.analyst_estimates` のDTOからEPS trendと7日修正人数を削除し、30日修正人数のみ保持する。
- `app.data.market_data_provider.fetch_yfinance_analyst_estimates()` がyFinance値をDTOへ正規化する。
- `FundamentalAnalysisService` が既存yFinance TTLと同じ12時間でアナリスト予想をキャッシュする。
- `build_fundamental_output()` のDTO表示経路に `AnalystEstimatesSection` を追加し、株価評価・資本効率ブロックの後、株探ブロックの前に表示する。
