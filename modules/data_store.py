"""
データストアモジュール (Supabase対応版)
- Supabaseへのデータ保存・読込・削除
- トレーサビリティ（親子関係の管理）
"""
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import streamlit as st
from supabase import create_client, Client

class DataStore:
    """データ保存・管理クラス (Supabase) - v1.1 refresh"""
    
    # データタイプとSupabaseテーブル名のマッピング
    TABLE_MAPPING = {
        "projects": "projects",
        "competitors": "competitors",
        "reviews": "review_analysis",
        "ideas": "differentiation_ideas",
        "employee_personas": "employee_personas",
        "employee_feedback": "employee_feedback",
        "settings": "settings"
        # "positioning" は未使用のため除外
    }

    # 親子関係の定義 (削除時の連動用)
    DATA_HIERARCHY = {
        "projects": None,
        "competitors": "projects",
        "reviews": "projects",
        "ideas": "projects",
        "employee_feedback": "employee_personas"
    }
    
    def __init__(self, data_dir: Optional[str] = None):
        # data_dir引数は互換性のために残すが使用しない
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            # Streamlit Secretsからの読み込みを試みる（ローカル実行時など）
            try:
                url = st.secrets["SUPABASE_URL"]
                key = st.secrets["SUPABASE_KEY"]
            except:
                pass

        if not url or not key:
            st.error("Warning: SUPABASE_URL or SUPABASE_KEY not found. DataStore will be disabled.")
            print("Warning: SUPABASE_URL or SUPABASE_KEY not found.")
            self.supabase: Optional[Client] = None
        else:
            self.supabase: Client = create_client(url, key)
    
    def _get_table_name(self, data_type: str) -> Optional[str]:
        return self.TABLE_MAPPING.get(data_type)
    
    def create(self, data_type: str, data: Dict) -> Dict:
        """新規作成"""
        if not self.supabase:
            msg = f"Error: Supabase client is not initialized. Cannot create {data_type}."
            print(msg)
            st.error(msg)
            return None # 明示的に失敗を返す

        table = self._get_table_name(data_type)
        if not table:
            msg = f"Error: No table mapping found for {data_type}."
            print(msg)
            st.error(msg)
            return None
        
        # UUID付与 (Python側で生成して渡す)
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        # タイムスタンプ付与
        now = datetime.now().isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now
        
        try:
            print(f"DEBUG: Inserting into {table}: {data['id']}")
            response = self.supabase.table(table).insert(data).execute()
            if response.data:
                print(f"DEBUG: Successfully inserted {len(response.data)} rows.")
                return response.data[0]
            else:
                msg = f"DEBUG: Insert executed but returned no data. Table: {table}"
                print(msg)
                st.error(msg)
        except Exception as e:
            msg = f"Supabase Create Error ({table}): {e}"
            print(msg)
            st.error(msg)
            import traceback
            st.code(traceback.format_exc())
            return None # エラー時はNoneを返す
        
        return None # データが返らなかった場合
    
    def get(self, data_type: str, id: str) -> Optional[Dict]:
        """IDでデータを取得"""
        if not self.supabase:
            return None
            
        table = self._get_table_name(data_type)
        if not table:
            return None
            
        try:
            response = self.supabase.table(table).select("*").eq("id", id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Supabase Get Error ({table}): {e}")
            
        return None
    
    def update(self, data_type: str, id: str, data: Dict) -> Optional[Dict]:
        """データを更新"""
        if not self.supabase:
            return None

        table = self._get_table_name(data_type)
        if not table:
            return None
            
        data["updated_at"] = datetime.now().isoformat()
        
        try:
            response = self.supabase.table(table).update(data).eq("id", id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
             print(f"Supabase Update Error ({table}): {e}")

        return None
    
    def delete(self, data_type: str, id: str) -> bool:
        """データを削除（Cascade削除はDB設定に依存するが、ここでは明示的にも処理）"""
        if not self.supabase:
            return False

        table = self._get_table_name(data_type)
        if not table:
            return False
            
        # 子データの削除コードを実行（DB側でCascade設定されていれば不要だが念のため）
        self._delete_children(data_type, id)
        
        try:
            self.supabase.table(table).delete().eq("id", id).execute()
            return True
        except Exception as e:
            print(f"Supabase Delete Error ({table}): {e}")
            return False
    
    def _delete_children(self, parent_type: str, parent_id: str) -> None:
        """子データを削除"""
        if not self.supabase:
            return

        parent_key = f"{parent_type[:-1]}_id"  # projects -> project_id
        
        for child_type, parent in self.DATA_HIERARCHY.items():
            if parent == parent_type:
                table = self._get_table_name(child_type)
                if table:
                    try:
                        self.supabase.table(table).delete().eq(parent_key, parent_id).execute()
                    except Exception as e:
                        print(f"Supabase Delete Children Error ({table}): {e}")

    def list(self, data_type: str, filters: Optional[Dict] = None) -> List[Dict]:
        """一覧取得（フィルタ対応）"""
        if not self.supabase:
            return []

        table = self._get_table_name(data_type)
        if not table:
            return []
            
        try:
            query = self.supabase.table(table).select("*")
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Supabase List Error ({table}): {e}")
            return []
    
    def list_by_parent(self, data_type: str, parent_id: str) -> List[Dict]:
        """親IDでリスト取得"""
        parent_type = self.DATA_HIERARCHY.get(data_type)
        if parent_type:
            # 特殊ケース: Supabaseのテーブル定義で外部キーカラム名が異なる場合はここで調整
            parent_key = f"{parent_type[:-1]}_id"
            return self.list(data_type, {parent_key: parent_id})
        return []
    
    def clear_children(self, parent_type: str, parent_id: str) -> None:
        """子データをクリア"""
        self._delete_children(parent_type, parent_id)
    
    def clear_all(self, data_type: str) -> None:
        """全データをクリア（開発用: 注意して使用）"""
        if not self.supabase:
            return

        table = self._get_table_name(data_type)
        if table:
            try:
                # 全件削除は危険なので、idがnot nullなど条件をつけて全件対象にする
                self.supabase.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            except Exception as e:
                print(f"Supabase Clear All Error ({table}): {e}")
                
    def count(self, data_type: str, filters: Optional[Dict] = None) -> int:
        """件数を取得"""
        if not self.supabase:
            return 0
            
        table = self._get_table_name(data_type)
        if not table:
            return 0
            
        try:
            query = self.supabase.table(table).select("*", count="exact", head=True)
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.count
        except Exception as e:
            print(f"Supabase Count Error ({table}): {e}")
            return 0

    def exists(self, data_type: str, id: str) -> bool:
        """存在確認"""
        if not self.supabase:
            return False
            
        table = self._get_table_name(data_type)
        if not table:
            return False

        try:
            response = self.supabase.table(table).select("id").eq("id", id).execute()
            return len(response.data) > 0
        except:
            return False
            
    def bulk_create(self, data_type: str, items: List[Dict]) -> List[Dict]:
        """一括作成"""
        if not self.supabase or not items:
            return []

        table = self._get_table_name(data_type)
        if not table:
            return []
            
        # 共通処理
        now = datetime.now().isoformat()
        for item in items:
            if "id" not in item:
                item["id"] = str(uuid.uuid4())
            if "created_at" not in item:
                item["created_at"] = now
            item["updated_at"] = now
            
        try:
            response = self.supabase.table(table).insert(items).execute()
            return response.data
        except Exception as e:
            print(f"Supabase Bulk Create Error ({table}): {e}")
            return []
            
    def bulk_delete(self, data_type: str, ids: List[str]) -> int:
        """一括削除"""
        if not self.supabase or not ids:
            return 0
            
        table = self._get_table_name(data_type)
        if not table:
            return 0
            
        try:
            response = self.supabase.table(table).delete().in_("id", ids).execute()
            return len(response.data)
        except Exception as e:
            print(f"Supabase Bulk Delete Error ({table}): {e}")
            return 0

    def get_employee_personas(self) -> List[Dict]:
        """全メンバー取得"""
        return self.list("employee_personas")

    def add_employee_persona(self, data: Dict) -> Dict:
        """新規メンバー追加"""
        return self.create("employee_personas", data)

    def update_employee_persona(self, id: str, data: Dict) -> Optional[Dict]:
        """メンバー情報更新"""
        return self.update("employee_personas", id, data)

    def delete_employee_persona(self, id: str) -> bool:
        """メンバー削除"""
        return self.delete("employee_personas", id)

    def get_employee_feedback(self, employee_id: str, limit: int = 10) -> List[Dict]:
        """フィードバック取得"""
        if not self.supabase:
            return []
        try:
            response = self.supabase.table("employee_feedback") \
                .select("*") \
                .eq("employee_id", employee_id) \
                .order("created_at", descending=True) \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            print(f"Supabase Get Feedback Error: {e}")
            return []

    def add_employee_feedback(self, data: Dict) -> Dict:
        """フィードバック追加"""
        return self.create("employee_feedback", data)

    def get_settings(self) -> Optional[Dict]:
        """設定取得（key='main'）"""
        if not self.supabase:
            return None
        try:
            response = self.supabase.table("settings").select("value").eq("key", "main").execute()
            if response.data:
                return response.data[0]["value"]
        except Exception as e:
            print(f"Supabase Get Settings Error: {e}")
        return None

    def save_settings(self, settings_data: Dict) -> bool:
        """設定保存（key='main'）"""
        if not self.supabase:
            return False
        try:
            data = {
                "key": "main",
                "value": settings_data,
                "updated_at": datetime.now().isoformat()
            }
            # upsert
            self.supabase.table("settings").upsert(data).execute()
            return True
        except Exception as e:
            print(f"Supabase Save Settings Error: {e}")
            return False

    def save_comparison_table(self, project_id: str, table_md: str) -> bool:
        """比較表を保存"""
        if not self.supabase:
            return False
        try:
            self.supabase.table("projects").update({
                "comparison_table": table_md
            }).eq("id", project_id).execute()
            return True
        except Exception as e:
            print(f"Save comparison table error: {e}")
            return False

    def get_comparison_table(self, project_id: str) -> Optional[str]:
        """比較表を取得"""
        if not self.supabase:
            return None
        try:
            response = self.supabase.table("projects").select("comparison_table").eq("id", project_id).execute()
            if response.data and response.data[0].get("comparison_table"):
                return response.data[0]["comparison_table"]
        except Exception as e:
            print(f"Get comparison table error: {e}")
        return None

    def save_review_analysis(self, project_id: str, data: dict) -> bool:
        """レビュー分析結果を保存"""
        if not self.supabase:
            return False
        try:
            import json
            self.supabase.table("projects").update({
                "review_analysis": json.dumps(data, ensure_ascii=False)
            }).eq("id", project_id).execute()
            return True
        except Exception as e:
            print(f"Save review analysis error: {e}")
            return False

    def get_review_analysis(self, project_id: str) -> Optional[dict]:
        """レビュー分析結果を取得"""
        if not self.supabase:
            return None
        try:
            import json
            response = self.supabase.table("projects").select("review_analysis").eq("id", project_id).execute()
            if response.data and response.data[0].get("review_analysis"):
                return json.loads(response.data[0]["review_analysis"])
        except Exception as e:
            print(f"Get review analysis error: {e}")
        return None
