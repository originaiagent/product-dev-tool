"""
プロンプト管理モジュール
- プロンプトテンプレートの保存・読込・編集
- 変数の埋め込み
- バージョン管理
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


class PromptManager:
    """プロンプトテンプレート管理クラス"""
    
    # 定義されたタスク一覧
    TASKS = {
        "extract": {
            "name": "競合情報抽出",
            "description": "画像・テキストから情報抽出"
        },
        "atomize": {
            "name": "レビュー原子化",
            "description": "キーワードを最小単位に分解"
        },
        "categorize": {
            "name": "カテゴリ分類",
            "description": "キーワードをカテゴリに分類"
        },
        "differentiate": {
            "name": "差別化案生成",
            "description": "差別化アイデアを生成"
        },
        "estimate": {
            "name": "有効度推定",
            "description": "潜在ニーズの有効度を推定"
        }
    }
    
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            self.prompts_dir = Path(__file__).parent.parent / "data" / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir = self.prompts_dir / "_versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    def load(self, prompt_name: str) -> Optional[str]:
        """プロンプトテンプレートを読み込む"""
        filepath = self.prompts_dir / f"{prompt_name}.md"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def save(self, prompt_name: str, content: str, create_version: bool = True) -> None:
        """プロンプトテンプレートを保存"""
        filepath = self.prompts_dir / f"{prompt_name}.md"
        
        # バージョン保存
        if create_version and filepath.exists():
            self._create_version(prompt_name)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_version(self, prompt_name: str) -> None:
        """バージョンを作成"""
        filepath = self.prompts_dir / f"{prompt_name}.md"
        if filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version_file = self.versions_dir / f"{prompt_name}_{timestamp}.md"
            shutil.copy(filepath, version_file)
    
    def list_prompts(self) -> List[Dict[str, str]]:
        """プロンプト一覧を取得"""
        prompts = []
        for task_id, task_info in self.TASKS.items():
            filepath = self.prompts_dir / f"{task_id}.md"
            prompts.append({
                "id": task_id,
                "name": task_info["name"],
                "description": task_info["description"],
                "exists": filepath.exists()
            })
        return prompts
    
    def render(self, prompt_name: str, variables: Dict[str, str]) -> Optional[str]:
        """変数を埋め込んでプロンプトを生成"""
        template = self.load(prompt_name)
        if template is None:
            return None
        
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        
        return result
    
    def get_versions(self, prompt_name: str) -> List[Dict[str, str]]:
        """バージョン履歴を取得"""
        versions = []
        for filepath in sorted(self.versions_dir.glob(f"{prompt_name}_*.md"), reverse=True):
            timestamp = filepath.stem.replace(f"{prompt_name}_", "")
            versions.append({
                "filename": filepath.name,
                "timestamp": timestamp,
                "path": str(filepath)
            })
        return versions
    
    def restore_version(self, prompt_name: str, version_filename: str) -> bool:
        """バージョンを復元"""
        version_path = self.versions_dir / version_filename
        if not version_path.exists():
            return False
        
        # 現在のバージョンを保存
        self._create_version(prompt_name)
        
        # 復元
        content = version_path.read_text(encoding='utf-8')
        self.save(prompt_name, content, create_version=False)
        return True
    
    def get_default(self, prompt_name: str) -> Optional[str]:
        """デフォルトプロンプトを取得"""
        defaults = self._get_default_prompts()
        return defaults.get(prompt_name)
    
    def reset_to_default(self, prompt_name: str) -> bool:
        """デフォルトに戻す"""
        default = self.get_default(prompt_name)
        if default:
            self.save(prompt_name, default)
            return True
        return False
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """デフォルトプロンプト定義"""
        return {
            "extract": self._default_extract(),
            "atomize": self._default_atomize(),
            "categorize": self._default_categorize(),
            "differentiate": self._default_differentiate(),
            "estimate": self._default_estimate()
        }
    
    def _default_extract(self) -> str:
        return """あなたは製品分析の専門家です。
アップロードされた画像とテキスト情報から、以下の項目を抽出してください：

- 製品名
- 価格
- 主要スペック（重量、サイズ、機能など）
- 製品特徴
- ユーザーレビューの傾向（ポジティブ/ネガティブ）

## 回答ルール
- 情報が不足している場合は「不明」と記載
- 推測・憶測で回答しない
- 画像から読み取れる情報のみを記載

## 出力フォーマット
JSON形式で以下の構造で出力してください：
```json
{
  "price": "価格",
  "specs": {
    "weight": "重量",
    "size": "サイズ",
    "power": "電源方式"
  },
  "features": ["特徴1", "特徴2"],
  "positives": ["良い点1", "良い点2"],
  "negatives": ["悪い点1", "悪い点2"]
}
```"""
    
    def _default_atomize(self) -> str:
        return """あなたはレビュー分析の専門家です。
以下のレビューテキストから、意味を保つ最小のキーワードを抽出してください。

## 抽出ルール
- 1つのレビューから複数のキーワードを抽出可能
- 同じ意味のキーワードは統一（例：「重い」「重たい」→「重い」）
- ポジティブ・ネガティブ両方を抽出
- 製品の特徴・機能に関するキーワードを優先

## 回答ルール
- 情報が不足している場合は「わからない」と正直に回答する
- 推測・憶測で回答しない

## 出力フォーマット
JSON形式で出力してください：
```json
{
  "keywords": [
    {"word": "重い", "sentiment": "negative", "count": 45},
    {"word": "軽い", "sentiment": "positive", "count": 30}
  ]
}
```"""
    
    def _default_categorize(self) -> str:
        return """あなたはデータ分類の専門家です。
以下のキーワードリストを、適切なカテゴリに分類してください。

## カテゴリ例
- 重量・携帯性
- 操作性・使いやすさ
- 静音性
- バッテリー
- デザイン・質感
- 温熱機能
- 耐久性
- 価格・コスパ

## 分類ルール
- 1つのキーワードは1つのカテゴリにのみ分類
- 適切なカテゴリがない場合は新規作成可能
- カテゴリ名は簡潔に

## 回答ルール
- 情報が不足している場合は「わからない」と正直に回答する
- 推測・憶測で回答しない

## 出力フォーマット
JSON形式で出力してください：
```json
{
  "categories": [
    {
      "name": "重量・携帯性",
      "keywords": ["重い", "軽い", "持ち運び"]
    }
  ]
}
```"""
    
    def _default_differentiate(self) -> str:
        return """あなたは製品開発の専門家です。
以下の競合分析とレビュー分析の結果を基に、差別化案を30〜50件生成してください。

## 差別化パターン
- 性能UP: 既存性能を強化
- 機能追加: 新機能を追加
- 合体: 製品を組み合わせ
- コスト削減: 機能削減でコストダウン

## 各案に含める情報
- title: 差別化内容のタイトル
- pattern: 性能UP / 機能追加 / 合体 / コスト削減
- difficulty: 低（工場既存品活用）/ 中（設計変更）/ 高（研究開発）
- ip: 特許 / 意匠 / null
- effectiveness: 有効度（0-100）
- eff_type: manifest（顕在）/ latent（潜在）
- eff_reasons: 有効度の根拠
- cost: コスト概算（例：¥200〜400）
- cost_reason: コストの理由
- time: 期間（例：1〜2ヶ月）

## 回答ルール
- 顕在ニーズはレビューデータから計算
- 潜在ニーズはAI推定として明記
- 実現可能性を重視
- 推測・憶測で回答する場合は明記

## 出力フォーマット
JSON形式で出力してください：
```json
{
  "ideas": [
    {
      "title": "超軽量化（180g以下）",
      "pattern": "性能UP",
      "difficulty": "低",
      "ip": null,
      "effectiveness": 50,
      "eff_type": "manifest",
      "eff_reasons": ["「重い」32%", "「軽いのが良い」18%"],
      "cost": "¥200〜400",
      "cost_reason": "素材変更のみ、金型不要",
      "time": "1〜2ヶ月"
    }
  ]
}
```"""
    
    def _default_estimate(self) -> str:
        return """あなたは市場分析の専門家です。
以下の差別化案について、潜在ニーズの有効度を推定してください。

## 推定の観点
- ターゲットユーザー層の割合
- 類似製品・機能の市場動向
- 技術トレンド
- 消費者行動の変化

## 回答ルール
- 推定値は必ず「（AI推定）」と明記
- 根拠を具体的に説明
- 不確実性が高い場合は範囲で回答

## 出力フォーマット
JSON形式で出力してください：
```json
{
  "estimates": [
    {
      "idea_id": "uuid",
      "effectiveness": 45,
      "reasons": ["便利と感じる層45%（AI推定）"],
      "confidence": "中",
      "notes": "補足説明"
    }
  ]
}
```"""
