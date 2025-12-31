<!-- /docs/spec/project_brief.md -->

# プロジェクト企画書（改訂版）

## 1. 背景と目的

### 1.1 背景
- 家庭用インクジェット／オフィスプリンタ環境では、ICCプロファイルや測色器が使われない状況が一般的であり、  
  「画面と印刷の色が合わない」問題が日常的に発生している。[web:315]
- ディスプレイ側のICCもプリンタ側のICCも事実上ブラックボックスであるため、  
  従来の色管理の枠組み（絶対色Labを介したICC変換）は、現場レベルでは機能しづらい。

### 1.2 本プロジェクトの目的
- 測色器を使わず、「人間の比較評価（A/B/C/Dの見た目比較）」だけを観測として用い、  
  **特定の「画面＋プリンタ＋用紙＋照明」環境における“見た目が合う”プロファイル（3D LUT）を少ない試行回数で求めるアプリ**を実装する。
- 併せて、このプロセスが本当に有効かどうかを検証するための、**実動するPoCアプリ**を優先的に完成させる。

---

## 2. 方針（企画レベルの決定事項）

### 2.1 アプリ実装と論文用データ取りを分離する
- **優先度1:** 仮説検証用のアプリを動かし、「5回程度の印刷で実用上の改善が得られるか」を検証する。
- **優先度2:** 大規模実験・論文化のための「正規化されたログ」「JSONスキーマ」「BoTorch向けデータエクスポート」は、  
  別レイヤ（analysis/export層）として実装する。
- アプリ内部のログ構造はシンプルに保ち、必要に応じて **デコレータやloggingで詳細ログを付与**する。

### 2.2 最適化手法の選択（MOBO → PairwiseGP へ変更）
- 当初案：  
  - 連続目的（例: ΔE, ニュートラル度, 彩度など）をGPでモデリングし、多目的BO（MOBO）＋ qEHVI / qNEHVI で探索する。[web:171]
- 改訂案（本PoCで採用）:
  - **ユーザーから得られるのは比較データ（どちらがマシか）のみ**であることから、
  - BoTorchの **PairwiseGP** による preference-based BO を採用し、  
    単一の潜在utility \(u(x)\) を学習する。[web:235]
  - 連続スコアによる多目的最適化（MOBO＋qNEHVI）は、  
    グレー/彩度/肌色などを数値化できるようになってから「将来の拡張」として検討する。

### 2.3 ROUND設計（5回で終わるセッション）

- ユーザー視点の ROUND 数は **最大5回** を基本とする。

1. **ROUND 1**: OA L4 による初期探索
   - exposure / color_temp の2軸で4候補を生成し、4分割印刷。
   - ユーザーが「一番マシな1つ」を選ぶ（undecidable時は、再評価/reprintフローへ）。

2. **ROUND 2〜5**: PairwiseGP＋Query Synthesis
   - これまでの比較データから PairwiseGP をfitし、
     - ROUND 2・3: exposure / color_temp を中心に、ニュートラル（色かぶり）の改善を優先。
     - ROUND 4: saturation を含めた3次元近傍探索。
     - ROUND 5: tint / contrast を含めた微調整（5次元）。  
   - 各ラウンドで2〜3候補を合成（プール選択は禁止し、必ず連続空間から合成する）。

### 2.4 ベテランの色調整ノウハウの取り込み（ラウンドごとの軸）

- パラメータ空間（内部）は最終的に 5次元:
  - exposure, color_temp, saturation, tint, contrast
- ラウンドごとの「動かす軸」は次のように制御する：
  - ROUND1〜2: 主に exposure / color_temp （グレー / ホワイトバランス）
  - ROUND3: exposure / color_temp / saturation
  - ROUND4〜5: 全5次元だが、tint / contrast は小さな範囲から始める
- これにより、実務に近い「ニュートラル → 彩度 → 微調整」の順序を、  
  PairwiseGP の探索空間上に反映する。[web:324][web:313]

---

## 3. UI/UX 方針（Streamlit）

- アプリは **StreamlitベースのWeb UI** とし、CLIは使わない。
- 各ROUNDにおけるUI要素:
  - A/B/C/D のサムネイル（最後に実際に印刷に使うシート画像のプレビュー）
  - 「どれが一番マシか？」の選択（A〜D）
  - 「判断つかない」「どれもダメ」の選択肢（judgment）
  - undecidable/both_bad時の「次どうするか？」選択:
    - rejudge（印刷せず、観点をガイドして再評価）
    - reprint（パラメータ振幅を拡大した新候補で再印刷）
  - 観点(rubric)選択:
    - gray / saturation / skin など（選好の判断に使ってほしいポイント）

---

## 4. 開発スコープ（PoCで必須とする機能）

### 4.1 必須要件（アプリとして）

- ROUND1 OA L4:
  - 4候補の生成・レンダリング・表示・印刷
  - 4択＋undecidable/both_badの入力
  - undecidable に対する P2ポリシー（OA振幅拡大＋再印刷 or 再評価）

- PairwiseGP:
  - ROUND1の比較データから PairwiseGP をfitし、  
    ROUND2候補を生成できること。[web:235]

- Query Synthesis:
  - 各ROUNDで、プール選択ではなく連続空間から候補を合成する。
  - 最低限、「current best 近傍＋少し離れた探索候補」を2〜3点出せる。

- ROUND 2〜5 のループ:
  - 最大5 ROUND まで UIが回る。
  - 各ROUNDのフィードバック（選択・undecidable・rubric）がログに残る。

### 4.2 PoCの評価指標（簡易）

- ラウンド開始時と終了時の印刷物を比較して、  
  被験者が「改善した」と感じた割合。
- undecidable / both_bad の発生頻度と、その後の rejudge / reprint の選択比。
- ラウンドごとに「どの軸を動かしたか」とユーザーのrubricの関係（定性的評価）。

---

## 5. 分析・論文化用の拡張（後続フェーズ）

- `/analysis/` 以下に、以下を別レイヤとして実装する：
  - `session_export.py`:  
    アプリ内部の SessionLog から、stimuli/observations/rounds に正規化されたログを生成。
  - `botorch_dataset_export.py`:  
    正規化ログから `train_X/train_comp` を生成（BoTorchのPairwiseGPチュートリアル形式）。[web:235]
  - `log_json_schema.json`:  
    正規化ログに対する Draft 2020-12 の JSON Schema と、オフライン検証スクリプト。

これにより、
- アプリは **シンプルな内部ログで素早く回す**ことができ、
- 論文化・大規模実験フェーズでは、analysis層で **厳密な正規化＋スキーマ検証** を行える。

---

## 6. 開発計画（マイルストーン）

### M1: ROUND1 OA L4 + Web UI

- `/core/oa_initial_design.py`: L4候補生成（exposure/temp）
- `/core/optimizer.py`: ROUND1用の `suggest_next_round()` と `update_from_round()`
- `/core/renderer_streamlit.py`: ダミー画像生成＋URL埋め込み
- `/core/feedback_streamlit.py`: 4択＋undecidable/both_badのUI
- `/app/main_streamlit.py`: 1 ROUND終了まで動く

### M2: PairwiseGP 接続 + ROUND2 候補生成

- `/core/botorch_backend.py`: SessionLog → train_X/train_comp → PairwiseGP fit.[web:235]
- `/core/optimizer.py`: ROUND2で PairwiseGP を呼び出し、2候補をQuery Synthesisで合成。
- UIはROUND2まで回る。

### M3: ROUND3〜5 + 軸の段階的拡張

- ROUND3で saturation を解放
- ROUND4〜5で tint / contrast を解放
- undecidable/rejudge/reprintのフローをROUND1以外にも適用可能にする。

### M4: analysisレイヤと正規化ログ

- `/analysis/session_export.py` + `/docs/spec/log_json_schema.json` の整合
- `/analysis/botorch_dataset_export.py` で、ログからBoTorchデータを生成

---

以上が、方針変更を反映した「企画書（改訂版）」です。  
次はこの企画書を前提に、**M1（ROUND1 OA L4 + Web UI）**に必要なファイルのスケルトン（関数シグネチャ＋docstring＋入出力）をまとめます。
