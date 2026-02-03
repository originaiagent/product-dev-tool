"""
プロジェクト管理ページ
- プロジェクトのCRUD
- 新規作成、編集、削除
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.manager_factory import get_managers

# ページ設定
st.set_page_config(
    page_title="プロジェクト - ProductDev",
    page_icon="📁",
    layout="wide"
)

# インスタンス
settings, data_store, storage_manager, ai_provider = get_managers()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    if st.button("← ダッシュボード"):
        st.switch_page("main.py")

# メインコンテンツ
st.title("📁 プロジェクト")
st.caption("製品開発プロジェクトを管理")

# 新規作成モーダル
if "show_create_modal" not in st.session_state:
    st.session_state.show_create_modal = False

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("➕ 新規プロジェクト", type="primary", use_container_width=True):
        st.session_state.show_create_modal = True

# 新規作成フォーム
if st.session_state.show_create_modal:
    with st.form("create_project_form"):
        st.subheader("新規プロジェクト作成")
        
        name = st.text_input("製品名 *", placeholder="例: ネックマッサージャー")
        category = st.selectbox(
            "カテゴリ",
            ["選択してください", "美容・健康家電", "日用品", "スポーツ用品", "家電", "その他"]
        )
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("作成", type="primary", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("キャンセル", use_container_width=True)
        
        if submitted and name:
            project = data_store.create("projects", {
                "name": name,
                "category": category if category != "選択してください" else None,
                "phase": "競合分析",
                "progress": 0
            })
            st.session_state.show_create_modal = False
            st.session_state.current_project = project
            st.success(f"✅ プロジェクト「{name}」を作成しました")
            st.rerun()
        
        if cancelled:
            st.session_state.show_create_modal = False
            st.rerun()

st.markdown("---")

# プロジェクト一覧
projects = data_store.list("projects")

if projects:
    # グリッド表示
    cols = st.columns(3)
    for i, project in enumerate(projects):
        with cols[i % 3]:
            phase = project.get("phase", "競合分析")
            progress = project.get("progress", 0)
            
            # フェーズカラー
            phase_color = "#64748b"
            if phase == "差別化検討":
                phase_color = "#16a34a"
            elif phase == "レビュー分析":
                phase_color = "#ca8a04"
            
            with st.container():
                st.markdown(f"""
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                    <span style="display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; 
                           font-size: 0.75rem; background: {phase_color}20; color: {phase_color};">{phase}</span>
                    <h4 style="margin: 0.5rem 0;">{project.get('name', '無題')}</h4>
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <div style="flex: 1; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                            <div style="width: {progress}%; height: 100%; background: #2563eb;"></div>
                        </div>
                        <span style="font-size: 0.75rem; color: #64748b;">{progress}%</span>
                    </div>
                    <p style="font-size: 0.75rem; color: #94a3b8; margin: 0;">
                        更新: {project.get('updated_at', '')[:10] if project.get('updated_at') else '-'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col_open, col_delete = st.columns(2)
                with col_open:
                    if st.button("開く", key=f"open_{project['id']}", use_container_width=True):
                        st.session_state.current_project = project
                        st.switch_page("pages/02_競合分析.py")
                with col_delete:
                    if st.button("🗑️", key=f"delete_{project['id']}", use_container_width=True):
                        data_store.delete("projects", project["id"])
                        st.success("削除しました")
                        st.rerun()
else:
    st.info("📭 プロジェクトがありません。「新規プロジェクト」ボタンから始めましょう。")
