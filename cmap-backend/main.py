import os
from openai import OpenAI
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router

# 加载环境变量（读取 .env 文件）
load_dotenv(dotenv_path="API.env")

print("OPENAI_API_KEY =", os.getenv("OPENAI_API_KEY"))

# 创建 OpenAI 客户端（新版 SDK 用法）
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": user_input}]
    )

    reply = response.choices[0].message.content
    return {"reply": reply}
