import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.utils.openrouter_client import chat_with_agent


# 加载环境变量（读取 API.env 文件）
load_dotenv(dotenv_path="API.env")

# 从环境变量中读取 OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # ⚠️注意变量名
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 创建 FastAPI 应用
app = FastAPI(
    title="Car Loan AI Agent",
    description="AI agent backend for car loan company",
    version="0.1"
)

# 添加 CORS 中间件，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 接口挂载
app.include_router(api_router)

# AI 聊天接口
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "google/gemini-2-0-flash-experimental",  # ✅ 模型名称必须用 OpenRouter 提供的
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return {"reply": f"Error: {response.status_code} - {response.text}"}

    result = response.json()
    reply = result['choices'][0]['message']['content']
    return {"reply": reply}
