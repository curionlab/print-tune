# PrintTune
PrintTune は、Photoshop のソフトプルーフや ICC 運用が難しい（または環境制約でできない）趣味ユーザー向けに、**「画面で見た印象」に近いプリント**へ寄せるための、比較選択ベースのチューニングアプリ（PoC）です。

## Live Demo
[print-tune.streamlit](https://print-tune.streamlit.app/)

---

## 特徴

- Streamlit UI で、各ラウンドの候補（A/B または A/B/C/D）を見比べて選ぶだけで進行。
- Round1 は OA L4（直交表）で 4 枚を提示し、露出・階調（contrast+gamma）・色温度（temp）に絞って方向性を決めます（彩度は Round1 では固定）。
- Round2 以降は Pairwise（2 枚比較）を繰り返し、PairwiseGP + EUBO で次の候補を提案します。
- 画像処理は「sRGB(u8) → Linear(f32) → パラメトリック変換 → sRGB(u8)」の Linear RGB パイプラインで統一しています。
- **PairwiseGPの事後平均最大化による推定best**を `best_params.json` に保存し、Final Print / 検証画像にも適用できます。
- **ユーザー画像アップロード対応**（JPEG/PNG両対応、EXIF orientation自動補正）
- **評価用フレーム**（グレーグラデーション＋原色パッチ）で印刷結果の評価を容易に

---

## 必要環境

- Windows + WSL2（Ubuntu 推奨）
- pixi（conda-forge 系依存の解決に使用）

---

## セットアップ（WSL2 + pixi）

### 1) リポジトリ取得

```
git clone https://github.com/curionlab/print-tune.git
cd print-tune
```

### 2) 依存導入

```
pixi install
```

> `src/` レイアウトのため、プロジェクト自体は editable install 済み（`pyproject.toml` + `pixi.toml` 側で path 指定）を前提とします。

### 3) Streamlit 起動

```
pixi run streamlit run app/main_streamlit.py
```

ブラウザで `http://localhost:8501` を開きます。

---

## 使い方（PoCの流れ）

1. `Run Session` で画像をアップロード（またはsample.pngを使用）してセッションを開始（Round1 の OA L4 が生成されます）。
2. 候補シートを印刷し、実プリントを見て「画面のターゲット画像」に近いものを選びます（chosen / undecidable / both_bad）。
   - 評価用フレーム（グレーグラデーション＋原色パッチ）が自動的に追加され、トーン再現と色偏りを確認しやすくなります。
3. chosen の場合は次ラウンドが生成され、比較を繰り返します（標準 5 ラウンド、最大 10 ラウンド）。
4. `Final Print` で `best_params.json` を適用した最終画像を出力します（評価用フレームのON/OFF選択可能）。

---

## ディレクトリ構成（概要）

```
print-tune/
  app/                      # Streamlit UI
    main_streamlit.py
    pages/
      1_Run_Session.py
      2_Final_Print.py
  src/printtune/             # Python package (src layout)
    core/
      imaging/               # 画像処理（Linear RGB pipeline）
      botorch/               # PairwiseGP / EUBO 提案
      optimizer/             # param空間・OA・center/best抽出
      io/                    # session.json / best_params.json の入出力
      session_loop.py        # ラウンド進行ロジック
      usecases.py            # UIから呼ぶユースケース
  data/
    input/       # sample.png など
    output/sessions/         # session.json / artifacts
  pixi.toml
  pyproject.toml
```

---

## 開発メモ（運用）

- 「選択・判断」は UI（app）、「最適化」は core/botorch・core/optimizer、「画像処理」は core/imaging に分離します。
- エラーが出た場合は、traceback と「どの Round / どの判定 / 次アクション」を共有してください。

---

## Roadmap（次の改善）

- テスト・検証基盤の構築（PoC → 運用フェーズ）
- 実写検証に基づくパラメータ微調整（Tint開始値、スケジュール数値等）
- 分析レイヤ（analysis）の実装（論文化準備）

---

## License

TBD
