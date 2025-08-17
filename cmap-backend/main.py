# main.py - Claude API版本（直接调用Anthropic API）
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

# 加载环境变量
load_dotenv()

# 全局变量
conversation_memory = {}

# 支持多种API密钥名称
ANTHROPIC_API_KEY = (
    os.getenv("ANTHROPIC_API_KEY") or 
    os.getenv("CLAUDE_API_KEY") or 
    os.getenv("OPENROUTER_API_KEY")  # 向后兼容
)

# API配置
if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-ant-"):
    # 直接使用Anthropic API
    API_URL = "https://api.anthropic.com/v1/messages"
    API_TYPE = "anthropic"
    MODEL_NAME = "claude-3-haiku-20240307"
elif ANTHROPIC_API_KEY and ANTHROPIC_API_KEY.startswith("sk-or-"):
    # 使用OpenRouter API
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

if ANTHROPIC_API_KEY:
    print(f"🔑 API Key preview: {ANTHROPIC_API_KEY[:15]}...{ANTHROPIC_API_KEY[-4:]}")

def cleanup_old_sessions():
    """清理超过1小时的旧会话"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in conversation_memory.items():
        if current_time - session_data.get("created_at", 0) > 3600:  # 1小时
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

def validate_customer_info(customer_info):
    """验证和清理客户信息"""
    if not isinstance(customer_info, dict):
        return {}
    
    cleaned = {}
    for key, value in customer_info.items():
        if value is not None and str(value).strip() and value != 'undefined':
            # 特殊处理数字字段
            if key in ['loan_amount', 'credit_score', 'ABN_years', 'GST_years']:
                try:
                    if isinstance(value, str):
                        clean_value = value.replace('$', '').replace(',', '').strip()
                        cleaned[key] = float(clean_value) if '.' in clean_value else int(clean_value)
                    else:
                        cleaned[key] = value
                except (ValueError, TypeError):
                    print(f"⚠️ Invalid numeric value for {key}: {value}")
            else:
                cleaned[key] = str(value).strip()
    
    return cleaned

async def test_api_connection():
    """测试API连接"""
    if not ANTHROPIC_API_KEY:
        return {"success": False, "error": "No API key configured"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if API_TYPE == "anthropic":
                # 测试Anthropic API
                test_response = await client.post(
                    API_URL,
                    json={
                        "model": MODEL_NAME,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hello"}]
                    },
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    }
                )
            else:
                # 测试OpenRouter API
                test_response = await client.post(
                    API_URL,
                    json={
                        "model": MODEL_NAME,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10
                    },
                    headers={
                        "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://lifex-backend.onrender.com",
                        "X-Title": "LIFEX Car Loan Agent Test"
                    }
                )
            
            if test_response.status_code == 200:
                return {"success": True, "status_code": 200, "api_type": API_TYPE}
            else:
                error_text = test_response.text
                return {
                    "success": False, 
                    "status_code": test_response.status_code,
                    "error": error_text,
                    "api_type": API_TYPE
                }
                
    except Exception as e:
        return {"success": False, "error": str(e), "api_type": API_TYPE}

async def call_ai_service(message, session_data):
    """AI服务调用 - 支持Anthropic和OpenRouter"""
    if not ANTHROPIC_API_KEY:
        raise Exception("API key not configured")
    
    print(f"🤖 Starting AI service call ({API_TYPE}) for message: {message[:50]}...")
    
    # 构建系统提示
    system_prompt = """You are Agent X, a professional car loan advisor specializing in Australian car loans. Help customers find the best car loan options.

Guidelines:
- Be friendly, professional, and helpful
- Ask relevant questions to understand their needs
- Provide practical car loan advice
- Keep responses conversational and concise
- Focus on Australian lending products and requirements"""
    
    # 添加客户上下文
    if session_data["customer_info"]:
        context_items = []
        for key, value in session_data["customer_info"].items():
            if value:
                context_items.append(f"{key.replace('_', ' ')}: {value}")
        
        if context_items:
            system_prompt += f"\n\nCustomer context: {', '.join(context_items)}"
    
    # 构建消息历史（最近6条消息）
    recent_messages = session_data["messages"][-6:]
    
    # 调用API（根据类型使用不同格式）
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(3):  # 3次重试
            try:
                print(f"🔄 AI API attempt {attempt + 1}/3 ({API_TYPE})")
                
                if API_TYPE == "anthropic":
                    # Anthropic API格式
                    messages = []
                    for msg in recent_messages:
                        messages.append({"role": msg["role"], "content": msg["content"]})
                    messages.append({"role": "user", "content": message})
                    
                    request_payload = {
                        "model": MODEL_NAME,
                        "max_tokens": 1000,
                        "messages": messages,
                        "system": system_prompt
                    }
                    
                    headers = {
                        "x-api-key": ANTHROPIC_API_KEY,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    }
                    
                else:
                    # OpenRouter API格式
                    messages = [{"role": "system", "content": system_prompt}]
                    for msg in recent_messages:
                        messages.append({"role": msg["role"], "content": msg["content"]})
                    messages.append({"role": "user", "content": message})
                    
                    request_payload = {
                        "model": MODEL_NAME,
                        "messages": messages,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {ANTHROPIC_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://lifex-backend.onrender.com",
                        "X-Title": "LIFEX Car Loan Agent"
                    }
                
                print(f"📤 Sending request to: {API_URL}")
                print(f"📤 Model: {request_payload['model']}")
                print(f"📤 Message count: {len(request_payload['messages']) if 'messages' in request_payload else 'system+messages'}")
                
                response = await client.post(
                    API_URL,
                    json=request_payload,
                    headers=headers
                )
                
                print(f"📥 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if API_TYPE == "anthropic":
                        ai_response = result["content"][0]["text"]
                    else:
                        ai_response = result["choices"][0]["message"]["content"]
                    
                    print(f"✅ AI API success on attempt {attempt + 1}")
                    print(f"✅ Response length: {len(ai_response)} characters")
                    return ai_response
                else:
                    error_text = response.text
                    print(f"❌ AI API returned {response.status_code}: {error_text}")
                    
                    # 如果是认证错误或其他严重错误，不要重试
                    if response.status_code in [401, 403]:
                        raise Exception(f"Authentication error {response.status_code}: {error_text}")
                    
                    if attempt == 2:  # 最后一次尝试
                        raise Exception(f"API returned {response.status_code}: {error_text}")
                    
            except Exception as e:
                print(f"❌ AI API attempt {attempt + 1} failed: {str(e)}")
                print(f"❌ Exception type: {type(e).__name__}")
                
                if attempt == 2:  # 最后一次尝试
                    raise e
                    
                await asyncio.sleep(2 ** attempt)  # 指数退避

def generate_recommendations(customer_info):
    """生成车贷推荐"""
    if not customer_info:
        return None
    
    recommendations = []
    
    # 基础推荐逻辑
    loan_amount = customer_info.get('loan_amount', 0)
    if isinstance(loan_amount, str):
        try:
            loan_amount = float(loan_amount.replace('$', '').replace(',', ''))
        except:
            loan_amount = 0
    
    # 示例推荐
    if loan_amount > 0:
        recommendations.append({
            "lender_name": "Major Bank",
            "product_name": "Car Loan",
            "base_rate": "7.49%",
            "comparison_rate": "7.89%",
            "monthly_payment": f"${loan_amount * 0.02:.2f}",
            "features": ["Quick approval", "No early repayment fees"]
        })
    
    return recommendations if recommendations else None

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
            "version": "4.3-claude-api",
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
                "cors_enabled": True
            }
        }
        self._send_json_response(200, response)
    
    def _handle_health(self):
        """处理健康检查"""
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "LIFEX Car Loan AI Agent is running",
            "version": "4.3-claude-api",
            "features": {
                "api_key_configured": bool(ANTHROPIC_API_KEY),
                "api_type": API_TYPE,
                "model": MODEL_NAME,
                "cors_enabled": True,
                "active_sessions": len(conversation_memory)
            }
        }
        self._send_json_response(200, response)
    
    def _handle_test_ai(self):
        """测试AI连接"""
        try:
            # 使用线程运行异步测试
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
            
            self._send_json_response(200, {
                "test_result": test_result,
                "timestamp": time.time(),
                "config": {
                    "api_type": API_TYPE,
                    "model": MODEL_NAME,
                    "api_url": API_URL
                }
            })
            
        except Exception as e:
            print(f"❌ AI test error: {e}")
            self._send_json_response(500, {
                "error": f"AI test failed: {str(e)}",
                "timestamp": time.time(),
                "config": {
                    "api_type": API_TYPE,
                    "model": MODEL_NAME,
                    "api_url": API_URL
                }
            })
    
    def _handle_chat(self, data):
        """处理聊天请求"""
        try:
            message = data.get("message", "").strip()
            session_id = data.get("session_id", f"session_{int(time.time())}")
            customer_info = validate_customer_info(data.get("current_customer_info", {}))
            
            if not message:
                self._send_error_response(400, "Message is required")
                return
            
            print(f"📨 Chat request: session={session_id}, message_len={len(message)}")
            
            # 检查API密钥
            if not ANTHROPIC_API_KEY:
                print(f"❌ No API key configured")
                self._send_error_response(500, "AI service not configured - no API key")
                return
            
            # 获取或创建会话
            session_data = get_session_or_create(session_id)
            
            # 更新客户信息
            if customer_info:
                session_data["customer_info"].update(customer_info)
                print(f"📊 Updated customer info: {len(customer_info)} fields")
            
            # 添加用户消息到会话
            user_message = {
                "role": "user",
                "content": message,
                "timestamp": time.time()
            }
            session_data["messages"].append(user_message)
            
            # 调用AI服务
            try:
                print(f"🤖 Starting AI call ({API_TYPE})...")
                
                # 使用线程池执行方式
                import concurrent.futures
                
                def run_ai_call():
                    """在新线程中运行AI调用"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(call_ai_service(message, session_data))
                    except Exception as e:
                        print(f"❌ Thread AI call error: {e}")
                        raise e
                    finally:
                        loop.close()
                
                # 使用线程执行AI调用
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_ai_call)
                    ai_response = future.result(timeout=90)  # 90秒超时
                
                print(f"✅ AI response generated successfully: {len(ai_response)} chars")
                
            except concurrent.futures.TimeoutError:
                print(f"❌ AI service timeout after 90 seconds")
                self._send_error_response(504, "AI service timeout - please try again")
                return
            except Exception as e:
                print(f"❌ AI service failed with error: {str(e)}")
                print(f"❌ Error type: {type(e).__name__}")
                
                # 提供更详细的错误信息
                error_msg = f"AI service error: {str(e)}"
                if "401" in str(e) or "403" in str(e):
                    error_msg = "API authentication failed - please check API key"
                elif "429" in str(e):
                    error_msg = "Rate limit exceeded - please try again later"
                elif "timeout" in str(e).lower():
                    error_msg = "AI service timeout - please try again"
                
                self._send_error_response(503, error_msg)
                return
            
            # 添加AI回复到会话
            assistant_message = {
                "role": "assistant",
                "content": ai_response,
                "timestamp": time.time()
            }
            session_data["messages"].append(assistant_message)
            
            # 生成推荐
            recommendations = generate_recommendations(session_data["customer_info"])
            
            # 定期清理
            if len(session_data["messages"]) % 20 == 0:
                cleanup_old_sessions()
            
            response = {
                "reply": ai_response,
                "session_id": session_id,
                "status": "success",
                "timestamp": time.time(),
                "customer_info_updated": bool(customer_info),
                "recommendations": recommendations if recommendations else None
            }
            
            print(f"✅ Chat response sent successfully")
            self._send_json_response(200, response)
            
        except Exception as e:
            print(f"❌ Chat handler error: {e}")
            print(f"❌ Error type: {type(e).__name__}")
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
                "last_active": session_data["last_active"]
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
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
        server.shutdown()
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    run_server()