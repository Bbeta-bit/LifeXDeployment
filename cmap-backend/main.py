# main.py - 修复CORS具体域名问题

import os
import sys
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
from contextlib import asynccontextmanager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("🚀 应用启动中...")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"环境变量PORT: {os.getenv('PORT', '未设置')}")
    
    # 检查服务状态
    service_status = "可用" if UNIFIED_SERVICE_AVAILABLE and unified_service else "不可用"
    api_status = "已配置" if CLAUDE_API_KEY else "未配置"
    logger.info(f"统一服务: {service_status}")
    logger.info(f"Claude API: {api_status}")
    
    yield
    
    # 关闭时执行
    logger.info("🛑 应用关闭中...")

# 创建FastAPI应用
app = FastAPI(
    title="LIFEX Car Loan AI Agent",
    description="AI智能贷款顾问 - 修复CORS域名问题",
    version="9.1-cors-domain-fixed",
    lifespan=lifespan
)

# 🔧 修复的CORS配置 - 添加你的具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # 本地开发环境
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:3001",
        "http://localhost:8080",
        
        # 🎯 你的具体部署域名
        "https://cmap-frontend.onrender.com",  # 从日志中看到的前端域名
        "https://lifex-frontend.onrender.com", # 可能的备用域名
        
        # 其他部署平台模式
        "https://*.netlify.app",
        "https://*.vercel.app", 
        "https://*.surge.sh",
        "https://*.github.io",
        "https://*.pages.dev",
        "https://*.herokuapp.com",
        "https://*.onrender.com",  # 所有Render域名
        
        # 通配符支持（作为后备）
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有头部
    expose_headers=["*"], # 暴露所有头部
)

# 尝试加载统一智能服务
UNIFIED_SERVICE_AVAILABLE = False
unified_service = None

try:
    # 尝试多个路径
    possible_paths = [
        'app/services',
        '.',
        'services',
        '../services'
    ]
    
    for path in possible_paths:
        sys.path.insert(0, path)
        try:
            from unified_intelligent_service import UnifiedIntelligentService
            UNIFIED_SERVICE_AVAILABLE = True
            logger.info(f"✅ 从 {path} 加载统一智能服务")
            break
        except ImportError:
            continue
    
    if UNIFIED_SERVICE_AVAILABLE:
        unified_service = UnifiedIntelligentService()
        logger.info("✅ 统一服务初始化成功")
    else:
        logger.error("❌ 无法找到unified_intelligent_service.py")
        
except Exception as e:
    logger.error(f"❌ 统一服务初始化失败: {e}")
    import traceback
    traceback.print_exc()

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    import traceback
    traceback.print_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "内部服务器错误",
            "message": "服务暂时不可用，请稍后重试",
            "timestamp": str(asyncio.get_event_loop().time())
        }
    )

# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = asyncio.get_event_loop().time()
    
    # 记录请求信息
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    url = str(request.url)
    origin = request.headers.get("origin", "无来源")
    user_agent = request.headers.get("user-agent", "无用户代理")[:100]
    
    logger.info(f"📨 {method} {url} - 来源: {origin} - IP: {client_ip}")
    
    try:
        response = await call_next(request)
        process_time = asyncio.get_event_loop().time() - start_time
        
        # 特别记录CORS相关的响应
        if method == "OPTIONS":
            logger.info(f"🔍 CORS预检: {method} {url} - 状态: {response.status_code} - 来源: {origin}")
        
        logger.info(f"✅ {method} {url} - 状态: {response.status_code} - 耗时: {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = asyncio.get_event_loop().time() - start_time
        logger.error(f"❌ {method} {url} - 错误: {str(e)} - 耗时: {process_time:.3f}s")
        raise

# 🔧 改进的OPTIONS预检请求处理
@app.options("/{full_path:path}")
async def handle_options(request: Request, full_path: str):
    """处理CORS预检请求 - 修复版本"""
    origin = request.headers.get("origin", "")
    method = request.headers.get("access-control-request-method", "")
    headers = request.headers.get("access-control-request-headers", "")
    
    logger.info(f"🔍 OPTIONS预检详情:")
    logger.info(f"   路径: {full_path}")
    logger.info(f"   来源: {origin}")
    logger.info(f"   请求方法: {method}")
    logger.info(f"   请求头部: {headers}")
    
    # 检查是否为已知的前端域名
    allowed_origins = [
        "https://cmap-frontend.onrender.com",
        "https://lifex-frontend.onrender.com",
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    # 确定允许的来源
    if origin in allowed_origins or origin.endswith(".onrender.com") or "localhost" in origin:
        allowed_origin = origin
        logger.info(f"✅ 允许的来源: {origin}")
    else:
        allowed_origin = "*"
        logger.info(f"⚠️ 未知来源，使用通配符: {origin}")
    
    response_headers = {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, HEAD",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, Origin, User-Agent, Cache-Control, X-Requested-With",
        "Access-Control-Max-Age": "86400",
        "Access-Control-Allow-Credentials": "true" if allowed_origin != "*" else "false",
        "Vary": "Origin"
    }
    
    logger.info(f"📤 CORS响应头: {response_headers}")
    
    return JSONResponse(
        status_code=200,  # 确保返回200状态码
        content={
            "message": "CORS预检成功", 
            "path": full_path,
            "origin": origin,
            "allowed": True
        },
        headers=response_headers
    )

# 🔧 根路径
@app.get("/")
async def root(request: Request):
    """根路径处理"""
    origin = request.headers.get('origin', '无来源')
    
    return {
        "message": "LIFEX Car Loan AI Agent API 运行中",
        "version": "9.1-cors-domain-fixed",
        "status": "在线",
        "timestamp": str(asyncio.get_event_loop().time()),
        "origin": origin,
        "services": {
            "unified_service": "可用" if UNIFIED_SERVICE_AVAILABLE else "不可用",
            "claude_api": "已配置" if CLAUDE_API_KEY else "未配置"
        },
        "endpoints": {
            "health": "/health",
            "chat": "/chat", 
            "cors_test": "/cors-test",
            "test_service": "/test-service"
        },
        "cors_status": "已启用",
        "detected_frontend": "https://cmap-frontend.onrender.com"
    }

# 🔧 CORS测试端点
@app.get("/cors-test")
async def cors_test(request: Request):
    """CORS连接测试端点"""
    origin = request.headers.get('origin', '无来源')
    
    logger.info(f"🧪 CORS测试请求 - 来源: {origin}")
    
    return {
        "message": "CORS测试成功！",
        "origin": origin,
        "timestamp": str(asyncio.get_event_loop().time()),
        "cors_check": "passed",
        "headers_received": {
            "origin": request.headers.get("origin"),
            "user_agent": request.headers.get("user-agent", "")[:100],
            "accept": request.headers.get("accept"),
            "content_type": request.headers.get("content-type")
        },
        "server_info": {
            "version": "9.1-cors-domain-fixed",
            "python_version": sys.version.split()[0],
            "platform": sys.platform
        }
    }

# 🔧 增强的健康检查端点
@app.get("/health")
async def health_check(request: Request):
    """增强的健康检查端点"""
    origin = request.headers.get('origin', '无来源')
    
    logger.info(f"📊 健康检查请求 - 来源: {origin}")
    
    # 检查服务状态
    service_status = "available" if UNIFIED_SERVICE_AVAILABLE and unified_service else "unavailable"
    api_status = "configured" if CLAUDE_API_KEY else "missing"
    
    # 检查产品文档
    docs_status = {}
    if unified_service:
        try:
            docs_status = {
                lender: "loaded" if doc and len(doc) > 100 else "missing"
                for lender, doc in unified_service.product_docs.items()
            }
        except Exception as e:
            docs_status = {"error": f"无法检查文档: {str(e)}"}
    
    health_data = {
        "status": "healthy",
        "message": "LIFEX Car Loan AI Agent 运行正常",
        "version": "9.1-cors-domain-fixed",
        "timestamp": str(asyncio.get_event_loop().time()),
        "origin": origin,
        
        "services": {
            "unified_service": service_status,
            "claude_api": api_status,
            "product_docs": docs_status
        },
        
        "cors_info": {
            "enabled": True,
            "detected_frontend": "https://cmap-frontend.onrender.com",
            "origin_allowed": origin in ["https://cmap-frontend.onrender.com", "https://lifex-frontend.onrender.com"] or "localhost" in origin or origin == "无来源"
        },
        
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "working_directory": os.getcwd(),
            "port": os.getenv('PORT', '8000'),
            "render_service_id": os.getenv('RENDER_SERVICE_ID', '未设置')
        },
        
        "features": {
            "conversation_stages": UNIFIED_SERVICE_AVAILABLE,
            "mvp_extraction": UNIFIED_SERVICE_AVAILABLE,
            "product_matching": UNIFIED_SERVICE_AVAILABLE and bool(CLAUDE_API_KEY),
            "round_limits": UNIFIED_SERVICE_AVAILABLE,
            "preference_collection": UNIFIED_SERVICE_AVAILABLE
        },
        
        "endpoints": {
            "root": "/",
            "chat": "/chat",
            "health": "/health",
            "cors_test": "/cors-test",
            "test_service": "/test-service",
            "conversation_status": "/conversation-status/{session_id}",
            "reset_conversation": "/reset-conversation"
        }
    }
    
    logger.info(f"📊 健康检查完成: {health_data['status']} - 来源: {origin}")
    return health_data

# 🔧 增强的聊天端点
@app.post("/chat")
async def chat(request: Request):
    """主聊天端点 - 增强错误处理"""
    start_time = asyncio.get_event_loop().time()
    origin = request.headers.get('origin', '无来源')
    
    logger.info(f"💬 聊天请求 - 来源: {origin}")
    
    try:
        # 解析请求数据
        try:
            data = await request.json()
        except Exception as e:
            logger.error(f"JSON解析错误: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "reply": "请求格式错误，请检查JSON数据",
                    "status": "json_parse_error",
                    "error_detail": str(e)
                }
            )
        
        user_message = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(asyncio.get_event_loop().time())}")
        chat_history = data.get("history", [])
        
        logger.info(f"📝 消息内容: '{user_message[:50]}{'...' if len(user_message) > 50 else ''}'")
        logger.info(f"🆔 会话ID: {session_id}")
        logger.info(f"📚 历史记录长度: {len(chat_history)}")
        
        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "reply": "请提供您的消息内容",
                    "status": "empty_message",
                    "session_id": session_id,
                    "recommendations": [],
                    "next_questions": [],
                    "round_count": 1
                }
            )
        
        # 检查统一服务可用性
        if not UNIFIED_SERVICE_AVAILABLE or not unified_service:
            logger.warning("⚠️ 统一服务不可用，返回基础响应")
            return JSONResponse(
                content={
                    "reply": "您好！我是AI贷款顾问。虽然高级功能暂时不可用，但我仍然可以为您提供基本的贷款咨询服务。请告诉我您需要什么类型的贷款？",
                    "status": "basic_mode",
                    "session_id": session_id,
                    "stage": "greeting",
                    "customer_profile": {},
                    "recommendations": [],
                    "next_questions": [
                        "车辆贷款咨询",
                        "设备融资咨询", 
                        "商业贷款咨询"
                    ],
                    "round_count": 1,
                    "error_detail": "统一智能服务不可用"
                }
            )
        
        if not CLAUDE_API_KEY:
            logger.warning("⚠️ Claude API密钥未配置")
            return JSONResponse(
                content={
                    "reply": "AI处理服务暂时不可用，请稍后重试。如果问题持续，请联系技术支持。",
                    "status": "api_key_missing", 
                    "session_id": session_id,
                    "stage": "error",
                    "customer_profile": {},
                    "recommendations": [],
                    "next_questions": [],
                    "round_count": 1,
                    "error_detail": "ANTHROPIC_API_KEY未配置"
                }
            )
        
        # 调用统一智能服务
        logger.info("🤖 调用统一智能服务...")
        
        try:
            result = await unified_service.process_conversation(
                user_message=user_message,
                session_id=session_id,
                chat_history=chat_history
            )
            
            process_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ 统一服务处理完成 - 耗时: {process_time:.3f}s")
            
            # 验证并补全响应数据
            response = {
                "reply": result.get("reply", "抱歉，我无法正确处理您的请求。"),
                "session_id": result.get("session_id", session_id),
                "stage": result.get("stage", "greeting"),
                "customer_profile": result.get("customer_profile", {}),
                "recommendations": result.get("recommendations", []),
                "next_questions": result.get("next_questions", []),
                "round_count": result.get("round_count", 1),
                "status": result.get("status", "success"),
                "ai_provider": "unified-intelligent-service",
                "version": "9.1-cors-domain-fixed",
                "process_time": process_time
            }
            
            # 记录推荐数量
            if response["recommendations"]:
                logger.info(f"📊 返回 {len(response['recommendations'])} 个产品推荐")
            
            return JSONResponse(content=response)
            
        except Exception as service_error:
            logger.error(f"❌ 统一服务错误: {service_error}")
            import traceback
            traceback.print_exc()
            
            return JSONResponse(
                status_code=500,
                content={
                    "reply": "AI服务暂时遇到技术问题，请稍后重试。",
                    "status": "service_error",
                    "session_id": session_id,
                    "stage": "error",
                    "customer_profile": {},
                    "recommendations": [],
                    "next_questions": [],
                    "round_count": 1,
                    "error_detail": f"服务错误: {str(service_error)[:100]}"
                }
            )
            
    except Exception as e:
        logger.error(f"❌ 聊天端点异常: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "reply": "服务暂时不可用，请稍后重试。",
                "status": "server_error",
                "session_id": session_id if 'session_id' in locals() else "error_session",
                "stage": "error",
                "customer_profile": {},
                "recommendations": [],
                "next_questions": [],
                "round_count": 1,
                "error_detail": f"服务器错误: {str(e)[:100]}"
            }
        )

# 其他端点保持不变...
@app.get("/test-service")
async def test_service(request: Request):
    """测试统一服务功能"""
    origin = request.headers.get('origin', '无来源')
    
    logger.info(f"🧪 服务测试请求 - 来源: {origin}")
    
    if not unified_service:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": "统一服务不可用",
                "origin": origin,
                "recommendations": [
                    "检查 unified_intelligent_service.py 文件是否存在",
                    "确保所有依赖已正确安装",
                    "检查文件路径和导入配置"
                ]
            }
        )
    
    try:
        test_session = f"test_session_{int(asyncio.get_event_loop().time())}"
        test_message = "您好，我需要为卡车申请商业贷款。我有房产，信用良好。"
        
        logger.info("🚀 开始服务测试...")
        start_time = asyncio.get_event_loop().time()
        
        result = await unified_service.process_conversation(
            user_message=test_message,
            session_id=test_session,
            chat_history=[]
        )
        
        process_time = asyncio.get_event_loop().time() - start_time
        
        # 清理测试会话
        if hasattr(unified_service, 'conversation_states') and test_session in unified_service.conversation_states:
            del unified_service.conversation_states[test_session]
        
        logger.info(f"✅ 服务测试完成 - 耗时: {process_time:.3f}s")
        
        return {
            "status": "success",
            "message": "服务工作正常",
            "origin": origin,
            "test_result": {
                "response_generated": bool(result.get("reply")),
                "stage_detected": result.get("stage"),
                "round_count": result.get("round_count"),
                "has_questions": bool(result.get("next_questions")),
                "response_length": len(result.get("reply", "")),
                "process_time": process_time
            },
            "sample_response": (result.get("reply", "")[:200] + "...") if len(result.get("reply", "")) > 200 else result.get("reply", ""),
            "timestamp": str(asyncio.get_event_loop().time())
        }
        
    except Exception as e:
        logger.error(f"❌ 服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"服务测试失败: {str(e)}",
                "origin": origin,
                "recommendations": [
                    "检查Claude API密钥是否正确配置",
                    "验证产品文档文件是否存在",
                    "检查网络连接是否正常",
                    "查看服务器日志获取详细信息"
                ]
            }
        )

# 对话状态管理端点
@app.get("/conversation-status/{session_id}")
async def get_conversation_status(session_id: str, request: Request):
    """获取对话状态"""
    origin = request.headers.get('origin', '无来源')
    logger.info(f"📋 对话状态查询: {session_id} - 来源: {origin}")
    
    if not unified_service:
        return JSONResponse(
            status_code=503,
            content={"error": "服务不可用", "session_id": session_id}
        )
    
    try:
        status = await unified_service.get_conversation_status(session_id)
        return status
    except Exception as e:
        logger.error(f"获取对话状态失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"获取状态失败: {str(e)}", "session_id": session_id}
        )

@app.post("/reset-conversation")
async def reset_conversation(request: Request):
    """重置对话"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        logger.info(f"🔄 重置对话: {session_id}")
        
        if unified_service and hasattr(unified_service, 'conversation_states'):
            if session_id in unified_service.conversation_states:
                del unified_service.conversation_states[session_id]
                logger.info(f"✅ 对话 {session_id} 重置成功")
        
        return {
            "status": "success",
            "message": f"对话 {session_id} 已重置",
            "session_id": session_id,
            "timestamp": str(asyncio.get_event_loop().time())
        }
    except Exception as e:
        logger.error(f"重置对话失败: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动 LIFEX Car Loan AI Agent - CORS域名修复版")
    print("=" * 50)
    print(f"统一服务: {'✅ 可用' if UNIFIED_SERVICE_AVAILABLE else '❌ 不可用'}")
    print(f"Claude API: {'✅ 已配置' if CLAUDE_API_KEY else '❌ 未配置'}")
    print(f"检测到的前端域名: https://cmap-frontend.onrender.com")
    
    if not UNIFIED_SERVICE_AVAILABLE:
        print("\n⚠️  unified_intelligent_service.py 未找到!")
        print("📁 请确保文件位于以下位置之一:")
        print("   - 与main.py同目录")
        print("   - app/services/unified_intelligent_service.py")
        print("   - services/unified_intelligent_service.py")
    
    if not CLAUDE_API_KEY:
        print("\n⚠️  Claude API密钥未配置!")
        print("🔧 请设置环境变量: ANTHROPIC_API_KEY=sk-ant-your-key-here")
    
    if UNIFIED_SERVICE_AVAILABLE and CLAUDE_API_KEY:
        print("\n✅ 所有系统就绪!")
        print("🎯 启用的功能:")
        print("   - 修复的CORS配置（包含具体域名）")
        print("   - 增强的OPTIONS预检处理")
        print("   - 详细的CORS日志记录")
        print("   - 智能对话管理")
        print("   - 产品推荐系统")
    
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🌐 服务器启动地址: http://0.0.0.0:{port}")
    print("📋 API端点:")
    print("   GET  / - 根端点")
    print("   POST /chat - 主聊天端点")
    print("   GET  /health - 健康检查")
    print("   GET  /cors-test - CORS测试")
    print("   GET  /test-service - 服务功能测试")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info",
        access_log=True
    )