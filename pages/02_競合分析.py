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

from modules.manager_factory import get_managers
from modules.prompt_manager import PromptManager
from modules.ai_sidebar import render_ai_sidebar
from modules.file_processor import FileProcessor
from modules.utils import parse_json_response

# ページ設定
st.set_page_config(
    page_title="競合分析 - ProductDev",
    page_icon="🔍",
    layout="wide"
)

# インスタンス
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
    for i, comp in enumerate(competitors):
        # 2つごとに新しいカラム行を作成（レイアウト崩れ防止）
        if i % 2 == 0:
            cols = st.columns(2)
        
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
                    if "product_info" in extracted or "features" in extracted:
                        st.caption("✅ 分析済み")
                    else:
                        st.caption("⚠️ 未分析")

                    # 5指標（再掲）
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
                    
                    if "product_info" in extracted or "features" in extracted or "specs" in extracted:
                        # 新形式の表示（徹底抽出版）
                        
                        # --- 基本情報 & スペック ---
                        col_info, col_spec = st.columns([1, 1])
                        
                        with col_info:
                            st.markdown("###### 📋 基本情報")
                            p_info = extracted.get("product_info", {})
                            if isinstance(p_info, dict) and p_info:
                                for k, v in p_info.items():
                                    st.write(f"- **{k}**: {v}")
                            else:
                                st.caption("情報なし")

                            # USPとターゲット（基本情報の下に配置）
                            if extracted.get("usp"):
                                st.info(f"✨ **USP**: {extracted.get('usp')}")
                            if extracted.get("target_audience"):
                                st.caption(f"🎯 ターゲット: {extracted.get('target_audience')}")

                        with col_spec:
                            st.markdown("###### ⚙️ スペック")
                            specs = extracted.get("specs", {})
                            if isinstance(specs, dict) and specs:
                                for k, v in specs.items():
                                    st.write(f"- **{k}**: {v}")
                            else:
                                st.caption("情報なし")
                        
                        # --- バリエーション & 付属品 ---
                        has_variations = extracted.get("variations")
                        has_accessories = extracted.get("accessories")
                        
                        if has_variations or has_accessories:
                            st.markdown("---")
                            col_var, col_acc = st.columns([1, 1])
                            
                            with col_var:
                                if has_variations:
                                    st.markdown("###### 🎨 バリエーション")
                                    vars = extracted.get("variations", {})
                                    if isinstance(vars, dict):
                                        for k, v in vars.items():
                                            if isinstance(v, list):
                                                st.write(f"- **{k}**: {', '.join(v)}")
                                            else:
                                                st.write(f"- **{k}**: {v}")
                            
                            with col_acc:
                                if has_accessories:
                                    st.markdown("###### 📦 付属品")
                                    accs = extracted.get("accessories", [])
                                    if isinstance(accs, list):
                                        for acc in accs:
                                            st.write(f"- {acc}")
                                    else:
                                        st.write(accs)

                        # --- 特徴 ---
                        st.markdown("---")
                        st.markdown("###### ✨ 特徴")
                        features = extracted.get("features", [])
                        if isinstance(features, list) and features:
                            # 数が多いのでExpanderにするか、あるいはスクロールで見るか
                            # 20個以上目標なので、最初の5個を表示し、残りをExpanderにするとか
                            if len(features) > 5:
                                for f in features[:5]:
                                    st.write(f"- {f}")
                                with st.expander(f"すべての特徴を見る ({len(features)}個)"):
                                    for f in features[5:]:
                                        st.write(f"- {f}")
                            else:
                                for f in features:
                                    st.write(f"- {f}")
                        else:
                            st.caption("特徴情報なし")

                    elif "basic" in extracted:
                        # 暫定：旧中間形式（タブ形式）も維持
                        st.info("旧形式のデータです。再分析を推奨します。")
                        det_tab1, det_tab2, det_tab3, det_tab4 = st.tabs(["基本・スペック", "素材・構成", "セット・保証", "分析深掘り"])
                        # ... (中略、必要なら残すが、ユーザーは「修正」を求めているのでシンプルにするなら削除もありだが、実行エラーを避けるために最小限に留める)
                        # ここではシンプルにするため、以前のタブ表示を簡略化して表示するか、
                        # ユーザーの「修正ください」に従い、新形式に特化したコードに置き換える。
                        # ただし、壊さないために。
                        with det_tab1: st.write(extracted.get("basic", {}))
                    else:
                        # 下位互換表示 (さらに古いデータ)
                         if extracted.get("price") and extracted.get("price") != "不明":
                            st.markdown(f"**価格**: {extracted.get('price')}")
                        
                         col_spec1, col_spec2 = st.columns(2)
                         with col_spec1:
                            st.markdown("**主な特徴:**")
                            for f in extracted.get("features", [])[:5]:
                                st.write(f"- {f}")
                
                st.markdown("---")
    
    # ガチ比較表
    st.markdown("---")
    st.subheader("📊 ガチ比較表")
    st.caption("全競合のAI分析結果をまとめて比較します")
    
    if st.button("📊 ガチ比較表を生成", type="primary", use_container_width=True):
        if len(competitors) > 0:
            # 全競合のキーを収集
            all_spec_keys = set()
            all_var_keys = set()
            all_info_keys = set()
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                all_spec_keys.update(extracted.get("specs", {}).keys())
                all_var_keys.update(extracted.get("variations", {}).keys())
                all_info_keys.update(extracted.get("product_info", {}).keys())
            
            # ヘッダー
            header_cols = ["比較項目"] + [c.get("name", "競合") for c in competitors]
            
            # テーブルデータを構築
            rows = []
            
            # URL行
            url_row = ["商品URL"] + [f"[🔗]({c.get('url', '#')})" if c.get('url') else "-" for c in competitors]
            rows.append(url_row)
            
            # product_info行（動的）
            for key in sorted(all_info_keys):
                info_row = [key]
                for comp in competitors:
                    extracted = comp.get("extracted_data", {})
                    val = extracted.get("product_info", {}).get(key, "-")
                    info_row.append(val if val else "-")
                rows.append(info_row)
            
            # specs行（動的）
            for key in sorted(all_spec_keys):
                spec_row = [key]
                for comp in competitors:
                    extracted = comp.get("extracted_data", {})
                    val = extracted.get("specs", {}).get(key, "-")
                    spec_row.append(val if val else "-")
                rows.append(spec_row)
            
            # variations行（動的）
            for key in sorted(all_var_keys):
                var_row = [key]
                for comp in competitors:
                    extracted = comp.get("extracted_data", {})
                    vals = extracted.get("variations", {}).get(key, [])
                    var_row.append(", ".join(vals) if vals else "-")
                rows.append(var_row)
            
            # 付属品行
            acc_row = ["付属品"]
            has_accessories = False
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                acc = extracted.get("accessories", [])
                if acc:
                    has_accessories = True
                acc_row.append(", ".join(acc) if acc else "-")
            if has_accessories:
                rows.append(acc_row)
            
            # USP行
            usp_row = ["USP（独自の強み）"]
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                usp_row.append(extracted.get("usp") or "-")
            rows.append(usp_row)
            
            # ターゲット行
            target_row = ["ターゲット層"]
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                target_row.append(extracted.get("target_audience") or "-")
            rows.append(target_row)
            
            # 特徴行（箇条書き、最大10個）
            feature_row = ["主な特徴"]
            for comp in competitors:
                extracted = comp.get("extracted_data", {})
                features = extracted.get("features", [])
                if features:
                    feature_row.append("・" + "・".join(features[:10]))
                else:
                    feature_row.append("-")
            rows.append(feature_row)
            
            # Markdown テーブル作成
            md_table = "| " + " | ".join(header_cols) + " |\n"
            md_table += "| " + " | ".join(["---"] * len(header_cols)) + " |\n"
            for row in rows:
                cells = [str(cell).replace("\n", " ").replace("|", "｜") for cell in row]
                md_table += "| " + " | ".join(cells) + " |\n"
            
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
