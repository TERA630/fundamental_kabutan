# 仕様書インデックス

このディレクトリでは、責務ごとに正本仕様を分ける。
完了済みの実装工程・PR分割・作業ログは仕様書へ残さない。

## 正本仕様

| 責務 | 正本 | 内容 |
|------|------|------|
| 全体アーキテクチャ / Domain責務 | `domain_spec_proposal.md` | Data / Domain / UseCase / Presentation / GUI の境界、主要モデル、計算ルール |
| 表示仕様 | `display_spec.md` | GUI共通文言、Fundamental / Technical出力、機関投資サマリ固定パネル |
| Technicalデータ / 指標 | `unite_tech_spec.md` | Technicalタブ、Technicalデータ取得、Technical指標作成 |
| 監視銘柄サマリ | `summery_spec.md` | `fundamental_summery-yyyy-mm-dd.md` の出力仕様 |
| rankCF採点ルール | `rankCF_spec.md` | スコア配点、ランク、免責・補正、総合判定 |
| rankCF実装責務 | `cf_scoring_design.md` | rankCF のモデル、UseCase接続、Presentation接続 |
| アナリスト予想 | `analyst_estimates_spec.md` | yFinanceアナリスト目標株価・EPS修正人数の取得と表示 |
| Web UI案 | `web_ui_design.md` | Flask Web UI の未実装設計案 |

## アーカイブ

`archive/` は過去の提案・表示ラフを残す場所とする。
正本仕様ではないため、実装判断では上記の正本仕様を優先する。

## 運用ルール

- 実装済みの作業工程、完了日、PRログは残さない。
- 仕様と実装が異なる可能性がある場合は、仕様書へ確定内容として書かず、確認事項として扱う。
- 新しい仕様は、責務が最も近い正本へ追記する。
- 提案段階の案は、正本へ混ぜずに明示的に「案」として分離する。
