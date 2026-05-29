---
# 表示仕様書

## 1. 目的

本仕様書は、GUIおよび分析出力テキストの表示仕様を整理する正本である。
完了済みの差分分析や移行タスクは本書へ反映済みとし、未完了タスクは保持しない。

---

## 2. 対象範囲

- GUI画面上の固定ラベル・ステータスメッセージ
- 出力テキスト（分析結果）内の株探セクション表示
- 表示に必要な入力データ、およびフォールバック時の表示

---

## 3. 責務境界

本書は表示仕様のみを定義する。

- GUI上の固定ラベル、ステータスメッセージ、出力テキストの順序・文言・数値表現を定義する。
- データ取得、HTML解析、キャッシュ、ドメインモデル、指標計算の責務分離は `docs/domain_spec_proposal.md` を正とする。
- rankCF の採点ルールは `docs/rankCF_spec.md`、実装設計は `docs/cf_scoring_design.md` を正とする。
- 表示に必要な計算値は UseCase / Domain / Presenter から受け取り、本書では表示時の扱いだけを規定する。

---

## 4. GUI表示仕様

### 4.1 固定ラベル

**ボタン**

- `監視銘柄ファイルを開く`
- `株探HTMLフォルダを選択`
- `取得`
- `コピー`
- `保存`

**株価ソース**

- `株価: yFinance固定`

### 4.2 ステータスメッセージ

| 状態 | 表示文言 |
|------|---------|
| 初期 | `監視銘柄ファイルを読み込んでください。` |
| 監視銘柄ロード完了 | `{count}件の監視銘柄を読み込みました。` |
| 銘柄選択 | `銘柄を選択しました。取得ボタンを押してください。` |
| 必須項目不足 | `先に監視銘柄ファイルと銘柄を選んでください。` |
| 取得中 | `取得中: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance` |
| 生成完了 | `生成完了: {name} ({code4}) / 業績=株探(HTML優先) / 指標=yFinance` |
| キャッシュ表示 | `キャッシュ表示: {name} ({code4})` |
| 株探HTMLフォルダ選択後 | `株探HTMLフォルダを設定しました（出力キャッシュをクリア）。` |
| コピー不可 | `コピーするテキストがありません。` |
| コピー完了 | `クリップボードにコピーしました。` |
| 保存不可 | `保存するテキストがありません。` |
| 保存完了 | `保存完了: {path}` |

---

## 5. 出力テキスト仕様

### 5.0 全体表示順

1. 冒頭サマリーブロック（銘柄ヘッダを含む）
2. 株価評価・資本効率ブロック
3. Qualityスコアブロック
4. Growthスコアブロック
5. Valuationスコアブロック
6. ルール注記
7. 株探 通期業績推移
8. 成長性
9. キャッシュフロー
10. 四半期業績推移

### 5.1 セクション見出し・ソース表示

**見出し**

```
■株探 通期業績推移

```

**ソース表示**

| 条件 | 表示 |
|------|------|
| HTML解析成功 | `株探ソース: HTML` |
| 取得不可（理由なし） | `株探ソース: 取得不可` |
| 取得不可（理由あり） | `株探ソース: 取得不可 ({message})` |

### 5.2 テーブル表示

**ヘッダ**

```
売上 / 営業益(率) / 経常益(率) / 最終益 / 1株益 / 1株配当
```

**行（優先表示順）**

| 行ラベル | 表示形式 |
|---------|---------|
| 前々々期実績 | `YYYY年` |
| 前々期実績 | `YYYY年` |
| 前期実績 | `YYYY年` |
| 今期予想 | `YYYY年(予)` |
| 来期予想 | `YYYY年(予)` |

**数値フォーマット**

| 種別 | フォーマット |
|------|------------|
| 金額（売上・各利益） | `value ÷ 100` を `x,xxx.x億` 形式 |
| 比率 | `x.x%` |
| EPS・配当 | `x.x円` |
| 欠損値 | `N/A` |

### 5.3 営業利益成長率・EPS成長率

- 行単位で `calc_operating_growth_rate` を適用（前行の営業利益対比）
- EPS 成長率も同様に行単位で算出
- 先頭行は比較元なしのため `N/A`
- 同一年に実績行と予想行が存在する場合、同年実績→同年予想の比較を避けるため、予想行は成長率の計算対象外
- 成長加速率は廃止

### 5.4 冒頭サマリーブロック

**目的**

- 出力冒頭で、銘柄・現在株価・時価総額・総合評価・投資判断の方向性を短く提示する。
- 旧仕様の `投資分類` / `投資戦略` / `算出基準` をフラットに並べる形式は廃止し、投資判断に必要な要約ラベルを3分類タグとして表示する。

**表示形式**

```
【{name} ({code4})】
株価 {price}円　時価総額 {market_cap}億円（{market_cap_class}）

総合評価 {rank}（{score}/100）
{growth_phase} / {per_level} / {roic_level}
{investment_strategy}
```

**表示例**

```
【ハーモニック・ドライブ・システム (6324)】
株価 7,690円　時価総額 7,279億円（中型主役）

総合評価 B（49/100）
利益改善型 / 超高PER / 低ROIC
順張り対象外・逆張り限定
```

**各項目**

| 項目 | 表示内容 |
|------|----------|
| `{name}` | 銘柄名 |
| `{code4}` | 4桁銘柄コード |
| `{price}` | 株価。整数円、3桁カンマ区切り |
| `{market_cap}` | 時価総額。億円単位、整数、3桁カンマ区切り |
| `{market_cap_class}` | 時価総額分類ラベル |
| `{rank}` | 総合評価ランク `{S/A/B/C/D}` |
| `{score}` | 総合スコア。整数、100点満点 |
| `{growth_phase}` | 成長フェーズ分類 |
| `{per_level}` | PER水準分類 |
| `{roic_level}` | ROIC水準分類 |
| `{investment_strategy}` | 投資戦略ラベル |

**成長フェーズ分類 `{growth_phase}`**

以下のいずれかを表示する。

- `業績回復途上`
- `低成長`
- `安定成長`
- `利益改善型`
- `高成長鈍化後`
- `成長再加速`
- `高成長中`

**PER水準分類 `{per_level}`**

以下のいずれかを表示する。

- `割安PER`
- `適正PER`
- `高PER`
- `超高PER`

**ROIC水準分類 `{roic_level}`**

以下のいずれかを表示する。

- `低収益ROIC`
- `低ROIC`
- `良好ROIC`
- `高ROIC`
- `超高ROIC`

**投資戦略 `{investment_strategy}`**

以下のいずれかを表示する。

- `押し目で積極監視`
- `トレンド・地合い次第で順張り`
- `順張り対象外・逆張り限定`
- `基本ノータッチ`

**フォールバック**

- 株価が欠損する場合は `株価 N/A` と表示する。
- 時価総額が欠損する場合は `時価総額 N/A` と表示し、時価総額分類の丸括弧は表示しない。
- `{growth_phase}` / `{per_level}` / `{roic_level}` のいずれかが欠損する場合は、該当位置に `N/A` を表示し、区切り `/` は維持する。
- 投資戦略が欠損する場合は `投資戦略 N/A` と表示する。

### 5.5 株価評価・資本効率ブロック
1.  縦並び表で
   """ 20xx年(実績)|20xx年(実績/予)|20xx年(予)| PER
   PER| xx.x倍|xx.x倍|xx.x倍
   PBR| x.xx倍|x.xx倍|x.xx倍
   ROE| x.x%|x.x%|x.x%
   ROIC| x.x%|x.x%|x.x%
   配当利回り|   x.xx%|x.xx%|x.xx%|
   FCF Yield| x.x%|x.x%|x.x%
   """
**算出ルール**

- PER・配当利回りは、株探行データの「修正1株益」「修正1株配当」を基準に算出する。
- PBR・ROE・ROIC は、財務指標行データの最新3年を基準に算出する。
- FCF Yield は、CF実績行のフリーCFと時価総額から算出する。
- 年列は PER・配当利回り・PBR・ROE・ROIC・FCF Yield の表示対象年を統合し、年順で表示する。
- 指標ごとに該当年の値がない場合は `N/A` と表示する。
- 表示年の決定：
  - PER行は、修正1株益が取得できた最新年を `Y_per` として `Y_per-2`・`Y_per-1`・`Y_per` の3年を表示する。
  - 配当利回り行は、修正1株配当が取得できた最新年を `Y_div` として `Y_div-2`・`Y_div-1`・`Y_div` の3年を表示する。
  - 対象3年のうち該当する株探行データが存在しない年は表示しない。
  - PER行と配当利回り行の表示年は独立に判定する（無配・配当欠損でもPER表示は継続）。
- 年ラベル：予想値は `YYYY年(予)`、実績値は `YYYY年(実績)`
- 計算式：
  - `PER = 株価 ÷ 修正1株益`
  - `配当利回り(%) = 修正1株配当 ÷ 株価 × 100`
- PERソース優先順：
  - 第1優先：forecast EPS（来期予想→今期予想の順で採用）
  - 第2優先：market PER（forecast EPS が取得不可の場合のみフォールバック）
- market PER フォールバック時は、年ヘッダを `市場PER` として `PER|xx.x倍` を表示する。

### 5.6 Quality スコアブロック

**表示形式**

```
[Quality] xx/60
ROIC                 B    9/15 xx.xx
Cash Conversion...  S   15/15 x.xx
営業CFマージン       B    6/10 xx.xx
営業利益率           D    0/10 xx.xx
FCF Ratio...        B    4/10 x.xx
```

- 1行目は `[Quality] {subtotal}/{max_points}` とする。
- 明細行は `指標名 / ランク / 点数 / 値` の列順で表示する。
- 値欠損の指標行は省略可能とし、内部ログに `取得不可: {指標名} (値欠損)` を出力する。

### 5.7 Growth スコアブロック

**表示形式**

```
[Growth] xx/25
EPS CAGR(3y)        S   15/15 xx.xx
売上CAGR(3y)        A    8/10 xx.xx
```

- 1行目は `[Growth] {subtotal}/{max_points}` とする。
- 明細行は `指標名 / ランク / 点数 / 値` の列順で表示する。

### 5.8 Valuation スコアブロック

**表示形式**

```
[Valuation] xx/15
FCF Yield           D    0/10 x.xx%
PER                 D    1/5  xx.xx
ルール注記:
- なし
```

- 1行目は `[Valuation] {subtotal}/{max_points}` とする。
- 明細行は `指標名 / ランク / 点数 / 値` の列順で表示する。
- `FCF Yield` の値は `%` 付きで表示する。
- `ルール注記` は日本語表示とし、内部識別子（英語キー）は表示しない。

**欠損値の表示ルール**
- 欠損値（N/A）は、本文の当該行を省略可能とする。
- 省略した場合でも、内部ログには「取得不可（指標名・理由）」を必ず出力する。
- ルール注記は内部識別子（英語キー）を表示せず、日本語文言へ変換して表示する。

### 5.9 CF 経時ブロック
**算出定義の参照先**
- 本ブロックで利用する指標（FCF / FCFマージン / 営業CFマージン / Cash Conversion / FCF Yield / 投資積極性）の算出定義は、ドメイン層仕様書 `docs/domain_spec_proposal.md` を正とする。

**表示順**

会社のキャッシュ創出力と投資姿勢を直感的に読むため、1表に集約して表示する。

```
■キャッシュフロー
年度 | 営業CF | FCF | 投資積極性 | 現金残高
YYYY | xxx | xxx | xx.x% | xxx
```

- 営業CF / FCF / 現金残高は百万円単位で表示する。
- FCF が欠損し、営業CF・投資CFが取得できる場合は `営業CF + 投資CF` で補完する。
- 投資積極性は `abs(投資CF) / 営業CF * 100` を表示する。
- Cash Conversion / FCF Yield / FCFマージン / 営業CFマージンは、スコアブロックや株価評価・資本効率ブロックで確認できるため、本ブロックでは表示しない。

### 5.10  成長性経時ブロック

単年成長率列は表示せず、CAGRのみを表示する。

```
■成長性
売上CAGR YYYY→YYYY xx.x%
営業利益CAGR YYYY→YYYY xx.x%
EPS CAGR YYYY→YYYY xx.x%
```

- CAGR の開始年・終了年を解決できない場合は、該当行を `N/A` と表示する。
- 極小利益からの反転で単年成長率が過大表示されるノイズを避けるため、`EPS成長率` / `営業利益成長率` の年次列は表示しない。

### 5.11 財務ブロック

- フル分析出力では、ROE・ROIC・PBR は 5.5 `株価評価・資本効率ブロック` に統合し、独立した財務ブロックは表示しない。
- 株探セクション単体出力など、冒頭の株価評価・資本効率ブロックへ統合できない呼び出しでは、従来どおり独立した `■財務ブロック` を表示してよい。

### 5.12 四半期業績推移

- 見出し: `■四半期業績推移`
- 対象: 四半期実績のみ。予想行は表示しない。
- 対象期間: 直近5四半期。
- 行ラベル: `YYYY.M`（例: `2025.3`）。
- カラム順:
  1. 売上高
  2. 営業益（前年同期比%）
  3. 経常益
  4. 最終益
  5. 修正1株益（前年同期比%）
  6. 売上損益率
- 前年同期比:
  - 比較対象は `Q(fiscal_year-1, same quarter)`。
  - `quarter` は通期業績テーブルの決算月を優先して解決する。
  - 計算式は `((current - previous) / abs(previous)) * 100`。
  - 比較元なし・欠損・0除算は空白表示。
- 売上損益率:
  - HTML値があれば優先する。
  - HTML値がない場合は `営業益 / 売上 * 100` で補完する。
  - 営業益が欠損の場合のみ `経常益 / 売上 * 100` で補完する。
  - 欠損・0除算時は `N/A`。
---

## 6. 株探データ探索仕様

| 条件 | 動作 |
|------|------|
| HTMLフォルダ未設定 | `取得不可 (HTMLフォルダ未設定)` を返す |
| HTMLフォルダ設定済み | ファイル名（stem）に4桁コードを含むHTML/HTMを正規表現で探索 |

**取得モード（既定）**

- HTML優先・Webフォールバックなし

---

## 7. キャッシュと再表示

- **キャッシュキー**：`code4` ＋ `kabutan_html_dir`
- **キャッシュクリア条件**：監視銘柄再読込、または株探HTMLフォルダ再選択時
- **キャッシュヒット時**：再計算せず `キャッシュ表示` ステータスで描画

### 7.1 株探HTMLフォルダの自動復元（Phase 1）

- データ層は、最後に取得成功で使用した株探HTMLフォルダを永続キャッシュする。
- GUI起動時にキャッシュ済みフォルダを読み込み、存在かつディレクトリであれば自動復元する。
- 復元先フォルダが無効（未存在・ディレクトリでない）な場合のみ、取得操作時にGUIから再選択を促す。
- GUIでフォルダを再選択して確定した場合、永続キャッシュを更新する。

---

## 8. 備考

- 将来のWeb優先モードや複数ソース統合表示は対象外。
- 本書を表示仕様の単一ソースとする。

---

## 9. GUI層実装工程

### 9.1 Phase 1: 冒頭サマリーDTO / Formatter追加

**状態: 完了（2026-05-28）**

- `OpeningSummarySection` を追加し、冒頭サマリーブロックの表示に必要な値を保持する。
- `format_opening_summary()` を追加し、5.4 の表示形式に従ってテキスト化する。
- 既存の `SummarySection` / `ScoreSummarySection` の出力はこの段階では変更しない。
- Formatter単体テストで、通常表示と欠損時フォールバックを確認する。

**完了内容**

- `OpeningSummarySection` は、銘柄名、4桁コード、株価、時価総額、時価総額分類、総合評価、総合スコア、成長フェーズ、PER水準、ROIC水準、投資戦略ラベルを保持する。
- `format_opening_summary()` は、5.4 の表示形式に従い、通常表示と欠損値の `N/A` フォールバックを扱う。
- Phase 1 では Presenter 結合を行わず、既存の `SummarySection` / `ScoreSummarySection` の出力を維持する。

### 9.2 Phase 2: Presenter結合

**状態: 完了（2026-05-28）**

- `build_fundamental_output()` が `growth_phase` / `per_level` / `roic_level` を受け取る。
- `SummarySection` と `ScoreSummarySection` を冒頭で統合し、`OpeningSummarySection` に変換する。
- 旧表示の `投資分類` / `算出基準` は冒頭サマリーからは出さない。
- `Quality` / `Growth` / `Valuation` の詳細スコア、ルール注記、バリュエーション表以降の表示順は維持する。

**完了内容**

- `build_fundamental_output()` は `growth_phase` / `per_level` / `roic_level` を受け取り、rankCF結果がある場合に既存の `SummarySection` を `OpeningSummarySection` へ置換する。
- 冒頭サマリーでは `ScoreSummarySection` の旧形式出力を使わず、総合評価、3分類タグ、投資戦略のみを表示する。
- `投資分類` / `算出基準` は冒頭サマリーから除外し、`Quality` / `Growth` / `Valuation` の詳細スコアと後続セクションの順序は維持する。

### 9.3 Phase 3: 統合テスト更新

**状態: 完了（2026-05-28）**

- `build_fundamental_output()` の期待出力を新冒頭サマリーへ更新する。
- `FundamentalAnalysisService.build_analysis_output()` から渡される `growth_phase` / `per_level` / `roic_level` が表示へ反映されることを確認する。
- 全体テスト `python -m pytest` を通す。

**完了内容**

- Presenter統合テストは、新冒頭サマリー、旧 `投資分類` / `算出基準` の非表示、詳細スコアと後続セクション順序の維持を確認する。
- UseCase統合テストは、`FundamentalAnalysisService.build_analysis_output()` が `growth_phase` / `per_level` / `roic_level` を `build_output_fn` へ渡すことを確認する。
- 全体テストは環境依存の `bs4` 未導入により収集で停止したため、依存導入後に再実行する。

### 9.4 Phase 4: 株価評価・資本効率ブロック統合

**状態: 完了（2026-05-29）**

- 旧 `バリュエーション` ブロックを `株価評価・資本効率` ブロックへ変更する。
- PER・配当利回りに加え、PBR・ROE・ROIC・FCF Yield を同じ年次列へ統合する。
- フル分析出力では後段の独立 `財務ブロック` を表示せず、ROE・ROIC・PBR の確認箇所を株価評価・資本効率ブロックへ集約する。
- 株探セクション単体出力では、冒頭側へ統合できないため従来の財務ブロック表示を維持する。

**完了内容**

- `ValuationTableSection` に PBR / ROE / ROIC / FCF Yield の表示行を追加した。
- Presenter のフル出力経路では、財務指標行とCF実績行をバリュエーションDTOへ渡し、後段の財務ブロック重複を抑止する。
- 株探セクション単体出力では、従来どおり独立した財務ブロックを表示できる。

### 9.5 Phase 5: 成長性ブロックのCAGR集約

**状態: 完了（2026-05-29）**

- 成長性ブロックから単年の `EPS成長率` / `営業利益成長率` 列を外し、売上CAGR・営業利益CAGR・EPS CAGR の3行へ集約する。
- `GrowthTimelineSection` に売上CAGRを追加し、既存の営業利益CAGR・EPS CAGR と同じ開始年・終了年で表示する。

**完了内容**

- `format_growth_timeline()` は、`■成長性` 配下に CAGR 3行だけを表示する。
- 極小利益からの反転で単年成長率が極端に大きくなるケースでも、成長性ブロックの視認性を維持する。

### 9.6 Phase 6: CFブロックの意思決定順表示

**状態: 完了（2026-05-29）**

- CFブロックを2表構成から、営業CF・FCF・投資積極性・現金残高の1表へ集約する。
- FCF 欠損時は、従来どおり営業CF + 投資CFで補完した値を表示する。

**完了内容**

- `format_cashflow_timeline()` は、会社のキャッシュ創出力、投資姿勢、手元流動性を1行で確認できる表示に変更した。
- Cash Conversion / FCF Yield / FCFマージン / 営業CFマージンは、重複を避けるため CFブロック本文から外した。

### 9.7 Phase 7: 検証記録の更新

**状態: 完了（2026-05-29）**

- 古い `py_compile` 未完了記録を、`python -B -c ...` による import 確認へ代替済みとして整理する。
- 全体テスト件数を直近の結果へ更新する。

**完了内容**

- `__pycache__` 作成権限に依存する `py_compile` ではなく、`python -B -c` の import 確認を採用する。
- 全体確認は `python -m pytest` で行う。

### 9.8 Phase 8: スコア内訳の構造化表示

**状態: 完了（2026-05-29）**

- 旧 `Metric: raw -> rank(points)` 形式を廃止し、カテゴリごとに `[Quality] 45/60` の見出しと列揃えの明細行を表示する。
- 明細行は `指標名 / ランク / 点数 / 値` の順に表示する。

**完了内容**

- `format_score_category()` は `[Category] subtotal/max_points` と構造化明細を返す。
- 欠損値の指標行省略と取得不可ログは従来どおり維持する。

## 10. 検証状況

- Phase 2/3 直近確認: `python -m pytest tests/test_presenters_cf_scoring_output.py tests/test_usecase_cf_scoring_integration.py`
- 結果: `24 passed`
- 追加確認: `python -B -c "import app.presenters; import app.domain.usecases.fundamental_analysis; import app.domain.models.display_sections; import app.presentation.display_formatter; print('imports ok')"`
- 結果: 成功
- 全体確認: `python -m pytest`
- 結果: `193 passed, 1 warning`
- Phase 4 直近確認: `python -m pytest tests/test_presenters_cf_scoring_output.py tests/test_presenters_kabutan_output.py tests/test_usecase_cf_scoring_integration.py`
- 結果: `42 passed`
- Phase 4 import確認: `python -B -c "import app.presenters; import app.domain.builders.fundamental_output; import app.domain.builders.fundamental_output_impl; import app.domain.builders.kabutan_output; import app.domain.models.display_sections; import app.presentation.display_formatter; print('imports ok')"`
- 結果: 成功
- Phase 7 import確認: `python -B -c "import app.presenters; import app.presentation.display_formatter; print('imports ok')"`
- 結果: 成功
- Phase 5/6 直近確認: `python -m pytest tests/test_presenters_kabutan_output.py tests/test_presenters_cf_scoring_output.py tests/test_usecase_cf_scoring_integration.py`
- 結果: `42 passed`
- Phase 5/6 import確認: `python -B -c "import app.presenters; import app.domain.builders.kabutan_output; import app.domain.models.display_sections; import app.presentation.display_formatter; print('imports ok')"`
- 結果: 成功
- Phase 8 直近確認: `python -m pytest tests/test_presenters_cf_scoring_output.py tests/test_presenters_kabutan_output.py tests/test_usecase_cf_scoring_integration.py`
- 結果: `42 passed`
