"""
プロンプト管理ページ
- AIタスクのプロンプト編集
- バージョン管理
- デフォルト復元
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.manager_factory import get_managers
from modules.prompt_manager import PromptManager

# ページ設定
st.set_page_config(
    page_title="プロンプト管理 - ProductDev",
    page_icon="📝",
    layout="wide"
)

# インスタンス
@st.cache_resource
def get_prompt_manager():
    return PromptManager()

settings, data_store, storage_manager, ai_provider = get_managers()
prompt_manager = get_prompt_manager()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    if st.button("← ダッシュボード"):
        st.switch_page("main.py")

# メインコンテンツ
st.title("📝 プロンプト管理")
st.caption("AIタスクのプロンプトを編集")

# タスク一覧取得
prompts = prompt_manager.list_prompts()

# 選択状態
if "selected_task" not in st.session_state:
    st.session_state.selected_task = "extract"

# レイアウト
col_list, col_editor = st.columns([1, 3])

# タスク一覧
with col_list:
    st.subheader("タスク一覧")
    
    for prompt in prompts:
        task_id = prompt["id"]
        is_selected = st.session_state.selected_task == task_id
        
        bg_color = "#eff6ff" if is_selected else "white"
        border_color = "#2563eb" if is_selected else "#e2e8f0"
        
        st.markdown(f"""
        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 8px; padding: 0.5rem; margin-bottom: 0.5rem;">
            <p style="margin: 0; font-weight: 500; color: {'#1e40af' if is_selected else '#1e293b'};">{prompt['name']}</p>
            <p style="margin: 0; font-size: 0.75rem; color: #64748b;">{prompt['description']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("選択", key=f"select_{task_id}", use_container_width=True):
            st.session_state.selected_task = task_id
            st.rerun()

# プロンプト編集
with col_editor:
    selected_task = st.session_state.selected_task
    task_info = next((p for p in prompts if p["id"] == selected_task), None)
    
    if task_info:
        # ヘッダー
        col_title, col_actions = st.columns([3, 2])
        with col_title:
            st.subheader(task_info["name"])
        with col_actions:
            col_reset, col_save = st.columns(2)
            with col_reset:
                if st.button("デフォルトに戻す", use_container_width=True):
                    if prompt_manager.reset_to_default(selected_task):
                        st.success("デフォルトに戻しました")
                        st.rerun()
            with col_save:
                save_button = st.button("💾 保存", type="primary", use_container_width=True)
        
        # プロンプト内容読み込み
        prompt_content = prompt_manager.load(selected_task)
        if prompt_content is None:
            prompt_content = prompt_manager.get_default(selected_task)
        
        # エディタ
        st.markdown("**システムプロンプト**")
        edited_content = st.text_area(
            "プロンプト内容",
            value=prompt_content,
            height=400,
            key=f"editor_{selected_task}",
            label_visibility="collapsed"
        )
        
        # 保存処理
        if save_button:
            prompt_manager.save(selected_task, edited_content)
            st.success("✅ 保存しました")
        
        # バージョン履歴
        versions = prompt_manager.get_versions(selected_task)
        if versions:
            with st.expander("📜 バージョン履歴"):
                for version in versions[:10]:
                    col_ver, col_restore = st.columns([3, 1])
                    with col_ver:
                        st.text(version["timestamp"])
                    with col_restore:
                        if st.button("復元", key=f"restore_{version['filename']}"):
                            prompt_manager.restore_version(selected_task, version["filename"])
                            st.success("復元しました")
                            st.rerun()
        
        # 変数説明
        st.markdown("---")
        st.markdown("**📌 使用可能な変数**")
        
        variables = {
            "extract": "画像とテキスト情報は自動で付与されます",
            "atomize": "`{{reviews}}` - レビューテキスト",
            "categorize": "`{{keywords}}` - 原子化されたキーワード",
            "differentiate": "`{{competitors}}` - 競合データ、`{{reviews}}` - レビューデータ",
            "estimate": "`{{ideas}}` - 差別化案リスト"
        }
        
        st.info(variables.get(selected_task, "変数なし"))
