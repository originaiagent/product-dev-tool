"""
AIサイドバー/ポップアップモジュール
- ポップアップダイアログでAIチャット機能を提供
- コンテキスト保持
- システムプロンプト設定
"""
import streamlit as st
from typing import Optional, List, Dict


def render_ai_chat_button():
    """AIチャットボタンをサイドバーに表示"""
    with st.sidebar:
        st.markdown("---")
        if st.button("💬 AIアシスタント", use_container_width=True, type="primary"):
            st.session_state.show_ai_dialog = True


@st.dialog("💬 AIアシスタント", width="large")
def show_ai_dialog(ai_provider, context: Optional[str] = None):
    """AIチャットダイアログを表示"""
    
    # チャット履歴の初期化
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    
    # システムプロンプト
    system_prompt = _get_system_prompt(context)
    
    # コンテキスト表示
    if context:
        with st.expander("📋 現在のコンテキスト", expanded=False):
            st.caption(context)
    
    # チャット履歴表示エリア
    chat_container = st.container(height=400)
    with chat_container:
        if not st.session_state.ai_chat_history:
            st.info("💡 競合分析やレビュー分析について質問してください。")
        
        for message in st.session_state.ai_chat_history:
            role = message["role"]
            content = message["content"]
            if role == "user":
                st.markdown(f"""
                <div style="background: #eff6ff; border-radius: 12px; padding: 0.75rem; margin-bottom: 0.5rem;">
                    <p style="margin: 0; font-size: 0.875rem;"><strong>🧑 あなた</strong></p>
                    <p style="margin: 0.25rem 0 0 0;">{content}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: #f1f5f9; border-radius: 12px; padding: 0.75rem; margin-bottom: 0.5rem;">
                    <p style="margin: 0; font-size: 0.875rem;"><strong>🤖 AI</strong></p>
                    <p style="margin: 0.25rem 0 0 0;">{content}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # 入力エリア
    st.markdown("---")
    col_input, col_actions = st.columns([4, 1])
    
    with col_input:
        user_input = st.text_area(
            "質問を入力",
            height=80,
            placeholder="例: この競合の弱点は何ですか？",
            label_visibility="collapsed",
            key="ai_dialog_input"
        )
    
    with col_actions:
        send_clicked = st.button("📤 送信", use_container_width=True, type="primary")
        clear_clicked = st.button("🗑️ クリア", use_container_width=True)
    
    # クリア処理
    if clear_clicked:
        st.session_state.ai_chat_history = []
        st.rerun()
    
    # 送信処理
    if send_clicked and user_input.strip():
        # ユーザーメッセージを追加
        st.session_state.ai_chat_history.append({
            "role": "user",
            "content": user_input.strip()
        })
        
        # AI応答を生成
        with st.spinner("考え中..."):
            try:
                # コンテキストを含めたプロンプト構築
                full_prompt = user_input
                if context:
                    full_prompt = f"## 現在のコンテキスト\n{context}\n\n## 質問\n{user_input}"
                
                response = ai_provider.generate(
                    prompt=full_prompt,
                    system_prompt=system_prompt
                )
                
                st.session_state.ai_chat_history.append({
                    "role": "assistant",
                    "content": response
                })
            except Exception as e:
                st.session_state.ai_chat_history.append({
                    "role": "assistant",
                    "content": f"❌ エラーが発生しました: {str(e)}"
                })
        
        st.rerun()


def render_ai_sidebar(ai_provider, context: Optional[str] = None):
    """AIチャットボタンとダイアログを管理"""
    
    # ダイアログ表示フラグの初期化
    if "show_ai_dialog" not in st.session_state:
        st.session_state.show_ai_dialog = False
    
    # サイドバーにボタンを表示
    render_ai_chat_button()
    
    # ダイアログ表示
    if st.session_state.show_ai_dialog:
        show_ai_dialog(ai_provider, context)
        st.session_state.show_ai_dialog = False


def _get_system_prompt(context: Optional[str] = None) -> str:
    """システムプロンプトを取得"""
    base_prompt = """あなたは製品開発を支援するAIアシスタントです。

## 役割
- 競合分析のアドバイス
- レビュー分析の解釈支援
- 差別化案の検討支援
- 一般的な質問への回答

## 回答ルール
- 簡潔で実用的な回答を心がける
- 情報が不足している場合は「わからない」と正直に回答する
- 推測・憶測で回答しない
- 具体的な提案やアクションを含める
- 日本語で回答する"""
    
    return base_prompt


def get_chat_history() -> List[Dict[str, str]]:
    """チャット履歴を取得"""
    if "ai_chat_history" in st.session_state:
        return st.session_state.ai_chat_history
    return []


def clear_chat_history():
    """チャット履歴をクリア"""
    st.session_state.ai_chat_history = []


def set_context(context: str):
    """コンテキストを設定"""
    st.session_state.ai_chat_context = context
