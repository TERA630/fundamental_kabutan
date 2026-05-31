# Fundamental画面 yFinanceアナリスト予想 仕様

## 目的

Fundamental画面に、yFinanceから取得できるアナリスト目標株価、EPSトレンド、EPS修正人数を表示する。
現時点ではyFinanceの取得安定性を確認する段階のため、表示項目は多めに残し、今後の運用で集約する。

## 取得元

- 対象シンボルは既存yFinance取得と同じ `{code4}.T` とする。
- 目標株価とアナリスト人数は `ticker.info` から取得する。
  - `targetMeanPrice`
  - `numberOfAnalystOpinions`
- EPSトレンドは `ticker.eps_trend` のPandas DataFrameから取得する。
- EPS修正人数は `ticker.eps_revisions` のPandas DataFrameから取得する。
  - 互換性のため、属性名が `eps_revisons` の場合もフォールバックとして参照する。

## 表示対象

- 四半期行 `0q`, `+1q` は表示しない。
- 年度末行のみ表示する。
  - `0y`: 今期末
  - `+1y`: 来季末
- EPS trendは `90daysAgo -> 60daysAgo -> 30daysAgo -> 7daysAgo -> current` の順で表示する。
- EPS revisionsは30日を標準表示とし、7日も併記する。

## 表示形式

```text
■アナリスト予想(yFinance)
アナリスト目標株価：{targetMeanPrice} 円 (アナリスト {numberOfAnalystOpinions}人)
EPS trend :
  今期末 {90daysAgo}→{60daysAgo}→{30daysAgo}→{7daysAgo}→{current}
  来季末 {90daysAgo}→{60daysAgo}→{30daysAgo}→{7daysAgo}→{current}
EPS revisions (30日 / 7日):
今期末： 上方修正 {upLast30days}人（7日 {upLast7days}人）　下方修正 {downLast30days}人（7日 {downLast7days}人）
来季末： 上方修正 {upLast30days}人（7日 {upLast7days}人）　下方修正 {downLast30days}人（7日 {downLast7days}人）
```

## 欠損時の扱い

- ブロックは常に表示する。
- 取得失敗、対象行なし、対象列なし、値変換不可の場合は該当値を `N/A` と表示する。
- yFinance取得失敗は画面全体の失敗にしない。

## 実装方針

- `app.domain.models.analyst_estimates` にDTOを追加する。
- `app.data.market_data_provider.fetch_yfinance_analyst_estimates()` がyFinance値をDTOへ正規化する。
- `FundamentalAnalysisService` が既存yFinance TTLと同じ12時間でアナリスト予想をキャッシュする。
- `build_fundamental_output()` のDTO表示経路に `AnalystEstimatesSection` を追加し、株価評価・資本効率ブロックの後、株探ブロックの前に表示する。
