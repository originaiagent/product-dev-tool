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
from urllib.parse import unquote
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.ai_provider import AIProvider
from modules.prompt_manager import PromptManager
from modules.ai_sidebar import render_ai_sidebar
from modules.file_processor import FileProcessor
from modules.utils import parse_json_response
from modules.storage_manager import StorageManager

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
storage_manager = StorageManager()

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
            # reviews = st.number_input("レビュー数", min_value=0, value=0) # 削除
            sales = st.number_input("月間売上（万円）", min_value=0, value=0)
        with col_b:
            units = st.number_input("月間販売数", min_value=0, value=0)
        with col_c:
             st.empty() # レイアウト調整

        st.markdown("###### 評価指標 (1:弱い 〜 5:強い)")
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        with col_m1:
            seller_strength = st.selectbox("セラー強さ", [1, 2, 3, 4, 5], index=2)
        with col_m2:
            brand_power = st.selectbox("ブランド力", [1, 2, 3, 4, 5], index=2)
        with col_m3:
            specialization = st.selectbox("専門店化", [1, 2, 3, 4, 5], index=2)
        with col_m4:
            page_quality = st.selectbox("ページクオリティ", [1, 2, 3, 4, 5], index=2)
        with col_m5:
            review_power = st.selectbox("レビューパワー", [1, 2, 3, 4, 5], index=2)
        
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
                #"reviews": reviews, # 削除
                "sales": sales * 10000 if sales else None,
                "units": units if units else None,
                "images": [],
                "image_urls": [],
                "text_info": "",
                "extracted_data": {
                    "seller_strength": seller_strength,
                    "brand_power": brand_power,
                    "specialization": specialization,
                    "page_quality": page_quality,
                    "review_power": review_power,
                }
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
                
                # ファイルアップロード（拡張版）
                uploaded_files = st.file_uploader(
                    "ファイルをアップロード（画像・PDF・Excel・CSV等、最大30ファイル）",
                    type=FileProcessor.get_all_extensions(),
                    accept_multiple_files=True,
                    key=f"files_{comp['id']}"
                )
                
                if uploaded_files:
                    # ファイルを処理
                    processed_files = []
                    images_b64 = []
                    all_text = []
                    
                    for file in uploaded_files[:30]:
                        result = FileProcessor.process_file(file)
                        processed_files.append(result)
                        
                        # 画像の場合はStorageにアップロード
                        if result.get("type") == "image":
                            # base64があればプレビュー用に保持（UI応答性のため）
                            if result.get("base64"):
                                images_b64.append(result["base64"])
                            
                            # Supabase Storageへアップロード
                            path = f"competitors/{comp['id']}/{file.name}"
                            # fileはStreamlitのUploadedFileなのでそのまま渡せる
                            # カーソルをリセット
                            file.seek(0)
                            url = storage_manager.upload_file(file, path, content_type=file.type)
                            if url:
                                if "image_urls" not in comp:
                                    comp["image_urls"] = []
                                if url not in comp.get("image_urls", []):
                                    comp.setdefault("image_urls", []).append(url)
                        
                        # テキスト情報があれば収集
                        if result.get("text"):
                            all_text.append(f"--- {result['filename']} ---\n{result['text']}")
                    
                    # データを更新
                    update_data = {
                        "images": images_b64,  # 後方互換性と即時表示用（将来的に廃止可）
                        "image_urls": comp.get("image_urls", [])
                    }
                    if all_text:
                        # 既存のテキスト情報とマージ
                        extracted_text = "\n\n".join(all_text)
                        update_data["extracted_text"] = extracted_text
                    
                    data_store.update("competitors", comp["id"], update_data)
                    
                    # サマリー表示
                    summary = FileProcessor.create_summary(processed_files)
                    st.caption(summary)
                
                # 保存された画像の表示
                saved_image_urls = comp.get("image_urls", [])
                if saved_image_urls:
                    st.markdown("###### 🖼️ 保存済み画像")
                    # カルーセル風あるいはグリッド表示
                    # スペースの都合上、Expanderにするか、小さく表示
                    with st.expander(f"画像 ({len(saved_image_urls)}枚)", expanded=False):
                        st.image(saved_image_urls, width=150, caption=[url.split("/")[-1] for url in saved_image_urls])
                
                # テキスト情報
                text_info = st.text_area(
                    "テキスト情報（商品ページからコピペ）",
                    value=comp.get("text_info", ""),
                    height=100,
                    key=f"text_{comp['id']}"
                )
                
                if text_info != comp.get("text_info", ""):
                    data_store.update("competitors", comp["id"], {"text_info": text_info})
                
                # AI抽出ボタンエリア
                col_extract, col_delete = st.columns([3, 1])
                with col_extract:
                    # target_audienceがanalysis内にあるかチェック
                    extracted = comp.get("extracted_data", {})
                    is_analyzed = False
                    if "analysis" in extracted:
                         is_analyzed = extracted["analysis"].get("target_audience") is not None
                    elif extracted.get("target_audience"): # 互換性のため
                         is_analyzed = True
                         
                    btn_label = "🔄 AIで再分析する" if is_analyzed else "🔍 AI詳細分析を実行"
                    btn_type = "secondary" if is_analyzed else "primary"
                    
                    if st.button(btn_label, key=f"extract_{comp['id']}", type=btn_type, use_container_width=True):
                        with st.spinner("AIが徹底分析中...（画像の枚数によっては時間がかかります）"):
                            try:
                                # プロンプト取得
                                prompt = prompt_manager.load("extract")
                                if not prompt:
                                    prompt = prompt_manager.get_default("extract")
                                
                                # 画像を準備
                                images = comp.get("images", [])
                                image_urls = comp.get("image_urls", [])
                                
                                # 画像データがない場合、URLから取得を試みる
                                if not images and image_urls:
                                    for url in image_urls[:5]: # 最大5枚
                                        try:
                                            # URLからパス部分を抽出
                                            path_part = url.split(f"/public/{storage_manager.BUCKET_NAME}/")[-1]
                                            path_part = unquote(path_part)
                                            img_bytes = storage_manager.get_file_bytes(path_part)
                                            if img_bytes:
                                                import base64
                                                b64_str = base64.b64encode(img_bytes).decode('utf-8')
                                                images.append(b64_str)
                                        except Exception as e:
                                            print(f"Error fetching image from storage: {e}")
                                
                                # テキスト情報を結合
                                combined_text = text_info
                                extracted_text = comp.get("extracted_text", "")
                                if extracted_text:
                                    combined_text += f"\n\n## ファイルから抽出した情報\n{extracted_text}"
                                
                                # AI呼び出し
                                response = ai_provider.generate_with_retry(
                                    prompt=f"{prompt}\n\n## テキスト情報\n{combined_text}",
                                    task="extract",
                                    images=images[:5] if images else None
                                )
                                
                                # JSONを抽出
                                try:
                                    extracted = parse_json_response(response)
                                    # 既存データを保持してマージ
                                    current_data = comp.get("extracted_data", {}) or {}
                                    if isinstance(current_data, dict):
                                        current_data.update(extracted)
                                    else:
                                        current_data = extracted
                                    
                                    data_store.update("competitors", comp["id"], {"extracted_data": current_data})
                                    st.success("✅ AI分析が完了しました！")
                                    st.rerun()
                                except ValueError:
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
                    
                    # 分析済みステータス
                    if "analysis" in extracted:
                        st.caption("✅ 詳細分析済み")
                    else:
                        st.caption("⚠️ 未分析または旧形式データ")

                    # 5指標（再掲） - これはフラットなレベルで保存されていると仮定
                    m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
                    with m_col1:
                        st.metric("セラー強さ", extracted.get("seller_strength", "-"))
                    with m_col2:
                        st.metric("ブランド力", extracted.get("brand_power", "-"))
                    with m_col3:
                        st.metric("専門店化", extracted.get("specialization", "-"))
                    with m_col4:
                        st.metric("ページ", extracted.get("page_quality", "-"))
                    with m_col5:
                        st.metric("レビュー", extracted.get("review_power", "-"))
                    
                    if "basic" in extracted:
                        # タブ形式で詳細を表示
                        det_tab1, det_tab2, det_tab3, det_tab4 = st.tabs(["基本・スペック", "素材・構成", "セット・保証", "分析深掘り"])
                        
                        with det_tab1:
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                b = extracted.get("basic", {})
                                st.markdown(f"**ブランド**: {b.get('brand', '-')}")
                                st.markdown(f"**価格**: {b.get('price', '-')}")
                                st.markdown(f"**型番**: {b.get('model', '-')}")
                                st.markdown(f"**製造国**: {b.get('made_in', '-')}")
                            with col_b2:
                                d = extracted.get("dimensions", {})
                                st.markdown(f"**サイズ**: {d.get('size', '-')}")
                                st.markdown(f"**重量**: {d.get('weight', '-')}")
                            
                            st.markdown("---")
                            st.markdown("**性能・スペック:**")
                            s = extracted.get("specs", {})
                            scol1, scol2 = st.columns(2)
                            with scol1:
                                st.write(f"- 電源: {s.get('power', '-')}")
                                st.write(f"- バッテリー: {s.get('battery', '-')}")
                                st.write(f"- 防水: {s.get('waterproof', '-')}")
                            with scol2:
                                st.write(f"- 耐久性: {s.get('durability', '-')}")
                                st.write(f"- 騒音: {s.get('noise_level', '-')}")
                        
                        with det_tab2:
                            m = extracted.get("materials", {})
                            st.markdown(f"**主素材**: {m.get('main_material', '-')}")
                            st.markdown(f"**副素材**: {m.get('sub_materials', '-')}")
                            st.markdown(f"**表面加工**: {m.get('surface', '-')}")
                            st.markdown(f"**構造**: {m.get('structure', '-')}")
                        
                        with det_tab3:
                            col_p1, col_p2 = st.columns(2)
                            with col_p1:
                                p = extracted.get("package", {})
                                st.markdown("**付属品:**")
                                for acc in p.get("accessories", []):
                                    st.write(f"- {acc}")
                                st.markdown(f"**セット数**: {p.get('quantity', '-')}")
                            with col_p2:
                                sup = extracted.get("support", {})
                                st.markdown(f"**保証**: {sup.get('warranty', '-')}")
                                st.markdown(f"**サポート**: {sup.get('support', '-')}")
                        
                        with det_tab4:
                            a = extracted.get("analysis", {})
                            st.markdown(f"**USP (独自の売り)**: {a.get('usp', '-')}")
                            st.markdown(f"**ターゲット層**: {a.get('target_audience', '-')}")
                            
                            col_a1, col_a2 = st.columns(2)
                            with col_a1:
                                st.markdown("**強み:**")
                                for val in a.get("strengths", []):
                                    st.write(f"- {val}")
                            with col_a2:
                                st.markdown("**弱み:**")
                                for val in a.get("weaknesses", []):
                                    st.write(f"- {val}")
                            
                            st.markdown("**特徴一覧:**")
                            st.write(", ".join(a.get("features", [])))
                    else:
                        # 下位互換表示 (古いデータ)
                         if extracted.get("price"):
                            st.markdown(f"**価格**: {extracted.get('price')}")
                        
                         col_spec1, col_spec2 = st.columns(2)
                         with col_spec1:
                            st.markdown("**主な特徴:**")
                            for f in extracted.get("features", [])[:5]:
                                st.write(f"- {f}")
                            
                            if extracted.get("target_audience"):
                                st.markdown(f"**ターゲット層**: {extracted.get('target_audience')}")
    
                         with col_spec2:
                            st.markdown("**強み:**")
                            for s in extracted.get("strengths", []):
                                st.write(f"- {s}")
                            
                            st.markdown("**弱み:**")
                            # negatives または weaknesses
                            ws = extracted.get("weaknesses", []) or extracted.get("negatives", [])
                            for w in ws:
                                st.write(f"- {w}")
                
                st.markdown("---")
    
    # ガチ比較表
    # ガチ比較表
    st.markdown("---")
    st.subheader("📊 ガチ比較表")
    st.caption("全競合のAI分析結果をまとめて比較します")
    
    if st.button("📊 ガチ比較表を生成", type="primary", use_container_width=True):
        if len(competitors) > 0:
            # ヘッダー
            header_cols = ["項目", "自社目標"] + [c.get("name", "競合") for c in competitors]
            
            # テーブルデータ
            table_data = []
            
            # URL行
            url_row = ["URL", "-"] + [f"[🔗]({c.get('url', '#')})" if c.get('url') else "-" for c in competitors]
            
            # 価格行
            price_row = ["価格", "-"]
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                p = extracted.get("basic", {}).get("price") if "basic" in extracted else extracted.get("price")
                price_row.append(p or "-")
            
            # スペック行
            spec_rows = []
            for spec_key in ["weight", "size", "power"]:
                label = spec_key.replace("weight", "重量").replace("size", "サイズ").replace("power", "電源")
                row = [label, "-"]
                for comp in competitors:
                    extracted = comp.get("extracted_data", {})
                    # 新形式
                    if "dimensions" in extracted or "specs" in extracted:
                        val = extracted.get("dimensions", {}).get(spec_key) or extracted.get("specs", {}).get(spec_key)
                    else:
                        # 旧形式
                        val = extracted.get("specs", {}).get(spec_key) or extracted.get(spec_key)
                    row.append(val or "-")
                spec_rows.append(row)
            
            # 特徴、強み、弱み
            feature_row = ["主な特徴", "-"]
            strength_row = ["強み", "-"]
            weakness_row = ["弱み", "-"]
            
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                
                # 新旧両対応
                ana = extracted.get("analysis", {}) if "analysis" in extracted else extracted
                
                # 特徴
                features = ana.get("features", [])
                feature_row.append("<br>".join(features[:5]) if features else "-")
                
                # 強み
                strengths = ana.get("strengths", [])
                strength_row.append("<br>".join(strengths) if strengths else "-")
                
                # 弱み
                weaknesses = ana.get("weaknesses", []) or ana.get("negatives", [])
                weakness_row.append("<br>".join(weaknesses) if weaknesses else "-")
            
            # Markdown テーブル作成
            all_rows = [price_row] + spec_rows + [feature_row, strength_row, weakness_row]
            
            md_table = "| " + " | ".join(header_cols) + " |\n"
            md_table += "| " + " | ".join(["---"] * len(header_cols)) + " |\n"
            md_table += "| " + " | ".join(url_row) + " |\n" # URL行を追加
            
            for row in all_rows:
                md_table += "| " + " | ".join(str(cell).replace("\n", "<br>") for cell in row) + " |\n"
            
            st.markdown(md_table, unsafe_allow_html=True)
        else:
            st.warning("競合データがありません")
    
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
