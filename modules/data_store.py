"""
データストアモジュール
- データの保存・読込・削除
- トレーサビリティ（親子関係の管理）
- UUID管理
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class DataStore:
    """データ保存・管理クラス"""
    
    # データタイプと親子関係の定義
    DATA_HIERARCHY = {
        "projects": None,  # ルート
        "competitors": "projects",
        "reviews": "projects",
        "ideas": "projects",
        "positioning": "projects"
    }
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent / "data"
        else:
            self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_filepath(self, data_type: str) -> Path:
        """データタイプに応じたファイルパスを取得"""
        return self.data_dir / f"{data_type}.json"
    
    def _load_all(self, data_type: str) -> List[Dict]:
        """全データを読み込む"""
        filepath = self._get_filepath(data_type)
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def _save_all(self, data_type: str, data: List[Dict]) -> None:
        """全データを保存"""
        filepath = self._get_filepath(data_type)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create(self, data_type: str, data: Dict) -> Dict:
        """新規作成（UUID自動付与）"""
        all_data = self._load_all(data_type)
        
        # UUID付与
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        # タイムスタンプ付与
        now = datetime.now().isoformat()
        data["created_at"] = now
        data["updated_at"] = now
        
        all_data.append(data)
        self._save_all(data_type, all_data)
        return data
    
    def get(self, data_type: str, id: str) -> Optional[Dict]:
        """IDでデータを取得"""
        all_data = self._load_all(data_type)
        for item in all_data:
            if item.get("id") == id:
                return item
        return None
    
    def update(self, data_type: str, id: str, data: Dict) -> Optional[Dict]:
        """データを更新"""
        all_data = self._load_all(data_type)
        for i, item in enumerate(all_data):
            if item.get("id") == id:
                # 既存データをマージ
                updated = {**item, **data}
                updated["updated_at"] = datetime.now().isoformat()
                all_data[i] = updated
                self._save_all(data_type, all_data)
                return updated
        return None
    
    def delete(self, data_type: str, id: str) -> bool:
        """データを削除（子データも連動削除）"""
        all_data = self._load_all(data_type)
        original_len = len(all_data)
        all_data = [item for item in all_data if item.get("id") != id]
        
        if len(all_data) < original_len:
            self._save_all(data_type, all_data)
            # 子データも削除
            self._delete_children(data_type, id)
            return True
        return False
    
    def _delete_children(self, parent_type: str, parent_id: str) -> None:
        """子データを削除"""
        parent_key = f"{parent_type[:-1]}_id"  # projects -> project_id
        
        for child_type, parent in self.DATA_HIERARCHY.items():
            if parent == parent_type:
                all_data = self._load_all(child_type)
                all_data = [
                    item for item in all_data 
                    if item.get(parent_key) != parent_id
                ]
                self._save_all(child_type, all_data)
    
    def list(self, data_type: str, filters: Optional[Dict] = None) -> List[Dict]:
        """一覧取得（フィルタ対応）"""
        all_data = self._load_all(data_type)
        
        if filters:
            filtered = []
            for item in all_data:
                match = True
                for key, value in filters.items():
                    if item.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(item)
            return filtered
        
        return all_data
    
    def list_by_parent(self, data_type: str, parent_id: str) -> List[Dict]:
        """親IDでリスト取得"""
        parent_type = self.DATA_HIERARCHY.get(data_type)
        if parent_type:
            parent_key = f"{parent_type[:-1]}_id"
            return self.list(data_type, {parent_key: parent_id})
        return []
    
    def clear_children(self, parent_type: str, parent_id: str) -> None:
        """子データをクリア（トレーサビリティ対応）"""
        self._delete_children(parent_type, parent_id)
    
    def clear_all(self, data_type: str) -> None:
        """全データをクリア"""
        self._save_all(data_type, [])
    
    def count(self, data_type: str, filters: Optional[Dict] = None) -> int:
        """件数を取得"""
        return len(self.list(data_type, filters))
    
    def exists(self, data_type: str, id: str) -> bool:
        """存在確認"""
        return self.get(data_type, id) is not None
    
    def bulk_create(self, data_type: str, items: List[Dict]) -> List[Dict]:
        """一括作成"""
        created = []
        for item in items:
            created.append(self.create(data_type, item))
        return created
    
    def bulk_delete(self, data_type: str, ids: List[str]) -> int:
        """一括削除"""
        count = 0
        for id in ids:
            if self.delete(data_type, id):
                count += 1
        return count
