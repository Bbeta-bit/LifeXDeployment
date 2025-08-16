# main.py - 完整优化版本
import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 全局变量
conversation_memory = {}
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("🚀 LIFEX Car Loan AI Agent starting...")
    logger.info(f"🔑 API Key configured: {'✅' if OPENROUTER_API_KEY else '❌'}")
    
    # 清理旧的会话（启动时）
    cleanup_old_sessions()
    
    yield
    
    # 关闭时
    logger.info("🛑 LIFEX Car Loan AI Agent shutting down...")

# 创建FastAPI应用
app = FastAPI(
    title="LIFEX Car Loan AI Agent",
    description="AI assistant for car loan recommendations - Optimized",
    version="4.0-optimized",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 优化的CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5173",
        "https://lifex-car-loan-ai-agent.onrender.com",
        "https://cmap-frontend.onrender.com",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 工具函数
def cleanup_old_sessions():
    """清理超过1小时的旧会话"""
    current_time = time.time()
    expired_sessions = []
    
    for session_id, session_data in conversation_memory.items():
        if current_time - session_data.get("created_at", 0) > 3600:  # 1小时
            expired_sessions.append(session_id)
    
    for session_id in expired_sessions:
        del conversation_memory[session_id]
        logger.info(f"🗑️ Cleaned up expired session: {session_id}")

def get_session_or_create(session_id: str) -> Dict:
    """获取或创建会话"""
    if session_id not in conversation_memory:
        conversation_memory[session_id] = {
            "messages": [],
            "customer_info": {},
            "created_at": time.time(),
            "last_active": time.time()
        }
        logger.info(f"📝 Created new session: {session_id}")
    else:
        conversation_memory[session_id]["last_active"] = time.time()
    
    return conversation_memory[session_id]

def validate_customer_info(customer_info: Dict) -> Dict:
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
                        # 移除货币符号和逗号
                        clean_value = value.replace('$', '').replace(',', '').strip()
                        cleaned[key] = float(clean_value) if '.' in clean_value else int(clean_value)
                    else:
                        cleaned[key] = value
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Invalid numeric value for {key}: {value}")
            else:
                cleaned[key] = str(value).strip()
    
    return cleaned

# 根端点
@app.get("/")
async def root():
    """API信息"""
    return {
        "message": "LIFEX Car Loan AI Agent API",
        "status": "running",
        "version": "4.0-optimized",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "session_status": "/session-status/{session_id}",
            "reset_session": "/reset-session",
            "docs": "/docs"
        },
        "features": {
            "ai_enabled": bool(OPENROUTER_API_KEY),
            "cors_enabled": True,
            "session_management": True,
            "auto_cleanup": True
        }
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """增强的健康检查"""
    active_sessions = len(conversation_memory)
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "message": "LIFEX Car Loan AI Agent is running",
        "version": "4.0-optimized",
        "uptime": time.time(),
        "features": {
            "api_key_configured": bool(OPENROUTER_API_KEY),
            "cors_enabled": True,
            "active_sessions": active_sessions,
            "memory_usage": f"{len(str(conversation_memory))} chars"
        }
    }

# 主聊天端点
@app.post("/chat")
async def chat_endpoint(request: Request, background_tasks: BackgroundTasks):
    """优化的聊天处理"""
    try:
        # 解析请求数据
        data = await request.json()
        message = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(time.time())}")
        history = data.get("history", [])
        customer_info = validate_customer_info(data.get("current_customer_info", {}))
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required", "status": "error"}
            )
        
        logger.info(f"📨 Chat request: session={session_id}, message_len={len(message)}, customer_fields={len(customer_info)}")
        
        # 获取或创建会话
        session_data = get_session_or_create(session_id)
        
        # 更新客户信息
        if customer_info:
            session_data["customer_info"].update(customer_info)
            logger.info(f"📊 Updated customer info: {len(customer_info)} fields")
        
        # 添加用户消息到会话
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": time.time()
        }
        session_data["messages"].append(user_message)
        
        # AI处理
        if OPENROUTER_API_KEY:
            try:
                ai_response = await call_ai_service_optimized(message, session_data)
                status = "success"
            except Exception as e:
                logger.error(f"❌ AI service failed: {e}")
                ai_response = generate_fallback_response(message, session_data["customer_info"])
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
        recommendations = generate_smart_recommendations(session_data["customer_info"])
        
        # 后台任务：清理旧会话
        background_tasks.add_task(cleanup_old_sessions)
        
        response = {
            "reply": ai_response,
            "session_id": session_id,
            "status": status,
            "timestamp": time.time(),
            "customer_info_updated": bool(customer_info),
            "recommendations": recommendations if recommendations else None
        }
        
        return JSONResponse(content=response)
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON", "status": "error"}
        )
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "reply": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                "status": "error",
                "timestamp": time.time()
            }
        )

async def call_ai_service_optimized(message: str, session_data: Dict) -> str:
    """优化的AI服务调用"""
    # 构建系统提示
    system_prompt = """You are Agent X, a professional car loan advisor. Help customers find the best car loan options.

Guidelines:
- Be friendly, professional, and helpful
- Ask relevant questions to understand their needs
- Provide practical car loan advice
- Keep responses conversational and concise
- If they mention loan amounts or terms, acknowledge them"""
    
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
    recent_messages = session_data["messages"][-6:]  # 最近3轮对话
    
    for msg in recent_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 当前消息
    messages.append({"role": "user", "content": message})
    
    # 调用API（优化的重试和超时）
    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(2):  # 最多重试2次
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
                        "Content-Type": "application/json",
                        "X-Title": "LIFEX Car Loan Agent"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"⚠️ AI API returned {response.status_code}, attempt {attempt + 1}")
                    if attempt == 1:  # 最后一次尝试
                        raise Exception(f"API returned {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ AI API attempt {attempt + 1} failed: {e}")
                if attempt == 1:  # 最后一次尝试
                    raise e
                await asyncio.sleep(1)  # 重试前等待1秒

def generate_fallback_response(message: str, customer_info: Dict) -> str:
    """生成回退响应"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm Agent X, your car loan advisor. I'm currently experiencing some technical difficulties with my AI service, but I can still help with basic loan information. What would you like to know?"
    
    elif any(word in message_lower for word in ['loan', 'finance', 'borrow']):
        if customer_info.get('loan_amount'):
            return f"I see you're looking for a loan around ${customer_info['loan_amount']:,}. Even though I'm in limited mode right now, I can tell you that car loan rates typically range from 3-15% APR depending on your credit score and loan term. What specific questions do you have?"
        return "I'd be happy to help with car loan information! Even in limited mode, I can provide general guidance. Typical car loan rates range from 3-15% APR. What's your approximate loan amount and credit score range?"
    
    elif any(word in message_lower for word in ['rate', 'interest', 'apr']):
        return "Car loan rates vary based on credit score, loan term, and vehicle age. Generally: Excellent credit (750+): 3-6% APR, Good credit (650-749): 6-10% APR, Fair credit (600-649): 10-15% APR. What's your credit score range?"
    
    else:
        return "I'm currently in limited mode due to technical issues, but I can still help with basic car loan questions. Common topics I can assist with include: interest rates, loan terms, credit requirements, and documentation needs. What would you like to know?"

def generate_basic_response(message: str, customer_info: Dict) -> str:
    """生成基础响应"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm Agent X, your car loan advisor. I'm in basic mode but ready to help with loan information. What kind of vehicle are you looking to finance?"
    
    elif any(word in message_lower for word in ['loan', 'finance']):
        context = ""
        if customer_info.get('loan_amount'):
            context = f" I see you're considering a ${customer_info['loan_amount']:,} loan."
        return f"I'd be happy to help with car loan options!{context} To provide the best recommendations, could you tell me: your approximate credit score, preferred loan term, and type of vehicle you're considering?"
    
    elif any(word in message_lower for word in ['rate', 'interest']):
        return "Interest rates depend on several factors. Here's a general guide: Credit Score 750+: 3-6% APR, 650-749: 6-10% APR, 600-649: 10-15% APR. New cars typically get better rates than used cars. What's your credit score range?"
    
    else:
        return "I'm here to help with car loan questions! I can provide information about: interest rates, loan terms, credit requirements, lender options, and documentation needs. What specific aspect interests you?"

def generate_smart_recommendations(customer_info: Dict) -> Optional[List[Dict]]:
    """智能推荐生成"""
    if not customer_info.get('loan_amount'):
        return None
    
    try:
        loan_amount = float(str(customer_info['loan_amount']).replace(',', '').replace('$', ''))
        if loan_amount < 5000:
            return None
        
        credit_score = customer_info.get('credit_score', 700)
        if isinstance(credit_score, str):
            credit_score = 700  # 默认值
        
        # 基于信用分数确定利率范围
        if credit_score >= 750:
            base_rates = [4.2, 4.8, 5.1]
        elif credit_score >= 650:
            base_rates = [6.5, 7.2, 7.8]
        else:
            base_rates = [9.5, 10.2, 11.1]
        
        recommendations = []
        lenders = [
            ("Credit Union Plus", "Auto Loan Premium", "No fees, fast approval"),
            ("National Bank", "Vehicle Finance Pro", "Flexible terms, online tools"),
            ("Community Bank", "Car Loan Standard", "Local service, competitive rates")
        ]
        
        for i, (lender, product, features) in enumerate(lenders):
            term_months = int(customer_info.get('loan_term', 60))
            rate = base_rates[i]
            
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
                "features": [features, "Online application available"]
            })
        
        return recommendations
        
    except (ValueError, TypeError) as e:
        logger.warning(f"⚠️ Error generating recommendations: {e}")
        return None

# 会话管理端点
@app.get("/session-status/{session_id}")
async def get_session_status(session_id: str):
    """获取会话状态"""
    if session_id in conversation_memory:
        session_data = conversation_memory[session_id]
        return {
            "status": "active",
            "message_count": len(session_data["messages"]),
            "customer_info_fields": len(session_data["customer_info"]),
            "created_at": session_data["created_at"],
            "last_active": session_data["last_active"]
        }
    else:
        return {"status": "not_found"}

@app.post("/reset-session")
async def reset_session(request: Request):
    """重置会话"""
    data = await request.json()
    session_id = data.get("session_id")
    
    if session_id and session_id in conversation_memory:
        del conversation_memory[session_id]
        logger.info(f"🔄 Session reset: {session_id}")
        return {"status": "reset", "session_id": session_id}
    
    return {"status": "not_found"}

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found", 
            "path": str(request.url),
            "available_endpoints": ["/", "/health", "/chat", "/session-status", "/reset-session", "/docs"]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"❌ Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error", 
            "message": "Please try again later",
            "timestamp": time.time()
        }
    )

# 启动配置
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"🚀 启动LIFEX Car Loan AI Agent服务器...")
    logger.info(f"📍 服务器地址: {host}:{port}")
    logger.info(f"🔑 API Key配置: {'✅' if OPENROUTER_API_KEY else '❌ (基础模式)'}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )