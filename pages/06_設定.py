"""
設定ページ
- LLM設定（プロバイダ・モデル選択）
- APIキー状態確認
- タスク別モデル設定
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.settings_manager import SettingsManager

# ページ設定
st.set_page_config(
    page_title="設定 - ProductDev",
    page_icon="⚙️",
    layout="wide"
)

# インスタンス
@st.cache_resource
def get_settings():
    return SettingsManager()

settings = get_settings()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    if st.button("← ダッシュボード"):
        st.switch_page("main.py")

# メインコンテンツ
col_title, col_refresh = st.columns([4, 1])
with col_title:
    st.title("⚙️ 設定")
    st.caption("AIモデルとAPIの設定")
with col_refresh:
    if st.button("🔄 モデル一覧を更新"):
        with st.spinner("モデル一覧を取得中..."):
            try:
                current_provider = settings.get_provider()
                models = settings.refresh_models(current_provider)
                if models:
                    st.success(f"✅ {len(models)}件のモデルを取得しました")
                else:
                    st.warning("⚠️ モデルを取得できませんでした（APIキーを確認してください）")
            except Exception as e:
                st.error(f"❌ エラー: {str(e)}")
        st.rerun()

# タブ
tab1, tab2, tab3 = st.tabs(["LLM設定", "APIキー", "使用状況"])

# LLM設定タブ
with tab1:
    st.subheader("LLM設定")
    
    # プロバイダ選択
    providers = settings.get_available_providers()
    current_provider = settings.get_provider()
    
    provider_names = [p["name"] for p in providers]
    provider_ids = [p["id"] for p in providers]
    current_idx = provider_ids.index(current_provider) if current_provider in provider_ids else 0
    
    selected_provider_name = st.selectbox(
        "プロバイダ",
        provider_names,
        index=current_idx
    )
    selected_provider = provider_ids[provider_names.index(selected_provider_name)]
    
    # モデル選択
    models = settings.get_available_models(selected_provider)
    current_model = settings.get_model()
    
    model_names = [m["name"] for m in models]
    model_ids = [m["id"] for m in models]
    current_model_idx = model_ids.index(current_model) if current_model in model_ids else 0
    
    selected_model_name = st.selectbox(
        "モデル",
        model_names,
        index=current_model_idx
    )
    selected_model = model_ids[model_names.index(selected_model_name)]
    
    if st.button("LLM設定を保存", type="primary"):
        settings.set_provider(selected_provider)
        settings.set_model(selected_model, selected_provider)
        st.success("✅ LLM設定を保存しました")
    
    # タスク別モデル設定
    st.markdown("---")
    st.subheader("タスク別モデル設定")
    st.caption("特定のタスクに別のモデルを使用できます")
    
    tasks = [
        {"id": "extract", "name": "競合情報抽出（画像分析）"},
        {"id": "atomize", "name": "レビュー分析"},
        {"id": "differentiate", "name": "差別化案生成"}
    ]
    
    for task in tasks:
        col_task, col_model = st.columns([2, 2])
        with col_task:
            st.write(task["name"])
        with col_model:
            task_model = settings.get(f"ai.task_models.{task['id']}")
            options = ["デフォルトを使用"] + model_ids
            current = options.index(task_model) if task_model in options else 0
            
            new_model = st.selectbox(
                f"モデル（{task['id']}）",
                options,
                index=current,
                key=f"task_model_{task['id']}",
                label_visibility="collapsed"
            )
            
            if new_model != (task_model or "デフォルトを使用"):
                settings.set_task_model(
                    task["id"],
                    None if new_model == "デフォルトを使用" else new_model
                )

# APIキータブ
with tab2:
    st.subheader("APIキー設定状態")
    st.caption("環境変数から読み込まれます")
    
    api_status = settings.check_api_key_status()
    
    for provider in providers:
        provider_id = provider["id"]
        is_set = api_status.get(provider_id, False)
        
        env_var = {
            "google": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }.get(provider_id, "")
        
        col_name, col_status, col_env = st.columns([2, 1, 2])
        with col_name:
            st.write(provider["name"])
        with col_status:
            if is_set:
                st.success("✓ 設定済み")
            else:
                st.error("✗ 未設定")
        with col_env:
            st.code(env_var)
    
    st.markdown("---")
    st.info("""
    **APIキーの設定方法**
    
    1. 各プロバイダでAPIキーを取得
    2. 環境変数に設定:
    ```bash
    export GOOGLE_API_KEY="your-key"
    export ANTHROPIC_API_KEY="your-key"
    export OPENAI_API_KEY="your-key"
    ```
    3. Streamlit Cloudの場合は「Secrets」に設定
    """)

# 使用状況タブ
with tab3:
    st.subheader("使用状況")
    st.caption("※ 現在の実装ではトラッキングされていません")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("今月のAPI呼び出し", "-")
    with col2:
        st.metric("推定コスト", "-")
    with col3:
        st.metric("トークン数", "-")
    
    st.info("使用状況のトラッキングは今後のバージョンで対応予定です。")
