"""
Utility functions for the application.
Includes robust JSON parsing for AI responses.
"""
import json
import ast
import re
import logging

# Configure logger
logger = logging.getLogger(__name__)

def parse_json_response(response: str) -> dict:
    """AI応答からJSONを抽出してパース"""
    import json
    import re
    
    text = response.strip()
    
    # コードブロックを除去
    if "```json" in text:
        match = re.search(r'```json\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
    elif "```" in text:
        match = re.search(r'```\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
    
    # JSONオブジェクトを探す
    start = text.find('{')
    if start == -1:
        raise ValueError("JSONオブジェクトが見つかりません")
    
    # 不完全なJSONの場合、配列を閉じる試み
    text = text[start:]
    
    # まずそのままパースを試す
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 不完全なJSON配列を閉じる試み
    # ideas配列が途中で切れている場合
    if '"ideas"' in text and text.count('[') > text.count(']'):
        # 最後の完全なオブジェクトまでを抽出
        last_complete = text.rfind('},')
        if last_complete > 0:
            text = text[:last_complete + 1] + ']}'
            try:
                return json.loads(text)
            except:
                pass
        
        last_complete = text.rfind('}')
        if last_complete > 0:
            text = text[:last_complete + 1] + ']}'
            try:
                return json.loads(text)
            except:
                pass
    
    raise ValueError(f"JSONのパースに失敗: {text[:200]}...")
