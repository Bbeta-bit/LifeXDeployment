# main.py - 修复版本：恢复unified_intelligent_service集成
import os
import json
import time
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import httpx
import threading

# 🔧 关键修复：恢复unified_intelligent_service导入
try:
    from unified_intelligent_service import UnifiedIntelligentService
    UNIFIED_SERVICE_AVAILABLE = True
    print("✅ Unified intelligent service loaded successfully")
except ImportError as e:
    print(f"⚠️ Failed to load unified service: {e}")
    UNIFIED_SERVICE_AVAILABLE = False

# 加载环境变量
load_dotenv()

# 全局变量
conversation_memory = {}
unified_service = None

# 🔧 修复：初始化unified service
if UNIFIED_SERVICE_AVAILABLE:
    try:
        unified_service = UnifiedIntelligentService()
        print("✅ Unified service initialized with product database integration")
    except Exception as e:
        print(f"❌ Failed to initialize unified service: {e}")
        UNIFIED_SERVICE_AVAILABLE = False

# API配置
ANTHROPIC_API_KEY = (
    os.getenv("ANTHROPIC_API_KEY") or 
    os.getenv("CLAUDE_API_KEY") or 
    os.getenv("OPENROUTER_API_KEY")
)

if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-ant-"):
    API_URL = "https://api.anthropic.com/v1/messages"
    API_TYPE = "anthropic"
    MODEL_NAME = "claude-3-haiku-20240307"
elif ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-or-"):
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    API_TYPE = "openrouter"
    MODEL_NAME = "anthropic/claude-3-haiku"
else:
    API_URL = None
    API_TYPE = None
    MODEL_NAME = None

print(f"🚀 LIFEX Car Loan AI Agent starting...")
print(f"🔑 API Key configured: {'✅' if ANTHROPIC_API_KEY else '❌'}")
print(f"🔗 API Type: {API_TYPE}")
print(f"🤖 Model: {MODEL_NAME}")
print(f"🧠 Unified Service: {'✅ Active' if UNIFIED_SERVICE_AVAILABLE else '❌ Disabled'}")
print(f"📁 Product Database: {'docs/' if UNIFIED_SERVICE_AVAILABLE else 'Not available'}")

def cleanup_old_sessions():
    """清理超过1小时的旧会话"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in conversation_memory.items():
        if current_time - session_data.get("created_at", 0) > 3600:
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del conversation_memory[session_id]
        print(f"🗑️ Cleaned up expired session: {session_id}")

def get_session_or_create(session_id):
    """获取或创建会话"""
    if session_id not in conversation_memory:
        conversation_memory[session_id] = {
            "messages": [],
            "customer_info": {},
            "created_at": time.time(),
            "last_active": time.time()
        }
        print(f"📝 Created new session: {session_id}")
    else:
        conversation_memory[session_id]["last_active"] = time.time()
    
    return conversation_memory[session_id]

async def process_with_unified_service(message, session_id, customer_info):
    """🔧 修复：使用统一智能服务处理消息 - 保持原有功能完整"""
    try:
        print(f"🧠 Processing with unified service: {session_id}")
        print(f"👤 Customer info fields: {list(customer_info.keys())}")
        
        # 🔧 关键：调用统一服务的核心方法，保持原有prompt管理和推荐策略
        result = await unified_service.process_user_message(
            user_message=message,
            session_id=session_id,
            current_customer_info=customer_info
        )
        
        print(f"✅ Unified service response type: {type(result)}")
        
        # 🔧 确保返回标准化格式，保持前端兼容性
        if isinstance(result, dict):
            # 确保包含前端需要的所有字段
            standardized_response = {
                "reply": result.get("message", "I'm here to help with your loan needs."),
                "recommendations": result.get("recommendations", []),
                "session_id": session_id,
                "status": "success",
                "service_used": "unified_intelligent_service",
                # 🔧 保持function bar需要的数据格式
                "extracted_info": result.get("extracted_info", {}),
                "customer_profile": result.get("customer_profile", {}),
                "conversation_stage": result.get("stage", "greeting")
            }
            
            # 🔧 确保推荐数据包含前端product comparison需要的完整信息
            if standardized_response["recommendations"]:
                for rec in standardized_response["recommendations"]:
                    # 确保每个推荐包含必要字段
                    if "timestamp" not in rec:
                        rec["timestamp"] = time.time()
                    if "id" not in rec:
                        rec["id"] = f"{rec.get('lender_name', 'unknown')}_{rec.get('product_name', 'product')}_{int(time.time())}"
            
            return standardized_response
        else:
            # 降级处理：如果返回不是字典格式
            return {
                "reply": str(result) if result else "I'm here to help with your loan needs.",
                "recommendations": [],
                "session_id": session_id,
                "status": "success",
                "service_used": "unified_intelligent_service"
            }
            
    except Exception as e:
        print(f"❌ Unified service error: {e}")
        print(f"❌ Error details: {type(e).__name__}: {str(e)}")
        return None

async def fallback_ai_response(message, session_id, customer_info):
    """降级AI响应 - 当unified service不可用时使用"""
    system_prompt = """You are a professional Australian car loan advisor. 
Help customers find suitable car loan options.

Guidelines:
- Be friendly, professional, and helpful
- Ask relevant questions to understand their needs
- Provide practical car loan advice
- Keep responses conversational and concise
- Focus on Australian lending products and requirements"""
    
    if customer_info:
        context_items = []
        for key, value in customer_info.items():
            if value:
                context_items.append(f"{key.replace('_', ' ')}: {value}")
        
        if context_items:
            system_prompt += f"\n\nCustomer context: {', '.join(context_items)}"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if API_TYPE == "anthropic":
                request_payload = {
                    "model": MODEL_NAME,
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": message}],
                    "system": system_prompt
                }
                
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                
                response = await client.post(API_URL, json=request_payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"]
                    
            else:  # OpenRouter
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
                
                request_payload = {
                    "model": MODEL_NAME,
                    "messages": messages,
                    "max_tokens": 1000,
                    "temperature": 0.7
                }
                
                headers = {
                    "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                response = await client.post(API_URL, json=request_payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                    
    except Exception as e:
        print(f"❌ AI API error: {e}")
    
    return "I'm here to help with your car loan needs. Could you tell me more about what you're looking for?"

async def test_api_connection():
    """测试API连接"""
    try:
        test_message = "Hello, I need a car loan."
        response = await fallback_ai_response(test_message, "test", {})
        
        if response and len(response) > 10:
            return {
                "status": "success",
                "message": "API connection successful",
                "test_response_length": len(response),
                "api_type": API_TYPE,
                "model": MODEL_NAME
            }
        else:
            return {
                "status": "failed",
                "message": "API connection failed - no valid response",
                "api_type": API_TYPE
            }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"API test failed: {str(e)}",
            "api_type": API_TYPE
        }

def validate_customer_info(customer_info):
    """🔧 增强：验证和清理客户信息 - 保持function bar兼容性"""
    if not isinstance(customer_info, dict):
        return {}
    
    cleaned = {}
    for key, value in customer_info.items():
        if value is not None and str(value).strip() and value != 'undefined':
            # 🔧 保持数据类型一致性，供dynamic form使用
            if key in ['loan_amount', 'desired_loan_amount', 'credit_score', 'ABN_years', 'GST_years']:
                try:
                    if isinstance(value, str):
                        clean_value = value.replace('$', '').replace(',', '').strip()
                        cleaned[key] = float(clean_value) if '.' in clean_value else int(clean_value)
                    else:
                        cleaned[key] = value
                except (ValueError, TypeError):
                    continue
            else:
                cleaned[key] = str(value).strip()
    
    return cleaned

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程HTTP服务器"""
    daemon_threads = True

class CORSRequestHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        """设置CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Access-Control-Max-Age', '3600')
    
    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        response_json = json.dumps(data, ensure_ascii=False)
        self.wfile.write(response_json.encode('utf-8'))
    
    def _send_error_response(self, status_code, message):
        """发送错误响应"""
        self._send_json_response(status_code, {"error": message})
    
    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/' or path == '':
            self._handle_root()
        elif path == '/health':
            self._handle_health()
        elif path == '/test-ai':
            self._handle_test_ai()
        elif path.startswith('/session-status/'):
            session_id = path.split('/')[-1]
            self._handle_session_status(session_id)
        else:
            self._handle_404()
    
    def do_POST(self):
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
        except (ValueError, TypeError) as e:
            self._send_error_response(400, "Invalid JSON")
            return
        
        if path == '/chat':
            self._handle_chat(data)
        elif path == '/reset-session':
            self._handle_reset_session(data)
        else:
            self._handle_404()
    
    def _handle_root(self):
        """处理根路径"""
        response = {
            "message": "LIFEX Car Loan AI Agent API",
            "status": "running",
            "version": "4.5-unified-integrated",
            "endpoints": {
                "health": "/health",
                "chat": "/chat",
                "test_ai": "/test-ai",
                "session_status": "/session-status/{session_id}",
                "reset_session": "/reset-session"
            },
            "features": {
                "ai_enabled": bool(ANTHROPIC_API_KEY),
                "api_type": API_TYPE,
                "model": MODEL_NAME,
                "unified_service": UNIFIED_SERVICE_AVAILABLE,
                "product_database": "docs/ (4 lenders)" if UNIFIED_SERVICE_AVAILABLE else None,
                "cors_enabled": True
            }
        }
        self._send_json_response(200, response)
    
    def _handle_health(self):
        """🔧 增强：健康检查 - 包含服务状态"""
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "LIFEX Car Loan AI Agent is running",
            "version": "4.5-unified-integrated",
            "features": {
                "api_key_configured": bool(ANTHROPIC_API_KEY),
                "api_type": API_TYPE,
                "model": MODEL_NAME,
                "unified_service": UNIFIED_SERVICE_AVAILABLE,
                "product_database_status": "loaded" if UNIFIED_SERVICE_AVAILABLE else "unavailable",
                "lenders_available": ["Angle", "BFS", "FCAU", "RAF"] if UNIFIED_SERVICE_AVAILABLE else [],
                "cors_enabled": True,
                "active_sessions": len(conversation_memory)
            }
        }
        self._send_json_response(200, response)
    
    def _handle_test_ai(self):
        """测试AI连接和unified service"""
        try:
            import concurrent.futures
            
            def run_test():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(test_api_connection())
                finally:
                    loop.close()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_test)
                test_result = future.result(timeout=60)
            
            # 🔧 添加unified service测试状态
            response = {
                "api_test": test_result,
                "unified_service": {
                    "available": UNIFIED_SERVICE_AVAILABLE,
                    "product_database": "4 lenders (Angle, BFS, FCAU, RAF)" if UNIFIED_SERVICE_AVAILABLE else "Not available"
                },
                "timestamp": time.time()
            }
            
            self._send_json_response(200, response)
            
        except Exception as e:
            self._send_error_response(500, f"Test failed: {str(e)}")
    
    def _handle_chat(self, data):
        """🔧 核心修复：聊天请求处理 - 完整集成unified service"""
        try:
            message = data.get("message", "").strip()
            session_id = data.get("session_id", f"session_{int(time.time())}")
            customer_info = validate_customer_info(data.get("current_customer_info", {}))
            
            if not message:
                self._send_error_response(400, "Message content cannot be empty")
                return
            
            print(f"💬 Processing chat: {session_id}")
            print(f"📝 Message: {message[:100]}...")
            print(f"👤 Customer info fields: {list(customer_info.keys())}")
            
            # 获取或创建会话
            session_data = get_session_or_create(session_id)
            
            # 🔧 保持customer info在会话中，供function bar使用
            session_data["customer_info"].update(customer_info)
            
            # 添加用户消息到历史
            session_data["messages"].append({
                "role": "user",
                "content": message,
                "timestamp": time.time()
            })
            
            # 定期清理旧会话
            if len(conversation_memory) > 50:
                cleanup_old_sessions()
            
            # 🔧 核心：使用unified service处理消息
            import concurrent.futures
            
            def run_chat_processing():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if UNIFIED_SERVICE_AVAILABLE:
                        # 🔧 使用unified service处理，保持原有prompt管理和推荐策略
                        return loop.run_until_complete(
                            process_with_unified_service(message, session_id, session_data["customer_info"])
                        )
                    else:
                        # 降级处理
                        ai_response = loop.run_until_complete(
                            fallback_ai_response(message, session_id, session_data["customer_info"])
                        )
                        return {
                            "reply": ai_response,
                            "recommendations": [],
                            "session_id": session_id,
                            "status": "fallback",
                            "service_used": "basic_ai"
                        }
                finally:
                    loop.close()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_chat_processing)
                response = future.result(timeout=120)  # 120秒超时，给复杂推荐算法足够时间
            
            # 🔧 处理响应并保持数据完整性
            if response:
                # 添加助手消息到历史，包含推荐信息
                assistant_message = {
                    "role": "assistant", 
                    "content": response.get("reply", ""),
                    "timestamp": time.time(),
                    "recommendations": response.get("recommendations", []),
                    "conversation_stage": response.get("conversation_stage", "unknown")
                }
                
                session_data["messages"].append(assistant_message)
                
                # 🔧 保持推荐历史供function bar使用
                if response.get("recommendations"):
                    if "recommendation_history" not in session_data:
                        session_data["recommendation_history"] = []
                    session_data["recommendation_history"].extend(response.get("recommendations", []))
                
                # 限制历史长度
                if len(session_data["messages"]) > 20:
                    session_data["messages"] = session_data["messages"][-20:]
                
                # 🔧 确保响应包含前端需要的所有字段
                final_response = {
                    "reply": response.get("reply"),
                    "recommendations": response.get("recommendations", []),
                    "session_id": session_id,
                    "status": response.get("status", "success"),
                    "service_used": response.get("service_used", "unified_intelligent_service"),
                    # function bar需要的额外数据
                    "extracted_info": response.get("extracted_info", {}),
                    "customer_profile": response.get("customer_profile", {}),
                    "conversation_stage": response.get("conversation_stage", "greeting"),
                    "timestamp": time.time()
                }
                
                self._send_json_response(200, final_response)
            else:
                self._send_error_response(500, "Failed to process message")
            
        except Exception as e:
            print(f"❌ Chat handler error: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            self._send_error_response(500, f"Internal server error: {str(e)}")
    
    def _handle_session_status(self, session_id):
        """处理会话状态查询"""
        if session_id in conversation_memory:
            session_data = conversation_memory[session_id]
            response = {
                "status": "active",
                "message_count": len(session_data["messages"]),
                "customer_info_fields": len(session_data["customer_info"]),
                "created_at": session_data["created_at"],
                "last_active": session_data["last_active"],
                "has_recommendations": "recommendation_history" in session_data and len(session_data.get("recommendation_history", [])) > 0
            }
            self._send_json_response(200, response)
        else:
            self._send_json_response(200, {"status": "not_found"})
    
    def _handle_reset_session(self, data):
        """处理会话重置"""
        session_id = data.get("session_id")
        
        if session_id and session_id in conversation_memory:
            del conversation_memory[session_id]
            print(f"🔄 Session reset: {session_id}")
            response = {"status": "reset", "session_id": session_id}
        else:
            response = {"status": "not_found"}
        
        self._send_json_response(200, response)
    
    def _handle_404(self):
        """处理404错误"""
        response = {
            "error": "Endpoint not found",
            "path": self.path,
            "available_endpoints": ["/", "/health", "/test-ai", "/chat", "/session-status/{id}", "/reset-session"]
        }
        self._send_json_response(404, response)
    
    def log_message(self, format, *args):
        """简化日志输出"""
        print(f"🌐 {self.client_address[0]} - {format % args}")

def run_server():
    """运行服务器"""
    PORT = int(os.getenv('PORT', 10000))
    
    try:
        server = ThreadingHTTPServer(('0.0.0.0', PORT), CORSRequestHandler)
        print(f"🚀 Server starting on port {PORT}")
        print(f"🔗 Health check: http://localhost:{PORT}/health")
        print(f"💬 Chat endpoint: http://localhost:{PORT}/chat")
        print(f"🧪 AI test: http://localhost:{PORT}/test-ai")
        print(f"🧠 Unified Service: {'✅ Enabled with product database' if UNIFIED_SERVICE_AVAILABLE else '❌ Disabled - using fallback'}")
        print(f"📁 Product Database: {'docs/ (Angle, BFS, FCAU, RAF)' if UNIFIED_SERVICE_AVAILABLE else 'Not available'}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
        server.shutdown()
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    run_server()