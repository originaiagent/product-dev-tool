"""
設定ページ
- LLM設定（プロバイダ・モデル選択）
- APIキー状態確認
- タスク別モデル設定
"""
import streamlit as st
import sys
import uuid
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
@st.cache_resource(ttl=3600)
def get_managers_v2():
    settings = SettingsManager()
    data_store = DataStore()
    storage_manager = StorageManager()
    ai_provider = AIProvider(settings)
    return settings, data_store, storage_manager, ai_provider

settings, data_store, storage_manager, ai_provider = get_managers_v2()

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
    # ... (existing content is same)
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

    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["メンバー一覧", "AIかんたん作成", "手動登録"])

    # 1. メンバー一覧
    with sub_tab1:
        members = data_store.get_employee_personas()
        if not members:
            st.info("登録済みのメンバーはいません")
        else:
            for member in members:
                with st.expander(f"{member.get('name') or '無名'} ({member.get('demographic') or '未設定'})"):
                    col_img, col_info = st.columns([1, 4])
                    with col_img:
                        avatar_url = member.get("avatar_url")
                        if avatar_url:
                            st.image(avatar_url, width=100)
                        else:
                            st.write("No Image")
                    with col_info:
                        st.markdown(f"**評価の重点:** {member.get('evaluation_perspective')}")
                        st.markdown(f"**性格・口調:** {member.get('personality_traits')}")
                        
                        col_edit, col_del = st.columns(2)
                        with col_del:
                            if st.button(f"削除: {member.get('name')}", key=f"del_{member['id']}", type="secondary"):
                                if data_store.delete_employee_persona(member['id']):
                                    st.success(f"削除しました: {member.get('name')}")
                                    st.rerun()

    # 2. AIかんたん作成
    with sub_tab2:
        st.write("20問の簡単な質問に答えるだけで、AIが詳細なプロフィールを生成します")
        questions = [
            "新しいガジェットが好きだ", "商品の見た目より機能を重視する", "口コミを必ずチェックする",
            "ブランド品には目がない", "価格が安ければ品質は二の次だ", "限定品という言葉に弱い",
            "SNSで流行っているものを買う", "長く使えるものを好む", "衝動買いをよくする",
            "エコや倫理的な配慮を重視する", "使いやすさ（UI）が重要だ", "サポートの充実が不可欠だ",
            "コスパ最高なものを探すのが得意", "デザインが良ければ高くても買う", "新しいサービスはすぐ試す",
            "自分だけのこだわりがある", "家族の意見を重視する", "機能はシンプルな方がいい",
            "自分へのご褒美をよく買う", "投資だと思って高いものを買う"
        ]
        
        survey_answers = []
        for i, q in enumerate(questions):
            ans = st.slider(f"Q{i+1}: {q}", 1, 6, 3, key=f"q_{i}")
            survey_answers.append(f"{q}: {ans}")

        member_name = st.text_input("メンバー名", "AIメンバーA", key="auto_name")
        
        if st.button("プロフィールを自動生成", type="primary"):
            with st.spinner("AIがプロフィールを構築中..."):
                survey_text = "\n".join(survey_answers)
                prompt = f"""
                以下の20問のアンケート結果（1:全く思わない〜6:強く思う）を元に、
                商品企画を評価する「メンバーペルソナ」を詳細に作成してください。
                回答者の特性を分析し、具体的で深みのある人物像にしてください。

                【アンケート結果】
                {survey_text}

                以下の項目を日本語のJSON形式で出力してください：
                - evaluation_perspective (評価の重点)
                - personality_traits (性格・口調)
                - pain_points (悩み・課題)
                - info_literacy (情報リテラシー)
                - purchase_trigger (購入の決め手)
                - lifestyle (ライフスタイル)
                - psychographic (価値観・関心)
                - demographic (基本属性)
                - buying_behavior (購買行動)
                - ng_points (NGポイント)
                """
                try:
                    import json
                    res_text = ai_provider.generate_with_retry(prompt, task="atomize")
                    # JSON抽出
                    if "```json" in res_text:
                        res_text = res_text.split("```json")[1].split("```")[0]
                    persona_data = json.loads(res_text)
                    persona_data["name"] = member_name
                    
                    added = data_store.add_employee_persona(persona_data)
                    st.success(f"メンバー「{member_name}」を作成しました！")
                    st.json(persona_data)
                    st.rerun()
                except Exception as e:
                    st.error(f"生成エラー: {e}")

    # 3. 手動登録
    with sub_tab3:
        with st.form("manual_member_form"):
            name = st.text_input("名前（必須）")
            eval_p = st.text_area("評価の重点")
            traits = st.text_area("性格・口調")
            pains = st.text_area("悩み・課題")
            literacy = st.text_input("情報リテラシー")
            trigger = st.text_input("購入の決め手")
            life = st.text_area("ライフスタイル")
            psycho = st.text_area("価値観・関心")
            demo = st.text_input("基本属性")
            behavior = st.text_area("購買行動")
            ng = st.text_area("NGポイント")
            
            avatar_file = st.file_uploader("アバター画像", type=["jpg", "png", "jpeg"])
            
            submitted = st.form_submit_button("登録", type="primary")
            if submitted:
                if not name:
                    st.error("名前は必須です")
                else:
                    avatar_url = ""
                    if avatar_file:
                        path = f"avatars/{uuid.uuid4()}_{avatar_file.name}"
                        avatar_url = storage_manager.upload_file(avatar_file, path)
                    
                    new_member = {
                        "name": name,
                        "evaluation_perspective": eval_p,
                        "personality_traits": traits,
                        "pain_points": pains,
                        "info_literacy": literacy,
                        "purchase_trigger": trigger,
                        "lifestyle": life,
                        "psychographic": psycho,
                        "demographic": demo,
                        "buying_behavior": behavior,
                        "ng_points": ng,
                        "avatar_url": avatar_url
                    }
                    data_store.add_employee_persona(new_member)
                    st.success(f"メンバー「{name}」を登録しました")
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
