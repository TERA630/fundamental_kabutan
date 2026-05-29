

監視銘柄より銘柄コードを読み込み、fundamental_summery.mdとして出力する機能追加の仕様書。

# 起動
　GUI層にサマリ出力ボタンを作成する。　ユーザーがそれをクリックするとサマリ作成ユースケースが起動する。

# サマリ作成ユースケース
　
1．監視銘柄の先頭から順に銘柄コードを読み込む。
2．後述する列仕様で銘柄コードから必要な指標を計算し、行データを作成して保持する　|銘柄名(銘柄コード)|総合スコア|Qualityスコア|Growthスコア|Valuationスコア|...
3.　次の銘柄コードを読み込み、全ての銘柄について総合スコアを始めとした行データを作成して保持する。
4． 総合スコアが作成できなければその銘柄については行データは保持しない。
5．　Quality、Growth,Valuationのスコアのいずれかが算出できない場合は算出できないスコアは0点と評価するが、表には算出不可としておく。
6． 総合スコア順に行データをソートする。
7． 同スコアの場合は、Growthスコア、Qualityスコアの順に優先。
8． 行データにヘッダをつけ、ソートした行データを全て書き込み、Markdown文書(fundamental_summery.md)に出力する。

# 仕様
1．　列　　銘柄名(銘柄コード)
2．　スコア　：　銘柄の総合スコア(算出は既存ドメインルール通り)
3．　Quality ：　Qualityスコア(算出は既存ドメインルール通り)
4．　Growth　：　Growthスコア(算出は既存ドメインルール通り)
5．　Valuation：　Valuationスコア(算出は既存ドメインルール通り)
6．　ROIC：　取得できた最新の実績ROIC
7．　営業利益率：　取得できた最新の(予想でも良い)営業利益率
8．　Cash conversion：　取得できた最新の実績の Cash conversion
9.　　PER　　　　：　取得できた最新の(予想でも良い)　PER

---

# 実装前確認事項

ドメイン層実装では、以下を確認済み前提として扱う。

1. 出力ファイル名は `fundamental_summery.md` とする。
2. 総合スコアは、既存の rankCF ドメインルール `calculate_cf_score()` の `total.total_points` を使う。
   - 株探通期業績が取得できず `CfScoringInput` を組み立てられない場合は、総合スコア作成不可として行を出力しない。
3. Quality / Growth / Valuation は、既存 rankCF のカテゴリ subtotal を使う。
   - カテゴリ内の全指標が `N/A` の場合は、ソート上は `0` 点として扱い、Markdown 表示は `N/A` とする。
   - 一部指標だけが欠損している場合は、既存ルールどおり欠損指標を `0` 点として subtotal を表示する。
4. `ROIC` は、財務指標行から算出できた最新実績 ROIC を使う。
5. `営業利益率` は、株探通期業績行のうち、予想を含む最新行の `営業利益 ÷ 売上高` を使う。
6. `Cash conversion` は、既存 rankCF の Cash Conversion と同じく `営業CF ÷ 純利益` で算出する。
   - 分母が `0` または欠損、必要値が欠損している場合は `N/A` とする。
7. `PER` は、既存 rankCF 入力と同じく forecast EPS 由来を優先し、取得不可時のみ market PER を使う。

# ドメイン実装設計案

## 責務

| 追加要素 | 責務 |
|----------|------|
| `FundamentalSummaryRow` | Markdown 1行分のサマリ値を保持するDTO |
| `FundamentalSummaryTable` | ソート済み行と除外銘柄情報を保持するDTO |
| `SkippedSummaryStock` | 総合スコアを作成できず除外した銘柄と理由を保持するDTO |
| `FundamentalSummaryService` | 監視銘柄リストを順番に分析し、サマリ行を作成・ソートするUseCase |
| `build_fundamental_summary_markdown()` | サマリDTOをMarkdown表へ変換するBuilder |

## 処理フロー

1. GUI / Controller から監視銘柄の `(name, code4)` リストと株探HTMLフォルダを受け取る。
2. `FundamentalSummaryService` が銘柄ごとに既存 `FundamentalAnalysisService` の取得・計算処理を再利用する。
3. `CfScoringInput` が作成できない銘柄は `SkippedSummaryStock` として保持し、表には出さない。
4. `CfScoringResult` から総合スコア、Quality、Growth、Valuation を取り出す。
5. ROIC、営業利益率、Cash conversion、PER を同じ入力データから解決する。
6. 総合スコア降順、Growth降順、Quality降順、銘柄コード昇順でソートする。
7. Builder がMarkdown表を返す。ファイル書き込みはData / GUI結合側で行う。

## ソート仕様

| 優先 | キー | 順序 |
|------|------|------|
| 1 | 総合スコア | 降順 |
| 2 | Growthスコア | 降順 |
| 3 | Qualityスコア | 降順 |
| 4 | 銘柄コード | 昇順 |

## Markdown列仕様

| 列 | 表示 |
|----|------|
| 銘柄名(銘柄コード) | `{name} ({code4})` |
| 総合スコア | 整数 |
| Quality | 整数または `N/A` |
| Growth | 整数または `N/A` |
| Valuation | 整数または `N/A` |
| ROIC | `x.x%` または `N/A` |
| 営業利益率 | `x.x%` または `N/A` |
| Cash conversion | `x.xx` または `N/A` |
| PER | `x.x倍` または `N/A` |

# ドメイン層実装工程

## Phase 1: DTO追加

**状態: 完了（2026-05-29）**

- `app/domain/models/fundamental_summary.py` を追加する。
- サマリ行、サマリ表、除外銘柄のDTOを定義する。

## Phase 2: UseCase追加

**状態: 完了（2026-05-29）**

- `app/domain/usecases/fundamental_summary.py` を追加する。
- 既存 `FundamentalAnalysisService` の価格取得、株探HTML取得、財務行構築、rankCF入力構築を再利用してサマリ行を作成する。
- 総合スコアが作成できない銘柄を表から除外し、理由を保持する。

## Phase 3: Markdown Builder追加

**状態: 完了（2026-05-29）**

- `app/domain/builders/fundamental_summary.py` を追加する。
- サマリ表DTOをMarkdown表へ変換する。
- 欠損値は表示仕様どおり `N/A` とする。

## Phase 4: ドメイン単体テスト追加

**状態: 完了（2026-05-29）**

- サマリ行の作成、欠損カテゴリの `N/A` 表示、ソート順、総合スコア作成不可銘柄の除外をテストする。

## Phase 5: Cash conversion列への差し替え

**状態: 完了（2026-05-30）**

- サマリ列に `Cash conversion` を採用する。
- `FundamentalSummaryRow` は `cash_conversion` を保持する。
- 値は rankCF の `cash_conversion_np` 指標と同じ計算結果を採用する。
- Markdown Builder は `Cash conversion` を小数2桁で表示する。

# GUI結合工程案

## Phase 6: Controller結合

**状態: 完了（2026-05-30）**

- `FundamentalGuiController` にサマリ作成メソッドを追加する。
- 監視銘柄リスト、株探HTMLフォルダ、保存先ディレクトリを受け取り、`FundamentalSummaryService` と `build_fundamental_summary_markdown()` を呼ぶ。
- 出力ファイル名は固定で `fundamental_summery.md` とする。
- 書き込み成功時は保存先パスを返す。

**完了内容**

- `FundamentalGuiController.build_and_save_fundamental_summary()` を追加した。
- 保存先は呼び出し元から受け取り、固定ファイル名 `fundamental_summery.md` で書き込む。
- GUIからは監視銘柄ファイルの親ディレクトリを保存先として渡す。

## Phase 7: GUIボタン追加

**状態: 完了（2026-05-30）**

- GUIに `サマリ出力` ボタンを追加する。
- 監視銘柄未読込時は既存の必須項目不足メッセージに準じてステータス表示する。
- 実行中はサマリ作成中、完了時は `保存完了: {path}` に準じたステータス表示にする。

**完了内容**

- `サマリ出力` ボタンを取得ボタンの隣に追加した。
- サマリ作成は既存の取得処理と同じく別スレッドで実行し、実行中は主要ボタンを無効化する。
- 株探HTMLフォルダ未設定時は既存の再選択フローを使う。
- 完了時は `保存完了: {path}`、失敗時は `サマリ作成に失敗しました。` を表示する。

## Phase 8: GUI結合テスト

**状態: 未着手**

- Controller単体テストで、監視銘柄からMarkdownが作成され `fundamental_summery.md` に保存されることを確認する。
- GUI状態テストで、ボタン操作時の必須項目チェックと完了ステータスを確認する。
