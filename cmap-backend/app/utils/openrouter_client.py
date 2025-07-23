import os
import httpx
from dotenv import load_dotenv

# 加载环境变量（API.env）
load_dotenv(dotenv_path="API.env")

async def chat_with_agent(message: str):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "HTTP-Referer": "https://yourprojectsite.com",  # 任意域名也行
    }

    payload = {
        "model": "google/gemini-pro-1.5-flash",  # 也可以换成你在 openrouter 上选的其他模型
        "messages": [{"role": "user", "content": message}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )

        # 错误处理（可选）
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
