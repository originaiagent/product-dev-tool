"""
AIプロバイダモジュール
- 複数LLMの統一インターフェース
- リトライ処理
- エラーハンドリング
"""
import time
import base64
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

# 遅延インポート（必要時のみロード）
anthropic = None
openai = None
genai = None


def _import_anthropic():
    global anthropic
    if anthropic is None:
        import anthropic as _anthropic
        anthropic = _anthropic
    return anthropic


def _import_openai():
    global openai
    if openai is None:
        import openai as _openai
        openai = _openai
    return openai


def _import_genai():
    global genai
    if genai is None:
        import google.generativeai as _genai
        genai = _genai
    return genai


class AIProvider:
    """AIプロバイダ統一インターフェース"""
    
    def __init__(self, settings_manager):
        self.settings = settings_manager
        self._client = None
        self._current_provider = None
    
    def _get_client(self, provider: Optional[str] = None):
        """プロバイダに応じたクライアントを取得"""
        if provider is None:
            provider = self.settings.get_provider()
        
        api_key = self.settings.get_api_key(provider)
        if not api_key:
            raise ValueError(f"API key not found for provider: {provider}")
        
        if provider == "google":
            _genai = _import_genai()
            _genai.configure(api_key=api_key)
            return _genai
        elif provider == "anthropic":
            _anthropic = _import_anthropic()
            return _anthropic.Anthropic(api_key=api_key)
        elif provider == "openai":
            _openai = _import_openai()
            return _openai.OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task: Optional[str] = None,
        images: Optional[List[Union[str, bytes]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """テキスト生成（プロバイダ共通）"""
        provider = self.settings.get_provider()
        model = self.settings.get_model(task)
        client = self._get_client(provider)
        
        if provider == "google":
            return self._generate_gemini(client, model, prompt, system_prompt, images, temperature, max_tokens)
        elif provider == "anthropic":
            return self._generate_claude(client, model, prompt, system_prompt, images, temperature, max_tokens)
        elif provider == "openai":
            return self._generate_openai(client, model, prompt, system_prompt, images, temperature, max_tokens)
    
    def _generate_gemini(
        self,
        client,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        images: Optional[List],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Gemini APIでテキスト生成"""
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        model_instance = client.GenerativeModel(
            model_name=model,
            generation_config=generation_config,
            system_instruction=system_prompt if system_prompt else None
        )
        
        # コンテンツ構築
        content = []
        if images:
            for img in images:
                if isinstance(img, str):
                    # base64文字列の場合
                    content.append({
                        "mime_type": "image/jpeg",
                        "data": img
                    })
                elif isinstance(img, bytes):
                    content.append({
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(img).decode()
                    })
        content.append(prompt)
        
        response = model_instance.generate_content(content)
        return response.text
    
    def _generate_claude(
        self,
        client,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        images: Optional[List],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Claude APIでテキスト生成"""
        messages = []
        
        # ユーザーメッセージ構築
        user_content = []
        if images:
            for img in images:
                if isinstance(img, str):
                    # base64文字列
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img
                        }
                    })
                elif isinstance(img, bytes):
                    user_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": base64.b64encode(img).decode()
                        }
                    })
        user_content.append({"type": "text", "text": prompt})
        
        messages.append({"role": "user", "content": user_content})
        
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt if system_prompt else "",
            messages=messages,
            temperature=temperature
        )
        
        return response.content[0].text
    
    def _generate_openai(
        self,
        client,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        images: Optional[List],
        temperature: float,
        max_tokens: int
    ) -> str:
        """OpenAI APIでテキスト生成"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # ユーザーメッセージ構築
        user_content = []
        if images:
            for img in images:
                if isinstance(img, str):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img}"}
                    })
                elif isinstance(img, bytes):
                    b64 = base64.b64encode(img).decode()
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })
        user_content.append({"type": "text", "text": prompt})
        
        messages.append({"role": "user", "content": user_content})
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task: Optional[str] = None,
        images: Optional[List] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> str:
        """リトライ付きテキスト生成"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    task=task,
                    images=images
                )
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
        
        raise last_error
    
    def switch_provider(self, provider: str) -> None:
        """プロバイダを切り替え"""
        self.settings.set_provider(provider)
        self._client = None
        self._current_provider = None
    
    def switch_model(self, model: str) -> None:
        """モデルを切り替え"""
        self.settings.set_model(model)
