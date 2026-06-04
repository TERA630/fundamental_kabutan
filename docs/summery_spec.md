# 監視銘柄 Fundamental サマリ仕様

監視銘柄ファイルから銘柄コードを読み込み、Fundamentalサマリを Markdown 表として `fundamental_summery-yyyy-mm-dd.md` に出力する。

## 1. 位置づけ

- 本書は監視銘柄単位の Fundamental サマリ出力仕様を定義する。
- 個別銘柄の表示仕様は `docs/display_spec.md` を正とする。
- rankCF の採点ルールは `docs/rankCF_spec.md` を正とする。
- Domain / UseCase / Builder の責務境界は `docs/domain_spec_proposal.md` を正とする。

## 2. 起動条件

- GUI の `サマリ出力` ボタンから起動する。
- Fundamentalタブ選択時のみサマリを作成する。
- Technicalタブ選択時はファイル作成・ステータス変更・エラー表示を行わない。
- 監視銘柄ファイルと株探HTMLフォルダが必要。
- 出力先は監視銘柄ファイルの親ディレクトリとする。

## 3. 処理フロー

1. 監視銘柄の先頭から順に `(銘柄名, 4桁コード)` を読み込む。
2. 銘柄ごとに既存 `FundamentalAnalysisService` の取得・計算処理を再利用する。
3. `CfScoringInput` を作成できない銘柄は、総合スコア作成不可として表へ出力しない。
4. `CfScoringResult` から総合スコア、Quality、Growth、Valuation を取り出す。
5. 営業利益率、営業利益3年CAGR、ROIC、Cash conversion、PER、投資率を同じ入力データから解決する。
6. 総合スコア降順、Growth降順、Quality降順、銘柄コード昇順でソートする。
7. Markdown表を作成し、`fundamental_summery-yyyy-mm-dd.md` として保存する。

## 4. 出力ファイル

- ファイル名: `fundamental_summery-yyyy-mm-dd.md`
- `yyyy-mm-dd` はサマリ作成日の年月日。
- 文字コードは UTF-8。

## 5. Markdown列仕様

| 列 | 表示 |
|----|------|
| 銘柄名(銘柄コード) | `{name} ({code4})` |
| 総合スコア | 整数 |
| Quality | 整数または `N/A` |
| Growth | 整数または `N/A` |
| Valuation | 整数または `N/A` |
| 営業利益率 | `x.x%` または `N/A` |
| 営業利益3年CAGR | `x.x%` または `N/A` |
| ROIC | `x.x%` または `N/A` |
| Cash conversion | `x.xx` または `N/A` |
| PER | `x.x倍` または `N/A` |
| 投資率 | `x.x%` または `N/A` |

## 6. 指標解決ルール

- 総合スコアは `calculate_cf_score()` の `total.total_points` を使う。
- Quality / Growth / Valuation は rankCF のカテゴリ subtotal を使う。
- カテゴリ内の全指標が `N/A` の場合は、ソート上は `0` 点、Markdown表示は `N/A` とする。
- 一部指標だけが欠損している場合は、rankCF ルールどおり欠損指標を `0` 点として subtotal を表示する。
- `営業利益率` は、株探通期業績行のうち予想を含む最新行の `営業利益 ÷ 売上高` を使う。
- `営業利益3年CAGR` は、予想を含む最新通期行を終点、終点年度の3年前の行を始点として `calc_cagr(始点営業利益, 終点営業利益, 3)` で算出する。
- `ROIC` は、財務指標行から算出できた最新実績 ROIC を使う。
- `Cash conversion` は、rankCF の Cash Conversion と同じく `営業CF ÷ 純利益` で算出する。
- `PER` は、rankCF 入力と同じく forecast EPS 由来を優先し、取得不可時のみ market PER を使う。
- `投資率` は、最新CF実績行の `投資CF ÷ 営業CF × 100` で算出し、符号を維持する。

## 7. 欠損時の扱い

- 総合スコアを作成できない銘柄は表へ出力しない。
- 3年前の営業利益が欠損、0以下、または該当年度がない場合、営業利益3年CAGR は `N/A` とする。
- Cash conversion は、分母が `0` または欠損、必要値が欠損している場合は `N/A` とする。
- 投資率は、営業CFが `0` または欠損、投資CFが欠損している場合は `N/A` とする。

## 8. 実装責務

| 要素 | 責務 |
|------|------|
| `FundamentalSummaryRow` | Markdown 1行分のサマリ値を保持するDTO |
| `FundamentalSummaryTable` | ソート済み行と除外銘柄情報を保持するDTO |
| `SkippedSummaryStock` | 総合スコアを作成できず除外した銘柄と理由を保持するDTO |
| `FundamentalSummaryService` | 監視銘柄リストを順番に分析し、サマリ行を作成・ソートするUseCase |
| `build_fundamental_summary_markdown()` | サマリDTOをMarkdown表へ変換するBuilder |

