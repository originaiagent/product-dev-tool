import sys
from pathlib import Path
import os
import json

# モジュールパスを追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.settings_manager import SettingsManager

def verify():
    print("Verifying Supabase Settings...")
    try:
        sm = SettingsManager()
        
        if not sm.supabase:
            print("❌ No Supabase connection available.")
            return

        print("✅ Supabase connection established.")
        
        # Read
        print("Reading 'settings' table...")
        response = sm.supabase.table("settings").select("*").eq("key", "main").execute()
        
        if response.data:
            print("✅ Found 'main' settings record:")
            print(json.dumps(response.data[0], indent=2, ensure_ascii=False))
        else:
            print("⚠️ No 'main' record found in settings table.")
            
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    verify()
