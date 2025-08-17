# main.py - 纯HTTP服务器版本（完全避免FastAPI/Pydantic）
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
    # 构建系统提示
    system_prompt = """You are Agent X, a professional car loan advisor. Help customers find the best car loan options.

Guidelines:
- Be friendly, professional, and helpful
- Ask relevant questions to understand their needs
- Provide practical car loan advice
- Keep responses conversational and concise"""
    
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
    
    # 调用API
    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(2):
            try:
                response = await client.post(
                    OPENROUTER_API_URL,
                    json={
                        "model": "anthropic/claude-3-haiku",
                        "messages": messages,
                        "max_tokens": 800,
                        "temperature": 0.7
                    },
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    print(f"⚠️ AI API returned {response.status_code}, attempt {attempt + 1}")
                    if attempt == 1:
                        raise Exception(f"API returned {response.status_code}")
                    
            except Exception as e:
                print(f"⚠️ AI API attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    raise e
                await asyncio.sleep(1)

def generate_basic_response(message, customer_info):
    """生成基础响应"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm Agent X, your car loan advisor. What kind of vehicle are you looking to finance?"
    
    elif any(word in message_lower for word in ['loan', 'finance']):
        context = ""
        if customer_info.get('loan_amount'):
            context = f" I see you're considering a ${customer_info['loan_amount']:,} loan."
        return f"I'd be happy to help with car loan options!{context} What's your approximate credit score and preferred loan term?"
    
    else:
        return "I'm here to help with car loan questions! What specific aspect interests you?"

def generate_recommendations(customer_info):
    """生成推荐"""
    if not customer_info.get('loan_amount'):
        return None
    
    try:
        loan_amount = float(str(customer_info['loan_amount']).replace(',', '').replace('$', ''))
        if loan_amount < 5000:
            return None
        
        credit_score = customer_info.get('credit_score', 700)
        if isinstance(credit_score, str):
            credit_score = 700
        
        # 基于信用分数确定利率
        if credit_score >= 750:
            rates = [4.2, 4.8, 5.1]
        elif credit_score >= 650:
            rates = [6.5, 7.2, 7.8]
        else:
            rates = [9.5, 10.2, 11.1]
        
        recommendations = []
        lenders = [
            ("Credit Union Plus", "Auto Loan Premium"),
            ("National Bank", "Vehicle Finance Pro"),
            ("Community Bank", "Car Loan Standard")
        ]
        
        for i, (lender, product) in enumerate(lenders):
            term_months = int(customer_info.get('loan_term', 60))
            rate = rates[i]
            
            # 计算月供
            monthly_rate = rate / 100 / 12
            monthly_payment = (loan_amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_months))
            
            recommendations.append({
                "lender_name": lender,
                "product_name": product,
                "base_rate": rate,
                "loan_amount": loan_amount,
                "term_months": term_months,
                "monthly_payment": round(monthly_payment, 2),
                "total_interest": round((monthly_payment * term_months) - loan_amount, 2),
                "features": ["Online application", "Fast approval"]
            })
        
        return recommendations
        
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error generating recommendations: {e}")
        return None

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """支持多线程的HTTP服务器"""
    daemon_threads = True

class LIFEXHandler(BaseHTTPRequestHandler):
    """LIFEX Car Loan AI Agent HTTP请求处理器"""
    
    def _set_cors_headers(self):
        """设置CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
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
        
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
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
            "version": "4.2-http-server",
            "endpoints": {
                "health": "/health",
                "chat": "/chat",
                "session_status": "/session-status/{session_id}",
                "reset_session": "/reset-session"
            },
            "features": {
                "ai_enabled": bool(OPENROUTER_API_KEY),
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
            "version": "4.2-http-server",
            "features": {
                "api_key_configured": bool(OPENROUTER_API_KEY),
                "cors_enabled": True,
                "active_sessions": len(conversation_memory)
            }
        }
        self._send_json_response(200, response)
    
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
            
            # 处理AI响应（同步方式）
            if OPENROUTER_API_KEY:
                try:
                    # 使用线程池处理异步AI调用
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            call_ai_service(message, session_data)
                        )
                        ai_response = future.result(timeout=50)  # 50秒超时
                    status = "success"
                except Exception as e:
                    print(f"❌ AI service failed: {e}")
                    ai_response = f"I'm currently experiencing technical difficulties. However, I can help with basic car loan information. What would you like to know?"
                    status = "fallback"
            else:
                ai_response = generate_basic_response(message, session_data["customer_info"])
                status = "basic_mode"
            
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
            "available_endpoints": ["/", "/health", "/chat", "/session-status", "/reset-session"]
        }
        self._send_json_response(404, response)
    
    def _send_json_response(self, status_code, data):
        """发送JSON响应"""
        self.send_response(status_code)
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, status_code, message):
        """发送错误响应"""
        response = {
            "error": message,
            "status": "error",
            "timestamp": time.time()
        }
        self._send_json_response(status_code, response)
    
    def log_message(self, format, *args):
        """重写日志方法，简化输出"""
        print(f"📡 {self.address_string()} - {format % args}")

def run_server():
    """运行HTTP服务器"""
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 启动LIFEX Car Loan AI Agent HTTP服务器...")
    print(f"📍 服务器地址: {host}:{port}")
    
    server = ThreadingHTTPServer((host, port), LIFEXHandler)
    
    try:
        print(f"✅ 服务器正在运行在 http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器关闭")
        server.shutdown()

if __name__ == "__main__":
    run_server()