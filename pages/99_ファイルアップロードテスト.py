"""
ファイルアップロード機能のテストページ
- 各種ファイル形式のアップロードテスト
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.file_processor import FileProcessor
from modules.file_upload_widget import (
    render_file_uploader, 
    extract_text_from_files, 
    extract_images_from_files,
    get_dataframes_from_files
)

# ページ設定
st.set_page_config(
    page_title="ファイルアップロードテスト",
    page_icon="📎",
    layout="wide"
)

st.title("📎 ファイルアップロード機能テスト")
st.caption("PDF、Excel、CSV、画像など、幅広いファイル形式をテストできます")

st.markdown("---")

# タブで機能を分ける
tab1, tab2, tab3 = st.tabs(["📁 基本アップロード", "🧪 詳細テスト", "📊 データ抽出"])

# タブ1: 基本アップロード
with tab1:
    st.subheader("基本的なファイルアップロード")
    st.write("統合ウィジェットを使った簡単なアップロード")
    
    processed_files = render_file_uploader(
        key="basic_upload",
        label="ファイルをアップロード（全形式対応）",
        max_files=30,
        show_summary=True,
        show_preview=True
    )
    
    if processed_files:
        st.markdown("---")
        
        # 抽出したテキスト表示
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📝 抽出テキスト")
            text = extract_text_from_files(processed_files)
            if text:
                st.text_area("全ファイルから抽出", text, height=300, key="text_basic")
            else:
                st.info("テキストを抽出できるファイルがありません")
        
        with col2:
            st.subheader("🖼️ 抽出画像")
            images = extract_images_from_files(processed_files, max_images=10)
            if images:
                st.write(f"画像数: {len(images)}枚")
                for i, img_b64 in enumerate(images[:3]):
                    st.image(f"data:image/png;base64,{img_b64}", caption=f"画像 {i+1}")
            else:
                st.info("画像ファイルがありません")

# タブ2: 詳細テスト
with tab2:
    st.subheader("詳細なファイル情報")
    
    # ファイルタイプ別にアップロード
    st.write("**ファイルタイプを指定してアップロード**")
    
    col_test1, col_test2, col_test3 = st.columns(3)
    
    with col_test1:
        st.markdown("##### 🖼️ 画像のみ")
        images_only = render_file_uploader(
            key="images_only",
            label="画像ファイル",
            allowed_types=["jpg", "jpeg", "png", "gif"],
            max_files=10,
            show_summary=True,
            show_preview=False
        )
    
    with col_test2:
        st.markdown("##### 📊 データファイルのみ")
        data_only = render_file_uploader(
            key="data_only",
            label="Excel/CSV",
            allowed_types=["xlsx", "xls", "csv"],
            max_files=5,
            show_summary=True,
            show_preview=False
        )
    
    with col_test3:
        st.markdown("##### 📄 ドキュメントのみ")
        docs_only = render_file_uploader(
            key="docs_only",
            label="PDF/Word",
            allowed_types=["pdf", "docx", "doc"],
            max_files=5,
            show_summary=True,
            show_preview=False
        )
    
    st.markdown("---")
    
    # 詳細情報表示
    st.subheader("🔍 ファイル処理の詳細")
    
    all_files = (images_only or []) + (data_only or []) + (docs_only or [])
    
    if all_files:
        for pf in all_files:
            with st.expander(f"📄 {pf['filename']}"):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write("**ファイル情報**")
                    st.json({
                        "type": pf.get("type"),
                        "filename": pf.get("filename"),
                        "has_text": bool(pf.get("text")),
                        "has_base64": bool(pf.get("base64")),
                        "error": pf.get("error")
                    })
                
                with col_info2:
                    st.write("**抽出テキスト（プレビュー）**")
                    if pf.get("text"):
                        preview = pf["text"][:500]
                        st.text(preview + "..." if len(pf["text"]) > 500 else preview)
                    else:
                        st.info("テキストなし")

# タブ3: データ抽出
with tab3:
    st.subheader("📊 Excel/CSVデータの抽出とプレビュー")
    
    data_files = render_file_uploader(
        key="data_extraction",
        label="Excel/CSVファイルをアップロード",
        allowed_types=["xlsx", "xls", "csv", "tsv"],
        max_files=10,
        show_summary=True,
        show_preview=False
    )
    
    if data_files:
        # DataFrameを抽出
        dataframes = get_dataframes_from_files(data_files)
        
        if dataframes:
            st.success(f"✅ {len(dataframes)}個のデータセットを抽出しました")
            
            # データセット選択
            selected_df = st.selectbox(
                "データセットを選択",
                list(dataframes.keys())
            )
            
            if selected_df:
                df = dataframes[selected_df]
                
                # データ情報
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("行数", len(df))
                with col_stat2:
                    st.metric("列数", len(df.columns))
                with col_stat3:
                    st.metric("データ型数", df.dtypes.nunique())
                
                # データプレビュー
                st.markdown("**データプレビュー（先頭20行）**")
                st.dataframe(df.head(20), use_container_width=True)
                
                # カラム情報
                with st.expander("📋 カラム情報"):
                    st.write(df.dtypes)
                
                # 基本統計
                with st.expander("📈 基本統計"):
                    st.write(df.describe())
        else:
            st.info("データを抽出できるファイルがありません")

# フッター
st.markdown("---")
st.caption("💡 対応形式: 画像(jpg/png/gif等)、PDF、Excel(xlsx/xls)、CSV、Word(docx)、テキスト(txt/md/json)")

# サイドバー：使い方
with st.sidebar:
    st.markdown("### 📖 使い方")
    st.write("""
    **基本アップロード**
    - 全形式のファイルをアップロード
    - テキスト・画像を自動抽出
    
    **詳細テスト**
    - ファイルタイプ別にテスト
    - 処理結果の詳細を確認
    
    **データ抽出**
    - Excel/CSVをDataFrameとして読み込み
    - データのプレビューと統計
    """)
    
    st.markdown("---")
    
    st.markdown("### 🎯 サポート形式")
    file_types = {
        "🖼️ 画像": "jpg, png, gif, bmp, webp",
        "📄 PDF": "pdf",
        "📊 Excel": "xlsx, xls",
        "📈 CSV": "csv, tsv",
        "📝 Word": "docx, doc",
        "📃 テキスト": "txt, md, json"
    }
    
    for category, exts in file_types.items():
        st.markdown(f"**{category}**")
        st.caption(exts)
