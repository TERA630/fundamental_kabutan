# Fundamental Summary Display Specification

## 1. 概要

本仕様書は、Tkinter GUI と Web UI における Fundamental サマリ表示の動作要件を整理する。

- Tkinter は現状の `サマリ出力` の動作と表示を変更しない。
- Web UI では `サマリ表示` を Web 固有の HTML 表示とし、同等出力を画面上で表現する。
- Web UI の Technical 画面では `サマリ表示` ボタンを表示するが、無効化する。

## 2. 目的

Web UI における Fundamental 画面のサマリ体験を、Tkinter で生成していた Markdown 出力と同等の見た目・情報量で実装しつつ、Web UI 固有の HTML 表示を提供する。

## 3. 対象範囲

### 3.1 変更対象

- `app/web.py`
- `app/templates/index.html`
- Web UI 用の表示ロジック（`app/presentation/web_fundamental_output.py` など）
- `docs/fundamental_summary_spec.md`

### 3.2 変更しない対象

- `app/gui.py` / Tkinter の画面表示と動作
- `app/gui_view.py` / `app/gui_controller.py` の Tkinter 向け既存動作
- `FundamentalSummaryService` の内部ロジック

## 4. 要件

### 4.1 ボタン名称変更

- Web UI の `app/templates/index.html` で、`/summary` 呼び出しボタンのラベルを `サマリ表示` に変更する。
- 表示モードは `Fundamental` / `Technical` によって切り替えできる。

### 4.2 Web UI Fundamental 画面の挙動

- `Fundamental` モードで `サマリ表示` を押すと、以下の処理を行う。
  1. 現在の WatchList と Kabutan HTML フォルダなどの入力を前提に、`FundamentalSummaryService` を使ってサマリデータを生成する。
  2. 生成されたサマリを `build_fundamental_summary_markdown()` 相当の構造で受け取り、Web表示用に HTML テーブルへ変換する。
  3. Web 画面には Markdown ではなく HTML 表として表示する。

- 表示内容は Tkinter の Markdown 出力イメージと同等とする。
- HTML 表は見出し、横並びセル、集計値、スコアを含む。
- 色付けや強調は可読性を高める範囲で適用する。

### 4.3 Web UI Technical 画面の挙動

- `Technical` モードでも `サマリ表示` ボタンは表示されたままとする。
- ただし、このモードではボタンを押せないように無効化する。
- Technical 画面のサマリ表示処理は別工程で扱い、今回の実装では `未対応` とする。

### 4.4 保存設計の提案

#### 4.4.1 Web UI の保存要件

- Web UI における `サマリ表示` は HTML レンダリングを主目的とする。
- 同時に「ファイル保存」も可能にしたいが、保存方式は Web UI の特性を踏まえて設計する。

#### 4.4.2 提案 1：HTML 表示とダウンロード両対応

- `サマリ表示` を押したときに表示する HTML を内部で生成し、画面にレンダリングする。
- 追加で「HTML ダウンロード」ボタンを用意し、同じ HTML 表をファイルとしてダウンロードできるようにする。
- 保存するファイル形式は `summary.html` もしくは `summary.md` で選択可能にすると柔軟。

#### 4.4.3 提案 2：Web UI 側で Markdown も保持してダウンロード

- `FundamentalSummaryService` から Markdown を生成したあと、HTML 表と並行して Markdown データも保持する。
- 画面上は HTML 表として表示しつつ、`ダウンロード` ボタンで Markdown 版を取得できるようにする。
- こうすることで Tkinter の既存出力と同等の形式を保持しつつ、Web 表示と保存を切り分けられる。

#### 4.4.4 推奨

- まずは Web UI に HTML 表表示を実装し、`HTMLダウンロード` を追加する設計が最も自然。
- その後、必要に応じて Markdown ダウンロードも追加するのが段階的で良い。

## 5. 表示仕様

### 5.1 Fundamentals サマリ HTML 表構造

Web UI では以下の構造を想定する。

- `機関投資サマリ` 固定パネルは現在と同じ `state.institutional_summary` で表示継続。
- `サマリ表示` は以下のセクションで構成される。
  - 全体説明文（サマリの対象銘柄と生成日など）
  - 監視銘柄サマリテーブル
  - 災害や取得失敗時は `N/A` を明確表示

- テーブル列は横並びで表示する。
- テーブルは以下の項目を含む。
  - 銘柄名 / コード
  - スコア合計、Quality、Growth、Valuation
  - ROIC、PER、過去数年の売上/利益推移など
- スコアや値の見出し行は強調し、奇数/偶数行は背景色を切り替えて可読性を上げる。

### 5.2 HTML 表の見た目方針

- セルは左寄せ / 右寄せを用途に応じて使い分ける。
- 数値は桁区切り・単位表記を維持する。
- `N/A` は淡いグレーで表示するか、弱い色で目立ちすぎないようにする。
- 表見出しの固定表示は `th` で実装。
- 関連集計値は、表の上部または列のラベルに明示する。

## 6. 画面操作フロー

### 6.1 Web UI Fundamental モード

1. ユーザーが銘柄と Kabutan HTML フォルダを指定する。
2. `取得` ボタンで出力を生成する（既存機能）。
3. `サマリ表示` ボタンを押す。
4. サマリ生成処理が実行され、画面に HTML テーブルが表示される。
5. 必要なら `ダウンロード` もしくは `HTML保存` によって保存できる。

### 6.2 Web UI Technical モード

1. `Technical` を選択すると `サマリ表示` ボタンは有効化されない。
2. `取得` ボタンのみが有効に働く。

### 6.3 Tkinter GUI

- Tkinter の `サマリ出力` は現状どおり Markdown を生成してファイルへ保存する。
- Web UI の変更は Tkinter に影響しない。

## 7. 追加設計メモ

- `サマリ表示` には `GET /summary` のような別エンドポイントを使っても良いが、現在の `POST /summary` を流用して差し替えるのが最小変更。
- `WebOutputBlock` に HTML テーブルブロックを追加し、`output_blocks` のレンダリングで扱う方式が既存の Web 表示ロジックと親和性が高い。
- Markdown 生成を再利用し、HTML 変換処理を別関数に切り出すと保守性が高まる。

## 8. まとめ

- Web UI の `サマリ表示` は `サマリ出力` から名称変更する。
- Web UI Fundamental では Markdown 相当の情報を HTML 表で表示する。
- Technical ではボタンは表示するが無効化する。
- 保存はまず HTML 表のダウンロードを提案し、必要なら Markdown ダウンロードを追加する。
- Tkinter の挙動はそのまま維持する。
