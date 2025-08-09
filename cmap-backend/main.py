# main.py - 简化版本，专为小项目设计

import os
import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# 简单日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 获取API密钥
def get_api_key():
    # 先从环境变量取，再从文件取
    key = os.getenv("ANTHROPIC_API_KEY")
    if key:
        return key
    
    # 从本地文件取（开发用）
    try:
        with open("API.env", 'r') as f:
            for line in f:
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except:
        pass
    
    return None

CLAUDE_API_KEY = get_api_key()

# 创建应用
app = FastAPI(title="LIFEX Loan Agent", version="1.0-simple")

# 🔧 最简CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# 加载智能服务
unified_service = None
try:
    from unified_intelligent_service import UnifiedIntelligentService
    unified_service = UnifiedIntelligentService()
    logger.info("✅ 服务加载成功")
except Exception as e:
    logger.error(f"❌ 服务加载失败: {e}")

# 根路径
@app.get("/")
async def root():
    return {
        "message": "LIFEX Loan Agent API",
        "status": "running",
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
        session_id = data.get("session_id", f"session_{int(os.times().elapsed)}")
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
        
        # 检查服务
        if not unified_service:
            return JSONResponse(
                content={
                    "reply": "Hello! I'm your AI loan advisor. How can I help you with your loan requirements today?",
                    "session_id": session_id,
                    "stage": "greeting",
                    "customer_profile": {},
                    "recommendations": [],
                    "next_questions": [],
                    "round_count": 1,
                    "status": "basic_mode"
                }
            )
        
        if not CLAUDE_API_KEY:
            return JSONResponse(
                content={
                    "reply": "AI service is temporarily unavailable. Please try again later.",
                    "session_id": session_id,
                    "stage": "error",
                    "customer_profile": {},
                    "recommendations": [],
                    "next_questions": [],
                    "round_count": 1,
                    "status": "no_api_key"
                }
            )
        
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
                "stage": "error",
                "customer_profile": {},
                "recommendations": [],
                "next_questions": [],
                "round_count": 1,
                "status": "server_error"
            }
        )

# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting LIFEX Loan Agent on port {port}")
    print(f"✅ AI Service: {'Ready' if unified_service else 'Not Available'}")
    print(f"✅ API Key: {'Configured' if CLAUDE_API_KEY else 'Missing'}")
    
    uvicorn.run(app, host="0.0.0.0", port=port)