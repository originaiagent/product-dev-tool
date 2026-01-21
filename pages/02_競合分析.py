"""
競合分析ページ
- 競合情報入力（画像・テキスト）
- AI情報抽出
- ガチ比較表
"""
import streamlit as st
import sys
import json
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.ai_sidebar import render_ai_sidebar

# ページ設定
st.set_page_config(
    page_title="競合分析 - ProductDev",
    page_icon="🔍",
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
    
    # 現在のプロジェクト
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
st.title("🔍 競合分析")
st.caption("競合ごとに画像・テキストをアップロード → 情報を自動抽出")

# 競合追加モーダル
if "show_add_competitor" not in st.session_state:
    st.session_state.show_add_competitor = False

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("➕ 競合を追加", type="primary", use_container_width=True):
        st.session_state.show_add_competitor = True

# 競合追加フォーム
if st.session_state.show_add_competitor:
    with st.form("add_competitor_form"):
        st.subheader("競合を追加")
        
        name = st.text_input("競合名 *", placeholder="例: NIPLUX")
        url = st.text_input("URL（任意）", placeholder="https://amazon.co.jp/...")
        platform = st.selectbox("プラットフォーム", ["Amazon", "楽天", "その他"])
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            reviews = st.number_input("レビュー数", min_value=0, value=0)
        with col_b:
            sales = st.number_input("月間売上（万円）", min_value=0, value=0)
        with col_c:
            units = st.number_input("月間販売数", min_value=0, value=0)
        
        col_submit, col_cancel = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("追加", type="primary", use_container_width=True)
        with col_cancel:
            cancelled = st.form_submit_button("キャンセル", use_container_width=True)
        
        if submitted and name:
            competitor = data_store.create("competitors", {
                "project_id": project_id,
                "name": name,
                "url": url,
                "platform": platform,
                "reviews": reviews,
                "sales": sales * 10000 if sales else None,
                "units": units if units else None,
                "images": [],
                "text_info": "",
                "extracted_data": {}
            })
            st.session_state.show_add_competitor = False
            st.success(f"✅ 競合「{name}」を追加しました")
            st.rerun()
        
        if cancelled:
            st.session_state.show_add_competitor = False
            st.rerun()

st.markdown("---")

# 競合一覧
competitors = data_store.list_by_parent("competitors", project_id)

if competitors:
    # 競合カード（2列）
    cols = st.columns(2)
    for i, comp in enumerate(competitors):
        with cols[i % 2]:
            with st.container():
                # ヘッダー
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <strong>{comp.get('name', '無題')}</strong>
                        <span style="background: #f1f5f9; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">
                            {comp.get('platform', 'Amazon')}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 画像アップロード
                uploaded_images = st.file_uploader(
                    "画像をアップロード（最大30枚）",
                    type=["jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                    key=f"images_{comp['id']}"
                )
                
                if uploaded_images:
                    # 画像をbase64でエンコードして保存
                    images_b64 = []
                    for img in uploaded_images[:30]:
                        b64 = base64.b64encode(img.read()).decode()
                        images_b64.append(b64)
                        img.seek(0)  # ポインタをリセット
                    
                    data_store.update("competitors", comp["id"], {"images": images_b64})
                    st.caption(f"📷 {len(images_b64)}枚の画像をアップロード済み")
                
                # テキスト情報
                text_info = st.text_area(
                    "テキスト情報（商品ページからコピペ）",
                    value=comp.get("text_info", ""),
                    height=100,
                    key=f"text_{comp['id']}"
                )
                
                if text_info != comp.get("text_info", ""):
                    data_store.update("competitors", comp["id"], {"text_info": text_info})
                
                # AI抽出ボタン
                col_extract, col_delete = st.columns([3, 1])
                with col_extract:
                    if st.button("🤖 情報を自動抽出", key=f"extract_{comp['id']}", use_container_width=True):
                        with st.spinner("AI分析中..."):
                            try:
                                # プロンプト取得
                                prompt = prompt_manager.load("extract")
                                if not prompt:
                                    prompt = prompt_manager.get_default("extract")
                                
                                # 画像を準備
                                images = comp.get("images", [])
                                
                                # AI呼び出し
                                response = ai_provider.generate_with_retry(
                                    prompt=f"{prompt}\n\n## テキスト情報\n{text_info}",
                                    task="extract",
                                    images=images[:5] if images else None  # 最大5枚
                                )
                                
                                # JSONを抽出
                                try:
                                    # ```json ... ``` の中身を抽出
                                    if "```json" in response:
                                        json_str = response.split("```json")[1].split("```")[0]
                                    elif "```" in response:
                                        json_str = response.split("```")[1].split("```")[0]
                                    else:
                                        json_str = response
                                    
                                    extracted = json.loads(json_str.strip())
                                    data_store.update("competitors", comp["id"], {"extracted_data": extracted})
                                    st.success("✅ 情報を抽出しました")
                                    st.rerun()
                                except json.JSONDecodeError:
                                    st.error("AI応答の解析に失敗しました")
                                    st.text(response)
                            except Exception as e:
                                st.error(f"エラー: {str(e)}")
                
                with col_delete:
                    if st.button("🗑️", key=f"del_{comp['id']}", use_container_width=True):
                        data_store.delete("competitors", comp["id"])
                        st.rerun()
                
                # 抽出されたデータ表示
                extracted = comp.get("extracted_data", {})
                if extracted:
                    st.markdown("---")
                    ext_col1, ext_col2, ext_col3 = st.columns(3)
                    with ext_col1:
                        st.caption("⭐ レビュー数")
                        st.write(f"{comp.get('reviews', 0):,}件")
                    with ext_col2:
                        if comp.get("sales"):
                            st.caption("💰 月間売上")
                            st.write(f"¥{comp.get('sales', 0) // 10000:,}万")
                    with ext_col3:
                        if comp.get("units"):
                            st.caption("📦 月間販売数")
                            st.write(f"{comp.get('units', 0):,}個")
                    
                    if extracted.get("features"):
                        st.caption("✨ 特徴")
                        st.write(", ".join(extracted.get("features", [])[:3]))
                    
                    if extracted.get("negatives"):
                        st.caption("😞 悪い点")
                        st.write(", ".join(extracted.get("negatives", [])[:3]))
                
                st.markdown("---")
    
    # ガチ比較表
    st.subheader("📊 ガチ比較表")
    st.caption("※アップロード情報から自動抽出")
    
    # テーブル作成
    if len(competitors) > 0:
        # ヘッダー
        header_cols = ["項目", "自社目標"] + [c.get("name", "競合") for c in competitors]
        
        # スペック項目を収集
        all_specs = set()
        for comp in competitors:
            extracted = comp.get("extracted_data", {})
            specs = extracted.get("specs", {})
            all_specs.update(specs.keys())
        
        # テーブルデータ
        table_data = []
        
        # URL行
        url_row = ["URL", "-"] + [f"[🔗]({c.get('url', '#')})" if c.get('url') else "-" for c in competitors]
        
        # 価格行
        price_row = ["価格", "-"]
        for comp in competitors:
            extracted = comp.get("extracted_data", {})
            price_row.append(extracted.get("price", "-"))
        
        # スペック行
        spec_rows = []
        for spec_key in ["weight", "size", "power"]:
            row = [spec_key.replace("weight", "重量").replace("size", "サイズ").replace("power", "電源"), "-"]
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                specs = extracted.get("specs", {})
                row.append(specs.get(spec_key, "-"))
            spec_rows.append(row)
        
        # Markdown テーブル作成
        all_rows = [price_row] + spec_rows
        
        # ヘッダー
        md_table = "| " + " | ".join(header_cols) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(header_cols)) + " |\n"
        
        for row in all_rows:
            md_table += "| " + " | ".join(str(cell) for cell in row) + " |\n"
        
        st.markdown(md_table)
    
    # 次へボタン
    st.markdown("---")
    col_back, col_next = st.columns([1, 1])
    with col_next:
        if st.button("レビュー分析へ進む →", type="primary", use_container_width=True):
            # プロジェクトの進捗を更新
            data_store.update("projects", project_id, {"phase": "レビュー分析", "progress": 30})
            st.switch_page("pages/03_レビュー分析.py")

else:
    st.info("📭 競合データがありません。「競合を追加」ボタンから始めましょう。")

# AIサイドバー
if settings.get_api_key(settings.get_provider()):
    context = f"プロジェクト: {project.get('name')}\n競合数: {len(competitors)}"
    render_ai_sidebar(ai_provider, context)
