# main.py - 最终精简版本，基于你的unified_intelligent_service设计

import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# 安全的环境变量加载
def load_claude_api_key():
    """安全地加载Claude API密钥"""
    
    # 从系统环境变量获取
    key = os.getenv("ANTHROPIC_API_KEY")
    
    if key:
        print(f"✅ 从环境变量加载API密钥: {key[:10]}...{key[-4:]}")
        return key
    
    # 从本地文件获取
    if os.path.exists("API.env"):
        try:
            with open("API.env", 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        print(f"✅ 从API.env文件加载密钥: {key[:10]}...{key[-4:]}")
                        return key
        except Exception as e:
            print(f"⚠️ 读取API.env失败: {e}")
    
    print("❌ 未找到ANTHROPIC_API_KEY")
    return None

# 加载API密钥
CLAUDE_API_KEY = load_claude_api_key()

# 创建FastAPI应用
app = FastAPI(
    title="Car Loan AI Agent - Final Streamlined",
    description="Streamlined AI loan advisor using unified intelligent service",
    version="7.0-final-streamlined"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 尝试加载统一智能服务
try:
    # 假设unified_intelligent_service.py在app/services/目录下
    sys.path.append('app/services')
    from unified_intelligent_service import UnifiedIntelligentService
    UNIFIED_SERVICE_AVAILABLE = True
    print("✅ Unified Intelligent Service loaded")
except ImportError:
    try:
        # 或者直接在当前目录
        from unified_intelligent_service import UnifiedIntelligentService
        UNIFIED_SERVICE_AVAILABLE = True
        print("✅ Unified Intelligent Service loaded from current directory")
    except ImportError as e:
        print(f"❌ Unified service not available: {e}")
        UNIFIED_SERVICE_AVAILABLE = False

# 初始化服务
unified_service = None
if UNIFIED_SERVICE_AVAILABLE:
    try:
        unified_service = UnifiedIntelligentService()
        print("✅ Unified service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize unified service: {e}")

@app.post("/chat")
async def chat(request: Request):
    """精简的聊天端点 - 使用你的unified intelligent service"""
    try:
        data = await request.json()
        user_message = data.get("message", "")
        session_id = data.get("session_id", "default")
        chat_history = data.get("history", [])
        
        if not user_message:
            return {"reply": "Please provide a message", "status": "error"}
        
        # 检查服务可用性
        if not UNIFIED_SERVICE_AVAILABLE or not unified_service:
            return {
                "reply": "Service not available. Please check your unified_intelligent_service.py file.",
                "status": "error",
                "error_detail": "unified_intelligent_service not loaded"
            }
        
        if not CLAUDE_API_KEY:
            return {
                "reply": "Claude API not configured. Please check your API.env file.",
                "status": "error",
                "error_detail": "ANTHROPIC_API_KEY missing"
            }
        
        # 使用你的统一智能服务处理对话
        result = await unified_service.process_conversation(
            user_message=user_message,
            session_id=session_id,
            chat_history=chat_history
        )
        
        # 返回结果（保持与你的设计一致）
        return {
            "reply": result.get("reply"),
            "session_id": result.get("session_id"),
            "stage": result.get("stage"),
            "customer_profile": result.get("customer_profile"),
            "recommendations": result.get("recommendations", []),
            "next_questions": result.get("next_questions", []),
            "round_count": result.get("round_count"),
            "status": result.get("status", "success"),
            "ai_provider": "unified-intelligent-service",
            "version": "7.0-final-streamlined"
        }
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return {
            "reply": "I'm experiencing technical difficulties. Please try again.",
            "status": "error",
            "error_detail": str(e)
        }

@app.get("/health")
async def health_check():
    """健康检查"""
    service_status = "available" if UNIFIED_SERVICE_AVAILABLE and unified_service else "unavailable"
    
    # 检查产品文档加载状态
    docs_status = {}
    if unified_service:
        try:
            docs_status = {
                lender: "loaded" if doc and len(doc) > 100 else "missing"
                for lender, doc in unified_service.product_docs.items()
            }
        except:
            docs_status = {"error": "could not check docs"}
    
    return {
        "status": "healthy",
        "version": "7.0-final-streamlined",
        "unified_service": service_status,
        "claude_api": "configured" if CLAUDE_API_KEY else "missing",
        "product_docs": docs_status,
        "features": {
            "conversation_stages": UNIFIED_SERVICE_AVAILABLE,
            "mvp_extraction": UNIFIED_SERVICE_AVAILABLE,
            "product_matching": UNIFIED_SERVICE_AVAILABLE,
            "round_limits": UNIFIED_SERVICE_AVAILABLE,
            "preference_collection": UNIFIED_SERVICE_AVAILABLE
        },
        "design_philosophy": "Streamlined conversation with intelligent MVP collection and product matching"
    }

@app.get("/conversation-status/{session_id}")
async def get_conversation_status(session_id: str):
    """获取对话状态"""
    if not unified_service:
        return {"error": "Service not available"}
    
    try:
        status = await unified_service.get_conversation_status(session_id)
        return status
    except Exception as e:
        return {"error": f"Failed to get status: {str(e)}"}

@app.post("/reset-conversation")
async def reset_conversation(request: Request):
    """重置对话"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        if unified_service and hasattr(unified_service, 'conversation_states'):
            if session_id in unified_service.conversation_states:
                del unified_service.conversation_states[session_id]
        
        return {
            "status": "success",
            "message": f"Conversation {session_id} reset",
            "session_id": session_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/test-service")
async def test_service():
    """测试统一服务功能"""
    if not unified_service:
        return {
            "status": "error",
            "message": "Unified service not available",
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
        
        result = await unified_service.process_conversation(
            user_message=test_message,
            session_id=test_session,
            chat_history=[]
        )
        
        # 清理测试会话
        if test_session in unified_service.conversation_states:
            del unified_service.conversation_states[test_session]
        
        return {
            "status": "success",
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
        return {
            "status": "error",
            "message": f"Service test failed: {str(e)}",
            "recommendations": [
                "Check Claude API key in API.env",
                "Verify product documentation files exist",
                "Check internet connection for API calls"
            ]
        }

@app.get("/debug-info")
async def debug_info():
    """调试信息"""
    debug_data = {
        "environment": {
            "python_path": sys.path,
            "current_directory": os.getcwd(),
            "api_env_exists": os.path.exists("API.env"),
            "claude_api_configured": bool(CLAUDE_API_KEY)
        },
        "service_status": {
            "unified_service_available": UNIFIED_SERVICE_AVAILABLE,
            "service_initialized": unified_service is not None
        },
        "recommendations": []
    }
    
    # 生成调试建议
    if not UNIFIED_SERVICE_AVAILABLE:
        debug_data["recommendations"].append("Place unified_intelligent_service.py in the same directory as main.py or in app/services/")
    
    if not CLAUDE_API_KEY:
        debug_data["recommendations"].append("Add ANTHROPIC_API_KEY to your API.env file")
    
    if unified_service:
        try:
            debug_data["product_docs"] = {
                lender: len(doc) for lender, doc in unified_service.product_docs.items()
            }
            debug_data["conversation_states"] = len(unified_service.conversation_states)
        except:
            debug_data["service_error"] = "Could not access service properties"
    
    return debug_data

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting Final Streamlined Car Loan AI Agent")
    print(f"Unified Service: {'✅' if UNIFIED_SERVICE_AVAILABLE else '❌'}")
    print(f"Claude API: {'✅' if CLAUDE_API_KEY else '❌'}")
    
    if not UNIFIED_SERVICE_AVAILABLE:
        print("\n⚠️ unified_intelligent_service.py not found!")
        print("📁 Please ensure the file is in one of these locations:")
        print("   - Same directory as main.py")
        print("   - app/services/unified_intelligent_service.py")
    
    if not CLAUDE_API_KEY:
        print("\n⚠️ Claude API key not configured!")
        print("📝 Add to API.env: ANTHROPIC_API_KEY=sk-ant-your-key-here")
    
    if UNIFIED_SERVICE_AVAILABLE and CLAUDE_API_KEY:
        print("\n✅ All systems ready!")
        print("🎯 Features enabled:")
        print("   - Intelligent conversation stages")
        print("   - MVP field extraction")
        print("   - Product matching with Claude")
        print("   - 4-round conversation limit")
        print("   - Preference collection")
    
    print(f"\n🌐 Starting server on http://localhost:8000")
    print("📋 API endpoints:")
    print("   POST /chat - Main chat endpoint")
    print("   GET /health - Health check")
    print("   GET /test-service - Test service functionality")
    print("   GET /debug-info - Debug information")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

# 额外的工具函数
def check_file_structure():
    """检查文件结构"""
    files_to_check = [
        "unified_intelligent_service.py",
        "app/services/unified_intelligent_service.py",
        "API.env",
        "Angle.md",
        "BFS.md",
        "FCAU.md",
        "RAF.md"
    ]
    
    status = {}
    for file_path in files_to_check:
        status[file_path] = "✅ Found" if os.path.exists(file_path) else "❌ Missing"
    
    return status

# 运行前的文件检查
if __name__ == "__main__":
    print("\n📁 File Structure Check:")
    file_status = check_file_structure()
    for file_path, status in file_status.items():
        print(f"   {file_path}: {status}")
