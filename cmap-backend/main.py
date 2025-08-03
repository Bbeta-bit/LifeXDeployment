# main.py - Updated for Claude 4 Integration with Enhanced Services
import os
import requests
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router

# Enhanced Memory Service (Primary)
try:
    from app.services.enhanced_memory_conversation_service import EnhancedMemoryService, ConversationStage
    ENHANCED_MEMORY_AVAILABLE = True
    print("✅ Enhanced memory service loaded")
except ImportError as e:
    print(f"⚠️ Enhanced memory service not available: {e}")
    ENHANCED_MEMORY_AVAILABLE = False

# AI Service for Claude 4
try:
    from app.services.ai_service import UnifiedAIService, AIProvider
    AI_SERVICE_AVAILABLE = True
    print("✅ Unified AI service loaded")
except ImportError as e:
    print(f"⚠️ AI service not available: {e}")
    AI_SERVICE_AVAILABLE = False

# Enhanced Services
try:
    from app.services.enhanced_prompt_service import EnhancedPromptService
    ENHANCED_PROMPT_AVAILABLE = True
    print("✅ Enhanced prompt service loaded")
except ImportError as e:
    print(f"⚠️ Enhanced prompt service not available: {e}")
    ENHANCED_PROMPT_AVAILABLE = False

try:
    from app.services.conversation_flow_service import EnhancedConversationFlowService
    CONVERSATION_FLOW_AVAILABLE = True
    print("✅ Enhanced conversation flow service loaded")
except ImportError as e:
    print(f"⚠️ Conversation flow service not available: {e}")
    CONVERSATION_FLOW_AVAILABLE = False

try:
    from app.services.mvp_preference_extractor import MVPPreferenceExtractor
    MVP_EXTRACTOR_AVAILABLE = True
    print("✅ MVP preference extractor loaded")
except ImportError as e:
    print(f"⚠️ MVP preference extractor not available: {e}")
    MVP_EXTRACTOR_AVAILABLE = False

try:
    from app.services.product_matching_service import ProductMatchingService
    PRODUCT_MATCHING_AVAILABLE = True
    print("✅ Product matching service loaded")
except ImportError as e:
    print(f"⚠️ Product matching service not available: {e}")
    PRODUCT_MATCHING_AVAILABLE = False

try:
    from app.services.enhanced_customer_extractor import EnhancedCustomerInfoExtractor
    CUSTOMER_EXTRACTOR_AVAILABLE = True
    print("✅ Enhanced customer extractor loaded")
except ImportError as e:
    print(f"⚠️ Enhanced customer extractor not available: {e}")
    CUSTOMER_EXTRACTOR_AVAILABLE = False

# Load environment variables
load_dotenv(dotenv_path="API.env")

# Fallback OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Create FastAPI application
app = FastAPI(
    title="Car Loan AI Agent - Claude 4 Enhanced",
    description="AI agent backend with Claude 4, enhanced memory, and multi-lender support",
    version="3.0-claude4-enhanced"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://cmap-frontend.onrender.com",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
enhanced_memory_service = EnhancedMemoryService() if ENHANCED_MEMORY_AVAILABLE else None
ai_service = UnifiedAIService() if AI_SERVICE_AVAILABLE else None
enhanced_prompt_service = EnhancedPromptService() if ENHANCED_PROMPT_AVAILABLE else None
conversation_flow_service = EnhancedConversationFlowService() if CONVERSATION_FLOW_AVAILABLE else None
mvp_extractor = MVPPreferenceExtractor() if MVP_EXTRACTOR_AVAILABLE else None
product_matcher = ProductMatchingService() if PRODUCT_MATCHING_AVAILABLE else None
customer_extractor = EnhancedCustomerInfoExtractor() if CUSTOMER_EXTRACTOR_AVAILABLE else None

# Configure AI service for Claude 4
if AI_SERVICE_AVAILABLE and ai_service:
    # Try to use Claude 4 through OpenRouter, fallback to Gemini
    try:
        ai_service.switch_provider(AIProvider.OPENROUTER, "claude")
        print("✅ Configured for Claude 4 via OpenRouter")
    except:
        ai_service.switch_provider(AIProvider.OPENROUTER, "gemini_flash")
        print("⚠️ Fallback to Gemini Flash")

app.include_router(api_router)

@app.post("/chat")
async def chat(request: Request):
    """Enhanced chat endpoint with Claude 4, memory, and multi-lender support"""
    try:
        data = await request.json()
        user_input = data.get("message")
        session_id = data.get("session_id", "default")
        chat_history = data.get("history", [])
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

        # Enhanced memory context building
        memory_context = ""
        extracted_info = {}
        conversation_state = None
        
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            # Create memory-aware context
            memory_context = enhanced_memory_service.create_context_aware_prompt(session_id, user_input)
            
            # Get session memory
            memory = enhanced_memory_service.get_or_create_session(session_id)
            
            # Extract customer information from conversation history
            if CUSTOMER_EXTRACTOR_AVAILABLE and customer_extractor:
                conversation_for_extraction = chat_history + [{"role": "user", "content": user_input}]
                customer_info = await customer_extractor.extract_from_conversation(conversation_for_extraction)
                
                # Update memory with extracted info
                for field in customer_info.extracted_fields:
                    value = getattr(customer_info.personal_info, field, None) or \
                           getattr(customer_info.business_info, field, None) or \
                           getattr(customer_info.asset_info, field, None) or \
                           getattr(customer_info.financial_info, field, None)
                    if value is not None:
                        memory.customer_info.update_field(field, value)
            
            # Get collected information from memory
            collected_fields = {}
            for field in memory.customer_info.confirmed_fields:
                value = getattr(memory.customer_info, field, None)
                if value is not None:
                    collected_fields[field] = value
            
            extracted_info = {"mvp_fields": collected_fields, "preferences": {}}
        
        # Conversation flow management
        if CONVERSATION_FLOW_AVAILABLE and conversation_flow_service:
            if session_id not in conversation_states:
                conversation_state = conversation_flow_service.init_conversation_state()
            else:
                conversation_state = conversation_states[session_id]
            
            # Update conversation state with extracted info
            conversation_state = conversation_flow_service.update_conversation_state(
                conversation_state, extracted_info
            )
            
            conversation_states[session_id] = conversation_state
        
        # Build AI messages with enhanced prompts
        messages = []
        
        # System prompt with memory and conversation context
        if ENHANCED_PROMPT_AVAILABLE and enhanced_prompt_service and conversation_state:
            context = conversation_flow_service.get_conversation_context(conversation_state)
            system_prompt = enhanced_prompt_service.create_system_prompt(
                conversation_state.stage, context
            )
        else:
            system_prompt = f"""You are a professional loan advisor AI assistant with enhanced capabilities.

## CORE PRINCIPLES:
1. NEVER repeat questions about information the customer has already provided
2. DO NOT repeat questions that were asked in recent conversation rounds
3. Use existing information intelligently to advance the conversation
4. Only ask for genuinely missing critical information

## CURRENT MEMORY CONTEXT:
{memory_context if memory_context else "No memory context available"}

## YOUR TASK:
- Respond intelligently based on the memory context above
- Only ask for truly missing important information
- Avoid ANY form of repetitive questioning
- When sufficient information is available, recommend suitable loan products from ALL FOUR LENDERS: Angle, BFS, FCAU, and RAF
- Always specify lender name clearly in recommendations: [Lender Name] - [Product Name]

Please respond based on the above context and memory information."""

        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (limit to avoid token overflow)
        recent_history = chat_history[-8:] if len(chat_history) > 8 else chat_history
        for chat in recent_history:
            if "user" in chat and "assistant" in chat:
                messages.append({"role": "user", "content": chat["user"]})
                messages.append({"role": "assistant", "content": chat["assistant"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
        # Call AI service (Claude 4 or fallback)
        response = None
        if AI_SERVICE_AVAILABLE and ai_service:
            response = await ai_service.call_ai(messages, temperature=0.7, max_tokens=1200)
        
        # Fallback to OpenRouter direct call
        if not response:
            response = await _call_openrouter_api(messages)
        
        if not response:
            return _create_error_response("Failed to get AI response")
        
        # Update memory and conversation state
        conversation_summary = {}
        if ENHANCED_MEMORY_AVAILABLE and enhanced_memory_service:
            memory = enhanced_memory_service.get_or_create_session(session_id)
            memory.add_message("assistant", response)
            conversation_summary = enhanced_memory_service.get_conversation_summary(session_id)
        
        # Product matching if sufficient information
        matched_products_count = 0
        product_matches = []
        if PRODUCT_MATCHING_AVAILABLE and extracted_info.get("mvp_fields"):
            mvp_fields = extracted_info["mvp_fields"]
            if len(mvp_fields) >= 3:  # When enough information is available
                try:
                    matching_result = product_matcher.find_best_loan_product(
                        user_profile=mvp_fields,
                        soft_prefs=extracted_info.get("preferences", {})
                    )
                    matched_products_count = len(matching_result.get("matches", []))
                    product_matches = matching_result.get("matches", [])
                except Exception as e:
                    print(f"Product matching error: {e}")
        
        return {
            "reply": response,
            "session_id": session_id,
            "memory_summary": conversation_summary,
            "extracted_info": extracted_info,
            "matched_products_count": matched_products_count,
            "conversation_stage": conversation_state.stage.value if conversation_state else "unknown",
            "ai_provider": ai_service.get_current_config() if AI_SERVICE_AVAILABLE else "fallback",
            "status": "success",
            "features": {
                "claude_4_support": AI_SERVICE_AVAILABLE,
                "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
                "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
                "context_aware": ENHANCED_MEMORY_AVAILABLE,
                "conversation_flow": CONVERSATION_FLOW_AVAILABLE,
                "mvp_extraction": MVP_EXTRACTOR_AVAILABLE,
                "customer_extraction": CUSTOMER_EXTRACTOR_AVAILABLE,
                "product_matching": PRODUCT_MATCHING_AVAILABLE,
                "multi_lender_support": True
            }
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        return _create_error_response(f"Technical issue: {str(e)}")

@app.post("/switch-ai-provider")
async def switch_ai_provider(request: Request):
    """Switch AI provider and model"""
    try:
        data = await request.json()
        provider = data.get("provider", "openrouter")
        model = data.get("model", "gemini_flash")
        
        if not AI_SERVICE_AVAILABLE or not ai_service:
            return {
                "status": "not_available",
                "message": "AI service not loaded"
            }
        
        try:
            if provider == "openrouter":
                ai_service.switch_provider(AIProvider.OPENROUTER, model)
            elif provider == "google_studio":
                ai_service.switch_provider(AIProvider.GOOGLE_STUDIO, model)
            else:
                return {
                    "status": "error",
                    "message": f"Unsupported provider: {provider}"
                }
            
            return {
                "status": "success",
                "current_config": ai_service.get_current_config(),
                "message": f"Switched to {provider} - {model}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-memory-status")
async def get_memory_status(request: Request):
    """Get comprehensive memory system status"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        if not ENHANCED_MEMORY_AVAILABLE or not enhanced_memory_service:
            return {
                "status": "memory_not_available",
                "message": "Enhanced memory service not loaded"
            }
        
        summary = enhanced_memory_service.get_conversation_summary(session_id)
        memory = enhanced_memory_service.get_or_create_session(session_id)
        
        return {
            "status": "memory_available",
            "session_summary": summary,
            "anti_repetition_status": {
                "asked_fields": list(memory.customer_info.asked_fields),
                "confirmed_fields": list(memory.customer_info.confirmed_fields),
                "recent_questions": memory.last_questions[-5:],
                "conversation_rounds": memory.conversation_round
            },
            "next_recommended_questions": enhanced_memory_service.get_next_questions(session_id, max_questions=3),
            "customer_profile": {
                field: getattr(memory.customer_info, field) 
                for field in memory.customer_info.confirmed_fields
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-customer-info")
async def extract_customer_info(request: Request):
    """Extract comprehensive customer information"""
    try:
        data = await request.json()
        conversation_history = data.get("conversation_history", [])
        
        if not CUSTOMER_EXTRACTOR_AVAILABLE or not customer_extractor:
            return {
                "status": "not_available",
                "message": "Customer extractor not loaded"
            }
        
        customer_info = await customer_extractor.extract_from_conversation(conversation_history)
        
        return {
            "status": "success",
            "customer_info": {
                "loan_type": customer_info.loan_type,
                "personal_info": customer_info.personal_info.dict(),
                "business_info": customer_info.business_info.dict(),
                "asset_info": customer_info.asset_info.dict(),
                "financial_info": customer_info.financial_info.dict(),
                "extracted_fields": customer_info.extracted_fields,
                "confidence_score": customer_info.confidence_score
            },
            "missing_fields": customer_extractor.get_missing_fields(customer_info),
            "follow_up_questions": customer_extractor.generate_follow_up_questions(customer_info)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find-products-multi-lender")
async def find_products_multi_lender(request: Request):
    """Find products across all lenders"""
    try:
        data = await request.json()
        user_profile = data.get("user_profile", {})
        preferences = data.get("preferences", {})
        
        if not PRODUCT_MATCHING_AVAILABLE or not product_matcher:
            return {
                "status": "not_available",
                "message": "Product matching service not loaded"
            }
        
        result = product_matcher.find_best_loan_product(
            user_profile=user_profile,
            soft_prefs=preferences
        )
        
        return {
            **result,
            "lenders_checked": ["Angle", "BFS", "FCAU", "RAF"],
            "service_type": "multi_lender"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Car Loan AI Agent - Claude 4 Enhanced",
        "version": "3.0-claude4-enhanced",
        "ai_provider": ai_service.get_current_config() if AI_SERVICE_AVAILABLE else "fallback",
        "features": {
            "claude_4_support": AI_SERVICE_AVAILABLE,
            "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
            "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
            "context_awareness": ENHANCED_MEMORY_AVAILABLE,
            "enhanced_prompt": ENHANCED_PROMPT_AVAILABLE,
            "conversation_flow": CONVERSATION_FLOW_AVAILABLE,
            "mvp_extraction": MVP_EXTRACTOR_AVAILABLE,
            "customer_extraction": CUSTOMER_EXTRACTOR_AVAILABLE,
            "product_matching": PRODUCT_MATCHING_AVAILABLE,
            "multi_lender_support": True
        },
        "lenders_supported": ["Angle", "BFS", "FCAU", "RAF"],
        "ai_capabilities": {
            "providers_available": ["OpenRouter", "Google Studio"] if AI_SERVICE_AVAILABLE else ["OpenRouter Fallback"],
            "models_available": ["Claude 4", "Gemini Flash", "GPT-4"] if AI_SERVICE_AVAILABLE else ["Gemini Flash"]
        }
    }

@app.get("/system-status")
async def system_status():
    """Comprehensive system status"""
    return {
        "timestamp": "2025-08-03",
        "version": "3.0-claude4-enhanced",
        "services": {
            "ai_service": {
                "available": AI_SERVICE_AVAILABLE,
                "current_provider": ai_service.get_current_config() if AI_SERVICE_AVAILABLE else None,
                "status": "loaded" if AI_SERVICE_AVAILABLE else "not_found"
            },
            "enhanced_memory_service": {
                "available": ENHANCED_MEMORY_AVAILABLE,
                "status": "loaded" if ENHANCED_MEMORY_AVAILABLE else "not_found",
                "active_sessions": len(enhanced_memory_service.sessions) if ENHANCED_MEMORY_AVAILABLE else 0
            },
            "enhanced_prompt_service": {
                "available": ENHANCED_PROMPT_AVAILABLE,
                "status": "loaded" if ENHANCED_PROMPT_AVAILABLE else "not_found"
            },
            "conversation_flow_service": {
                "available": CONVERSATION_FLOW_AVAILABLE,
                "status": "loaded" if CONVERSATION_FLOW_AVAILABLE else "not_found"
            },
            "mvp_preference_extractor": {
                "available": MVP_EXTRACTOR_AVAILABLE,
                "status": "loaded" if MVP_EXTRACTOR_AVAILABLE else "not_found"
            },
            "customer_extractor": {
                "available": CUSTOMER_EXTRACTOR_AVAILABLE,
                "status": "loaded" if CUSTOMER_EXTRACTOR_AVAILABLE else "not_found"
            },
            "product_matching_service": {
                "available": PRODUCT_MATCHING_AVAILABLE,
                "status": "loaded" if PRODUCT_MATCHING_AVAILABLE else "not_found"
            }
        },
        "functionality": {
            "claude_4_ai": AI_SERVICE_AVAILABLE,
            "enhanced_memory": ENHANCED_MEMORY_AVAILABLE,
            "anti_repetition": ENHANCED_MEMORY_AVAILABLE,
            "conversation_management": CONVERSATION_FLOW_AVAILABLE,
            "customer_extraction": CUSTOMER_EXTRACTOR_AVAILABLE,
            "product_matching": PRODUCT_MATCHING_AVAILABLE,
            "multi_lender_support": True
        },
        "recommendations": {
            "production_ready": all([
                AI_SERVICE_AVAILABLE,
                ENHANCED_MEMORY_AVAILABLE,
                CONVERSATION_FLOW_AVAILABLE,
                PRODUCT_MATCHING_AVAILABLE
            ]),
            "missing_services": [
                service for service, available in [
                    ("ai_service", AI_SERVICE_AVAILABLE),
                    ("enhanced_memory", ENHANCED_MEMORY_AVAILABLE),
                    ("conversation_flow", CONVERSATION_FLOW_AVAILABLE),
                    ("product_matching", PRODUCT_MATCHING_AVAILABLE)
                ] if not available
            ]
        }
    }

# Store conversation states
conversation_states = {}

# Helper functions

async def _call_openrouter_api(messages: list) -> str:
    """Fallback OpenRouter API call"""
    try:
        if not OPENROUTER_API_KEY:
            return "API key not configured. Please check your environment settings."
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1200
        }

        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return "I'm experiencing connectivity issues. Please try again later."

        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        print(f"OpenRouter API call failed: {e}")
        return "I'm having technical difficulties. Please try again."

def _create_error_response(error_message: str) -> dict:
    """Create standardized error response"""
    return {
        "reply": "I apologize, but I'm experiencing a technical issue. Please try again or contact our support team if the problem persists.",
        "status": "error",
        "error_detail": error_message,
        "features": {
            "claude_4_support": AI_SERVICE_AVAILABLE,
            "enhanced_memory": False,
            "anti_repetition": False,
            "context_awareness": False
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)