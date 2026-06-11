# 株探HTML Package運用メモ

## 目的

ローカルで保存した株探HTMLを正規化し、Web UI の Fundamental 解析で使える Package Zip として扱う。

Technical 解析では使わない。

## 通常運用

Web UI でユーザーが通常触る入力は次のどちらか。

- `Kabutan HTML folder` でHTMLフォルダをアップロード、または `Kabutan_html_dir` にコンテナ内パスを入力して `フォルダ設定` を押す。
- Tkinterで作成済みのPackage Zipを `Kabutan HTML package zip` で選択し、`Zipを展開して設定` を押す。

Package Zip は選択後すぐにアプリ内部のキャッシュ領域へ展開し、展開後の `html/` を既存の解析処理へ渡す。

## Package作成

Package Zip の作成は Tkinter UI で行う。Web UI ではHTML正規化とZip作成は行わない。

1. Tkinterで株探HTMLフォルダを設定する。
2. `HTML正規化+Zip作成` を押す。
3. 作成された `kabutan_html_package.zip` を必要に応じてWeb UIへアップロードする。

作成先は Tkinter のキャッシュ領域配下。

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
- 展開に失敗した場合は、途中展開ディレクトリを削除する。
