"""
差別化検討ページ
- AI差別化案生成
- 選択UI（2列カード）
- ポジショニングマップ
"""
import streamlit as st
import sys
import json
import pandas as pd
import altair as alt
import plotly.graph_objects as go
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.manager_factory import get_managers
from modules.prompt_manager import PromptManager
from modules.ai_sidebar import render_ai_sidebar
from modules.utils import parse_json_response

# ページ設定
st.set_page_config(
    page_title="差別化検討 - ProductDev",
    page_icon="💡",
    layout="wide"
)

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
st.title("💡 差別化検討")
st.caption("差別化案を選択・組み合わせ")

# レビュー分析データの取得
review_analysis = data_store.get_review_analysis(project_id)

if review_analysis and review_analysis.get("raw_data"):
    st.subheader("📊 レビューキーワード分析")
    
    raw_data = review_analysis.get("raw_data", {})
    raw_text = raw_data.get("text", "")
    
    # テキストからデータをパース（テーブル形式を想定）
    # | カテゴリ | コア要素 | YSAGi | PLUS(プラス) | amesoba | ...
    lines = raw_text.strip().split('\n')
    
    if len(lines) > 2:  # ヘッダー + 区切り + データ
        # ヘッダー解析
        header_line = lines[0]
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        # 競合名を取得（3列目以降）
        competitor_names = headers[2:] if len(headers) > 2 else []
        
        # データ解析
        keyword_data = []
        for line in lines[2:]:  # 区切り行をスキップ
            if '|' in line and '---' not in line:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if len(cells) >= 3:
                    keyword = cells[1] if len(cells) > 1 else cells[0]  # コア要素
                    values = {}
                    for i, comp in enumerate(competitor_names):
                        try:
                            val = int(cells[i + 2]) if i + 2 < len(cells) else 0
                        except:
                            val = 0
                        values[comp] = val
                    keyword_data.append({"keyword": keyword, **values})
        
        if keyword_data:
            df = pd.DataFrame(keyword_data)
            
            # タブで切り替え
            tab1, tab2 = st.tabs(["📊 キーワードTOP10", "🎯 競合別レーダー"])
            
            with tab1:
                # 横棒グラフ：キーワード別合計TOP10
                df_melted = df.melt(id_vars=['keyword'], var_name='competitor', value_name='count')
                df_total = df_melted.groupby('keyword')['count'].sum().reset_index()
                df_total = df_total.sort_values('count', ascending=False).head(10)
                
                chart = alt.Chart(df_total).mark_bar().encode(
                    x=alt.X('count:Q', title='出現数（全競合合計）'),
                    y=alt.Y('keyword:N', sort='-x', title='キーワード'),
                    color=alt.value('#3b82f6'),
                    tooltip=['keyword', 'count']
                ).properties(
                    height=400
                )
                st.altair_chart(chart, use_container_width=True)
                st.caption("顧客が重視しているキーワードTOP10")
            
            with tab2:
                # Plotlyでレーダーチャート
                import plotly.graph_objects as go
                
                st.markdown("#### 競合別キーワード構成比（レーダーチャート）")
                st.caption("各競合のレビュー内でのキーワード出現割合（正規化済み）")
                
                # 上位6キーワードに絞る
                df_melted = df.melt(id_vars=['keyword'], var_name='competitor', value_name='count')
                top_keywords = df_melted.groupby('keyword')['count'].sum().nlargest(6).index.tolist()
                df_top = df[df['keyword'].isin(top_keywords)]
                
                # 各競合の合計を計算して正規化
                competitor_cols = [c for c in df_top.columns if c != 'keyword']
                totals = {col: df[col].sum() for col in competitor_cols}  # 全キーワードの合計
                
                # レーダーチャート作成
                fig = go.Figure()
                
                colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
                
                for i, comp in enumerate(competitor_cols[:6]):  # 最大6競合
                    if totals[comp] > 0:
                        values = []
                        for keyword in top_keywords:
                            row = df_top[df_top['keyword'] == keyword]
                            if not row.empty:
                                val = row[comp].values[0] / totals[comp] * 100
                                values.append(round(val, 1))
                            else:
                                values.append(0)
                        
                        # 閉じるために最初の値を最後に追加
                        values.append(values[0])
                        keywords_closed = top_keywords + [top_keywords[0]]
                        
                        fig.add_trace(go.Scatterpolar(
                            r=values,
                            theta=keywords_closed,
                            fill='toself',
                            name=comp,
                            line_color=colors[i % len(colors)],
                            opacity=0.7
                        ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, max(30, max([max(trace.r) for trace in fig.data]) + 5) if fig.data else 30]
                        )
                    ),
                    showlegend=True,
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.info("💡 面積が大きいキーワード = その競合のレビューで特に言及されやすい要素")
        else:
            st.warning("データを解析できませんでした")
    else:
        st.info("レビュー分析データがありません。先にレビュー分析ページでデータをアップロードしてください。")
else:
    st.info("📝 レビュー分析データがありません。先にレビュー分析ページでデータをアップロードしてください。")

st.markdown("---")

# フィルター・ソート
col_filter1, col_filter2, col_sort = st.columns([2, 2, 2])
with col_filter1:
    pattern_filter = st.selectbox(
        "パターン",
        ["全パターン", "性能UP", "機能追加", "合体", "コスト削減"],
        label_visibility="collapsed"
    )
with col_filter2:
    difficulty_filter = st.selectbox(
        "難易度",
        ["全難易度", "低", "中", "高"],
        label_visibility="collapsed"
    )
with col_sort:
    sort_by = st.selectbox(
        "並び替え",
        ["有効度順", "コスト順", "期間順"],
        label_visibility="collapsed"
    )

# AI生成ボタン
col_gen, col_space = st.columns([1, 3])
with col_gen:
    if st.button("🤖 AIで再生成", type="primary"):
        with st.spinner("差別化案を生成中...（30〜50件）"):
            try:
                # 競合データ取得
                competitors = data_store.list_by_parent("competitors", project_id)
                competitors_text = json.dumps([{
                    "name": c.get("name"),
                    "extracted_data": c.get("extracted_data", {})
                } for c in competitors], ensure_ascii=False)
                
                # レビューデータ取得
                reviews_data = data_store.list_by_parent("reviews", project_id)
                reviews_text = json.dumps(reviews_data[0] if reviews_data else {}, ensure_ascii=False)
                
                # プロンプト
                diff_prompt = prompt_manager.load("differentiate")
                if not diff_prompt:
                    diff_prompt = prompt_manager.get_default("differentiate")
                
                diff_prompt = diff_prompt.replace("{{competitors}}", competitors_text)
                diff_prompt = diff_prompt.replace("{{reviews}}", reviews_text)
                
                # AI呼び出し
                response = ai_provider.generate_with_retry(
                    prompt=diff_prompt,
                    task="differentiate"
                )
                
                # JSON抽出
                try:
                    ideas_data = parse_json_response(response)
                except ValueError:
                    st.error("AI応答の解析に失敗しました")
                    # デバッグ用
                    # st.text(response)
                    ideas_data = {"ideas": []}
                
                ideas = ideas_data.get("ideas", [])
                
                # 既存削除→新規作成
                existing = data_store.list_by_parent("ideas", project_id)
                for ex in existing:
                    data_store.delete("ideas", ex["id"])
                
                for idea in ideas:
                    idea["project_id"] = project_id
                    idea["selected"] = False
                    data_store.create("ideas", idea)
                
                st.success(f"✅ {len(ideas)}件の差別化案を生成しました")
                st.rerun()
                
            except Exception as e:
                st.error(f"エラー: {str(e)}")

st.markdown("---")

# 差別化案一覧
ideas = data_store.list_by_parent("ideas", project_id)

# フィルタリング
if pattern_filter != "全パターン":
    ideas = [i for i in ideas if i.get("pattern") == pattern_filter]
if difficulty_filter != "全難易度":
    ideas = [i for i in ideas if i.get("difficulty") == difficulty_filter]

# ソート
if sort_by == "有効度順":
    ideas = sorted(ideas, key=lambda x: x.get("effectiveness", 0), reverse=True)
elif sort_by == "コスト順":
    ideas = sorted(ideas, key=lambda x: x.get("cost", "¥0"))
elif sort_by == "期間順":
    ideas = sorted(ideas, key=lambda x: x.get("time", ""))

# 選択状態管理
if "selected_ideas" not in st.session_state:
    st.session_state.selected_ideas = set()

if ideas:
    # 2列カード表示
    cols = st.columns(2)
    for i, idea in enumerate(ideas):
        with cols[i % 2]:
            idea_id = idea["id"]
            is_selected = idea_id in st.session_state.selected_ideas
            
            # カードスタイル
            border_color = "#2563eb" if is_selected else "#e2e8f0"
            bg_color = "#eff6ff" if is_selected else "white"
            
            # 難易度カラー
            diff_colors = {"低": "#22c55e", "中": "#eab308", "高": "#ef4444"}
            diff_color = diff_colors.get(idea.get("difficulty", "中"), "#64748b")
            
            with st.container():
                st.markdown(f"""
                <div style="background: {bg_color}; border: 2px solid {border_color}; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; gap: 0.5rem; align-items: flex-start;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 0.5rem 0; font-size: 0.875rem;">{idea.get('title', '無題')}</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 0.25rem; margin-bottom: 0.5rem;">
                                <span style="background: #dbeafe; color: #1e40af; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">
                                    {idea.get('pattern', '')}
                                </span>
                                <span style="background: {diff_color}20; color: {diff_color}; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem;">
                                    {idea.get('difficulty', '')}
                                </span>
                                <span style="background: #1e293b; color: white; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">
                                    {idea.get('effectiveness', 0)}
                                </span>
                            </div>
                            <p style="font-size: 0.75rem; color: #64748b; margin: 0 0 0.25rem 0;">
                                {'📊' if idea.get('eff_type') == 'manifest' else '🔮'} {', '.join(idea.get('eff_reasons', [])[:2])}
                            </p>
                            <p style="font-size: 0.75rem; color: #64748b; margin: 0;">
                                💴 {idea.get('cost', '-')} ⏱ {idea.get('time', '-')}
                            </p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # 選択チェックボックス
                if st.checkbox("選択", value=is_selected, key=f"select_{idea_id}"):
                    st.session_state.selected_ideas.add(idea_id)
                else:
                    st.session_state.selected_ideas.discard(idea_id)
    
    # ポジショニングマップ
    st.markdown("---")
    st.subheader("📍 ポジショニングマップ")
    st.caption("選択した差別化で自社の位置が変わります")
    
    # 競合データ取得
    competitors = data_store.list_by_parent("competitors", project_id)
    
    # ポジショニング図（Plotly）
    fig = go.Figure()
    
    # 競合プロット
    colors = ["#ef4444", "#f97316", "#eab308", "#22c55e"]
    for i, comp in enumerate(competitors[:4]):
        fig.add_trace(go.Scatter(
            x=[50 + (i * 15) % 40],
            y=[40 + (i * 20) % 50],
            mode="markers+text",
            name=comp.get("name", f"競合{i+1}"),
            marker=dict(size=20, color=colors[i % len(colors)]),
            text=[comp.get("name", "")],
            textposition="top center"
        ))
    
    # 自社プロット（選択した差別化に応じて調整）
    target_x = 40
    target_y = 65
    if st.session_state.selected_ideas:
        # 選択した差別化の有効度に応じてY軸を上げる
        selected = [i for i in ideas if i["id"] in st.session_state.selected_ideas]
        total_eff = sum(i.get("effectiveness", 0) for i in selected)
        target_y = min(95, 50 + total_eff / 10)
    
    fig.add_trace(go.Scatter(
        x=[target_x],
        y=[target_y],
        mode="markers+text",
        name="自社目標",
        marker=dict(size=25, color="#2563eb", line=dict(width=3, color="white")),
        text=["自社"],
        textposition="top center"
    ))
    
    fig.update_layout(
        xaxis=dict(title="価格（低←→高）", range=[0, 100], showgrid=True, gridcolor="#e2e8f0"),
        yaxis=dict(title="機能性（シンプル←→高機能）", range=[0, 100], showgrid=True, gridcolor="#e2e8f0"),
        height=400,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("📭 差別化案がありません。「AIで再生成」ボタンから生成しましょう。")

# 下部固定バー
st.markdown("---")
selected_count = len(st.session_state.selected_ideas)
selected_ideas_list = [i for i in ideas if i["id"] in st.session_state.selected_ideas]

# 合計計算
total_effectiveness = sum(i.get("effectiveness", 0) for i in selected_ideas_list)

col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
with col1:
    st.metric("選択中", f"{selected_count}件")
with col2:
    st.metric("合計コスト", "計算中" if selected_count > 0 else "-")
with col3:
    st.metric("期間", "計算中" if selected_count > 0 else "-")
with col4:
    st.metric("有効度計", f"{total_effectiveness}" if selected_count > 0 else "-")
with col5:
    if st.button("✓ 差別化を確定", type="primary", use_container_width=True, disabled=selected_count == 0):
        # 選択を保存
        for idea in ideas:
            is_selected = idea["id"] in st.session_state.selected_ideas
            data_store.update("ideas", idea["id"], {"selected": is_selected})
        
        data_store.update("projects", project_id, {"phase": "完了", "progress": 100})
        st.success("✅ 差別化を確定しました！")

# ナビゲーション
st.markdown("---")
if st.button("← レビュー分析に戻る"):
    st.switch_page("pages/03_レビュー分析.py")

# AIサイドバー
if settings.get_api_key(settings.get_provider()):
    context = f"プロジェクト: {project.get('name')}\n差別化案: {len(ideas)}件"
    render_ai_sidebar(ai_provider, context)
