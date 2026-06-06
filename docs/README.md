# 仕様書インデックス

## 正本

現行実装の正本仕様は `current_implementation_spec.md` とする。
画面表示の詳細仕様は `screen_spec.md` とする。
プレゼンテーション層の詳細仕様は `presentation_spec.md` とする。

この仕様書は、分割されていた表示仕様、Technical仕様、Domain責務、rankCF、監視銘柄サマリ、アナリスト予想の内容を統合し、次の責務ごとに整理している。

- 画面表示案
- プレゼンテーション層
- ドメイン層
- データー層

## 分離仕様

- `screen_spec.md`: GUI画面表示、操作、ステータス、固定パネル、GUI出力キャッシュ表示
- `presentation_spec.md`: 出力テキスト、Markdown、表示用セクション、数値表現、N/A表現

## 案

- `web_ui_design.md` は未実装のWeb UI案であり、現行実装仕様ではない。

## 運用ルール

- 完了済みの作業工程、PR分割、進捗ログは正本仕様に残さない。
- 仕様と実装が異なる可能性がある場合は、確定内容として書かず確認事項として扱う。
- 新しい仕様は `current_implementation_spec.md` へ追記する。
- 提案段階の案は、正本へ混ぜずに明示的に「案」として分離する。
