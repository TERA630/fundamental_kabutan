# rankCF 実装設計

最終更新: 2026-05-28

rankCF 採点仕様の正本は `docs/rankCF_spec.md`。本書は実装構成、責務分離、運用上の確定事項、未完了タスクを管理する。

## 1. 目的

- rankCF の採点ロジックを Domain 層の純粋関数として保持する。
- GUI 層は計算を持たず、UseCase から受け取った `CfScoringResult` を表示する。
- 将来の UI 差し替え時も、採点ロジックを再利用できる構成にする。

## 2. 責務分離

依存方向:

- Presentation → UseCase → Domain
- Data / Infrastructure は UseCase に注入される Port 実装として接続する。

禁止事項:

- Domain / UseCase は `tkinter` などの UI ライブラリを import しない。
- GUI コードは採点ロジックを直接実装しない。

## 3. Domain

### 入力モデル

- `app/domain/models/cf_scoring_input.py`
- `CfScoringInput`

主なフィールド:

- `code4`
- `as_of`
- `roic`
- `ocf`
- `net_income`
- `operating_income`
- `revenue`
- `fcf`
- `eps_cagr_3y`
- `sales_cagr_3y`
- `fcf_yield`
- `per`

### 結果モデル

- `app/domain/models/cf_scoring_result.py`
- `MetricScore`
- `CategoryScore`
- `TotalScore`
- `CfScoringResult`

`MetricScore.rule_notes` に免責・ペナルティ適用理由を保持する。

### 採点ポリシー

- `app/domain/policies/cf_scoring.py`
- 公開関数: `calculate_cf_score(input_data: CfScoringInput) -> CfScoringResult`

採点順:

1. 指標ごとの基礎点を計算する。
2. 免責ルールを適用する。
3. ペナルティを適用する。
4. Quality / Growth / Valuation 小計と Total を確定する。

## 4. UseCase

- `app/domain/usecases/fundamental_analysis.py`
- `FundamentalAnalysisService.build_cf_scoring_input()` が市況・株探・CF・財務データから `CfScoringInput` を構築する。
- `FundamentalAnalysisService.build_analysis_output()` が `calculate_cf_score()` を呼び出し、出力ビルダへ `cf_scoring_result` を渡す。

確定している入力優先ルール:

- PER は forecast EPS 由来を優先する。
- forecast EPS が取得不可の場合のみ market PER を使う。
- `fcf_yield` は `FCF / 時価総額` で算出する。
- `as_of` は表示仕様上 `cf_scoring_result.as_of` として扱う。

## 5. Presentation

- `app/presenters.py` が `CfScoringResult` を表示セクションDTOへ変換する。
- `app/presentation/display_formatter.py` が表示文字列へ整形する。
- 表示順と表示文言は `docs/display_spec.md` を正とする。

欠損値:

- 欠損指標は `N/A`、0点として扱う。
- 表示では当該指標行を省略可能。
- 省略時は内部ログに `取得不可: {指標名} ({理由})` を出力する。

## 6. テスト

主なテスト:

- `tests/test_cf_scoring_policy.py`
- `tests/test_usecase_cf_scoring_integration.py`
- `tests/test_usecase_fundamental_analysis.py`
- `tests/test_presenters_cf_scoring_output.py`

確認対象:

- 指標ごとの境界値
- FCF Ratio 救済
- FCF Yield 底上げ
- PER 高成長加点
- Cash Conversion 品質フィルター
- UseCase での入力構築
- Presenter 表示と欠損ログ

## 7. 未完了タスク

なし。

## 8. 検証状況

- 直近確認: `python -m pytest`
- 結果: `193 passed, 1 warning`
