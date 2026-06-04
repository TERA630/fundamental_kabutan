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
- watchlist は、repo内パス入力またはファイルアップロードで扱う。
- 株探HTMLフォルダは、コンテナ内パス指定を基本案とする。
- 必要に応じて HTML ZIP アップロードを追加候補とする。

## 9. 確認事項

以下は仕様確定前に確認が必要。

1. Web UI を既存 Tkinter GUI と共存させる方針でよいか。
2. Codespaces で watchlist はパス入力とアップロードのどちらを優先するか。
3. `kabutan_html_dir` はコンテナ内パス指定で扱う想定でよいか。
4. コピー対象に機関投資サマリ固定パネルを含めるか。
