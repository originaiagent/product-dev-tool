"""
商品開発ツール - ダッシュボード
製品の差別化戦略を支援するツール
"""
import streamlit as st
import sys
from pathlib import Path

# モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(
    page_title="ProductDev - 商品開発ツール",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# インスタンス初期化
@st.cache_resource
def get_settings():
    return SettingsManager()

@st.cache_resource
def get_data_store():
    return DataStore()

@st.cache_resource
def get_ai_provider(_settings):
    return AIProvider(_settings)

settings = get_settings()
data_store = get_data_store()
ai_provider = get_ai_provider(settings)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 0.875rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .stat-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .stat-label {
        font-size: 0.75rem;
        color: #64748b;
        margin-bottom: 0.25rem;
    }
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
    }
    .project-card {
        background: #f8fafc;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: background 0.2s;
    }
    .project-card:hover {
        background: #f1f5f9;
    }
    .phase-badge {
        display: inline-block;
        padding: 0.125rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .phase-green { background: #dcfce7; color: #166534; }
    .phase-yellow { background: #fef9c3; color: #854d0e; }
    .phase-gray { background: #f1f5f9; color: #475569; }
</style>
""", unsafe_allow_html=True)

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    
    # 現在のプロジェクト
    if "current_project" in st.session_state and st.session_state.current_project:
        project = st.session_state.current_project
        st.info(f"📁 {project.get('name', '未選択')}")
    else:
        st.caption("プロジェクト未選択")

# メインコンテンツ
st.markdown('<p class="main-header">ダッシュボード</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">プロジェクトの概要です。</p>', unsafe_allow_html=True)

# 統計データ取得
projects = data_store.list("projects")
in_progress = len([p for p in projects if p.get("phase") != "完了"])
completed = len([p for p in projects if p.get("phase") == "完了"])

# 統計カード
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">🕐 進行中</div>
        <div class="stat-value">{}</div>
    </div>
    """.format(in_progress), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">📈 差別化決定</div>
        <div class="stat-value">{}</div>
    </div>
    """.format(len([p for p in projects if p.get("phase") == "差別化検討"])), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-label">✅ 完了</div>
        <div class="stat-value">{}</div>
    </div>
    """.format(completed), unsafe_allow_html=True)

st.markdown("---")

# プロジェクト一覧
col_header, col_button = st.columns([4, 1])
with col_header:
    st.subheader("プロジェクト一覧")
with col_button:
    if st.button("➕ 新規作成", type="primary", use_container_width=True):
        st.switch_page("pages/01_プロジェクト.py")

if projects:
    for project in projects:
        phase = project.get("phase", "競合分析")
        progress = project.get("progress", 0)
        
        # フェーズに応じた色
        phase_class = "phase-gray"
        if phase == "差別化検討":
            phase_class = "phase-green"
        elif phase == "レビュー分析":
            phase_class = "phase-yellow"
        
        with st.container():
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"""
                <div class="project-card">
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                        <span style="font-weight: 500;">{project.get('name', '無題')}</span>
                        <span class="phase-badge {phase_class}">{phase}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <div style="flex: 1; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden;">
                            <div style="width: {progress}%; height: 100%; background: #2563eb; border-radius: 3px;"></div>
                        </div>
                        <span style="font-size: 0.75rem; color: #64748b;">{progress}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button("開く", key=f"open_{project['id']}", use_container_width=True):
                    st.session_state.current_project = project
                    st.switch_page("pages/02_競合分析.py")
else:
    st.info("📭 プロジェクトがありません。「新規作成」ボタンから始めましょう。")

# AIサイドバー（APIキーが設定されている場合のみ）
if settings.get_api_key(settings.get_provider()):
    render_ai_sidebar(ai_provider)
