# Web UI 設計案

## 1. 位置づけ

本書は、現在の Tkinter デスクトップ GUI と共存する Flask ベース Web UI の設計案である。
現時点では未実装案として扱い、実装判断では `docs/README.md` に記載した正本仕様を優先する。

## 2. 目的

- 既存の Domain / UseCase / Presenter 層を再利用する。
- ブラウザ上で Fundamental / Technical の取得結果を表示する。
- 既存出力テキストと同等のコピー・保存機能を提供する。
- GitHub Codespaces でも実行できる構成にする。

## 3. 対象範囲

- Flask ベースの Web UI 追加。
- 既存 Tkinter GUI との共存。
- 既存出力テキストの再利用。
- Codespaces 実行対応。
- ブラウザでのクリップボードコピー。

## 4. 再利用方針

- `FundamentalGuiController` を Web 側から再利用する。
- Tkinter GUI の `open_watchlist`, `open_kabutan_html_dir`, `generate_text`, `generate_summary` 相当の操作を Web ルートまたは API にマッピングする。
- 出力は既存の `build_fundamental_output()` / `build_technical_output()` が生成する文字列を使う。
- 画面上の表示テキストとコピー対象テキストは同一にする。

## 5. 新規構成案

| ファイル | 責務 |
|----------|------|
| `app/web.py` | Flask アプリケーションのエントリポイント、ルート定義、フォーム受け取り、実行結果返却 |
| `app/templates/index.html` | ブラウザ UI テンプレート |
| `app/static/web.css` | Web UI用スタイル |

追加依存:

- `Flask`

## 6. 画面項目

- 監視銘柄ファイル入力
- 株探 HTML フォルダ入力
- 銘柄選択
- Fundamental / Technical モード切替
- 取得
- サマリ出力
- コピー
- 保存
- ステータスメッセージ表示
- 機関投資サマリ表示
- 出力表示エリア

## 7. 操作仕様

### 7.1 取得

- Fundamental選択時は Fundamental 取得を実行する。
- Technical選択時は Technical 取得を実行する。
- ステータスメッセージと出力本文は、既存 GUI と同等の意味にする。

### 7.2 サマリ出力

- Fundamental選択時のみ `fundamental_summery-yyyy-mm-dd.md` を作成する。
- Technical選択時は、既存 GUI と同じく何もしない。

### 7.3 コピー

- ブラウザ側で `navigator.clipboard.writeText(output)` を呼び出す。
- コピー対象は表示中の出力本文とする。
- 機関投資サマリ固定パネルをコピー対象に含めるかは未確定。

### 7.4 保存

- 生成済みテキストを `text/plain` または Markdown としてダウンロード提供する。

## 8. Codespaces対応

- Flask は `0.0.0.0` で起動する。
- ポートは `PORT` 環境変数を優先し、未設定時は `8080` を使う。
- watchlist はファイルアップロードを優先し、未指定時のみ repo内/コンテナ内パス入力を扱う。
- 株探HTMLフォルダは、コンテナ内パス指定を基本案とする。
- 必要に応じて HTML ZIP アップロードを追加候補とする。

## 9. 確認事項

以下は仕様確定済み。

1. Web UI は既存 Tkinter GUI と共存させる。
2. Codespaces で watchlist はアップロードを優先する。
3. `kabutan_html_dir` はコンテナ内パス指定で扱う。
4. コピー対象に機関投資サマリ固定パネルを含める。

## 10. Fundamental 表示テーブル化仕様

### 10.1 目的

Web UI の Fundamental 画面では、既存のプレーンテキスト出力をコピー・保存用の正本として維持しつつ、画面表示だけを読みやすい HTML 表示にする。

### 10.2 対象ブロック

以下のブロックを HTML テーブルとして表示する。

1. `■株価評価・資本効率`
   - PER、配当利回り、PBR、ROE、ROIC、FCF Yield を年度列で表示する。
2. `■株探 通期業績推移`
   - 年次の売上、営業益、営業利益率、経常益、経常利益率、最終益、1株益、1株配当を表示する。
3. `■キャッシュフロー`
   - 年次の営業CF、投資CF、財務CF、現金等、Cash Conversion、FCF Yield、FCF Margin、営業CF Margin、投資積極度を表示する。
4. `■四半期トレンド`
   - 四半期ごとの売上、営業利益率、昨年同期比、修正一株益を表示する。

### 10.3 表示方針

- Web 画面には `textarea` とは別に Fundamental 用の HTML 表示領域を用意する。
- Fundamental モードでは HTML 表示領域を表示し、Technical モードでは従来どおりプレーンテキスト表示を使う。
- コピー・保存対象は従来どおり `state.output` のプレーンテキストとする。
- テーブル化対象外の Fundamental ブロックは、見出しと本文をプレーンテキスト相当のブロックとして表示する。
- データー欠損時は既存出力と同じく `N/A` または取得不可メッセージを表示する。

### 10.4 実装方針

- 既存の `build_fundamental_output()` が返す文字列は変更しない。
- Web 表示用に `DisplaySections` から HTML 表示モデルを作るレンダラーを追加する。
- 対象データは既存のセクションモデルを再利用する。
  - `ValuationTableSection`
  - `ForecastTableSection`
  - `CashflowTimelineSection`
  - `QuarterlyMetricsSection`
- Flask の `/fetch` では、Fundamental 取得時にプレーンテキストとあわせて Web 表示用 HTML を生成して `index.html` に渡す。
- HTML はテンプレート側で安全に描画できる構造にし、値はエスケープ済み文字列として扱う。

### 10.5 スタイル仕様

- テーブルは横スクロール可能なラッパー内に配置し、狭い画面でも列が潰れないようにする。
- 見出し行は薄い背景色、本文は罫線と余白で読みやすくする。
- 数値列は右寄せ、年度・四半期ラベル列は左寄せにする。
- テーブルの外枠は既存 Web UI の `--line`、`--panel`、`--text`、`--muted`、`--accent` に合わせる。
- 角丸は既存 UI と同じく 8px 以下にする。

### 10.6 テスト方針

- Web 表示モデル生成の単体テストを追加する。
- 少なくとも以下を検証する。
  - 株価評価・資本効率が PER から FCF Yield まで行として出る。
  - 株探通期業績推移が年次行のテーブルになる。
  - キャッシュフローが年次行のテーブルになる。
  - 四半期トレンドが四半期行のテーブルになる。
  - `state.output` のコピー・保存用テキストは従来どおり維持される。

## 11. 作業進捗

- 2026-06-07: `■四半期業績推移` は通常表示対象ではないため、対象を `■四半期トレンド` に確定。
- 2026-06-07: Web 表示用に Fundamental 出力テキストをブロック化し、対象4ブロックをテーブル表示モデルへ変換する方針で実装開始。
- 2026-06-07: `app/presentation/web_fundamental_output.py` を追加し、株価評価・資本効率、株探通期業績推移、キャッシュフロー、四半期トレンドのテーブル化を実装。
- 2026-06-07: `app/web.py`、`app/templates/index.html`、`app/static/web.css` を更新し、Fundamental モードのみリッチ表示に切り替えるよう実装。
- 2026-06-07: `tests/test_web_fundamental_output.py` を追加し、対象4ブロックとコピー用プレーンテキスト維持のテストを追加。
- 2026-06-07: WebUIでテーブル表示にならない事象を確認。テンプレート単体ではテーブルHTML生成済みであることを確認し、古い可能性のある `8080` プロセスを停止して修正版コードで再起動。
- 2026-06-07: 表示用の既定を `textarea` にする必要がないため、出力パネルを常に HTML 表示領域へ変更。Fundamental はテーブル混在表示、Technical は `<pre>` 表示とし、コピー用の隠し `textarea` のみ維持。
- 2026-06-07: `8080` に古い `python -m app.web` プロセスが複数残っていたため、全WebUIプロセスを停止。起動元を明示する `run_web.py` を追加し、`8080` は `run_web.py` 起動の1プロセスに整理。
