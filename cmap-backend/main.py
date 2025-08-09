# main.py - Render专用简化版

import os
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# 简单日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取API密钥 - 只从环境变量
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 创建应用
app = FastAPI(title="LIFEX Loan Agent", version="1.1-render")

# CORS - 允许所有（Render部署用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 加载AI服务
unified_service = None
try:
    from unified_intelligent_service import UnifiedIntelligentService
    unified_service = UnifiedIntelligentService()
    logger.info("✅ AI服务加载成功")
except Exception as e:
    logger.error(f"❌ AI服务加载失败: {e}")

# 根路径
@app.get("/")
async def root():
    return {
        "message": "LIFEX Loan Agent API",
        "status": "running",
        "version": "1.1-render",
        "services": {
            "ai_service": "available" if unified_service else "unavailable",
            "api_key": "configured" if CLAUDE_API_KEY else "missing"
        }
    }

# 健康检查
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "unified_service": "available" if unified_service else "unavailable",
        "claude_api": "configured" if CLAUDE_API_KEY else "missing"
    }

# CORS测试
@app.get("/cors-test")
async def cors_test():
    return {"message": "CORS OK", "status": "success"}

# 主聊天端点
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(asyncio.get_event_loop().time())}")
        chat_history = data.get("history", [])
        
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "reply": "Please provide a message",
                    "session_id": session_id,
                    "status": "error"
                }
            )
        
        # 基础模式（没有AI服务时）
        if not unified_service:
            return JSONResponse(content={
                "reply": "Hello! I'm your AI loan advisor. How can I help you with your loan requirements today?",
                "session_id": session_id,
                "stage": "greeting",
                "customer_profile": {},
                "recommendations": [],
                "next_questions": ["Tell me about your loan needs"],
                "round_count": 1,
                "status": "basic_mode"
            })
        
        # 没有API密钥
        if not CLAUDE_API_KEY:
            return JSONResponse(content={
                "reply": "AI service is temporarily unavailable. Please try again later.",
                "session_id": session_id,
                "stage": "error",
                "customer_profile": {},
                "recommendations": [],
                "next_questions": [],
                "round_count": 1,
                "status": "no_api_key"
            })
        
        # 调用AI服务
        result = await unified_service.process_conversation(
            user_message=user_message,
            session_id=session_id,
            chat_history=chat_history
        )
        
        # 返回结果
        return JSONResponse(content={
            "reply": result.get("reply", "Sorry, I couldn't process that."),
            "session_id": result.get("session_id", session_id),
            "stage": result.get("stage", "greeting"),
            "customer_profile": result.get("customer_profile", {}),
            "recommendations": result.get("recommendations", []),
            "next_questions": result.get("next_questions", []),
            "round_count": result.get("round_count", 1),
            "status": result.get("status", "success")
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "reply": "Service temporarily unavailable. Please try again.",
                "session_id": session_id if 'session_id' in locals() else "error",
                "status": "server_error"
            }
        )

# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 LIFEX Loan Agent starting on port {port}")
    print(f"✅ AI Service: {'Ready' if unified_service else 'Not Available'}")
    print(f"✅ API Key: {'Configured' if CLAUDE_API_KEY else 'Missing'}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)