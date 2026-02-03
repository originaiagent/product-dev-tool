"""
レビュー分析ページ
競合レビューシートをAIで分析
"""
import streamlit as st
import json
from pathlib import Path
from modules.manager_factory import get_managers

st.set_page_config(page_title="レビュー分析", page_icon="📝", layout="wide")

# マネージャー取得
settings, data_store, storage_manager, ai_provider = get_managers()

st.title("📝 レビュー分析")
st.caption("競合レビューシートをAIで分析し、顧客が重視するキーワードを抽出します")

# プロジェクト選択
projects = data_store.list("projects")
if not projects:
    st.warning("プロジェクトがありません。先にプロジェクトを作成してください。")
    st.stop()

project_names = [p["name"] for p in projects]
selected_name = st.selectbox("プロジェクト", project_names)
project = next((p for p in projects if p["name"] == selected_name), None)

if not project:
    st.stop()

project_id = project["id"]

st.markdown("---")

# session_state初期化
if "review_uploader_key" not in st.session_state:
    st.session_state.review_uploader_key = 0

# ファイルアップロード
st.subheader("📄 競合レビューシート")

uploaded_file = st.file_uploader(
    "レビューデータをアップロード（PDF/Excel/CSV）",
    type=['pdf', 'xlsx', 'csv'],
    key=f"review_upload_{st.session_state.review_uploader_key}"
)

if uploaded_file:
    with st.spinner("ファイルを解析中..."):
        try:
            from modules.file_parser import FileParser
            parser = FileParser()
            
            # バイトデータから解析
            content = uploaded_file.getvalue()
            parsed = parser.parse_bytes(content, uploaded_file.name)
            
            # 解析結果を保存
            review_data = {
                "filename": uploaded_file.name,
                "type": parsed["type"],
                "text": parsed["text"][:10000],  # 最大10000文字
                "row_count": parsed.get("row_count"),
                "columns": parsed.get("columns")
            }
            
            data_store.save_review_analysis(project_id, {"raw_data": review_data})
            
            st.session_state.review_uploader_key += 1
            st.success(f"✅ {uploaded_file.name} を解析しました")
            st.rerun()
            
        except Exception as e:
            st.error(f"解析エラー: {e}")

# 保存済みデータの表示
saved_analysis = data_store.get_review_analysis(project_id)

if saved_analysis and saved_analysis.get("raw_data"):
    raw_data = saved_analysis["raw_data"]
    
    st.success(f"📄 アップロード済み: {raw_data.get('filename', '不明')}")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if raw_data.get("row_count"):
            st.caption(f"行数: {raw_data['row_count']}行")
    with col2:
        if st.button("🗑️ データを削除"):
            data_store.save_review_analysis(project_id, None)
            st.rerun()
    
    # プレビュー
    with st.expander("📋 データプレビュー"):
        preview_text = raw_data.get("text", "")[:2000]
        st.text(preview_text + ("..." if len(raw_data.get("text", "")) > 2000 else ""))
    
    st.markdown("---")
    
    # AI分析
    st.subheader("🤖 AI分析")
    
    if st.button("🔍 キーワード重要度を分析", type="primary", use_container_width=True):
        with st.spinner("AIが分析中..."):
            try:
                # プロンプト読み込み
                prompt_path = Path(__file__).parent.parent / "data" / "prompts" / "review_analysis.md"
                prompt_template = prompt_path.read_text(encoding="utf-8")
                
                # データを埋め込み
                review_text = raw_data.get("text", "")[:5000]
                prompt = prompt_template.replace("{review_data}", review_text)
                
                # AI実行
                result = ai_provider.generate(prompt)
                
                # 結果を保存
                saved_analysis["analysis_result"] = result
                data_store.save_review_analysis(project_id, saved_analysis)
                
                st.success("分析完了！")
                st.rerun()
                
            except Exception as e:
                st.error(f"分析エラー: {e}")
    
    # 分析結果表示
    if saved_analysis.get("analysis_result"):
        st.markdown("### 📊 分析結果")
        
        result = saved_analysis["analysis_result"]
        
        # 編集可能なテキストエリア
        edited = st.text_area(
            "内容（編集可能）",
            value=result,
            height=400,
            label_visibility="collapsed"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 変更を保存"):
                saved_analysis["analysis_result"] = edited
                data_store.save_review_analysis(project_id, saved_analysis)
                st.success("保存しました")
        with col2:
            if st.button("🔄 再分析"):
                saved_analysis["analysis_result"] = None
                data_store.save_review_analysis(project_id, saved_analysis)
                st.rerun()

else:
    st.info("👆 レビューシートをアップロードしてください")
