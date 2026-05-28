# 表示順序ギャップ分析と修正設計案（2026-05-27）

最終更新: 2026-05-28

対象:
- 仕様: `docs/display_spec.md`
- 実装: `app/domain/builders/fundamental_output_impl.py`, `app/domain/builders/kabutan_output.py`, `app/domain/models/display_sections.py`, `app/presentation/display_formatter.py`, `app/presenters.py`

## 1. 結論（現状）

2026-05-28 時点で、当初検出した主要差分のうち Step 1、Step 2、PR 1、PR 2、PR 3、PR 4 相当は実装済みです。

完了済み:

1. **サマリブロック位置差異は解消済み**
   - 仕様: 株価・時価総額の直後に「総合評価 → 投資分類 → 投資戦略 → 算出基準」。
   - 現実装: `株価`、`時価総額` の直後に総合評価等を表示。
   - `■rankCF スコア` 見出しは出力しない。

2. **成長性ブロック内の行順差異は解消済み**
   - 仕様: `EPS成長率` → `営業利益成長率`。
   - 現実装: `EPS成長率` → `営業利益成長率`。

3. **CF経時ブロック内の指標順差異は解消済み**
   - 仕様: 「CF実績 → Cash Conversion → FCF Yield → FCFマージン/営業CFマージン → 投資積極性」。
   - 現実装: `[A] CF実績` の後、`[B] 指標` で `Cash conversion | FCF Yield | FCFマージン | 営業CFマージン | 投資積極性` を表示。
   - 旧記述「投資積極性は未表示」は誤り。現在は表示済み。

4. **Valuation表示形式差異は概ね解消済み**
   - 仕様: 年ヘッダ + `PER` 行 + `配当利回り` 行の縦並び表。
   - 現実装: `■バリュエーション` に `年度`、`PER`、`配当利回り` の表を表示。
   - 年ラベルは `YYYY年(実績)` / `YYYY年(予)` に統一済み。
   - forecast EPS が取得不可の場合のみ、market PER を `市場PER` として表示する。

5. **CF実績表の列順は仕様準拠済み**
   - 現実装: `年度 | 営業CF | 投資CF | 財務CF | 現金等残高`。
   - フリーCFは実績表には表示せず、指標算出内部で利用する。

6. **欠損値ログの検証を拡張済み**
   - スコア指標に加えて、Valuation、株探通期、CF、財務、四半期の欠損ログをテストで確認。

残差分:

1. **通期業績後のブロック順**
   - 仕様章順: `■株探 通期業績推移` → CF経時ブロック → 成長性経時ブロック。
   - 現実装: `■株探 通期業績推移` → `■成長性` → `■キャッシュフロー`。

2. **DTO分離は主要ブロック完了**
   - 完了: サマリ、Valuation、スコアサマリ、Quality/Growth/Valuationスコア、ルール注記。
   - 完了: 株探通期、CF経時、成長性経時、財務、四半期。
   - 継続対象: 表示順とラベル細部の仕様差分。

## 2. 現行実装の表示順（As-Is）

1. `【銘柄】...`
2. サマリブロック
   - `株価`
   - `時価総額`
   - `総合評価`
   - `投資分類`
   - `投資戦略`
   - `算出基準`
3. `■バリュエーション`（年度、PER、配当利回り）
4. Qualityスコアブロック
5. Growthスコアブロック
6. Valuationスコアブロック
7. ルール注記
8. `■株探 通期業績推移`（ソース、通期テーブル）
9. `■成長性`（EPS成長率、営業利益成長率、3年営業利益CAGR、3年EPS CAGR）
10. `■キャッシュフロー`（[A] CF実績、[B] 指標）
11. `■財務ブロック`
12. `■四半期業績推移`

## 3. 目標表示順（To-Be）

`docs/display_spec.md` に合わせ、以下を目標順とする。

1. `【銘柄】...`
2. サマリブロック
   - 株価
   - 時価総額
   - 総合評価
   - 投資分類
   - 投資戦略
   - 算出基準
3. Valuationブロック（年ヘッダ + PER行 + 配当利回り行）
4. Qualityスコアブロック
5. Growthスコアブロック
6. Valuationスコアブロック
7. `■株探 通期業績推移`
8. CF経時ブロック（仕様順）
9. 成長性経時ブロック（EPS成長率 → 営業利益成長率）
10. 既存の財務/四半期補助ブロック（仕様追記が必要なため暫定で末尾配置）

## 4. 修正設計案（レイヤー分離準拠）

### 4.1 方針

- **Presenterは表示順制御のみ**を担当し、計算ロジックはドメイン側で完結させる。
- 既存の `build_fundamental_output_text_impl()` / `build_kabutan_forecast_output()` の「文字列直結」を縮小し、
  **ドメインDTO（表示モデル）→ Presenter整形**へ段階移行する。
- UI依存コードは追加せず、ドメインは純粋Pythonのまま維持する。

### 4.2 追加/変更コンポーネント

1. **ドメイン表示モデル**
   - 実装済み: `app/domain/models/display_sections.py`
   - 役割:
     - 実装済み: `SummarySection`
     - 実装済み: `ValuationTableSection`
     - 実装済み: `ScoreSummarySection`
     - 実装済み: `ScoreCategorySection`（quality/growth/valuation）
     - 実装済み: `RuleNotesSection`
     - 実装済み: `ForecastTableSection`
     - 実装済み: `CashflowTimelineSection`
     - 実装済み: `GrowthTimelineSection`
     - 実装済み: `FinancialMetricsSection`
     - 実装済み: `QuarterlyMetricsSection`

2. **ドメイン組み立て器（新規）**
   - 追加候補: `app/domain/builders/display_section_builder.py`
   - 役割:
     - 既存入力（price, market_cap, forecast, cf_scoring_result等）から上記セクションDTOを構築。
     - 表示順はここで固定せず、セクション内容のみ返す。

3. **Presenterフォーマッタ**
   - 実装済み: `app/presentation/display_formatter.py`
   - 役割:
     - セクションDTOを文字列化。
     - ラベル差異（例: 算出日/算出基準）を統一。
     - スコア指標の欠損値省略とログ出力を担当。

4. **既存ビルダーの縮退**
   - `fundamental_output_impl.py`:
     - `■指標` に混在する PER/配当利回りを Valuation表へ移管。
   - `kabutan_output.py`:
     - 成長性行順を仕様順へ修正。
     - CF経時ブロックを仕様順へ再構成。
   - `presenters.py`:
     - `build_cf_scoring_summary_text()` を「末尾追記」用途から、サマリ/各スコアブロック生成に再編。

### 4.3 実装ステップ（段階導入）

- **Step 1（低リスク・順序修正）: 完了**
  - 成長性経時ブロック順を入れ替え（EPS先行）。
  - CF経時ブロック内の行順を仕様順へ変更。
- **Step 2（Valuation表化）: 完了**
  - 年ヘッダ + PER行 + 配当利回り行を専用関数で生成。
  - `■指標` から旧PER/配当利回り行を削除。
- **Step 3（サマリ統合）: 完了**
  - 総合評価/投資分類/投資戦略/算出基準をサマリ位置へ移設。
  - `■rankCF スコア` 見出しは出力廃止。
- **Step 4（DTO分離）: 完了**
  - 文字列連結ロジックを表示モデル+フォーマッタに分割。
  - サマリ、Valuation、スコアブロック、ルール注記はDTO基準へ移行済み。
  - 株探通期、CF、成長性、財務、四半期もDTO基準へ移行済み。

### 4.4 影響範囲

- 主変更: `app/domain/builders/fundamental_output_impl.py`, `app/domain/builders/kabutan_output.py`, `app/presenters.py`
- 追加想定: 表示モデル/フォーマッタモジュール、対応テスト
- 非影響: GUIフレームワーク層（`tkinter`側イベント/Widget実装）

## 5. 受け入れ条件（Definition of Done）

1. 生成テキストのブロック順が `docs/display_spec.md` 5.4〜5.10 と一致する。: **未完了**
2. 成長性経時ブロックが `EPS成長率` → `営業利益成長率` になる。: **完了**
3. Valuationが「年ヘッダ + PER行 + 配当利回り行」の3行表で出力される。: **完了**
4. CF経時ブロックに「投資積極性」が表示される。: **完了**
5. 欠損値（N/A）時の省略/注記挙動が仕様に沿ってテストで検証される。: **完了**
   - スコア指標は欠損時の省略とログ出力をテスト済み。
   - Valuation、株探通期、CF、財務、四半期の欠損時ログ出力をテスト済み。

## 6. 未確定事項

1. 「算出基準」は現実装では `cf_scoring_result.as_of` を `YYYY-MM` に丸めて表示している。仕様文言どおり「最新実績年月」を厳密に使うかは継続確認。
2. 既存 `■財務ブロック` / `■四半期業績推移` の仕様上の正式位置。
3. 通期業績後の `■成長性` と `■キャッシュフロー` のブロック順を仕様章順に合わせるか。

## 7. 検証状況

- `python -m pytest`
- 結果: `148 passed, 1 warning`
