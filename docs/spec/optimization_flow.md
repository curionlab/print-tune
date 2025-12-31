# Optimization Flow Spec

## 0. 目的
本仕様は、Taguchi（初期探索）→ FMBO/MOBO → Query Synthesis による候補生成、ならびに「迷った」「どちらもダメ」を含む人間フィードバックの統計的取り扱いを定義する。

BoTorch を採用し、MOBOは qEHVI / qNEHVI、FMBOは multi-fidelity KG 系（例：qMFKG）を基本路線とする。[BoTorch docs: qEHVI/qNEHVI][BoTorch docs: MFKG] [web:108][web:127]

---

## 1. 最適化対象（パラメータ空間）

### 1.1 最適化変数 θ（低次元化）
LUTの格子点を直接最適化せず、以下の低次元パラメータを最適化する。

例（最小）:
- exposure
- color_temp
- tint
- contrast

例（拡張）:
- saturation_global
- skin_tone (小さく制限)
- smoothness_weight（LUT平滑性の正則化強度）

### 1.2 候補生成は「クエリ合成」
候補は離散プールから選ばず、連続空間から獲得関数を最大化して生成する（optimize_acqf相当）。[web:108]

---

## 2. フィデリティ設計（FMBO）

### 2.1 Fidelityレベル
fidelity ∈ {0, 1, 2} の離散レベルを採用（将来連続化可）。

- fidelity=0 (Low):
  - パッチ中心（写真は小さく/省略可）
  - 目的：ニュートラル・階調の大方向を掴む（安価・高速）
- fidelity=1 (Mid):
  - 写真＋パッチ（標準）
- fidelity=2 (High):
  - 異なる画像（別被写体）で検証＋パッチ（ロバスト確認）

※実装上、fidelity は入力Xの追加次元として扱う（BoTorchのmulti-fidelityチュートリアルに沿う）。[web:127]

---

## 3. 目的関数（MOBO）

### 3.1 目的は「複数」を前提
本アプリは単一スカラーへの押し込みを避け、パレート最適を扱う。

例（3目的）:
- obj1: neutral_quality（グレーの色かぶりが小さいほど良い）
- obj2: tone_quality（階調破綻が少ないほど良い）
- obj3: photo_match（写真の“意図”に近いほど良い：初期は人間選好を代理スコア化）

MOBOの獲得関数として qEHVI / qNEHVI を採用する（ノイズが強いのでNEHVI寄りを優先）。[web:108]

### 3.2 人間フィードバックの取り込み
ユーザー入力は「目的値そのもの」ではなく、以下の役割を持つ。

- choice（A/B/C）:
  - photo_match の代理信号（少なくとも順序情報）
- ng_tags:
  - 目的の重み付け・制約の一時的強化に使う
  - 例: "gray" が多発 → neutral_quality をより重視するモードへ

---

## 4. ラウンド設計（5回で終えるための規定）

### Round 1: OA-based Low-Fidelity Initial Design (L4)

- 目的:
  - exposure と color_temp の「主な傾向」を、低フィデリティ（パッチ中心）の 4 候補から一度に推定する。
  - **「正解を決める」のではなく、「どの方向に有望な領域がありそうか」という事前分布を更新する。**

- 実装:
  - L4 直交表（Orthogonal Array）に従って 4 候補（Exposure±, ColorTemp±）を生成し、1枚に4分割で印刷する。
  - ユーザーには「4つのうち一番マシなもの」を 1 つだけ選んでもらう（順位付けは不要）。

- 観測の扱い:
  - 4択の結果（例: Aが選ばれた）は、「Aが正解」とは解釈しない。
  - 選好確率モデル（例: Bradley–Terry モデル）を背後に置き、
    - 「A が B/C/D より好ましい確率が高い」
    - 「“正解”は A 周辺にあり、B/C/D の近傍からは遠い可能性が高い」
    という **ソフトな情報として GP / MFBO の事前分布を更新**する。[web:151]

- MFBO における位置づけ:
  - このラウンドは fidelity=0 の「低フィデリティ観測」としてログに残し、
  - Round 2 以降の A/B テスト（写真＋パッチ）は fidelity=1 以上の「高フィデリティ観測」として、**学習の重みづけを変えて扱う。**[web:127]

- 結果:
  - θ0 は「A のパラメータそのもの」ではなく、
    - L4 の 4点と選好結果から得られた **“有望領域の中心”** として推定される。
  - 2 ラウンド目では、「A をさらに改良したより良い候補」をクエリ合成で生成できる。

### Round 2-5: FMBO + MOBO + Query Synthesis
- 目的: パレートを改善しつつ、ロバストな一点を決める。
- 出力: 2候補（A/B）＋参照C（前回ベスト）を提示。
- 観測: choice + judgment + ng_tags + comment。

---

## 5. 「迷った」「どちらもダメ」の統計的取り扱い

### 5.1 undecidable（判断保留）
- 意味: 提示したA/B/Cの差が小さすぎる or 判断不能。
- 扱い（規定）:
  1) このラウンドの preference observation を GP の学習に **低重み**で入れる、または入れない。
  2) 次ラウンドの候補生成では、A-Bの差分（Δθ）を下限以上にする。
  3) 同じ軸で迷いが続く場合は、探索軸を切り替える（例：exposure→tint）。

### 5.2 both_bad（どちらもダメ）
- 意味: A/Bは悪化で、方向転換が必要。
- 扱い（規定）:
  1) 参照C（前回ベスト）を保持し、探索中心をCに戻す。
  2) A/Bを “bad examples” として記録し、次の獲得関数最大化でその近傍を避ける（制約/ペナルティ）。
  3) ng_tags と合わせて「どの目的が破綻したか」を推定し、目的の優先順位（重み）を一時的に変更。

---

## 6. コアモジュール間インターフェース（実装ガイド）

### 6.1 core.optimizer（司令塔）
- 入力: history（interaction_model.mdのJSONログ列）
- 出力: candidates（A/B/Cそれぞれの params と fidelity と識別子）

### 6.2 core.acquisition（獲得関数）
- MOBO:
  - qEHVI / qNEHVI を基本実装（ノイズ込み前提）。[web:108]
- FMBO:
  - multi-fidelity KG 系を採用（コスト考慮含む）。[web:127]
- 条件:
  - judgment="undecidable" の頻発 → “差分を大きくする制約” を追加
  - judgment="both_bad" → “参照回帰 + 近傍回避” を追加

### 6.3 core.query_synthesis（候補合成）
- 実装方針:
  - optimize_acqf 相当で、連続空間から候補点を生成する。[web:108]
  - A/Bは「近傍比較」になりがちなので、
    - Δθ の下限（識別可能差）と上限（極端すぎる差）を制約として入れる。
  - C は参照点（前回ベスト）として固定。

---

## 7. 早期PoCの「最小要件」
PoCで必ず満たすこと（最初の2週間の目標）:

1) Round1 Taguchi L4 が動く（4分割印刷→ベスト選択→θ0決定）
2) Round2 の MOBO が動く（最小2目的でOK、qNEHVI推奨）[web:108]
3) Query synthesis で候補が生成される（プール選択禁止）
4) 「undecidable」「both_bad」がログに残り、次候補生成に反映される

---

## 8. 受け入れ基準（Acceptance Criteria）
- ログのみから、同一の候補列が再生成できる（再現性）。
- 5回のラウンドで、少なくとも被験者の過半数が「初期より良い」と回答する（暫定基準）。
- 「迷った」が発生してもセッションが破綻せず、次ラウンドの候補差分が調整される。
