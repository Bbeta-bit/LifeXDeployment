# app/services/ai_service.py
import os
import httpx
import json
from typing import Dict, List, Any, Optional
from enum import Enum
from dotenv import load_dotenv

load_dotenv(dotenv_path="API.env")

class AIProvider(Enum):
    GOOGLE_STUDIO = "google_studio"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROK = "grok"

class UnifiedAIService:
    """统一的AI调用服务，支持多个AI提供商"""
    
    def __init__(self):
        self.providers = {
            AIProvider.GOOGLE_STUDIO: {
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "base_url": "https://generativelanguage.googleapis.com/v1beta/models",
                "models": {
                    "flash": "gemini-1.5-flash",
                    "pro": "gemini-1.5-pro", 
                    "flash_exp": "gemini-2.0-flash-exp",
                    "pro_old": "gemini-1.0-pro"
                }
            },
            AIProvider.OPENROUTER: {
                "api_key": os.getenv("OPENROUTER_API_KEY"),
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "models": {
                    "gemini_flash": "google/gemini-2.0-flash-exp:free",
                    "claude": "anthropic/claude-3.5-sonnet",
                    "gpt4": "openai/gpt-4o-mini"
                }
            },
            # AIProvider.ANTHROPIC: {
            #     "api_key": os.getenv("ANTHROPIC_API_KEY"),
            #     "base_url": "https://api.anthropic.com/v1/messages",
            #     "models": {
            #         "claude": "claude-3-5-sonnet-20241022"
            #     }
            # },
            # AIProvider.OPENAI: {
            #     "api_key": os.getenv("OPENAI_API_KEY"),
            #     "base_url": "https://api.openai.com/v1/chat/completions",
            #     "models": {
            #         "gpt4": "gpt-4o-mini",
            #         "gpt35": "gpt-3.5-turbo"
            #     }
            # },
            # AIProvider.GROK: {
            #     "api_key": os.getenv("GROK_API_KEY"),
            #     "base_url": "https://api.x.ai/v1/chat/completions",
            #     "models": {
            #         "grok": "grok-beta"
            #     }
            # }
        }
        
        # 当前配置 - 可以通过环境变量或配置文件修改
        self.current_provider = AIProvider.OPENROUTER  # 改为GOOGLE_STUDIO测试Google AI Studio
        self.current_model = "gemini_flash"  # 改为"flash"测试Google AI Studio
        
    async def call_ai(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1000) -> Optional[str]:
        """统一的AI调用接口"""
        
        provider_config = self.providers.get(self.current_provider)
        if not provider_config or not provider_config["api_key"]:
            print(f"Provider {self.current_provider.value} not configured")
            return None
            
        model_name = provider_config["models"].get(self.current_model)
        if not model_name:
            print(f"Model {self.current_model} not found for provider {self.current_provider.value}")
            return None
            
        try:
            if self.current_provider == AIProvider.GOOGLE_STUDIO:
                return await self._call_google_studio(provider_config, model_name, messages, temperature, max_tokens)
            elif self.current_provider == AIProvider.OPENROUTER:
                return await self._call_openrouter(provider_config, model_name, messages, temperature, max_tokens)
            # elif self.current_provider == AIProvider.ANTHROPIC:
            #     return await self._call_anthropic(provider_config, model_name, messages, temperature, max_tokens)
            # elif self.current_provider == AIProvider.OPENAI:
            #     return await self._call_openai(provider_config, model_name, messages, temperature, max_tokens)
            # elif self.current_provider == AIProvider.GROK:
            #     return await self._call_grok(provider_config, model_name, messages, temperature, max_tokens)
            else:
                print(f"Provider {self.current_provider.value} not implemented")
                return None
                
        except Exception as e:
            print(f"AI call failed for {self.current_provider.value}: {e}")
            return None
    
    async def _call_google_studio(self, config: Dict, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[str]:
        """调用Google AI Studio API"""
        
        # 转换消息格式为Google格式
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                # Google API没有system role，将其合并到user消息中
                if contents and contents[-1]["role"] == "user":
                    contents[-1]["parts"][0]["text"] = msg["content"] + "\n\n" + contents[-1]["parts"][0]["text"]
                else:
                    contents.append({
                        "role": "user",
                        "parts": [{"text": msg["content"]}]
                    })
            elif msg["role"] == "user":
                contents.append({
                    "role": "user", 
                    "parts": [{"text": msg["content"]}]
                })
            elif msg["role"] == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        url = f"{config['base_url']}/{model}:generateContent?key={config['api_key']}"
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            
            if response.status_code != 200:
                print(f"Google Studio API error: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            
            if "candidates" in result and result["candidates"]:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    return candidate["content"]["parts"][0]["text"]
            
            return None
    
    async def _call_openrouter(self, config: Dict, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[str]:
        """调用OpenRouter API"""
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["base_url"], headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"OpenRouter API error: {response.status_code} - {response.text}")
                return None
                
            result = response.json()
            return result['choices'][0]['message']['content']
    
    # async def _call_anthropic(self, config: Dict, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[str]:
    #     """调用Anthropic Claude API"""
    #     
    #     # 提取system消息
    #     system_message = ""
    #     claude_messages = []
    #     
    #     for msg in messages:
    #         if msg["role"] == "system":
    #             system_message += msg["content"] + "\n"
    #         else:
    #             claude_messages.append(msg)
    #     
    #     headers = {
    #         "x-api-key": config['api_key'],
    #         "Content-Type": "application/json",
    #         "anthropic-version": "2023-06-01"
    #     }
    #     
    #     payload = {
    #         "model": model,
    #         "max_tokens": max_tokens,
    #         "temperature": temperature,
    #         "system": system_message.strip(),
    #         "messages": claude_messages
    #     }
    #     
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(config["base_url"], headers=headers, json=payload)
    #         
    #         if response.status_code != 200:
    #             print(f"Anthropic API error: {response.status_code} - {response.text}")
    #             return None
    #             
    #         result = response.json()
    #         return result['content'][0]['text']
    
    # async def _call_openai(self, config: Dict, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[str]:
    #     """调用OpenAI API"""
    #     
    #     headers = {
    #         "Authorization": f"Bearer {config['api_key']}",
    #         "Content-Type": "application/json"
    #     }
    #     
    #     payload = {
    #         "model": model,
    #         "messages": messages,
    #         "temperature": temperature,
    #         "max_tokens": max_tokens
    #     }
    #     
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(config["base_url"], headers=headers, json=payload)
    #         
    #         if response.status_code != 200:
    #             print(f"OpenAI API error: {response.status_code} - {response.text}")
    #             return None
    #             
    #         result = response.json()
    #         return result['choices'][0]['message']['content']
    
    # async def _call_grok(self, config: Dict, model: str, messages: List[Dict], temperature: float, max_tokens: int) -> Optional[str]:
    #     """调用Grok API"""
    #     
    #     headers = {
    #         "Authorization": f"Bearer {config['api_key']}",
    #         "Content-Type": "application/json"
    #     }
    #     
    #     payload = {
    #         "model": model,
    #         "messages": messages,
    #         "temperature": temperature,
    #         "max_tokens": max_tokens
    #     }
    #     
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post(config["base_url"], headers=headers, json=payload)
    #         
    #         if response.status_code != 200:
    #             print(f"Grok API error: {response.status_code} - {response.text}")
    #             return None
    #             
    #         result = response.json()
    #         return result['choices'][0]['message']['content']
    
    def switch_provider(self, provider: AIProvider, model: str):
        """切换AI提供商和模型"""
        if provider in self.providers and model in self.providers[provider]["models"]:
            self.current_provider = provider
            self.current_model = model
            print(f"Switched to {provider.value} - {model}")
        else:
            print(f"Invalid provider {provider.value} or model {model}")
    
    def get_current_config(self) -> Dict[str, str]:
        """获取当前配置信息"""
        return {
            "provider": self.current_provider.value,
            "model": self.current_model,
            "model_name": self.providers[self.current_provider]["models"][self.current_model]
        }