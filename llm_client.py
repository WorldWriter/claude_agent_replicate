"""LLM客户端封装 - 支持Anthropic Claude和Kimi K2"""
import os
import requests
import time
from anthropic import Anthropic


class LLMClient:
    """统一的LLM接口"""

    def __init__(self, provider="anthropic"):
        self.provider = provider.lower()

        if self.provider == "anthropic":
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-3-haiku-20240307"  # 使用Claude 3 Haiku模型
        elif self.provider == "kimi":
            self.api_key = os.getenv("MOONSHOT_API_KEY")
            self.base_url = "https://api.moonshot.ai/v1/chat/completions"
            self.model = "moonshot-v1-32k"
        else:
            raise ValueError(f"不支持的provider: {provider}")

    def call(self, messages, temperature=0.7, max_tokens=2000):
        """调用LLM API"""
        if self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )
            return response.content[0].text

        elif self.provider == "kimi":
            # 添加请求延迟，避免触发速率限制
            time.sleep(2)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
