"""
メンバー評価ページ
- 商品企画の選択
- 評価メンバーの選択
- 各メンバー視点でのAI評価生成
- フィードバックの記録
"""
import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.manager_factory import get_managers

# ページ設定
st.set_page_config(
    page_title="メンバー評価 - ProductDev",
    page_icon="👥",
    layout="wide"
)

# インスタンス
settings, data_store, storage_manager, ai_provider = get_managers()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    if st.button("← ダッシュボード"):
        st.switch_page("main.py")

st.title("👥 メンバー評価")
st.caption("AIメンバーの視点で商品企画を診断します")

# 1. 評価対象の選択
col1, col2 = st.columns([2, 1])
with col1:
    projects = data_store.list("projects")
    project_names = [p.get("name") or "無名プロジェクト" for p in projects]
    project_ids = [p.get("id") for p in projects]
    
    if not project_ids:
        st.warning("プロジェクトが登録されていません。プロジェクトページで作成してください。")
        st.stop()
        
    selected_project_name = st.selectbox("評価する商品企画（プロジェクト）を選択", project_names)
    selected_project_id = project_ids[project_names.index(selected_project_name)]
    selected_project = next((p for p in projects if p["id"] == selected_project_id), {})

with col2:
    members = data_store.get_employee_personas()
    if not members:
        st.warning("メンバーAIが登録されていません。設定ページで登録してください。")
        st.stop()
    
    selected_member_names = st.multiselect(
        "評価を依頼するメンバーを選択",
        [m.get("name") for m in members],
        default=[m.get("name") for m in members][:2] if members else []
    )
    selected_members = [m for m in members if m.get("name") in selected_member_names]

if st.button("🚀 診断開始", type="primary"):
    if not selected_members:
        st.error("メンバーを選択してください")
    else:
        st.session_state["evaluation_results"] = {}
        # 商品情報のテキスト化
        product_content = f"""
        商品名: {selected_project.get('name')}
        コンセプト: {selected_project.get('concept')}
        ターゲット: {selected_project.get('target')}
        """
        
        # 各メンバーごとに評価生成
        for member in selected_members:
            with st.status(f"メンバー「{member.get('name')}」が考えています...", expanded=False):
                past_feedbacks = data_store.get_employee_feedback(member["id"], limit=5)
                try:
                    evaluation = ai_provider.evaluate_by_employee(
                        employee=member,
                        product_content=product_content,
                        past_feedbacks=past_feedbacks
                    )
                    st.session_state["evaluation_results"][member["id"]] = evaluation
                except Exception as e:
                    st.error(f"エラー ({member.get('name')}): {e}")

# 2. 評価結果の表示
if "evaluation_results" in st.session_state and st.session_state["evaluation_results"]:
    st.markdown("---")
    st.subheader("📊 評価結果")
    
    for member_id, result in st.session_state["evaluation_results"].items():
        member = next((m for m in members if m["id"] == member_id), {})
        
        with st.container():
            col_avatar, col_eval = st.columns([1, 5])
            with col_avatar:
                if member.get("avatar_url"):
                    st.image(member.get("avatar_url"), width=100)
                else:
                    st.write(f"👤 **{member.get('name')}**")
            
            with col_eval:
                st.markdown(f"### {member.get('name')} の評価")
                st.markdown(result)
                
                # フィードバック入力
                with st.expander("AIにフィードバックを送る（次回の評価に反映されます）"):
                    fb_key = f"fb_{selected_project_id}_{member_id}"
                    user_fb = st.text_area("修正指示・感想", key=fb_key)
                    if st.button("フィードバックを保存", key=f"btn_{fb_key}"):
                        if user_fb:
                            data_store.add_employee_feedback({
                                "employee_id": member_id,
                                "product_id": selected_project_id,
                                "ai_evaluation": result,
                                "user_feedback": user_fb
                            })
                            st.success("フィードバックを保存しました")
                        else:
                            st.warning("内容を入力してください")
        st.markdown("---")
