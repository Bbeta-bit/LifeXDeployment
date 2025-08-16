# main.py - 完整修复版本，包含所有增强功能
import os
import requests
import json
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
from typing import Dict, List, Optional, Any

# Load environment variables
load_dotenv()

# Import services with fallback handling
try:
    from unified_intelligent_service import UnifiedIntelligentService
    unified_service = UnifiedIntelligentService()
    UNIFIED_SERVICE_AVAILABLE = True
    print("✅ Unified intelligent service loaded")
except ImportError as e:
    print(f"⚠️ Unified intelligent service not available: {e}")
    UNIFIED_SERVICE_AVAILABLE = False
    unified_service = None

# Import enhanced memory service
try:
    from conversation_flow_service import EnhancedMemoryService, ConversationStage
    enhanced_memory_service = EnhancedMemoryService()
    ENHANCED_MEMORY_AVAILABLE = True
    print("✅ Enhanced memory service loaded")
except ImportError as e:
    print(f"⚠️ Enhanced memory service not available: {e}")
    ENHANCED_MEMORY_AVAILABLE = False
    enhanced_memory_service = None

# Import other services with fallback
try:
    from app.services.enhanced_prompt_service import EnhancedPromptService
    prompt_service = EnhancedPromptService()
    ENHANCED_PROMPT_AVAILABLE = True
    print("✅ Enhanced prompt service loaded")
except ImportError as e:
    print(f"⚠️ Enhanced prompt service not available: {e}")
    ENHANCED_PROMPT_AVAILABLE = False
    try:
        from app.services.prompt_service import PromptService
        prompt_service = PromptService()
        print("✅ Using basic prompt service")
    except ImportError:
        print("❌ No prompt service available")
        prompt_service = None

try:
    from app.services.mvp_preference_extractor import MVPPreferenceExtractor
    mvp_extractor = MVPPreferenceExtractor()
    MVP_EXTRACTOR_AVAILABLE = True
    print("✅ MVP extractor loaded")
except ImportError as e:
    print(f"⚠️ MVP extractor not available: {e}")
    MVP_EXTRACTOR_AVAILABLE = False
    mvp_extractor = None

try:
    from app.services.product_matching_service import ProductMatchingService
    product_matcher = ProductMatchingService()
    PRODUCT_MATCHING_AVAILABLE = True
    print("✅ Product matching service loaded")
except ImportError as e:
    print(f"⚠️ Product matching service not available: {e}")
    PRODUCT_MATCHING_AVAILABLE = False
    product_matcher = None

# Import multi-lender services if available
try:
    from app.services.integrated_loan_matching_service import IntegratedLoanMatchingService
    from app.services.multi_lender_product_matcher import MultiLenderProductMatcher
    from app.services.monthly_payment_calculator import MonthlyPaymentCalculator
    integrated_matcher = IntegratedLoanMatchingService()
    multi_lender_matcher = MultiLenderProductMatcher()
    payment_calculator = MonthlyPaymentCalculator()
    MULTI_LENDER_AVAILABLE = True
    print("✅ Multi-lender matching system loaded")
except ImportError as e:
    print(f"⚠️ Multi-lender services not available: {e}")
    MULTI_LENDER_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="LIFEX Car Loan AI Agent",
    description="Enhanced AI assistant for car loan recommendations with business structure handling and amount updates",
    version="2.2-enhanced-fixed"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://lifex-car-loan-ai-agent.onrender.com",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router if available
try:
    from app.api.router import router as api_router
    app.include_router(api_router)
    print("✅ API router loaded")
except ImportError as e:
    print(f"⚠️ API router not available: {e}")

# Serve static files (for production)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the frontend application"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "LIFEX Car Loan AI Agent API is running", "status": "healthy"}

# Helper functions
def _create_error_response(message: str) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "reply": f"I apologize, but I'm experiencing some technical difficulties. {message}",
        "status": "error",
        "error_message": message,
        "session_id": "error",
        "features": {
            "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
            "unified_service": UNIFIED_SERVICE_AVAILABLE,
            "multi_lender_matching": MULTI_LENDER_AVAILABLE
        }
    }

async def _call_openrouter_api(messages: List[Dict[str, str]]) -> str:
    """Call OpenRouter API with fallback handling"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "I need an API key to provide intelligent responses. Please contact support."
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": messages,
                    "max_tokens": 2000,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"OpenRouter API error: {response.status_code} - {response.text}")
                return "I'm having trouble connecting to my AI service. Please try again in a moment."
                
    except Exception as e:
        print(f"OpenRouter API exception: {e}")
        return "I'm experiencing connectivity issues. Please try again shortly."

def _format_product_details(product_match) -> str:
    """Format detailed product information for response"""
    try:
        if hasattr(product_match, 'product_name'):
            details = f"""

## Recommended Product Details

**{product_match.lender_name} - {product_match.product_name}**
- **Base Rate**: {product_match.interest_rate}%
- **Comparison Rate**: {product_match.comparison_rate}% (includes fees)
- **Maximum Loan Amount**: ${product_match.loan_amount_max:,}
- **Loan Terms**: {product_match.loan_term_options}

**Monthly Payment**: ${product_match.monthly_payment:,.2f} (estimated)

**Fees Breakdown**:
{_format_fees(product_match.fees_breakdown)}

**Eligibility Status**: {'✅ All requirements met' if product_match.all_requirements_met else '⚠️ Some requirements need verification'}

**Why this product**: {', '.join(product_match.reasons)}
"""
        else:
            details = f"""
## Product Recommendation Available
Based on your information, I can recommend suitable loan products. Please provide any missing details for a complete assessment.
"""
        return details
    except Exception as e:
        print(f"Error formatting product details: {e}")
        return "Product details available - please check the comparison panel."

def _format_fees(fees_breakdown) -> str:
    """Format fees breakdown"""
    try:
        if isinstance(fees_breakdown, dict):
            formatted_fees = []
            for fee_type, amount in fees_breakdown.items():
                formatted_fees.append(f"- {fee_type}: ${amount}")
            return "\n".join(formatted_fees)
        return "Fees information available in product comparison panel"
    except Exception:
        return "Standard fees apply - see product comparison for details"

@app.post("/chat")
async def chat(request: Request):
    """🔧 修复：增强的chat端点，支持业务结构、会话重置和贷款金额更新"""
    try:
        data = await request.json()
        user_input = data.get("message")
        session_id = data.get("session_id", "default")
        chat_history = data.get("history", [])
        current_customer_info = data.get("current_customer_info", {})
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

        print(f"🔄 Processing chat request - Session: {session_id}")
        print(f"📝 User input: {user_input[:100]}...")
        print(f"📊 Customer info provided: {bool(current_customer_info)}")

        # 🔧 修复：使用统一智能服务处理对话
        if UNIFIED_SERVICE_AVAILABLE and unified_service:
            try:
                # 使用增强的对话处理
                result = await unified_service.process_conversation(
                    user_message=user_input,
                    session_id=session_id,
                    chat_history=chat_history,
                    current_customer_info=current_customer_info
                )
                
                # 🔧 修复：增强的响应格式
                response_data = {
                    "reply": result.get("reply", "I'm here to help you with loan options."),
                    "session_id": session_id,
                    "conversation_stage": result.get("stage", "mvp_collection"),
                    "customer_profile": result.get("customer_profile", {}),
                    "recommendations": result.get("recommendations", []),
                    "next_questions": result.get("next_questions", []),
                    "round_count": result.get("round_count", 1),
                    "features": {
                        "enhanced_memory": True,
                        "anti_repetition": True,
                        "context_aware": True,
                        "business_structure_handling": True,
                        "loan_amount_updates": True,
                        "session_reset_detection": True,
                        "product_matching": True,
                        "unified_service": True
                    },
                    "status": "success"
                }
                
                # 🔧 修复：检查是否有调整标记
                if result.get("adjustment_made"):
                    response_data["adjustment_made"] = True
                    response_data["adjustment_type"] = "loan_amount_update"
                
                print(f"✅ Unified service response generated successfully")
                return response_data
                
            except Exception as e:
                print(f"❌ Error in unified service: {e}")
                # 继续到降级处理
                pass
        
        # 降级处理：使用增强内存服务
        enhanced_response = ""
        memory_context = ""
        extracted_info = {}
        conversation_summary = {}
        
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            try:
                # 🔧 修复：检查会话重置
                if enhanced_memory_service.should_reset_session(session_id, user_input):
                    enhanced_memory_service.reset_session(session_id)
                    print(f"🔄 Session {session_id} reset for new loan case")
                
                # 创建内存感知上下文
                memory_context = enhanced_memory_service.create_context_aware_prompt(session_id, user_input)
                
                # 获取会话内存
                memory = enhanced_memory_service.get_or_create_session(session_id)
                
                # 🔧 修复：检测贷款金额变更
                amount_change = enhanced_memory_service.detect_loan_amount_change(session_id, user_input)
                if amount_change:
                    memory.customer_info.update_field('desired_loan_amount', amount_change)
                    enhanced_response = f"Perfect! I've updated your loan amount to ${amount_change:,}. Let me find the best products that can handle this amount."
                    print(f"💰 Loan amount updated to ${amount_change:,}")
                
                # 提取收集的信息
                collected_fields = {}
                for field in memory.customer_info.confirmed_fields:
                    value = getattr(memory.customer_info, field, None)
                    if value is not None:
                        collected_fields[field] = value
                
                extracted_info = {"mvp_fields": collected_fields, "preferences": {}}
                conversation_summary = enhanced_memory_service.get_conversation_summary(session_id)
                
                print(f"📊 Enhanced memory processing completed")
                
            except Exception as e:
                print(f"⚠️ Enhanced memory service error: {e}")
        
        # 降级提取
        elif MVP_EXTRACTOR_AVAILABLE and mvp_extractor:
            try:
                conversation_for_extraction = chat_history + [{"role": "user", "content": user_input}]
                extracted_info = await mvp_extractor.extract_mvp_and_preferences(conversation_for_extraction)
                print(f"📊 MVP extraction completed")
            except Exception as e:
                print(f"⚠️ MVP extraction error: {e}")
                extracted_info = {}
        
        # 🔧 修复：构建增强的系统提示
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service and memory_context:
            system_prompt = f"""You are a professional loan advisor AI assistant with enhanced capabilities.

## CORE PRINCIPLES:
1. NEVER repeat questions about information the customer has already provided
2. DO NOT repeat questions that were asked in recent conversation rounds  
3. Use existing information intelligently to advance the conversation
4. Prioritize business structure collection early in the conversation
5. Handle loan amount updates by triggering re-matching
6. Detect and handle session resets for new loan cases

## CURRENT MEMORY CONTEXT:
{memory_context}

## ENHANCED FEATURES:
- Business structure recognition and prioritization
- Automatic session reset for new loan cases
- Real-time loan amount update handling
- Anti-repetition memory system
- Context-aware conversation flow

## BUSINESS STRUCTURE HANDLING:
When asking about business structure, use these exact options:
- Sole Trader: For individuals trading alone
- Company (Pty Ltd): For incorporated businesses  
- Partnership: For joint business ventures
- Trust: For trust-based business structures

## LOAN AMOUNT UPDATES:
When customers change loan amounts, immediately:
1. Acknowledge the change
2. Filter products by new loan capacity
3. Recommend products that can handle the new amount
4. Prioritize lowest interest rates

## YOUR TASK:
- Respond intelligently based on memory context
- Only ask for truly missing critical information
- Avoid ANY form of repetitive questioning
- When sufficient information exists, provide comprehensive product recommendations
- Handle business structure as a high-priority field
- Detect and respond to loan amount changes appropriately

Please respond based on the above context and provide detailed, actionable advice."""
        else:
            system_prompt = """You are a professional loan advisor AI assistant. Help customers understand loan products and provide detailed recommendations.

## BUSINESS STRUCTURE PRIORITY:
Always ask about business structure early in the conversation using these options:
- Sole Trader
- Company (Pty Ltd)  
- Partnership
- Trust

## LOAN AMOUNT HANDLING:
When customers mention specific loan amounts or want to change amounts:
1. Acknowledge the amount clearly
2. Find products that can handle this amount
3. Prioritize lowest interest rates
4. Show maximum loan capacities

## ENHANCED FEATURES:
- Business structure field prioritization
- Session reset detection for new loan cases
- Loan amount update handling
- Anti-repetition questioning

When recommending products, always include:
- Specific lender and product names
- Interest rates and comparison rates  
- Monthly payment calculations
- All fees and requirements
- Complete eligibility assessment

Please avoid repeating questions about information already provided."""

        # 构建消息
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加对话历史（限制以避免token溢出）
        recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history
        for chat in recent_history:
            if "user" in chat and "assistant" in chat:
                messages.append({"role": "user", "content": chat["user"]})
                messages.append({"role": "assistant", "content": chat["assistant"]})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_input})
        
        # 调用AI
        if enhanced_response:
            # 使用预构建的响应（用于金额更改等）
            response = enhanced_response
        else:
            response = await _call_openrouter_api(messages)
        
        if not response:
            return _create_error_response("Failed to get AI response")
        
        # 更新内存
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            memory = enhanced_memory_service.get_or_create_session(session_id)
            memory.add_message("assistant", response)
            conversation_summary = enhanced_memory_service.get_conversation_summary(session_id)
        
        # 🔧 修复：增强的产品匹配，包含详细信息
        matched_products_info = []
        matched_products_count = 0
        
        if extracted_info.get("mvp_fields"):
            mvp_fields = extracted_info["mvp_fields"]
            
            # 尝试多贷方匹配
            if MULTI_LENDER_AVAILABLE and len(mvp_fields) >= 3:
                try:
                    conversation_for_matching = chat_history + [{"role": "user", "content": user_input}]
                    matching_result = await integrated_matcher.process_loan_request(
                        conversation_history=conversation_for_matching,
                        customer_profile=mvp_fields
                    )
                    
                    if matching_result and matching_result.get("status") == "success":
                        matched_products_info = matching_result.get("recommendations", [])
                        matched_products_count = len(matched_products_info)
                        
                        print(f"✅ Multi-lender matching: {matched_products_count} products found")
                        
                        # 🔧 修复：按利率排序产品（最低优先）
                        matched_products_info.sort(key=lambda x: x.get('interest_rate', 999))
                        
                except Exception as e:
                    print(f"⚠️ Multi-lender matching failed: {e}")
            
            # 降级到基础产品匹配
            if not matched_products_info and PRODUCT_MATCHING_AVAILABLE and product_matcher:
                try:
                    basic_matches = await product_matcher.find_matching_products(mvp_fields)
                    if basic_matches:
                        matched_products_info = basic_matches[:3]
                        matched_products_count = len(matched_products_info)
                        print(f"✅ Basic product matching: {matched_products_count} products found")
                except Exception as e:
                    print(f"⚠️ Basic product matching failed: {e}")
        
        # 构建最终响应
        return {
            "reply": response,
            "session_id": session_id,
            "conversation_stage": conversation_summary.get("stage", "information_gathering"),
            "customer_profile": extracted_info.get("mvp_fields", {}),
            "conversation_summary": conversation_summary,
            "extracted_info": extracted_info,
            "memory_context_provided": bool(memory_context),
            "recommendations": matched_products_info[:3] if matched_products_info else [],
            "matched_products_count": matched_products_count,
            "matched_products_details": matched_products_info[:3] if matched_products_info else [],
            "status": "success",
            "features": {
                "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
                "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
                "context_aware": ENHANCED_MEMORY_AVAILABLE,
                "business_structure_handling": ENHANCED_MEMORY_AVAILABLE,
                "loan_amount_updates": ENHANCED_MEMORY_AVAILABLE,
                "session_reset_detection": ENHANCED_MEMORY_AVAILABLE,
                "multi_lender_matching": MULTI_LENDER_AVAILABLE,
                "detailed_calculations": True,
                "mvp_extraction": MVP_EXTRACTOR_AVAILABLE,
                "product_matching": PRODUCT_MATCHING_AVAILABLE,
                "unified_service": UNIFIED_SERVICE_AVAILABLE
            }
        }
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return _create_error_response(f"Technical issue: {str(e)}")

# 🔧 修复：添加新的端点用于处理贷款金额更新
@app.post("/update-loan-amount")
async def update_loan_amount(request: Request):
    """处理贷款金额更新请求"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        new_amount = data.get("new_amount")
        
        if not new_amount or new_amount <= 0:
            raise HTTPException(status_code=400, detail="Valid loan amount is required")
        
        print(f"💰 Loan amount update request: ${new_amount:,} for session {session_id}")
        
        # 使用统一智能服务处理金额更新
        if UNIFIED_SERVICE_AVAILABLE and unified_service:
            # 获取当前会话状态
            if session_id in unified_service.conversation_states:
                state = unified_service.conversation_states[session_id]
                
                # 调用金额更新处理器
                result = await unified_service._handle_loan_amount_update(state, new_amount)
                
                print(f"✅ Loan amount updated successfully via unified service")
                return {
                    "status": "success",
                    "message": result.get("message"),
                    "new_amount": new_amount,
                    "recommendations": result.get("recommendations", []),
                    "adjustment_made": True
                }
        
        # 降级处理
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            memory = enhanced_memory_service.get_or_create_session(session_id)
            memory.customer_info.update_field('desired_loan_amount', new_amount)
            
            print(f"✅ Loan amount updated via enhanced memory service")
            return {
                "status": "success", 
                "message": f"Loan amount updated to ${new_amount:,}. New product recommendations will be generated.",
                "new_amount": new_amount
            }
        
        return {
            "status": "limited_success",
            "message": f"Loan amount noted as ${new_amount:,}. Please continue the conversation for updated recommendations.",
            "new_amount": new_amount
        }
        
    except Exception as e:
        print(f"❌ Update loan amount error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🔧 修复：添加会话重置端点
@app.post("/reset-session")
async def reset_session(request: Request):
    """重置会话用于新的贷款案例"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        print(f"🔄 Session reset request for: {session_id}")
        
        # 使用统一智能服务重置
        if UNIFIED_SERVICE_AVAILABLE and unified_service:
            if session_id in unified_service.conversation_states:
                del unified_service.conversation_states[session_id]
                print(f"🔄 Unified service session {session_id} reset")
        
        # 使用增强内存服务重置
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            enhanced_memory_service.reset_session(session_id)
        
        print(f"✅ Session {session_id} reset completed")
        return {
            "status": "success",
            "message": f"Session {session_id} has been reset for a new loan case",
            "session_id": session_id
        }
        
    except Exception as e:
        print(f"❌ Reset session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-memory")
async def reset_memory(request: Request):
    """Reset memory system"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            enhanced_memory_service.clear_session(session_id)
            return {
                "status": "success",
                "message": f"Memory cleared for session {session_id}"
            }
        else:
            return {
                "status": "not_available",
                "message": "Enhanced memory service not available"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session-status/{session_id}")
async def get_session_status(session_id: str):
    """Get session status and information"""
    try:
        if UNIFIED_SERVICE_AVAILABLE and unified_service:
            status = await unified_service.get_conversation_status(session_id)
            return status
        elif ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            summary = enhanced_memory_service.get_conversation_summary(session_id)
            return {
                "status": "active" if summary else "no_session",
                "summary": summary
            }
        else:
            return {
                "status": "service_unavailable",
                "message": "No session management service available"
            }
    except Exception as e:
        print(f"❌ Session status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 🔧 修复：增强的健康检查端点
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "LIFEX Car Loan AI Agent with Enhanced Business Structure and Amount Update Support",
        "version": "2.2-enhanced-fixed",
        "timestamp": "2025-08-16",
        "fixes_applied": [
            "Business structure field prioritization",
            "Enhanced auto-extraction with business structure patterns", 
            "Loan amount update with automatic re-matching",
            "Session reset detection for new loan cases",
            "Lowest interest rate prioritization",
            "Anti-repetition memory system",
            "Comprehensive error handling",
            "Multiple service fallback support"
        ],
        "features": {
            "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
            "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
            "context_awareness": ENHANCED_MEMORY_AVAILABLE,
            "business_structure_handling": True,
            "loan_amount_updates": True,
            "session_reset_detection": True,
            "multi_lender_matching": MULTI_LENDER_AVAILABLE,
            "detailed_calculations": True,
            "enhanced_prompt": ENHANCED_PROMPT_AVAILABLE,
            "mvp_extraction": MVP_EXTRACTOR_AVAILABLE,
            "product_matching": PRODUCT_MATCHING_AVAILABLE,
            "unified_service": UNIFIED_SERVICE_AVAILABLE
        }
    }

@app.get("/service-status")
async def service_status():
    """Detailed service availability status"""
    return {
        "timestamp": "2025-08-16",
        "services": {
            "unified_intelligent_service": {
                "available": UNIFIED_SERVICE_AVAILABLE,
                "description": "Main conversation processing with business structure and amount updates"
            },
            "enhanced_memory_service": {
                "available": ENHANCED_MEMORY_AVAILABLE,
                "description": "Anti-repetition memory and session management"
            },
            "enhanced_prompt_service": {
                "available": ENHANCED_PROMPT_AVAILABLE,
                "description": "Advanced prompt engineering"
            },
            "mvp_extraction": {
                "available": MVP_EXTRACTOR_AVAILABLE,
                "description": "Customer information extraction"
            },
            "product_matching": {
                "available": PRODUCT_MATCHING_AVAILABLE,
                "description": "Basic product matching"
            },
            "multi_lender_matching": {
                "available": MULTI_LENDER_AVAILABLE,
                "description": "Advanced multi-lender product comparison"
            }
        },
        "capabilities": {
            "business_structure_recognition": True,
            "session_reset_detection": ENHANCED_MEMORY_AVAILABLE,
            "loan_amount_updates": UNIFIED_SERVICE_AVAILABLE or ENHANCED_MEMORY_AVAILABLE,
            "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
            "context_awareness": ENHANCED_MEMORY_AVAILABLE,
            "product_recommendations": PRODUCT_MATCHING_AVAILABLE or MULTI_LENDER_AVAILABLE,
            "fallback_support": True
        }
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return {"error": "Endpoint not found", "status_code": 404}

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return {"error": "Internal server error", "status_code": 500}

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting LIFEX Car Loan AI Agent server...")
    print(f"📍 Server will run on {host}:{port}")
    print(f"🔧 Available features: Enhanced Memory: {ENHANCED_MEMORY_AVAILABLE}, Unified Service: {UNIFIED_SERVICE_AVAILABLE}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV") != "production",
        log_level="info"
    )