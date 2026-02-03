"""
設定管理モジュール
- 設定の読み書き
- API選択とモデル切替
- 環境変数からのAPIキー取得
"""
import json
import os
from pathlib import Path
from typing import Any, Optional, List, Dict
from datetime import datetime


class SettingsManager:
    """設定管理クラス"""
    
    def __init__(self, settings_path: Optional[str] = None, data_store: Optional[Any] = None):
        if settings_path is None:
            self.settings_path = Path(__file__).parent.parent / "data" / "settings.json"
        else:
            self.settings_path = Path(settings_path)
        
        # DataStoreの初期化 (依存注入または内部生成)
        if data_store:
            self.data_store = data_store
        else:
            try:
                from modules.data_store import DataStore
                self.data_store = DataStore()
            except ImportError:
                print("SettingsManager: Failed to import DataStore.")
                self.data_store = None
        
        self._settings = self._load()
    
    def _load(self) -> dict:
        """DataStoreから設定を読み込む。失敗時はローカルまたはデフォルトを返す"""
        if self.data_store:
            try:
                # DataStoreのSupabase接続確認
                if hasattr(self.data_store, 'supabase') and self.data_store.supabase:
                    print("SettingsManager: Loading settings via DataStore...")
                    remote_settings = self.data_store.get_settings()
                    if remote_settings:
                        print(f"SettingsManager: Loaded settings from Supabase.")
                        return remote_settings
                    else:
                        print("SettingsManager: No settings found in Supabase (key='main'). Using defaults.")
            except Exception as e:
                print(f"SettingsManager: DataStore Load Error: {e}")

        # フォールバック: ローカルファイル
        try:
            if self.settings_path.exists():
                print(f"SettingsManager: Loading from local file: {self.settings_path}")
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"SettingsManager: Local Load Error: {e}")
            pass
            
        print("SettingsManager: Using default settings.")
        return self._default_settings()
    
    def _default_settings(self) -> dict:
        """デフォルト設定"""
        return {
            "ai": {
                "provider": "google",
                "models": {
                    "google": "gemini-2.0-flash",
                    "anthropic": "claude-3-5-sonnet-20241022",
                    "openai": "gpt-4o"
                },
                "task_models": {}
            },
            "ui": {
                "sidebar_expanded": True
            }
        }
    
    def _save(self) -> None:
        """DataStore経由で設定を保存"""
        if self.data_store:
            try:
                if hasattr(self.data_store, 'supabase') and self.data_store.supabase:
                    print("SettingsManager: Saving settings via DataStore...")
                    if self.data_store.save_settings(self._settings):
                        print("SettingsManager: Save successful.")
                        return
            except Exception as e:
                print(f"SettingsManager: DataStore Save Error: {e}")

        # フォールバック: ローカルファイル
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.settings_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings, f, ensure_ascii=False, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得（ドット区切りのキーに対応）"""
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """設定値を保存（ドット区切りのキーに対応）"""
        keys = key.split('.')
        target = self._settings
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self._save()
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """環境変数からAPIキーを取得"""
        env_keys = {
            "google": "GOOGLE_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY"
        }
        env_key = env_keys.get(provider)
        if env_key:
            return os.environ.get(env_key)
        return None
    
    def get_provider(self) -> str:
        """現在のプロバイダを取得"""
        return self.get("ai.provider", "google")
    
    def set_provider(self, provider: str) -> None:
        """プロバイダを設定"""
        self.set("ai.provider", provider)
    
    def get_model(self, task: Optional[str] = None) -> str:
        """モデルを取得（タスク指定時はタスク別モデル優先）"""
        if task:
            task_model = self.get(f"ai.task_models.{task}")
            if task_model:
                return task_model
        provider = self.get_provider()
        return self.get(f"ai.models.{provider}", "gemini-2.0-flash")
    
    def set_model(self, model: str, provider: Optional[str] = None) -> None:
        """モデルを設定"""
        if provider is None:
            provider = self.get_provider()
        self.set(f"ai.models.{provider}", model)
    
    def set_task_model(self, task: str, model: Optional[str]) -> None:
        """タスク別モデルを設定"""
        self.set(f"ai.task_models.{task}", model)
    
    def get_available_providers(self) -> List[Dict[str, str]]:
        """利用可能なプロバイダ一覧"""
        return [
            {"id": "google", "name": "Google (Gemini)"},
            {"id": "anthropic", "name": "Anthropic (Claude)"},
            {"id": "openai", "name": "OpenAI (GPT)"}
        ]
    
    def get_available_models(self, provider: str, force_refresh: bool = False) -> List[Dict[str, str]]:
        """プロバイダ別モデル一覧（API動的取得対応）"""
        # キャッシュキー
        cache_key = f"cached_models.{provider}"
        
        # キャッシュがあり、強制更新でない場合はキャッシュを返す
        if not force_refresh:
            cached = self.get(cache_key)
            if cached:
                return cached
        
        # API動的取得を試行
        try:
            models = self._fetch_models_from_api(provider)
            if models:
                # キャッシュに保存
                self.set(cache_key, models)
                return models
        except Exception:
            pass
        
        # フォールバック（静的リスト）
        return self._get_fallback_models(provider)
    
    def _fetch_models_from_api(self, provider: str) -> List[Dict[str, str]]:
        """APIからモデル一覧を取得"""
        api_key = self.get_api_key(provider)
        if not api_key:
            return []
        
        models = []
        
        if provider == "google":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                for model in genai.list_models():
                    if "generateContent" in model.supported_generation_methods:
                        model_id = model.name.replace("models/", "")
                        # Gemmaを除外、Geminiのみ残す
                        if model_id.startswith("gemini") and "gemma" not in model_id:
                            models.append({
                                "id": model_id,
                                "name": f"{model.display_name}"
                            })
            except Exception:
                pass
        
        elif provider == "openai":
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                response = client.models.list()
                for model in response.data:
                    if "gpt" in model.id:
                        models.append({
                            "id": model.id,
                            "name": model.id
                        })
                # 主要モデルを上に
                priority = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
                models.sort(key=lambda x: priority.index(x["id"]) if x["id"] in priority else 999)
            except Exception:
                pass
        
        elif provider == "anthropic":
            # Anthropicはモデル一覧APIがないため静的リスト
            return self._get_fallback_models(provider)
        
        return models
    
    def _get_fallback_models(self, provider: str) -> List[Dict[str, str]]:
        """フォールバック用の静的モデルリスト"""
        models = {
            "google": [
                {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash - 最新、高速"},
                {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite - 高速"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro - 高精度"},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash - バランス型"}
            ],
            "anthropic": [
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet - 高性能"},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku - 高速"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus - 最高精度"},
                {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku - 高速"}
            ],
            "openai": [
                {"id": "gpt-4o", "name": "GPT-4o - 最新"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini - 高速"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo - 高精度"},
                {"id": "o1", "name": "o1 - 推論特化"},
                {"id": "o1-mini", "name": "o1 Mini - 推論（高速）"}
            ]
        }
        return models.get(provider, [])
    
    def refresh_models(self, provider: str) -> List[Dict[str, str]]:
        """モデル一覧を強制更新"""
        return self.get_available_models(provider, force_refresh=True)
    
    def check_api_key_status(self) -> Dict[str, bool]:
        """各プロバイダのAPIキー設定状態を確認"""
        return {
            "google": bool(self.get_api_key("google")),
            "anthropic": bool(self.get_api_key("anthropic")),
            "openai": bool(self.get_api_key("openai"))
        }
