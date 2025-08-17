# main.py - 修复版本（移除Basic Mode，确保AI服务正常）
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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

print(f"🚀 LIFEX Car Loan AI Agent starting...")
print(f"🔑 API Key configured: {'✅' if OPENROUTER_API_KEY else '❌'}")

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

async def call_ai_service(message, session_data):
    """AI服务调用"""
    if not OPENROUTER_API_KEY:
        raise Exception("OpenRouter API key not configured")
    
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
    messages = [{"role": "system", "content": system_prompt}]
    recent_messages = session_data["messages"][-6:]
    
    for msg in recent_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 当前消息
    messages.append({"role": "user", "content": message})
    
    # 调用API（增强重试逻辑）
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(3):  # 增加到3次重试
            try:
                print(f"🔄 AI API attempt {attempt + 1}/3")
                
                response = await client.post(
                    OPENROUTER_API_URL,
                    json={
                        "model": "anthropic/claude-3-haiku",
                        "messages": messages,
                        "max_tokens": 1000,
                        "temperature": 0.7
                    },
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://lifex-backend.onrender.com",
                        "X-Title": "LIFEX Car Loan Agent"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result["choices"][0]["message"]["content"]
                    print(f"✅ AI API success on attempt {attempt + 1}")
                    return ai_response
                else:
                    error_text = await response.aread() if hasattr(response, 'aread') else response.text
                    print(f"⚠️ AI API returned {response.status_code}: {error_text}")
                    if attempt == 2:  # 最后一次尝试
                        raise Exception(f"API returned {response.status_code}: {error_text}")
                    
            except Exception as e:
                print(f"⚠️ AI API attempt {attempt + 1} failed: {e}")
                if attempt == 2:  # 最后一次尝试
                    raise e
                await asyncio.sleep(2 ** attempt)  # 指数退避

def run_async_in_thread(coro):
    """在线程中运行异步函数"""
    def run_in_thread():
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    return run_in_thread

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
            "version": "4.3-fixed",
            "endpoints": {
                "health": "/health",
                "chat": "/chat",
                "session_status": "/session-status/{session_id}",
                "reset_session": "/reset-session"
            },
            "features": {
                "ai_enabled": bool(OPENROUTER_API_KEY),
                "cors_enabled": True,
                "basic_mode_removed": True
            }
        }
        self._send_json_response(200, response)
    
    def _handle_health(self):
        """处理健康检查"""
        response = {
            "status": "healthy",
            "timestamp": time.time(),
            "message": "LIFEX Car Loan AI Agent is running",
            "version": "4.3-fixed",
            "features": {
                "api_key_configured": bool(OPENROUTER_API_KEY),
                "cors_enabled": True,
                "active_sessions": len(conversation_memory),
                "basic_mode_removed": True
            }
        }
        self._send_json_response(200, response)
    
    def _handle_chat(self, data):
        """处理聊天请求 - 移除Basic Mode"""
        try:
            message = data.get("message", "").strip()
            session_id = data.get("session_id", f"session_{int(time.time())}")
            customer_info = validate_customer_info(data.get("current_customer_info", {}))
            
            if not message:
                self._send_error_response(400, "Message is required")
                return
            
            print(f"📨 Chat request: session={session_id}, message_len={len(message)}")
            
            # 检查API密钥
            if not OPENROUTER_API_KEY:
                self._send_error_response(500, "AI service not configured")
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
            
            # 调用AI服务（必须成功，不再有Basic Mode后备）
            try:
                # 使用更稳定的线程池执行方式
                import concurrent.futures
                import threading
                
                def run_ai_call():
                    """在新线程中运行AI调用"""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(call_ai_service(message, session_data))
                    finally:
                        loop.close()
                
                # 使用线程执行AI调用，增加超时时间
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_ai_call)
                    ai_response = future.result(timeout=90)  # 90秒超时
                
                status = "success"
                print(f"✅ AI response generated successfully")
                
            except concurrent.futures.TimeoutError:
                print(f"❌ AI service timeout")
                self._send_error_response(504, "AI service timeout - please try again")
                return
            except Exception as e:
                print(f"❌ AI service failed: {e}")
                self._send_error_response(503, f"AI service unavailable: {str(e)}")
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
                "status": status,
                "timestamp": time.time(),
                "customer_info_updated": bool(customer_info),
                "recommendations": recommendations if recommendations else None
            }
            
            self._send_json_response(200, response)
            
        except Exception as e:
            print(f"❌ Chat error: {e}")
            self._send_error_response(500, "Internal server error")
    
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
            "available_endpoints": ["/", "/health", "/chat", "/session-status/{id}", "/reset-session"]
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
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
        server.shutdown()
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    run_server()