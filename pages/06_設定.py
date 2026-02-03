"""
設定ページ
- LLM設定（プロバイダ・モデル選択）
- APIキー状態確認
- メンバーAI管理
- タスク別モデル設定
"""
import streamlit as st
import sys
import uuid
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.storage_manager import StorageManager
from modules.ai_provider import AIProvider

# ページ設定
st.set_page_config(
    page_title="設定 - ProductDev",
    page_icon="⚙️",
    layout="wide"
)

# インスタンス (キャッシュを強制更新するためにキーを追加)
from modules.manager_factory import get_managers

# インスタンス取得
settings, data_store, storage_manager, ai_provider = get_managers()

# session_state初期化（メンバーAI用）
if "member_form_data" not in st.session_state:
    st.session_state.member_form_data = {}
if "member_generated" not in st.session_state:
    st.session_state.member_generated = False

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
tab1, tab2, tab3, tab4 = st.tabs(["LLM設定", "APIキー", "メンバーAI", "使用状況"])

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

# メンバーAIタブ
with tab3:
    st.subheader("メンバーAI設定")
    st.caption("商品企画を独自の視点で評価するAIメンバーを管理します")

    sub_tab1, sub_tab2 = st.tabs(["メンバー一覧", "新規作成"])

    # 1. メンバー一覧
    with sub_tab1:
        members = data_store.get_employee_personas()
        if not members:
            st.info("登録済みのメンバーはいません。「新規作成」タブからメンバーを追加してください。")
        else:
            for member in members:
                with st.expander(f"👤 {member.get('name') or '無名'}", expanded=False):
                    col_img, col_info = st.columns([1, 3])
                    with col_img:
                        avatar_url = member.get("avatar_url")
                        if avatar_url:
                            st.image(avatar_url, width=120)
                        else:
                            st.markdown("🧑💼")
                            st.caption("No Image")
                    
                    with col_info:
                        # 基本情報をカード形式で表示
                        st.markdown(f"**基本属性:** {member.get('demographic') or '未設定'}")
                        st.markdown(f"**評価の重点:** {member.get('evaluation_perspective') or '未設定'}")
                        st.markdown(f"**性格・口調:** {member.get('personality_traits') or '未設定'}")
                    
                    # 詳細情報（折りたたみ内の追加情報）
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**悩み・課題:** {member.get('pain_points') or '-'}")
                        st.markdown(f"**情報リテラシー:** {member.get('info_literacy') or '-'}")
                        st.markdown(f"**購入の決め手:** {member.get('purchase_trigger') or '-'}")
                        st.markdown(f"**ライフスタイル:** {member.get('lifestyle') or '-'}")
                    with col2:
                        st.markdown(f"**価値観・関心:** {member.get('psychographic') or '-'}")
                        st.markdown(f"**購買行動:** {member.get('buying_behavior') or '-'}")
                        st.markdown(f"**NGポイント:** {member.get('ng_points') or '-'}")
                    
                    # 削除ボタン
                    st.markdown("---")
                    if st.button(f"🗑️ このメンバーを削除", key=f"del_{member['id']}", type="secondary"):
                        if data_store.delete_employee_persona(member['id']):
                            st.success(f"削除しました: {member.get('name')}")
                            st.rerun()

    # 2. 新規作成（統合フロー）
    with sub_tab2:
        st.markdown("### 新規メンバー作成")
        st.caption("アンケートに回答 → AIがプロフィール生成 → 確認・編集 → 保存")
        
        # ========== STEP 1: アンケート ==========
        st.markdown("#### Step 1: アンケート回答")
        st.caption("1〜6で回答してください（1: 全く思わない ⇔ 6: 強く思う）")
        
        questions = [
            "新しいガジェットが好きだ", "商品の見た目より機能を重視する", "口コミを必ずチェックする",
            "ブランド品には目がない", "価格が安ければ品質は二の次だ", "限定品という言葉に弱い",
            "SNSで流行っているものを買う", "長く使えるものを好む", "衝動買いをよくする",
            "エコや倫理的な配慮を重視する", "使いやすさ（UI）が重要だ", "サポートの充実が不可欠だ",
            "コスパ最高なものを探すのが得意", "デザインが良ければ高くても買う", "新しいサービスはすぐ試す",
            "自分だけのこだわりがある", "家族の意見を重視する", "機能はシンプルな方がいい",
            "自分へのご褒美をよく買う", "投資だと思って高いものを買う"
        ]
        
        # 2列でスライダー表示
        col_left, col_right = st.columns(2)
        survey_answers = []
        for i, q in enumerate(questions):
            target_col = col_left if i % 2 == 0 else col_right
            with target_col:
                ans = st.slider(f"Q{i+1}: {q}", 1, 6, 3, key=f"survey_q_{i}")
                survey_answers.append(f"{q}: {ans}")
        
        # 自由記述（任意）
        st.markdown("#### 補足情報（任意）")
        free_text = st.text_area(
            "その他、このメンバーの特徴があれば記入してください",
            placeholder="例：30代女性、子供2人の共働き主婦。時短商品に興味がある。",
            key="free_text_input"
        )
        
        # メンバー名
        member_name = st.text_input("メンバー名", "AIメンバーA", key="new_member_name")
        
        # ========== STEP 2: AI生成ボタン ==========
        st.markdown("---")
        st.markdown("#### Step 2: プロフィール生成")
        
        if st.button("🤖 プロフィールを自動生成", type="primary", use_container_width=True):
            with st.spinner("AIがプロフィールを構築中..."):
                survey_text = "\n".join(survey_answers)
                additional = f"\n\n【補足情報】\n{free_text}" if free_text else ""
                
                prompt = f"""
以下の20問のアンケート結果（1:全く思わない〜6:強く思う）を元に、
商品企画を評価する「メンバーペルソナ」を詳細に作成してください。
回答者の特性を分析し、具体的で深みのある人物像にしてください。

【アンケート結果】
{survey_text}
{additional}

以下の項目を日本語のJSON形式で出力してください（各項目は50〜100文字程度で具体的に）：
- evaluation_perspective (評価の重点: この人が商品を見るときに最も重視するポイント)
- personality_traits (性格・口調: 話し方や性格の特徴)
- pain_points (悩み・課題: 日常で感じている不満や解決したい問題)
- info_literacy (情報リテラシー: 情報収集の仕方やITスキル)
- purchase_trigger (購入の決め手: 最終的に購入を決めるポイント)
- lifestyle (ライフスタイル: 日常の過ごし方)
- psychographic (価値観・関心: 大切にしていること、興味のある分野)
- demographic (基本属性: 年代、性別、職業、家族構成など)
- buying_behavior (購買行動: どこで何をどう買うか)
- ng_points (NGポイント: 絶対に許せない・買わない条件)

JSONのみを出力してください。説明文は不要です。
"""
                try:
                    res_text = ai_provider.generate_with_retry(prompt, task="atomize")
                    # JSON抽出
                    if "```json" in res_text:
                        res_text = res_text.split("```json")[1].split("```")[0]
                    elif "```" in res_text:
                        res_text = res_text.split("```")[1].split("```")[0]
                    
                    persona_data = json.loads(res_text.strip())
                    persona_data["name"] = member_name
                    
                    # session_stateに保存（フォームのvalueに反映される）
                    st.session_state.member_form_data = persona_data
                    st.session_state.member_generated = True
                    
                    st.success("✅ プロフィールを生成しました！下記で確認・編集してください。")
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"JSON解析エラー: {e}")
                    st.text("AI応答:")
                    st.code(res_text)
                except Exception as e:
                    st.error(f"生成エラー: {e}")
        
        # ========== STEP 3〜5: 確認・編集・保存フォーム ==========
        st.markdown("---")
        st.markdown("#### Step 3: 確認・編集 → 保存")
        
        if st.session_state.member_generated:
            st.info("💡 生成されたプロフィールを確認し、必要に応じて編集してください。")
        else:
            st.caption("プロフィール生成後、ここに結果が表示されます。手動で入力することも可能です。")
        
        # フォームデータ取得
        emp_to_edit = st.session_state.get('member_form_data', {})
        
        # st.form() を使用（LP Generatorと同じ方式）
        with st.form("member_profile_form", clear_on_submit=False):
            # 名前
            edit_name = st.text_input(
                "名前（必須）", 
                value=emp_to_edit.get("name", "")
            )
            
            col1, col2 = st.columns(2)
            with col1:
                edit_demographic = st.text_input(
                    "基本属性",
                    value=emp_to_edit.get("demographic", ""),
                    placeholder="例: 30代後半、女性、会社員、既婚・子供2人"
                )
                edit_eval = st.text_area(
                    "評価の重点",
                    value=emp_to_edit.get("evaluation_perspective", ""),
                    height=80
                )
                edit_traits = st.text_area(
                    "性格・口調",
                    value=emp_to_edit.get("personality_traits", ""),
                    height=80
                )
                edit_pains = st.text_area(
                    "悩み・課題",
                    value=emp_to_edit.get("pain_points", ""),
                    height=80
                )
                edit_literacy = st.text_input(
                    "情報リテラシー",
                    value=emp_to_edit.get("info_literacy", "")
                )
            
            with col2:
                edit_trigger = st.text_input(
                    "購入の決め手",
                    value=emp_to_edit.get("purchase_trigger", "")
                )
                edit_life = st.text_area(
                    "ライフスタイル",
                    value=emp_to_edit.get("lifestyle", ""),
                    height=80
                )
                edit_psycho = st.text_area(
                    "価値観・関心",
                    value=emp_to_edit.get("psychographic", ""),
                    height=80
                )
                edit_behavior = st.text_area(
                    "購買行動",
                    value=emp_to_edit.get("buying_behavior", ""),
                    height=80
                )
                edit_ng = st.text_area(
                    "NGポイント",
                    value=emp_to_edit.get("ng_points", ""),
                    height=80
                )
            
            # 画像アップロード（フォーム内）
            st.markdown("---")
            st.markdown("**アバター画像（任意）**")
            avatar_file = st.file_uploader(
                "プロフィール画像をアップロード",
                type=["jpg", "png", "jpeg"]
            )
            
            # 保存ボタン
            st.markdown("---")
            submitted = st.form_submit_button("💾 メンバーを保存", type="primary", use_container_width=True)
            
            if submitted:
                if not edit_name:
                    st.error("名前は必須です")
                else:
                    # 画像アップロード処理
                    avatar_url = ""
                    if avatar_file:
                        path = f"avatars/{uuid.uuid4()}_{avatar_file.name}"
                        avatar_url = storage_manager.upload_file(avatar_file, path)
                    
                    # データ作成
                    new_member = {
                        "name": edit_name,
                        "evaluation_perspective": edit_eval,
                        "personality_traits": edit_traits,
                        "pain_points": edit_pains,
                        "info_literacy": edit_literacy,
                        "purchase_trigger": edit_trigger,
                        "lifestyle": edit_life,
                        "psychographic": edit_psycho,
                        "demographic": edit_demographic,
                        "buying_behavior": edit_behavior,
                        "ng_points": edit_ng,
                        "avatar_url": avatar_url
                    }
                    
                    result = data_store.add_employee_persona(new_member)
                    if result:
                        st.success(f"✅ メンバー「{edit_name}」を保存しました！")
                        # フォームリセット
                        st.session_state.member_form_data = {}
                        st.session_state.member_generated = False
                        st.rerun()
                    else:
                        st.error("保存に失敗しました")
        
        # リセットボタン（フォーム外）
        if st.button("🔄 フォームをリセット"):
            st.session_state.member_form_data = {}
            st.session_state.member_generated = False
            st.rerun()

# 使用状況タブ
with tab4:
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
