# rankCFスコアリング 実装前設計書

## 1. 目的
- `docs/rankCF_spec.md` の採点ロジックを、**ドメイン層で計算・保持可能な形**に再構成する。
- GUI層は計算を持たず、UseCaseから受け取った結果を表示するのみとする。
- 将来のUI差し替え（Tkinter → 別GUI）時に、スコアロジックが再利用できる構成にする。

---

## 2. スコープ
### 2.1 対象
- rankCFスコア計算（Quality / Growth / Valuation）
- 免責・ペナルティルール適用
- スコア結果の保持（キャッシュ、および任意で永続化）
- GUI表示用DTOへの変換

### 2.2 非対象
- 新しいデータソース導入
- GUI見た目（色・レイアウト）詳細調整
- 外部API仕様変更

---

## 3. アーキテクチャ方針
依存方向は以下で固定する。

- UI(Presentation) → UseCase(Application) → Domain
- Infrastructure(Data) は UseCase に注入される Port 実装として接続

### 禁止事項
- Domain / UseCase が `tkinter` 等UIライブラリを import しない。
- GUIコードが採点ロジックを直接実装しない。

---

## 4. 追加・変更コンポーネント

## 4.1 Domain層

### (A) 新規: `app/domain/models/cf_scoring_input.py`
rankCF採点に必要な入力を定義する。

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class CfScoringInput:
    code4: str
    as_of: str | None

    roic: float | None
    ocf: float | None
    net_income: float | None
    operating_income: float | None
    revenue: float | None
    fcf: float | None

    eps_cagr_3y: float | None
    sales_cagr_3y: float | None

    fcf_yield: float | None
    per: float | None
```

> 備考: 既存モデルからの算出に不足がある場合は、UseCaseで `None` を許容して段階導入する。

### (B) 新規: `app/domain/models/cf_scoring_result.py`
採点結果と根拠を構造化して保持する。

```python
from dataclasses import dataclass
from typing import Literal

Rank = Literal["S", "A", "B", "C", "D", "E", "N/A"]
Category = Literal["quality", "growth", "valuation"]

@dataclass(frozen=True)
class MetricScore:
    metric_id: str
    category: Category
    raw_value: float | None
    rank: Rank
    points: int
    max_points: int
    rule_notes: tuple[str, ...] = ()

@dataclass(frozen=True)
class CategoryScore:
    category: Category
    subtotal: int
    max_points: int
    metrics: tuple[MetricScore, ...]

@dataclass(frozen=True)
class TotalScore:
    total_points: int
    max_points: int
    judgement: str
    priority_hint: str | None

@dataclass(frozen=True)
class CfScoringResult:
    version: str
    as_of: str | None
    quality: CategoryScore
    growth: CategoryScore
    valuation: CategoryScore
    total: TotalScore
```

### (C) 新規: `app/domain/policies/cf_scoring.py`
rankCF仕様に準拠した純粋関数群を定義する。

#### 公開IF（案）
```python
def calculate_cf_score(input_data: CfScoringInput) -> CfScoringResult: ...
```

#### 内部関数（案）
- `score_roic(roic)`
- `score_cash_conversion_np(ocf, net_income)`
- `apply_quality_filter_ocf_op(metric, ocf, operating_income)`
- `score_ocf_margin(ocf, revenue)`
- `score_op_margin(operating_income, revenue)`
- `score_fcf_ratio(fcf, ocf, sales_cagr_3y, roic)`
- `score_eps_cagr_3y(eps_cagr_3y)`
- `score_sales_cagr_3y(sales_cagr_3y)`
- `score_fcf_yield(fcf_yield, sales_cagr_3y)`
- `score_per(per, eps_cagr_3y)`
- `build_total_judgement(total_points)`

#### ルール適用順（固定）
1. 指標ごとの基礎点を計算
2. 免責ルール適用（例: FCF Ratio, FCF Yield, PER成長加点）
3. ペナルティ適用（営業CF/営業利益<0.7 の格下げ）
4. 小計・合計・判定を確定

> 適用理由は `MetricScore.rule_notes` に追記し、表示可能にする。

---

## 4.2 UseCase層

### (D) 変更: `app/domain/usecases/fundamental_analysis.py`
`FundamentalAnalysisService.build_analysis_output()` の処理に、スコア計算フローを追加する。

#### 追加責務
- 既存データ（forecast/cashflow/market snapshot等）から `CfScoringInput` を構築
- `calculate_cf_score()` を呼び出す
- `build_output_fn` に `cf_scoring_result` を渡す

#### シグネチャ影響（案）
既存 `build_output_fn(**output_context)` に以下キーを追加:
- `cf_scoring_result: CfScoringResult | None`

### (E) 任意追加: スコア永続化Port
`fundamental_analysis.py` か専用UseCaseに以下Portを定義する。

```python
class ScoringResultRepositoryPort(Protocol):
    def get(self, key: str) -> CfScoringResult | None: ...
    def set(self, key: str, value: CfScoringResult) -> None: ...
```

- まずは未導入でも可（GUI日次キャッシュで運用）
- 必要になった時点でJSON/SQLite実装をData層に追加

---

## 4.3 Presentation層

### (F) 変更: `app/presenters.py`
`build_fundamental_output()` に採点結果引数を追加。

```python
def build_fundamental_output(..., cf_scoring_result: CfScoringResult | None = None) -> str:
    ...
```

### 表示仕様（テキスト出力）
- 合計: `XX / 100`
- 判定: `◎ / ○ / △ / ✕`
- 内訳:
  - Quality `q / 60`
  - Growth `g / 25`
  - Valuation `v / 15`
- 各指標: `指標名: raw -> Rank(point)`
- 免責・ペナルティ: 箇条書き（`rule_notes`）

---

## 4.4 GUI State

### (G) 変更: `app/gui_state.py`
日次表示キャッシュにスコアも持たせる。

```python
output_cache: dict[str, str]
scoring_cache: dict[str, CfScoringResult]
```

- 既存 `build_output_cache_key(code4, kabutan_html_dir)` を流用
- `should_rotate_output_cache()` と同じタイミングで破棄

---

## 5. I/F一覧（確定候補）

## 5.1 Domain
- `calculate_cf_score(input_data: CfScoringInput) -> CfScoringResult`

## 5.2 UseCase
- `build_cf_scoring_input(...) -> CfScoringInput | None`（`FundamentalAnalysisService` の private method）

## 5.3 Presentation
- `build_fundamental_output(..., cf_scoring_result: CfScoringResult | None = None) -> str`

## 5.4 Data（任意）
- `ScoringResultRepositoryPort.get/set`

---

## 6. エラーハンドリング方針
- 必須データ不足時は `N/A` ランク・0点で継続（例外で停止しない）
- `CfScoringInput` 自体が作れない場合は `cf_scoring_result=None` で出力継続
- 表示時は「算出不可」メッセージを出す

---

## 7. テスト設計

## 7.1 Domain Policy単体テスト（最優先）
新規: `tests/test_cf_scoring_policy.py`

- 境界値テスト（各閾値の上下）
- 免責ルールテスト
  - FCF Ratio救済
  - FCF Yield底上げ
  - PER高成長加点
- ペナルティテスト
  - 営業CF/営業利益 < 0.7 で強制格下げ
- 合計点・判定テスト

## 7.2 UseCase統合テスト
新規: `tests/test_usecase_cf_scoring_integration.py`

- `build_analysis_output()` が `cf_scoring_result` を生成して `build_output_fn` へ渡す
- 入力不足時に `None` を渡し、既存出力が壊れない

## 7.3 Presenterテスト
新規: `tests/test_presenters_cf_scoring_output.py`

- 合計/内訳/注記が期待フォーマットで出る
- `None` 時のフォールバック表示

---

## 8. 導入ステップ（実装順）
1. Domainモデル + Policy + 単体テスト
2. UseCase連携（input組立と呼び出し）
3. Presenter表示拡張
4. GUI cache連携
5. （任意）RepositoryPort導入

---

## 9. 互換性・移行
- 既存 `app/domain/policies/ranking.py` は残置（既存表示の後方互換）
- rankCFは新モジュールとして追加し、段階的にUIへ露出
- 既存出力関数は `cf_scoring_result` を optional にして破壊的変更を回避

---

## 10. 決定事項（この設計で固定）
- スコア計算責務はDomainに固定
- 画面表示責務はPresentationに固定
- データ取得/保存はPort越しで抽象化
- 免責/ペナルティ適用理由を結果構造に保持し、監査可能にする
