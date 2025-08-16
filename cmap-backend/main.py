# main.py - 简化修复版本
import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import httpx
import time

# Load environment variables
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="LIFEX Car Loan AI Agent",
    description="AI assistant for car loan recommendations",
    version="2.3-fixed"
)

# 配置CORS - 添加您的前端URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5173",
        "https://lifex-car-loan-ai-agent.onrender.com",
        "https://cmap-frontend.onrender.com",  # 添加您的前端域名
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 全局变量
sessions = {}
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "message": "LIFEX Car Loan AI Agent is running",
        "version": "2.3-fixed",
        "features": {
            "api_key_configured": bool(OPENROUTER_API_KEY),
            "cors_enabled": True
        }
    }

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "LIFEX Car Loan AI Agent API",
        "status": "running",
        "health_check": "/health",
        "chat_endpoint": "/chat"
    }

# 简化的聊天端点
@app.post("/chat")
async def chat_endpoint(request: Request):
    """处理聊天请求"""
    try:
        # 获取请求数据
        data = await request.json()
        message = data.get("message", "")
        session_id = data.get("session_id", f"session_{time.time()}")
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required"}
            )
        
        # 如果有OpenRouter API Key，调用AI服务
        if OPENROUTER_API_KEY:
            try:
                ai_response = await call_openrouter_api(message)
                response = {
                    "reply": ai_response,
                    "session_id": session_id,
                    "status": "success",
                    "timestamp": time.time()
                }
            except Exception as e:
                print(f"AI API调用失败: {e}")
                response = {
                    "reply": "I'm currently experiencing technical difficulties with the AI service. Please try again in a moment.",
                    "session_id": session_id,
                    "status": "fallback",
                    "timestamp": time.time()
                }
        else:
            # 回退响应
            response = {
                "reply": "Hello! I'm Agent X. I'm here to help you with car loan recommendations. However, I'm currently in basic mode. Please tell me about your loan needs and I'll do my best to assist you.",
                "session_id": session_id,
                "status": "basic_mode",
                "timestamp": time.time()
            }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"聊天端点错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "Sorry, I'm experiencing technical difficulties.",
                "status": "error"
            }
        )

async def call_openrouter_api(message: str) -> str:
    """调用OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {
                "role": "system",
                "content": "You are Agent X, a helpful car loan advisor. Provide friendly, informative responses about car loans and financing options."
            },
            {
                "role": "user", 
                "content": message
            }
        ],
        "max_tokens": 500
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API调用失败: {response.status_code}")

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": "Please try again later"}
    )

# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 启动LIFEX Car Loan AI Agent服务器...")
    print(f"📍 服务器地址: {host}:{port}")
    print(f"🔑 API Key配置: {'✅' if OPENROUTER_API_KEY else '❌'}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # 生产环境关闭reload
        log_level="info"
    )