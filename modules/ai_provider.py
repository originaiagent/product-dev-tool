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
            "max_output_tokens": 16000 if max_tokens == 4096 else max_tokens, # デフォルト4096を16000に引き上げ
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

    def evaluate_by_employee(
        self,
        employee: Dict[str, Any],
        product_content: str,
        past_feedbacks: List[Dict[str, Any]] = None
    ) -> str:
        """メンバー視点での商品評価を生成"""
        # プロンプト読み込み
        prompt_path = Path(__file__).parent.parent / "data" / "prompts" / "employee_evaluation.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 過去のフィードバックをテキスト化
        past_feedback_text = ""
        if past_feedbacks:
            for i, fb in enumerate(past_feedbacks):
                past_feedback_text += f"【前回までの修正指示 {i+1}】\n{fb.get('user_feedback', '')}\n"
        else:
            past_feedback_text = "なし"

        # プロンプト埋め込み
        prompt = template.format(
            employee_name=employee.get("name") or "メンバー",
            employee_evaluation_perspective=employee.get("evaluation_perspective") or "未設定",
            employee_personality_traits=employee.get("personality_traits") or "未設定",
            employee_pain_points=employee.get("pain_points") or "未設定",
            employee_info_literacy=employee.get("info_literacy") or "未設定",
            employee_purchase_trigger=employee.get("purchase_trigger") or "未設定",
            employee_lifestyle=employee.get("lifestyle") or "未設定",
            employee_psychographic=employee.get("psychographic") or "未設定",
            employee_demographic=employee.get("demographic") or "未設定",
            employee_buying_behavior=employee.get("buying_behavior") or "未設定",
            employee_ng_points=employee.get("ng_points") or "未設定",
            past_feedback=past_feedback_text,
            product_content=product_content
        )

        # AIにリクエスト
        return self.generate_with_retry(prompt=prompt, task="evaluation")

    def generate_with_image(self, prompt: str, base64_image: str) -> str:
        """画像付きでテキスト生成"""
        provider = self.settings.get_provider()
        
        if provider == "google":
            import google.generativeai as genai
            import base64
            
            api_key = self.settings.get_api_key("google")
            genai.configure(api_key=api_key)
            
            model_name = self.settings.get_model()
            model = genai.GenerativeModel(model_name)
            
            # base64をバイトにデコード
            image_bytes = base64.b64decode(base64_image)
            
            # 画像データを準備
            image_part = {
                "mime_type": "image/png",
                "data": image_bytes
            }
            
            response = model.generate_content([prompt, image_part])
            return response.text
        else:
            raise ValueError(f"画像対応は現在Googleのみです: {provider}")
