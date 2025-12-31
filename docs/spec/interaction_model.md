# Interaction Model Spec

## 0. 目的
本仕様は、ユーザーが「印刷結果（紙）」を見て行う入力を最小化しつつ、最適化エンジン（Taguchi + FMBO/MOBO + Query Synthesis）が利用できる形に正規化するためのインタラクションモデルを定義する。

本アプリはICC/測色器を前提にせず、ユーザーの知覚に基づく比較（A/B/C）と簡易なNGタグ入力を主要な観測データとする。

---

## 1. 用語
- Candidate: 候補補正パラメータ（およびそこから生成される補正LUT/処理）。
- Round: 1回の「候補提示 → 印刷 → ユーザー評価 → 記録」のサイクル。
- Sheet: 1回の印刷物（写真＋プリセットパッチ等を含む）。
- Preset Patches: 写真以外に必ず印刷する、グレースケール/プリセット色パッチ群。

---

## 2. 入力（ユーザーが行うこと）

### 2.1 選択（Choice）
候補 A, B に加え、参照 C（現状/前回ベスト）を提示する。

- choice:
  - "A": Aが最も画面（意図）に近い
  - "B": Bが最も画面（意図）に近い
  - "C": 現状（参照）が最も近い（A/Bは悪化）

### 2.2 判断状態（Judgment）
人間は迷うため、選択の「品質」を分離して入力できるようにする。

- judgment:
  - "chosen": 上記 choice を自信を持って選べた
  - "undecidable": どれとも言えない（差が小さい/判断不能）
  - "both_bad": AもBも（場合によりCも）ダメで、方向性を変える必要がある

補足:
- "undecidable" は「A/Bがほぼ同等」や「差が知覚閾値以下」を意味し、最適化において “情報量の低いクエリ” として扱う。
- "both_bad" は「探索中心から外れている」または「提示した軸が間違っている」可能性が高い強い否定シグナルとして扱う。

### 2.3 NGタグ（どこが変か）
ユーザーは「何が変か」をカテゴリで選ぶ。複数選択可。

- ng_tags (set):
  - "gray": グレー/無彩色が色かぶりしている（ニュートラルNG）
  - "tones": 階調がおかしい（暗部つぶれ、ハイライト飛び等）
  - "saturation": 彩度が不自然（くすみ/派手すぎ等）
  - "skin": 肌色が不自然
  - "vivid": 高彩度領域（赤/青/緑など）が転ぶ
  - "other": その他（自由記述コメントとセット推奨）

### 2.4 任意コメント
- comment: free text
  - 例:「全体に暗い」「マゼンタ寄り」「シャドウが潰れてる」

---

## 3. 出力（システムが提示するもの）

### 3.1 印刷シートの内容（必須）
各候補（A/B/C）について、以下を **必ず同じレイアウト**で含める。

- Photo Region: ユーザーが選んだ写真（または資料ページ）
- Preset Patches:
  - Gray Scale: 例）0%〜100%の階調（少なくとも 7〜11段）
  - Preset Colors: 例）高彩度RGB/CMY相当、肌色域パッチ、ブランド色（任意）等
- Identifier:
  - round_id, candidate_id（A/B/C）, short hash（後でログと突合）

目的:
- 写真だけに最適化して “過学習” することを避ける。
- ユーザーが「グレー」「高彩度」「肌」など判断しやすい観測点を常に提供する。

---

## 4. ログ仕様（1ラウンドの記録）
最適化が再現できるよう、1ラウンドは必ず以下をJSONで記録する。

- round_id
- timestamp
- environment_meta:
  - display, printer, paper, room (任意)
- candidates:
  - A: params, lut_hash, sheet_hash
  - B: params, lut_hash, sheet_hash
  - C(ref): params, lut_hash, sheet_hash
- user_feedback:
  - choice: "A"|"B"|"C"|null
  - judgment: "chosen"|"undecidable"|"both_bad"
  - ng_tags: [...]
  - comment: string

---

## 5. 統計的扱い（最適化側への正規化インターフェース）

- Round 1 の 4択結果は、単なる「勝ち負け」ではなく、
  - 背後に Bradley–Terry / Luce choice model のような選好確率モデルを仮定し、
  - 「勝者Aが、B/C/D より好ましい確率が高い」という **soft constraint** として事前分布を更新する。
- これにより、
  - L4 の 4択で「A が選ばれたから A が正解」とはせず、
  - **「正解は A 周辺にあり、B/C/D側からは遠いらしい」という“傾向”だけを反映**する。
- Round 2 以降は、この更新済み事前分布を starting point として、FMBO/MOBO＋クエリ合成で高フィデリティ探索を行う。

最適化エンジンは、ユーザー入力を次の2種類の観測として扱う。

### 5.1 Preference Observation（比較観測）
- judgment="chosen" のとき：
  - (winner, losers) の順序情報として利用する。
  - 例: choice="A" → A ≻ B, A ≻ C を観測。

### 5.2 “弱い否定/不確実性”の観測
- judgment="undecidable":
  - 今回の比較は情報量が低いと記録し、パラメータ更新への寄与を低くする（重みを小さくする/学習に使わない等）。
  - 次回は「A-Bの差を広げる」「別軸を振る」などクエリ生成方針に反映する。
- judgment="both_bad":
  - A, B を “bad examples” として扱い、探索領域の中心を参照C側へ戻す/別軸へ切替える根拠として使う。

※具体的な重み付け・反映は `/docs/spec/optimization_flow.md` に定義する。
