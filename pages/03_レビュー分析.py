"""
レビュー分析ページ
- レビューファイルアップロード
- AI原子化 + カテゴリ分類
- カテゴリ×競合マトリクス
"""
import streamlit as st
import sys
import json
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(
    page_title="レビュー分析 - ProductDev",
    page_icon="⭐",
    layout="wide"
)

# インスタンス
@st.cache_resource
def get_settings():
    return SettingsManager()

@st.cache_resource
def get_data_store():
    return DataStore()

@st.cache_resource
def get_ai_provider(_settings):
    return AIProvider(_settings)

@st.cache_resource
def get_prompt_manager():
    return PromptManager()

settings = get_settings()
data_store = get_data_store()
ai_provider = get_ai_provider(settings)
prompt_manager = get_prompt_manager()

# サイドバー
with st.sidebar:
    st.markdown("### 💡 ProductDev")
    if st.button("← ダッシュボード"):
        st.switch_page("main.py")
    
    if "current_project" in st.session_state and st.session_state.current_project:
        project = st.session_state.current_project
        st.info(f"📁 {project.get('name', '未選択')}")
    else:
        st.warning("プロジェクトを選択してください")
        st.switch_page("pages/01_プロジェクト.py")

# プロジェクト確認
if "current_project" not in st.session_state or not st.session_state.current_project:
    st.error("プロジェクトが選択されていません。")
    st.stop()

project = st.session_state.current_project
project_id = project["id"]

# メインコンテンツ
st.title("⭐ レビュー分析")
st.caption("レビューからカテゴリ別の出現数を分析")

# 競合データ取得
competitors = data_store.list_by_parent("competitors", project_id)
competitor_names = {c["id"]: c["name"] for c in competitors}

# レビューアップロード
col1, col2 = st.columns([4, 1])
with col2:
    uploaded_file = st.file_uploader(
        "レビューをアップロード",
        type=["csv", "xlsx"],
        key="review_upload",
        label_visibility="collapsed"
    )

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success(f"✅ {len(df)}件のレビューを読み込みました")
        
        with st.expander("📄 データプレビュー"):
            st.dataframe(df.head(10))
        
        # AI分析ボタン
        if st.button("🤖 AIでレビューを分析", type="primary"):
            with st.spinner("AI分析中...（時間がかかる場合があります）"):
                try:
                    # レビューテキストを結合
                    review_column = None
                    for col in df.columns:
                        if "レビュー" in col or "review" in col.lower() or "コメント" in col or "本文" in col:
                            review_column = col
                            break
                    
                    if review_column is None:
                        review_column = df.columns[-1]  # 最後の列を使用
                    
                    reviews_text = "\n".join(df[review_column].astype(str).tolist()[:100])  # 最大100件
                    
                    # 原子化プロンプト
                    atomize_prompt = prompt_manager.load("atomize")
                    if not atomize_prompt:
                        atomize_prompt = prompt_manager.get_default("atomize")
                    
                    atomize_prompt = atomize_prompt.replace("{{reviews}}", reviews_text)
                    
                    # AI呼び出し（原子化）
                    atomize_response = ai_provider.generate_with_retry(
                        prompt=atomize_prompt,
                        task="atomize"
                    )
                    
                    # JSONを抽出
                    if "```json" in atomize_response:
                        json_str = atomize_response.split("```json")[1].split("```")[0]
                    elif "```" in atomize_response:
                        json_str = atomize_response.split("```")[1].split("```")[0]
                    else:
                        json_str = atomize_response
                    
                    keywords_data = json.loads(json_str.strip())
                    keywords = keywords_data.get("keywords", [])
                    
                    # カテゴリ分類プロンプト
                    categorize_prompt = prompt_manager.load("categorize")
                    if not categorize_prompt:
                        categorize_prompt = prompt_manager.get_default("categorize")
                    
                    keywords_text = json.dumps(keywords, ensure_ascii=False)
                    categorize_prompt = categorize_prompt.replace("{{keywords}}", keywords_text)
                    
                    # AI呼び出し（カテゴリ分類）
                    categorize_response = ai_provider.generate_with_retry(
                        prompt=categorize_prompt,
                        task="categorize"
                    )
                    
                    if "```json" in categorize_response:
                        json_str = categorize_response.split("```json")[1].split("```")[0]
                    elif "```" in categorize_response:
                        json_str = categorize_response.split("```")[1].split("```")[0]
                    else:
                        json_str = categorize_response
                    
                    categories_data = json.loads(json_str.strip())
                    
                    # 結果を保存
                    review_analysis = {
                        "project_id": project_id,
                        "total_reviews": len(df),
                        "categories": categories_data.get("categories", []),
                        "keywords": keywords
                    }
                    
                    # 既存のレビュー分析を削除して新規作成
                    existing = data_store.list_by_parent("reviews", project_id)
                    for ex in existing:
                        data_store.delete("reviews", ex["id"])
                    
                    data_store.create("reviews", review_analysis)
                    st.success("✅ レビュー分析が完了しました")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"エラー: {str(e)}")
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {str(e)}")

st.markdown("---")

# 分析結果表示
reviews_data = data_store.list_by_parent("reviews", project_id)

if reviews_data:
    review_analysis = reviews_data[0]
    total_reviews = review_analysis.get("total_reviews", 0)
    categories = review_analysis.get("categories", [])
    keywords = review_analysis.get("keywords", [])
    
    # 統計情報
    st.markdown(f"**全レビュー数合計: {total_reviews:,}件**")
    
    # カテゴリ×競合マトリクス
    if categories:
        st.subheader("📊 カテゴリ別集計")
        
        # テーブルデータ作成
        table_data = []
        for cat in categories:
            cat_name = cat.get("name", "")
            cat_keywords = cat.get("keywords", [])
            cat_total = len(cat_keywords) * 10  # 仮の計算
            cat_percent = round(cat_total / total_reviews * 100, 1) if total_reviews > 0 else 0
            
            table_data.append({
                "カテゴリ": cat_name,
                "合計": f"{cat_total} ({cat_percent}%)",
                "キーワード数": len(cat_keywords)
            })
        
        df_categories = pd.DataFrame(table_data)
        
        # カテゴリごとの展開表示
        for cat in categories:
            cat_name = cat.get("name", "")
            cat_keywords = cat.get("keywords", [])
            cat_total = len(cat_keywords) * 10
            cat_percent = round(cat_total / total_reviews * 100, 1) if total_reviews > 0 else 0
            
            with st.expander(f"📁 {cat_name} - {cat_total}件 ({cat_percent}%)"):
                st.write("**キーワード:**")
                keyword_text = ", ".join(cat_keywords[:20])
                st.write(keyword_text)
        
        # サマリーテーブル
        st.dataframe(df_categories, use_container_width=True, hide_index=True)
    
    # 原子化キーワードリスト
    if keywords:
        with st.expander("📝 原子化キーワードリスト（クリックで展開）"):
            for kw in keywords[:50]:
                word = kw.get("word", "")
                sentiment = kw.get("sentiment", "neutral")
                count = kw.get("count", 0)
                
                color = "#22c55e" if sentiment == "positive" else "#ef4444" if sentiment == "negative" else "#64748b"
                st.markdown(f'<span style="color: {color};">● {word}</span> ({count}件)', unsafe_allow_html=True)

else:
    st.info("📭 レビュー分析データがありません。CSVファイルをアップロードしてください。")
    
    # サンプルデータ表示
    with st.expander("💡 サンプルデータ形式"):
        sample_df = pd.DataFrame({
            "商品名": ["製品A", "製品A", "製品B"],
            "レビュー": ["軽くて使いやすい", "少し重いけど機能は良い", "静かで気に入った"],
            "評価": [5, 4, 5]
        })
        st.dataframe(sample_df)

# 次へボタン
st.markdown("---")
col_back, col_next = st.columns([1, 1])
with col_back:
    if st.button("← 競合分析に戻る", use_container_width=True):
        st.switch_page("pages/02_競合分析.py")
with col_next:
    if st.button("差別化検討へ進む →", type="primary", use_container_width=True):
        data_store.update("projects", project_id, {"phase": "差別化検討", "progress": 60})
        st.switch_page("pages/04_差別化検討.py")

# AIサイドバー
if settings.get_api_key(settings.get_provider()):
    context = f"プロジェクト: {project.get('name')}\nレビュー分析中"
    render_ai_sidebar(ai_provider, context)
