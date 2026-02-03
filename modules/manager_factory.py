import streamlit as st
from modules.settings_manager import SettingsManager
from modules.data_store import DataStore
from modules.storage_manager import StorageManager
from modules.ai_provider import AIProvider

@st.cache_resource
def get_managers():
    """全マネージャーを一括初期化してキャッシュするファクトリー関数 - v1.1 refresh"""
    # DataStore初期化（Supabase接続）
    data_store = DataStore()
    
    # SettingsManagerにDataStoreを注入
    settings = SettingsManager(data_store=data_store)
    
    # StorageManager初期化
    storage_manager = StorageManager()
    
    # AIProvider初期化
    ai_provider = AIProvider(settings)
    
    return settings, data_store, storage_manager, ai_provider
