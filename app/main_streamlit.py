# app/main_streamlit.py
import streamlit as st

st.set_page_config(
    page_title="PrintTune",
    page_icon="🖨️",
    layout="centered",
)

st.title("🖨️ PrintTune")
st.subheader("「画面で見た印象」に近いプリントへ寄せる比較選択ツール")

st.markdown("""
PrintTune は、ディスプレイの見た目と印刷物の色のズレを、数回の比較選択だけで解消するためのツールです。
複雑なカラーマネジメントの知識がなくても、直感的な操作で最適な補正パラメータを見つけることができます。

---

### 🚀 使い方

1.  **Run Session**: 
    - 補正したい画像をアップロードしてセッションを開始します。
    - 提示される4つの候補（Round1）を実際に印刷し、画面のターゲット画像に最も近いものを選びます。
    - 2枚比較（Round2以降）を繰り返し、徐々に理想の色へ追い込みます。
2.  **Final Print**:
    - 推定された最適なパラメータを適用した最終画像を書き出します。

---
""")

col1, col2 = st.columns(2)

with col1:
    st.info("### STEP 1\n補正セッションを開始・進行します。")
    if st.button("Run Session ページへ", type="primary", use_container_width=True):
        st.switch_page("pages/1_Run_Session.py")

with col2:
    st.success("### STEP 2\n最適化された結果を確認・出力します。")
    if st.button("Final Print ページへ", use_container_width=True):
        st.switch_page("pages/2_Final_Print.py")

st.divider()

with st.expander("💡 ヒント"):
    st.markdown("""
    - **評価用フレーム**: 印刷シートには自動的にグレーグラデーションと原色パッチが付与されます。これを見ることで、トーンの連続性や色の偏りを判断しやすくなります。
    - **判断に迷ったら**: 「Undecidable（判断つかない）」を選び、気になるポイント（肌色、グレーなど）を指定してください。AIがその観点を重点的に探索します。
    - **右クリック保存**: 画面上の画像はPNG形式で保持されています。右クリックで保存しても品質は維持されますが、最終結果は「Download」ボタンからの取得を推奨します。
    """)