import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.utils.openrouter_client import chat_with_agent
from app.services.prompt_service import PromptService

# 加载环境变量（读取 API.env 文件）
load_dotenv(dotenv_path="API.env")

# 从环境变量中读取 OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
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

# 初始化 Prompt 服务
prompt_service = PromptService()

# 接口挂载
app.include_router(api_router)

# AI 聊天接口 - 使用新的prompt系统
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_input = data.get("message")
        chat_history = data.get("history", [])  # 获取聊天历史（可选）
        
        if not user_input:
            raise HTTPException(status_code=400, detail="消息内容不能为空")

        # 使用 prompt_service 创建完整的消息列表
        messages = prompt_service.create_chat_messages(user_input, chat_history)

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": messages,  # 使用新的消息格式
            "temperature": 0.7,  # 添加一些创造性，但保持专业
            "max_tokens": 1000   # 限制回复长度
        }

        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return {"reply": f"Error: {response.status_code} - {response.text}"}

        result = response.json()
        reply = result['choices'][0]['message']['content']
        
        # 返回回复和用户需求分析（可选）
        user_requirements = prompt_service.extract_user_requirements(user_input)
        
        return {
            "reply": reply,
            "user_requirements": user_requirements,  # 这个信息可以用于后续分析
            "status": "success"
        }
        
    except Exception as e:
        return {
            "reply": "抱歉，系统出现了一些问题，请稍后再试或联系客服。",
            "status": "error",
            "error_detail": str(e)
        }

# 健康检查接口
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Car Loan AI Agent is running",
        "prompt_system": "loaded" if prompt_service.product_info != "产品信息暂时不可用" else "error"
    }
