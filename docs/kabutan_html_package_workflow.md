# 株探HTMLパッケージ運用メモ

## 目的

ローカルで保存した株探HTMLを、GitHub Codespaces の Web UI でも使えるようにする。

この機能は Fundamental 解析用の補助機能である。Technical 解析では使わない。

## 現状の実装範囲

Web UI と Tkinter GUI には、株探HTMLフォルダを正規化してZip化する導線がある。

Web UI には、作成済みZipをアップロードして展開し、展開後の `html/` を `kabutan_html_dir` に設定する導線がある。

ただし、実ブラウザでの運用確認はまだ十分ではない。動作が不安定な場合は、この文書の「確認事項」を優先して切り分ける。

## 正規化で行うこと

`app/domain/usecases/kabutan_html_normalizer.py` が担当する。

- `.html` / `.htm` を対象にする。
- `<body>` 内のHTMLを取り出す。
- `script`、`style`、`noscript`、`iframe`、HTMLコメントを除去する。
- `<title>` は4桁の銘柄コードのみへ整理する。
- 保存ファイル名は `7203.html` のような4桁コード基準にする。
- 同じコードが複数ある場合は `7203-2.html` のように連番を付ける。
- 4桁コードを推定できないHTMLはスキップし、manifestに記録する。

銘柄名は株探HTMLから取得しない。既存フローでは監視銘柄ファイルの `(銘柄名, コード)` を使う。

## パッケージ構成

`app/services/kabutan_html_package_service.py` が担当する。

Zipの基本構成は次の通り。

```text
kabutan_html_package.zip
  manifest.json
  html/
    7203.html
    7974.html
```

`manifest.json` には、元ファイル名、出力ファイル名、推定コード、処理結果、スキップ理由を記録する。

## Web UIでの作成手順

1. Web UIを起動する。
2. `Kabutan HTML folder` でHTMLフォルダをアップロードする、または `Kabutan_html_dir` にコンテナ内パスを入力して `フォルダ設定` を押す。
3. `HTMLを正規化してZip作成` を押す。
4. 正常に作成されると、正規化済み `html/` が現在の `kabutan_html_dir` に設定される。
5. `Zip保存` が表示された場合は、`kabutan_html_package.zip` をダウンロードできる。

作成先は `.fundamental_cache/web_kabutan_html_package/` 配下である。

## Codespacesでの受け入れ手順

1. CodespacesでWeb UIを開く。
2. `Kabutan HTML package zip` に `kabutan_html_package.zip` を選択する。
3. `Zipを展開して設定` を押す。
4. 展開後の `html/` が `kabutan_html_dir` に設定される。
5. Fundamentalの `取得` または `サマリ表示` を実行する。

展開先は `.fundamental_cache/web_imported_kabutan_html_package/` 配下である。

## 安全性と制約

- Zip内に `html/` フォルダがない場合は失敗する。
- Zip内の `html/` に `.html` がない場合は失敗する。
- Zip内の `../` など、展開先の外へ出るパスは拒否する。
- 展開に失敗した場合は、途中展開ディレクトリを削除する。
- Web UIのZip受け入れは `.zip` 拡張子のみを受け付ける。

## 確認事項

現時点では、次の手動確認が残っている。

- ローカルWeb UIでHTMLフォルダをアップロードできるか。
- `HTMLを正規化してZip作成` 後に `Zip保存` が表示されるか。
- ダウンロードしたZipをCodespaces側Web UIでアップロードできるか。
- `Zipを展開して設定` 後に、Fundamental解析が正規化済みHTMLを読めるか。
- スキップされたHTMLがある場合に、manifestで理由を確認できるか。

## 既知の弱い点

- manifestの中身は画面上に表表示していない。
- Status欄にパスと件数を出すだけなので、長いパスでは読みづらい。
- Tkinter GUIにはZip作成導線はあるが、Zip受け入れ導線はない。
- 実ブラウザでの確認が不十分なため、UI操作上の詰まりが残っている可能性がある。
