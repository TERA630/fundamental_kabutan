# rankCF 実装状況（2026-05-27 時点）

## 実装済み
- ドメインのスコア入力モデル `CfScoringInput` を実装済み。
- ドメインのスコア結果モデル `CfScoringResult`（カテゴリ別・総合点）を実装済み。
- rankCF 採点ポリシー `calculate_cf_score` と各指標スコア関数を実装済み。
- ユースケース `FundamentalAnalysisService.build_analysis_output()` で
  - 市況・業績データから `build_cf_scoring_input()` を構築
  - `calculate_cf_score()` を呼び出し
  - 出力ビルダへ `cf_scoring_result` を連携
- Presenter 側で rankCF 出力テキスト（合計点、判定、カテゴリ内訳、ルール注記）を表示済み。
- テストを追加済み（ポリシー単体、ユースケース統合、Presenter 出力、PER計算優先ルール）。

## 未完了 / 改善余地
1. **`build_cf_scoring_input()` 内の `fcf_yield` が実質未実装**
   - 現状は算出ロジックがなく、常に `None` のまま。
   - 結果として Valuation の一部が `N/A` になりやすい。

2. **`FundamentalAnalysisService` 内にスコア入力構築の重複実装がある**
   - `_build_cf_scoring_input()` と `build_cf_scoring_input()` が併存。
   - 片方は `market_cap` ベース、片方は `price/forecast EPS` ベースで PER 算出しており、挙動が二重化。

3. **仕様ドキュメントとの最終突合（表示仕様確定）が未完了**
   - どの指標を `N/A` 許容にするか
   - `as_of` の定義（実績基準 or 取得日基準）
   - 表示順・注記文言の最終化

## 次アクション案
- 重複する入力構築経路を一本化（公開 `build_cf_scoring_input()` に寄せる等）。
- `fcf_yield` を算出可能なデータ経路を定義（`market_cap` 利用 or 代替指標採用）。
- `docs/rankCF_spec.md` と `docs/display_spec.md` の突合チェックを行い、表示仕様を確定。
