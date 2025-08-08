# main.py - 修复 CORS 和部署问题

import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 安全的环境变量加载
def load_claude_api_key():
    """安全地加载Claude API密钥"""
    
    # 从系统环境变量获取
    key = os.getenv("ANTHROPIC_API_KEY")
    
    if key:
        logger.info(f"✅ 从环境变量加载API密钥: {key[:10]}...{key[-4:]}")
        return key
    
    # 从本地文件获取
    if os.path.exists("API.env"):
        try:
            with open("API.env", 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        logger.info(f"✅ 从API.env文件加载密钥: {key[:10]}...{key[-4:]}")
                        return key
        except Exception as e:
            logger.warning(f"⚠️ 读取API.env失败: {e}")
    
    logger.error("❌ 未找到ANTHROPIC_API_KEY")
    return None

# 加载API密钥
CLAUDE_API_KEY = load_claude_api_key()

# 创建FastAPI应用
app = FastAPI(
    title="Car Loan AI Agent - CORS Fixed",
    description="AI loan advisor with fixed CORS configuration",
    version="8.0-cors-fixed"
)

# 🔧 修复的 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://netlify.app",
        "https://*.netlify.app",
        "https://vercel.app", 
        "https://*.vercel.app",
        "https://surge.sh",
        "https://*.surge.sh",
        "https://github.io",
        "https://*.github.io",
        "https://pages.dev",
        "https://*.pages.dev",
        # 如果前端部署在这些域名，请添加具体的域名
        # "https://your-frontend-domain.netlify.app",
        # "https://your-frontend-domain.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "User-Agent",
        "Cache-Control",
        "Pragma"
    ],
)

# 尝试加载统一智能服务
try:
    sys.path.append('app/services')
    from unified_intelligent_service import UnifiedIntelligentService
    UNIFIED_SERVICE_AVAILABLE = True
    logger.info("✅ Unified Intelligent Service loaded")
except ImportError:
    try:
        from unified_intelligent_service import UnifiedIntelligentService
        UNIFIED_SERVICE_AVAILABLE = True
        logger.info("✅ Unified Intelligent Service loaded from current directory")
    except ImportError as e:
        logger.error(f"❌ Unified service not available: {e}")
        UNIFIED_SERVICE_AVAILABLE = False

# 初始化服务
unified_service = None
if UNIFIED_SERVICE_AVAILABLE:
    try:
        unified_service = UnifiedIntelligentService()
        logger.info("✅ Unified service initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize unified service: {e}")

# 🆕 添加 CORS 预检处理
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """处理 CORS 预检请求"""
    logger.info(f"OPTIONS request for path: {full_path}")
    logger.info(f"Origin: {request.headers.get('origin', 'No origin')}")
    
    return {
        "message": "CORS preflight handled",
        "path": full_path,
        "origin": request.headers.get('origin', 'No origin')
    }

# 添加根路径处理
@app.get("/")
async def root(request: Request):
    """根路径处理"""
    origin = request.headers.get('origin', 'No origin')
    user_agent = request.headers.get('user-agent', 'No user agent')
    
    logger.info(f"Root request from origin: {origin}")
    
    return {
        "message": "Car Loan AI Agent API is running",
        "version": "8.0-cors-fixed",
        "status": "online",
        "timestamp": os.environ.get('RENDER_SERVICE_START_TIME', 'unknown'),
        "origin": origin,
        "health_endpoint": "/health",
        "chat_endpoint": "/chat",
        "cors_test": "If you see this, CORS is working"
    }

@app.post("/chat")
async def chat(request: Request):
    """聊天端点 - 增强错误处理和日志"""
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"Chat request from origin: {origin}")
    
    try:
        data = await request.json()
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default")
        chat_history = data.get("history", [])
        
        logger.info(f"📨 收到聊天请求: {user_message[:50]}...")
        logger.info(f"Session: {session_id}, History length: {len(chat_history)}")
        
        if not user_message:
            return {"reply": "Please provide a message", "status": "error"}
        
        # 检查服务可用性
        if not UNIFIED_SERVICE_AVAILABLE or not unified_service:
            logger.warning("⚠️ Unified service not available, returning fallback response")
            return {
                "reply": "I'm here to help with your loan requirements. However, the advanced features are currently unavailable. Please describe what you're looking to finance and I'll do my best to assist you.",
                "status": "basic_mode",
                "session_id": session_id,
                "recommendations": [],
                "next_questions": [],
                "round_count": 1,
                "error_detail": "unified_intelligent_service not loaded"
            }
        
        if not CLAUDE_API_KEY:
            logger.warning("⚠️ Claude API not configured")
            return {
                "reply": "I'm currently experiencing technical difficulties with my AI processing. Please try again later.",
                "status": "error",
                "session_id": session_id,
                "recommendations": [],
                "next_questions": [],
                "round_count": 1,
                "error_detail": "ANTHROPIC_API_KEY missing"
            }
        
        # 使用统一智能服务处理对话
        result = await unified_service.process_conversation(
            user_message=user_message,
            session_id=session_id,
            chat_history=chat_history
        )
        
        logger.info(f"✅ 处理完成: {result.get('status', 'unknown')}")
        
        # 确保返回所有必需字段
        response = {
            "reply": result.get("reply", "I apologize, but I couldn't process your request properly."),
            "session_id": result.get("session_id", session_id),
            "stage": result.get("stage", "greeting"),
            "customer_profile": result.get("customer_profile", {}),
            "recommendations": result.get("recommendations", []),
            "next_questions": result.get("next_questions", []),
            "round_count": result.get("round_count", 1),
            "status": result.get("status", "success"),
            "ai_provider": "unified-intelligent-service",
            "version": "8.0-cors-fixed"
        }
        
        # 记录推荐数量
        if response["recommendations"]:
            logger.info(f"📊 返回 {len(response['recommendations'])} 个推荐")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "reply": "I'm experiencing technical difficulties. Please try again in a moment.",
            "status": "error",
            "session_id": session_id if 'session_id' in locals() else "error_session",
            "recommendations": [],
            "next_questions": [],
            "round_count": 1,
            "error_detail": str(e)
        }

@app.get("/health")
async def health_check(request: Request):
    """增强的健康检查"""
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"Health check from origin: {origin}")
    
    service_status = "available" if UNIFIED_SERVICE_AVAILABLE and unified_service else "unavailable"
    
    # 检查产品文档加载状态
    docs_status = {}
    if unified_service:
        try:
            docs_status = {
                lender: "loaded" if doc and len(doc) > 100 else "missing"
                for lender, doc in unified_service.product_docs.items()
            }
        except Exception as e:
            docs_status = {"error": f"could not check docs: {str(e)}"}
    
    health_data = {
        "status": "healthy",
        "version": "8.0-cors-fixed",
        "unified_service": service_status,
        "claude_api": "configured" if CLAUDE_API_KEY else "missing",
        "product_docs": docs_status,
        "origin": origin,
        "timestamp": os.environ.get('RENDER_SERVICE_START_TIME', 'unknown'),
        "environment": {
            "python_version": sys.version,
            "platform": sys.platform,
            "working_directory": os.getcwd(),
        },
        "features": {
            "conversation_stages": UNIFIED_SERVICE_AVAILABLE,
            "mvp_extraction": UNIFIED_SERVICE_AVAILABLE,
            "product_matching": UNIFIED_SERVICE_AVAILABLE,
            "round_limits": UNIFIED_SERVICE_AVAILABLE,
            "preference_collection": UNIFIED_SERVICE_AVAILABLE
        },
        "cors_enabled": True,
        "endpoints": {
            "chat": "/chat",
            "health": "/health", 
            "root": "/",
            "test": "/test-service"
        }
    }
    
    logger.info(f"📊 健康检查完成: {health_data['status']}")
    return health_data

# 🆕 添加简单的 CORS 测试端点
@app.get("/cors-test")
async def cors_test(request: Request):
    """CORS 连接测试"""
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"CORS test from origin: {origin}")
    
    return {
        "message": "CORS test successful!",
        "origin": origin,
        "headers": dict(request.headers),
        "timestamp": "2024-12-19T10:00:00Z"
    }

@app.get("/conversation-status/{session_id}")
async def get_conversation_status(session_id: str, request: Request):
    """获取对话状态"""
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"Conversation status request from origin: {origin}")
    
    if not unified_service:
        return {"error": "Service not available", "session_id": session_id}
    
    try:
        status = await unified_service.get_conversation_status(session_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get conversation status: {e}")
        return {"error": f"Failed to get status: {str(e)}", "session_id": session_id}

@app.post("/reset-conversation")
async def reset_conversation(request: Request):
    """重置对话"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        logger.info(f"Resetting conversation: {session_id}")
        
        if unified_service and hasattr(unified_service, 'conversation_states'):
            if session_id in unified_service.conversation_states:
                del unified_service.conversation_states[session_id]
                logger.info(f"Conversation {session_id} reset successfully")
        
        return {
            "status": "success",
            "message": f"Conversation {session_id} reset",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Failed to reset conversation: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/test-service")
async def test_service(request: Request):
    """测试统一服务功能"""
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"Service test from origin: {origin}")
    
    if not unified_service:
        return {
            "status": "error",
            "message": "Unified service not available",
            "origin": origin,
            "recommendations": [
                "Check if unified_intelligent_service.py exists",
                "Ensure all dependencies are installed", 
                "Check the file path and imports"
            ]
        }
    
    try:
        # 测试基本功能
        test_session = "test_session"
        test_message = "Hi, I need a business loan for a truck. I own property and have good credit."
        
        logger.info("Starting service test...")
        
        result = await unified_service.process_conversation(
            user_message=test_message,
            session_id=test_session,
            chat_history=[]
        )
        
        # 清理测试会话
        if test_session in unified_service.conversation_states:
            del unified_service.conversation_states[test_session]
        
        logger.info("Service test completed successfully")
        
        return {
            "status": "success",
            "origin": origin,
            "test_result": {
                "response_generated": bool(result.get("reply")),
                "stage_detected": result.get("stage"),
                "round_count": result.get("round_count"),
                "has_questions": bool(result.get("next_questions")),
                "response_length": len(result.get("reply", ""))
            },
            "sample_response": result.get("reply", "")[:200] + "..." if len(result.get("reply", "")) > 200 else result.get("reply", ""),
            "message": "Service working correctly"
        }
        
    except Exception as e:
        logger.error(f"Service test failed: {e}")
        return {
            "status": "error",
            "origin": origin,
            "message": f"Service test failed: {str(e)}",
            "recommendations": [
                "Check Claude API key in environment variables",
                "Verify product documentation files exist",
                "Check internet connection for API calls"
            ]
        }

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Car Loan AI Agent - CORS Fixed Version")
    print(f"Unified Service: {'✅' if UNIFIED_SERVICE_AVAILABLE else '❌'}")
    print(f"Claude API: {'✅' if CLAUDE_API_KEY else '❌'}")
    
    if not UNIFIED_SERVICE_AVAILABLE:
        print("\n⚠️ unified_intelligent_service.py not found!")
        print("📁 Please ensure the file is in one of these locations:")
        print("   - Same directory as main.py")
        print("   - app/services/unified_intelligent_service.py")
    
    if not CLAUDE_API_KEY:
        print("\n⚠️ Claude API key not configured!")
        print("🔧 Set environment variable: ANTHROPIC_API_KEY=sk-ant-your-key-here")
    
    if UNIFIED_SERVICE_AVAILABLE and CLAUDE_API_KEY:
        print("\n✅ All systems ready!")
        print("🎯 Features enabled:")
        print("   - Fixed CORS configuration")
        print("   - Enhanced error handling")
        print("   - Detailed logging")
        print("   - CORS test endpoint")
    
    # Render 使用环境变量 PORT
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🌐 Starting server on http://0.0.0.0:{port}")
    print("📋 API endpoints:")
    print("   GET  / - Root endpoint")
    print("   POST /chat - Main chat endpoint")
    print("   GET  /health - Health check")
    print("   GET  /cors-test - CORS connection test")
    print("   GET  /test-service - Test service functionality")
    
    uvicorn.run(app, host="0.0.0.0", port=port)