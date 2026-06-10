# 株探HTML Package運用メモ

## 目的

ローカルで保存した株探HTMLを正規化し、Web UI の Fundamental 解析で使える Package Zip として扱う。

Technical 解析では使わない。

## 通常運用

Web UI でユーザーが通常触る入力は次の2つだけ。

1. `WatchListファイル` で監視銘柄 md を選択する。
2. `正規化HTML Package Zip` で Package Zip を選択する。

どちらもファイル選択後に自動で読み込む。追加の読込ボタンや手動展開ボタンは置かない。

Package Zip は選択時に検査してパスを保持する。Fundamental の `取得` または `サマリ表示` が必要になった時だけ、アプリ内部でキャッシュ領域へ遅延展開する。

## Package作成

生の株探HTMLフォルダは通常運用には出さない。Web UI の `株探HTML正規化` を開いた時だけ使う。

1. `株探HTML正規化` を開く。
2. `生HTMLフォルダ` を選択する、または `生HTMLパス` を入力する。
3. `HTML正規化Zip作成` を押す。
4. 作成後、必要なら `Package保存` で `kabutan_html_package.zip` を保存する。

作成先は `.fundamental_cache/web_kabutan_html_package/` 配下。

## Package構成

```text
kabutan_html_package.zip
  manifest.json
  html/
    7203.html
    7974.html
```

`manifest.json` には、元ファイル名、出力ファイル名、推定コード、処理結果、スキップ理由を記録する。

## 正規化で行うこと

- `.html` / `.htm` を対象にする。
- `<body>` 内のHTMLを取り出す。
- `script`、`style`、`noscript`、`iframe`、HTMLコメントを除去する。
- `<title>` は4桁の銘柄コードのみへ整理する。
- 保存ファイル名は `7203.html` のような4桁コード基準にする。
- 同じコードが複数ある場合は `7203-2.html` のように連番を付ける。
- 4桁コードを推定できないHTMLはスキップし、manifestに記録する。

## 安全性と制約

- Package Zip 内に `html/` フォルダがない場合は失敗する。
- Package Zip 内の `html/` に `.html` がない場合は失敗する。
- Package Zip 内の `../` など、展開先の外へ出るパスは拒否する。
- 遅延展開に失敗した場合は、途中展開ディレクトリを削除する。
