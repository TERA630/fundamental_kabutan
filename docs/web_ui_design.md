# Web UI 設計案

## 1. 目的

この設計案は、現在の Tkinter デスクトップ GUI の動作を大きく変えずに、Flask を使ってブラウザ上で表示・操作できるようにするための設計です。

- 既存のドメイン / UseCase / Presenter 層はそのまま再利用する。
- ブラウザ版では、現在の出力テキストと同等のテキスト表示・コピー機能を維持する。
- GitHub Codespaces でも実行できる構成とする。

---

## 2. 対象範囲

- Flask ベースの Web UI 追加
- 既存 GUI 層の共存
- 既存出力テキストの再利用
- Codespaces 実行対応
- クリップボードコピー機能のブラウザ実装

---

## 3. 現状の構成と再利用方針

### 3.1 既存構成

- `app/gui.py` / `app/gui_view.py` で Tkinter 画面を構築
- `app/gui_controller.py` が UseCase / Domain / Presenter を仲介
- `app/presentation/display_formatter.py` がテキスト出力の整形を担当
- `app/data/file_cache.py` などで設定・キャッシュを保持

### 3.2 再利用方針

- `FundamentalGuiController` をそのまま再利用し、Web 側の操作フローを実装する。
- `GUI` の `open_watchlist`, `open_kabutan_html_dir`, `generate_text`, `generate_summary` の役割を、Web ルートと API にマッピングする。
- 画面出力は既存の `build_fundamental_output` / `build_technical_output` 文字列を HTML 内にそのまま埋め込み、文字列をそのままコピーできるようにする。

---

## 4. 新規構成案

### 4.1 追加ファイル

- `app/web.py`
  - Flask アプリケーションのエントリポイント
  - ルート定義、フォーム受け取り、実行結果返却を担当
- `app/templates/index.html`
  - ブラウザ UI のテンプレート
  - 現状の画面要素を HTML フォームにマッピング
- `app/static/web.css` (必要に応じて)
  - 最低限のスタイル

### 4.2 追加依存

- `Flask`

必要であれば `requirements.txt` を新規追加または更新する。

---

## 5. Web UI の画面・操作フロー

### 5.1 画面項目

- 監視銘柄ファイル入力
  - `watchlist_path` の文字列入力／ファイルアップロード
- 株探 HTML フォルダ入力
  - `kabutan_html_dir` の文字列入力
- 銘柄選択
  - watchlist 解析後に選択肢を表示
- モード切替
  - Fundamental / Technical
- 取得 (Fetch)
- サマリ出力
- コピー
- 保存
- ステータスメッセージ表示
- 機関投資サマリ表示
- 出力表示エリア (`<pre>` / `<textarea>`)

### 5.2 コピー機能

- ブラウザ側で `navigator.clipboard.writeText(output)` を呼び出す。
- 表示テキストはそのままコピーされ、現状の Tkinter の `clipboard_append` と同等の機能を実現する。
- テキスト出力のフォーマットは既存と同一を維持する。

### 5.3 保存機能

- 現在の画面と同じく、生成済みテキストをファイルダウンロードとして提供する。
- `download` ボタンで `text/plain` ファイルを返す。

---

## 6. Codespaces 実行対応

### 6.1 実行方法

- Flask を `0.0.0.0` で起動し、Codespaces の公開ポートにバインドする。
- `app/web.py` に `if __name__ == "__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))` を追加する。
- `.devcontainer/devcontainer.json` は既存のままで問題ないが、必要ならポートフォワーディング設定を追加できる。

### 6.2 ファイル選択の実装想定

Codespaces ではクライアントのローカルファイルシステムに直接アクセスできないため、以下のいずれかを実装候補とする。

- A: repo 内のパスを直接入力して利用する。
- B: watchlist ファイルをブラウザからアップロードする。アップロード済みファイルはサーバ側に保存し、解析に使う。
- C: HTML フォルダもパス指定で扱い、必要なら `zip` 形式でのアップロードを将来的に追加する。

---

## 7. 画面コピーとテキスト出力保持

- 出力は `app.domain` / `app.presenters` の既存テキスト生成パスをそのまま再利用する。
- ブラウザ側では `output_text` を `<textarea readonly>` もしくは `<pre>` で表示し、コピー時に同じ文字列を渡す。
- これにより「画面コピーを選ぶとクリップボードには現状と同等のテキスト出力を維持」という要件を満たす。

---

## 8. 仕様書化の位置

- この設計案は `docs/web_ui_design.md` にまとめる。
- 必要なら `docs/display_spec.md` に「Web UI 版の振る舞い追加」について補足を加える。

---

## 9. コミットごとの作業分割案

### コミット 1: Web UI 基盤追加

- `Flask` 依存を追加
- `app/web.py` の雛形を追加
- `app/templates/index.html` を追加
- `docs/web_ui_design.md` を追加

### コミット 2: 既存コントローラとの統合

- `FundamentalGuiController` を Web 側から利用できるようにする
- watchlist / HTML dir / stock 選択 / fetch / summary の各ルートを実装
- 出力テキストをブラウザ画面に表示
- コピー・保存ボタンの JavaScript 実装

### コミット 3: Codespaces 対応と実行ドキュメント

- Flask の起動設定を `0.0.0.0` / `PORT` 対応に調整
- `.devcontainer/devcontainer.json` へ必要な記載を追加（公開ポートなど）
- `docs` に Codespaces 実行手順を追加

### コミット 4: テストと品質確認

- Web API エンドポイントの単体テスト追加
- 出力テキスト整合性の確認テスト追加
- UI 画面の基本動作をドキュメント化

---

## 10. 確認したいこと

1. Web UI は「既存 Tkinter GUI と共存」させる形で進めてよいですか？
2. Codespaces では `watchlist` はパス入力／アップロードのどちらを優先したいですか？
3. `kabutan_html_dir` はブラウザからのディレクトリアップロードではなく、コンテナ内パス指定で扱う想定で問題ないですか？
4. 画面コピーの対象は「Fundamental / Technical のどちらの出力でも、表示されているテキスト全体」でよいですか？

---

## 11. 今後の拡張候補

- `watchlist` のファイルアップロードを追加
- `kabutan_html_dir` のフォルダアップロード / ZIP アップロード対応
- 画面のステータスやメッセージを HTML でより分かりやすくする
- Web UI とデスクトップ GUI の共通コードをさらに明確に分離する
