"""
ファイルアップロードウィジェット
- Streamlit用の統合ファイルアップロードUI
"""
import streamlit as st
from typing import List, Dict, Optional
from modules.file_processor import FileProcessor


def render_file_uploader(
    key: str,
    label: str = "ファイルをアップロード",
    max_files: int = 30,
    show_summary: bool = True,
    show_preview: bool = True,
    allowed_types: Optional[List[str]] = None
) -> List[Dict]:
    """
    統合ファイルアップロードウィジェット
    
    Args:
        key: ウィジェットの一意なキー
        label: 表示ラベル
        max_files: 最大ファイル数
        show_summary: サマリー表示するか
        show_preview: プレビュー表示するか
        allowed_types: 許可するファイルタイプ（Noneの場合は全て）
    
    Returns:
        処理済みファイルのリスト
    """
    # 許可するファイルタイプ
    if allowed_types is None:
        allowed_types = FileProcessor.get_all_extensions()
    
    # ファイルアップローダー
    uploaded_files = st.file_uploader(
        label,
        type=allowed_types,
        accept_multiple_files=True,
        key=f"uploader_{key}"
    )
    
    processed_files = []
    
    if uploaded_files:
        # ファイル処理
        with st.spinner("ファイルを処理中..."):
            for file in uploaded_files[:max_files]:
                result = FileProcessor.process_file(file)
                processed_files.append(result)
        
        # サマリー表示
        if show_summary:
            summary = FileProcessor.create_summary(processed_files)
            st.info(summary)
        
        # エラー表示
        errors = [pf for pf in processed_files if pf.get("error")]
        if errors:
            with st.expander("⚠️ エラー詳細", expanded=False):
                for error_file in errors:
                    st.error(f"{error_file['filename']}: {error_file['error']}")
        
        # プレビュー表示
        if show_preview and processed_files:
            with st.expander("📋 ファイル一覧", expanded=False):
                for pf in processed_files:
                    if pf.get("error"):
                        st.markdown(f"❌ **{pf['filename']}** - {pf['error']}")
                    else:
                        file_type_emoji = {
                            "image": "🖼️",
                            "pdf": "📄",
                            "excel": "📊",
                            "csv": "📈",
                            "word": "📝",
                            "text": "📃"
                        }
                        emoji = file_type_emoji.get(pf.get("type"), "📦")
                        st.markdown(f"{emoji} **{pf['filename']}** ({pf['type']})")
                        
                        # テキストプレビュー
                        if pf.get("text") and len(pf["text"]) > 100:
                            preview = pf["text"][:200] + "..."
                            st.caption(preview)
    
    return processed_files


def extract_text_from_files(processed_files: List[Dict]) -> str:
    """処理済みファイルからテキストを抽出"""
    return FileProcessor.extract_all_text(processed_files)


def extract_images_from_files(processed_files: List[Dict], max_images: int = 5) -> List[str]:
    """処理済みファイルから画像を抽出（base64）"""
    return FileProcessor.get_images_for_ai(processed_files, max_images)


def get_dataframes_from_files(processed_files: List[Dict]) -> Dict[str, 'pd.DataFrame']:
    """処理済みファイルからDataFrameを抽出"""
    import pandas as pd
    
    dataframes = {}
    
    for pf in processed_files:
        if pf.get("type") in ["excel", "csv"] and pf.get("content"):
            filename = pf["filename"]
            content = pf["content"]
            
            if isinstance(content, dict):  # Excelの場合（複数シート）
                for sheet_name, df in content.items():
                    dataframes[f"{filename}:{sheet_name}"] = df
            elif isinstance(content, pd.DataFrame):  # CSVの場合
                dataframes[filename] = content
    
    return dataframes
