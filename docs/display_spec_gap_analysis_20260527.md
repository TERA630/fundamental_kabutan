# 表示順序ギャップ分析と修正設計案（2026-05-27）

対象:
- 仕様: `docs/display_spec.md`
- 実装: `app/domain/builders/fundamental_output_impl.py`, `app/domain/builders/kabutan_output.py`, `app/presenters.py`

## 1. 結論（表示順序の差分）

表示順序は `docs/display_spec.md` と一致していません。差分は以下です。

1. **サマリブロック位置差異**
   - 仕様: 株価・時価総額の直後に「総合評価 → 投資分類 → 投資戦略 → 算出基準」。
   - 実装: 総合評価等は末尾 `■rankCF スコア` で表示。

2. **成長性ブロック順差異**
   - 仕様: `EPS成長率` → `営業利益成長率`。
   - 実装: `営業利益成長率` → `EPS成長率`。

3. **CF経時ブロック順差異**
   - 仕様: 「CF実績 → Cash Conversion → FCF Yield → FCFマージン/営業CFマージン → 投資積極性」。
   - 実装: `[A] CF実績` の後、`営業CFマージン → Cash conversion → FCFマージン → FCF Yield` の順で同一表表示。投資積極性は未表示。

4. **Valuation表示形式差異**
   - 仕様: 年ヘッダ + `PER` 行 + `配当利回り` 行の縦並び表。
   - 実装: `■指標` 内で `PER: ...` / `配当利回り: ...` のテキスト行。

## 2. 現行実装の表示順（As-Is）

1. `【銘柄】...`
2. `■指標`（株価/PBR/ROE、業種/時価総額、PER、配当利回り）
3. `■株探 通期業績推移`（ソース、通期テーブル）
4. `■成長性`（営業利益成長率、EPS成長率、3年営業利益CAGR、3年EPS CAGR）
5. `■キャッシュフロー`（[A] CF実績、[B] 指標）
6. `■財務ブロック`
7. `■四半期業績推移`
8. `■rankCF スコア`（算出日、総合評価、投資分類、投資戦略、合計、Quality/Growth/Valuation、ルール注記）

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

1. **ドメイン表示モデル（新規）**
   - 追加候補: `app/domain/models/display_sections.py`
   - 役割:
     - `SummarySection`
     - `ValuationTableSection`
     - `ScoreSection`（quality/growth/valuation）
     - `ForecastTableSection`
     - `CashflowTimelineSection`
     - `GrowthTimelineSection`

2. **ドメイン組み立て器（新規）**
   - 追加候補: `app/domain/builders/display_section_builder.py`
   - 役割:
     - 既存入力（price, market_cap, forecast, cf_scoring_result等）から上記セクションDTOを構築。
     - 表示順はここで固定せず、セクション内容のみ返す。

3. **Presenterフォーマッタ（新規）**
   - 追加候補: `app/presentation/display_formatter.py`（または `app/presenters.py` 内分離）
   - 役割:
     - 仕様どおりの順序でセクションDTOを文字列化。
     - ラベル差異（例: 算出日/算出基準）を統一。

4. **既存ビルダーの縮退**
   - `fundamental_output_impl.py`:
     - `■指標` に混在する PER/配当利回りを Valuation表へ移管。
   - `kabutan_output.py`:
     - 成長性行順を仕様順へ修正。
     - CF経時ブロックを仕様順へ再構成。
   - `presenters.py`:
     - `build_cf_scoring_summary_text()` を「末尾追記」用途から、サマリ/各スコアブロック生成に再編。

### 4.3 実装ステップ（段階導入）

- **Step 1（低リスク・順序修正）**
  - 成長性経時ブロック順を入れ替え（EPS先行）。
  - CF経時ブロック内の行順を仕様順へ変更。
- **Step 2（Valuation表化）**
  - 年ヘッダ + PER行 + 配当利回り行を専用関数で生成。
  - `■指標` から旧PER/配当利回り行を削除。
- **Step 3（サマリ統合）**
  - 総合評価/投資分類/投資戦略/算出基準をサマリ位置へ移設。
  - `■rankCF スコア` は廃止またはデバッグ専用化。
- **Step 4（DTO分離）**
  - 文字列連結ロジックを表示モデル+フォーマッタに分割。
  - テストを順次DTO基準へ移行。

### 4.4 影響範囲

- 主変更: `app/domain/builders/fundamental_output_impl.py`, `app/domain/builders/kabutan_output.py`, `app/presenters.py`
- 追加想定: 表示モデル/フォーマッタモジュール、対応テスト
- 非影響: GUIフレームワーク層（`tkinter`側イベント/Widget実装）

## 5. 受け入れ条件（Definition of Done）

1. 生成テキストのブロック順が `docs/display_spec.md` 5.4〜5.10 と一致する。
2. 成長性経時ブロックが `EPS成長率` → `営業利益成長率` になる。
3. Valuationが「年ヘッダ + PER行 + 配当利回り行」の3行表で出力される。
4. CF経時ブロックに「投資積極性」が表示される。
5. 欠損値（N/A）時の省略/注記挙動が仕様に沿ってテストで検証される。

## 6. 未確定事項（実装前に確定が必要）

1. 「算出基準」の表示値を `as_of`（取得日）とするか、最新実績年月とするか。
2. 既存 `■財務ブロック` / `■四半期業績推移` の仕様上の正式位置。
3. `■rankCF スコア` 見出しを完全廃止するか、互換モードとして残すか。
