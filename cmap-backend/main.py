# main.py - 完整Render部署修复版本
import os
import json
import time
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import httpx

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="LIFEX Car Loan AI Agent",
    description="AI assistant for car loan recommendations - Render Optimized",
    version="3.0-render-fixed",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置 - 包含您的前端URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000", 
        "http://127.0.0.1:5173",
        "https://lifex-car-loan-ai-agent.onrender.com",
        "https://cmap-frontend.onrender.com",
        "https://your-frontend-url.onrender.com",  # 替换为您的实际前端URL
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 全局变量和配置
sessions = {}
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 简单的内存存储（用于会话管理）
conversation_memory = {}

print(f"🚀 LIFEX Car Loan AI Agent starting...")
print(f"🔑 API Key configured: {'✅' if OPENROUTER_API_KEY else '❌'}")
print(f"🌐 CORS enabled for Render deployment")

# 根端点
@app.get("/")
async def root():
    """根端点 - API信息"""
    return {
        "message": "LIFEX Car Loan AI Agent API",
        "status": "running",
        "version": "3.0-render-fixed",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs"
        },
        "features": {
            "ai_enabled": bool(OPENROUTER_API_KEY),
            "cors_enabled": True,
            "render_optimized": True
        }
    }

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "message": "LIFEX Car Loan AI Agent is running",
        "version": "3.0-render-fixed",
        "uptime": time.time(),
        "features": {
            "api_key_configured": bool(OPENROUTER_API_KEY),
            "cors_enabled": True,
            "memory_sessions": len(conversation_memory)
        }
    }

# 主要聊天端点
@app.post("/chat")
async def chat_endpoint(request: Request):
    """处理聊天请求 - 增强版本"""
    try:
        # 获取请求数据
        data = await request.json()
        message = data.get("message", "").strip()
        session_id = data.get("session_id", f"session_{int(time.time())}")
        history = data.get("history", [])
        customer_info = data.get("current_customer_info", {})
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Message is required", "status": "error"}
            )
        
        print(f"📨 Received message from session {session_id}: {message[:50]}...")
        
        # 更新会话记忆
        if session_id not in conversation_memory:
            conversation_memory[session_id] = {
                "messages": [],
                "customer_info": {},
                "created_at": time.time()
            }
        
        # 更新客户信息
        if customer_info:
            conversation_memory[session_id]["customer_info"].update(customer_info)
            print(f"📊 Updated customer info: {len(customer_info)} fields")
        
        # 添加用户消息到记忆
        conversation_memory[session_id]["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": time.time()
        })
        
        # 如果有API Key，调用AI服务
        if OPENROUTER_API_KEY:
            try:
                ai_response = await call_ai_service(message, session_id, customer_info)
                
                # 添加AI回复到记忆
                conversation_memory[session_id]["messages"].append({
                    "role": "assistant", 
                    "content": ai_response,
                    "timestamp": time.time()
                })
                
                # 检查是否需要生成推荐
                recommendations = generate_loan_recommendations(customer_info)
                
                response = {
                    "reply": ai_response,
                    "session_id": session_id,
                    "status": "success",
                    "timestamp": time.time(),
                    "customer_info_updated": bool(customer_info),
                    "recommendations": recommendations if recommendations else None
                }
                
            except Exception as e:
                print(f"❌ AI服务调用失败: {e}")
                response = {
                    "reply": "I'm currently experiencing technical difficulties with the AI service. However, I can still help you with basic loan information. Please tell me about your loan needs.",
                    "session_id": session_id,
                    "status": "fallback",
                    "timestamp": time.time(),
                    "error_details": str(e)
                }
        else:
            # 基础模式回复
            basic_response = generate_basic_response(message, customer_info)
            
            conversation_memory[session_id]["messages"].append({
                "role": "assistant",
                "content": basic_response,
                "timestamp": time.time()
            })
            
            recommendations = generate_loan_recommendations(customer_info)
            
            response = {
                "reply": basic_response,
                "session_id": session_id,
                "status": "basic_mode",
                "timestamp": time.time(),
                "message": "Running in basic mode - API key not configured",
                "recommendations": recommendations if recommendations else None
            }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"❌ 聊天端点错误: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "reply": "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                "status": "error",
                "timestamp": time.time()
            }
        )

async def call_ai_service(message: str, session_id: str, customer_info: dict) -> str:
    """调用OpenRouter AI服务"""
    
    # 构建系统提示
    system_prompt = """You are Agent X, a professional car loan advisor. You help customers find the best car loan options based on their needs.

Key guidelines:
- Be friendly, professional, and helpful
- Ask relevant questions to understand their loan needs
- Provide practical advice about car loans
- If they mention specific loan amounts, terms, or preferences, acknowledge them
- Keep responses conversational and not too long"""
    
    # 如果有客户信息，添加到上下文
    if customer_info:
        context_info = []
        for key, value in customer_info.items():
            if value and str(value).strip():
                context_info.append(f"{key}: {value}")
        
        if context_info:
            system_prompt += f"\n\nCustomer context: {', '.join(context_info)}"
    
    # 获取最近的对话历史
    recent_messages = []
    if session_id in conversation_memory:
        recent_messages = conversation_memory[session_id]["messages"][-6:]  # 最近3轮对话
    
    # 构建消息
    messages = [{"role": "system", "content": system_prompt}]
    
    # 添加最近对话历史
    for msg in recent_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 添加当前消息
    messages.append({"role": "user", "content": message})
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "X-Title": "LIFEX Car Loan Agent"
    }
    
    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            error_text = response.text if response.text else f"HTTP {response.status_code}"
            raise Exception(f"API调用失败: {error_text}")

def generate_basic_response(message: str, customer_info: dict) -> str:
    """生成基础回复（无AI时使用）"""
    message_lower = message.lower()
    
    # 简单的关键词匹配
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm Agent X, your car loan advisor. I'm here to help you find the perfect car loan. What kind of vehicle are you looking to finance?"
    
    elif any(word in message_lower for word in ['loan', 'finance', 'borrow']):
        return "I'd be happy to help you with car loan options! To provide the best recommendations, could you tell me: What's your approximate loan amount needed? What's your preferred loan term? Do you have a specific monthly payment in mind?"
    
    elif any(word in message_lower for word in ['rate', 'interest', 'apr']):
        return "Interest rates vary based on factors like your credit score, loan term, and the vehicle age. Generally, rates range from 3-15% APR. To get you accurate rates, I'd need to know more about your situation. What's your credit score range?"
    
    elif any(word in message_lower for word in ['credit', 'score']):
        return "Credit scores significantly impact loan rates. Excellent credit (750+) gets the best rates, while fair credit (600-700) still has good options. What's your approximate credit score range?"
    
    elif any(word in message_lower for word in ['payment', 'monthly']):
        monthly_info = ""
        if customer_info.get('loan_amount') and customer_info.get('loan_term'):
            monthly_info = f" Based on your ${customer_info['loan_amount']} loan amount and {customer_info['loan_term']} term preference,"
        return f"Monthly payments depend on loan amount, term, and interest rate.{monthly_info} I can help calculate estimated payments. What loan amount are you considering?"
    
    else:
        return "I understand you're interested in car financing. I'm currently in basic mode, but I can still help with loan information. Could you tell me more about what you're looking for - loan amount, vehicle type, or preferred monthly payment?"

def generate_loan_recommendations(customer_info: dict) -> Optional[List[Dict]]:
    """根据客户信息生成基础推荐"""
    if not customer_info or not customer_info.get('loan_amount'):
        return None
    
    loan_amount = customer_info.get('loan_amount', 0)
    if isinstance(loan_amount, str):
        try:
            loan_amount = float(loan_amount.replace(',', '').replace('$', ''))
        except:
            return None
    
    if loan_amount < 5000:
        return None
    
    # 基础推荐模板
    recommendations = [
        {
            "lender_name": "Credit Union Plus",
            "product_name": "Auto Loan Standard",
            "base_rate": 4.5,
            "loan_amount": loan_amount,
            "term_months": int(customer_info.get('loan_term', 60)),
            "monthly_payment": round((loan_amount * 0.045 / 12) / (1 - (1 + 0.045/12)**(-60)), 2),
            "total_interest": round(loan_amount * 0.15, 2),
            "features": ["No prepayment penalty", "Online management"]
        },
        {
            "lender_name": "National Bank",
            "product_name": "Vehicle Finance Pro",
            "base_rate": 5.2,
            "loan_amount": loan_amount,
            "term_months": int(customer_info.get('loan_term', 72)),
            "monthly_payment": round((loan_amount * 0.052 / 12) / (1 - (1 + 0.052/12)**(-72)), 2),
            "total_interest": round(loan_amount * 0.18, 2),
            "features": ["Fast approval", "Flexible terms"]
        }
    ]
    
    return recommendations

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
            "created_at": session_data["created_at"]
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
            "available_endpoints": ["/", "/health", "/chat", "/docs"]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
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
    
    print(f"🚀 启动LIFEX Car Loan AI Agent服务器...")
    print(f"📍 服务器地址: {host}:{port}")
    print(f"🔑 API Key配置: {'✅' if OPENROUTER_API_KEY else '❌ (基础模式)'}")
    print(f"🌐 CORS配置完成")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # 生产环境关闭reload
        log_level="info"
    )