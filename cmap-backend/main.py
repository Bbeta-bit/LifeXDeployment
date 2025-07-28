import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.services.enhanced_prompt_service import EnhancedPromptService, ConversationStage
from app.services.conversation_flow_service import ConversationFlowService, ConversationState
from app.services.mvp_preference_extractor import MVPPreferenceExtractor
from app.services.product_matching_service import ProductMatchingService

# Load environment variables
load_dotenv(dotenv_path="API.env")

# OpenRouter API configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Create FastAPI application
app = FastAPI(
    title="Car Loan AI Agent",
    description="AI agent backend for car loan company with structured conversation flow",
    version="0.2"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://cmap-frontend.onrender.com",
        "https://*.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
prompt_service = EnhancedPromptService()
flow_service = ConversationFlowService()
mvp_extractor = MVPPreferenceExtractor()
product_matcher = ProductMatchingService()

# Store conversation states (in production, use Redis or database)
conversation_states = {}

app.include_router(api_router)

@app.post("/chat")
async def chat(request: Request):
    """Main chat endpoint with structured conversation flow"""
    try:
        data = await request.json()
        user_input = data.get("message")
        session_id = data.get("session_id", "default")
        chat_history = data.get("history", [])
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

        # Get or initialize conversation state
        if session_id not in conversation_states:
            conversation_states[session_id] = flow_service.init_conversation_state()
        
        current_state = conversation_states[session_id]
        
        # Extract MVP and preferences from conversation
        conversation_for_extraction = chat_history + [{"role": "user", "content": user_input}]
        extracted_data = await mvp_extractor.extract_mvp_and_preferences(conversation_for_extraction)
        
        # Update conversation state
        update_data = {}
        update_data.update(extracted_data.get("mvp_fields", {}))
        update_data.update(extracted_data.get("preferences", {}))
        
        updated_state = flow_service.update_conversation_state(current_state, update_data)
        
        # Handle stage-specific logic
        if updated_state.stage == ConversationStage.PRODUCT_MATCHING:
            matching_result = await _handle_product_matching(updated_state)
            if matching_result.get("status") == "no_perfect_match":
                updated_state.gaps = _extract_gaps_from_matches(matching_result.get("matches", []))
                updated_state.stage = ConversationStage.GAP_ANALYSIS
            else:
                updated_state.matched_products = matching_result.get("matches", [])
        
        # Prepare context for prompt generation
        context = flow_service.get_conversation_context(updated_state)
        
        # Create stage-specific messages
        messages = prompt_service.create_chat_messages(
            user_input, 
            updated_state.stage, 
            context, 
            chat_history
        )
        
        # Add stage-specific system instructions
        messages = _add_stage_instructions(messages, updated_state)
        
        # Call OpenRouter API
        response = await _call_openrouter_api(messages)
        
        if not response:
            return _create_error_response("Failed to get AI response")
        
        # Update conversation state
        updated_state.conversation_round += 1
        conversation_states[session_id] = updated_state
        
        return {
            "reply": response,
            "conversation_stage": updated_state.stage.value,
            "mvp_progress": {
                "completed_fields": list(updated_state.mvp_fields.keys()),
                "missing_fields": updated_state.missing_mvp_fields,
                "is_complete": len(updated_state.missing_mvp_fields) == 0
            },
            "preferences_collected": updated_state.preferences,
            "matched_products_count": len(updated_state.matched_products),
            "conversation_round": updated_state.conversation_round,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Chat error: {e}")
        return _create_error_response(f"Technical issue: {str(e)}")

@app.post("/get-conversation-state")
async def get_conversation_state(request: Request):
    """Get current conversation state for debugging"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        if session_id in conversation_states:
            state = conversation_states[session_id]
            return {
                "session_id": session_id,
                "stage": state.stage.value,
                "mvp_fields": state.mvp_fields,
                "missing_mvp_fields": state.missing_mvp_fields,
                "preferences": state.preferences,
                "conversation_round": state.conversation_round,
                "gaps": state.gaps,
                "matched_products_count": len(state.matched_products)
            }
        else:
            return {
                "session_id": session_id,
                "stage": "not_started",
                "message": "No conversation state found"
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-conversation")
async def reset_conversation(request: Request):
    """Reset conversation state for a session"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        
        conversation_states[session_id] = flow_service.init_conversation_state()
        
        return {
            "status": "success",
            "message": f"Conversation state reset for session {session_id}",
            "new_stage": "greeting"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/force-stage-transition")
async def force_stage_transition(request: Request):
    """Force transition to a specific stage (for testing)"""
    try:
        data = await request.json()
        session_id = data.get("session_id", "default")
        target_stage = data.get("target_stage")
        
        if session_id not in conversation_states:
            raise HTTPException(status_code=404, detail="Session not found")
        
        try:
            new_stage = ConversationStage(target_stage)
            conversation_states[session_id].stage = new_stage
            
            return {
                "status": "success",
                "message": f"Stage changed to {target_stage}",
                "current_stage": new_stage.value
            }
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {target_stage}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Car Loan AI Agent is running with structured flow",
        "services": {
            "prompt_service": "loaded",
            "flow_service": "loaded", 
            "mvp_extractor": "loaded",
            "product_matcher": "loaded"
        },
        "conversation_stages": [stage.value for stage in ConversationStage]
    }

# Helper functions

async def _call_openrouter_api(messages: list) -> str:
    """Call OpenRouter API and return response"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return None

        result = response.json()
        return result['choices'][0]['message']['content']
        
    except Exception as e:
        print(f"OpenRouter API call failed: {e}")
        return None

def _add_stage_instructions(messages: list, state: ConversationState) -> list:
    """Add stage-specific instructions to messages"""
    
    if state.stage == ConversationStage.MVP_COLLECTION:
        next_fields = flow_service.get_next_mvp_fields_to_ask(state, max_fields=2)
        if next_fields:
            questions = flow_service.generate_mvp_questions(next_fields)
            instruction = f"\n\n[SYSTEM INSTRUCTION: Ask about these specific MVP fields: {list(questions.keys())}. Use these questions: {list(questions.values())}. Do NOT ask about preferences yet.]"
            messages[-1]["content"] += instruction
    
    elif state.stage == ConversationStage.PREFERENCE_COLLECTION:
        if not state.preferences:
            instruction = f"\n\n[SYSTEM INSTRUCTION: MVP collection is complete. Now ask the customer to choose 1-2 preferences from the 4 options in your system prompt. Present the preference collection prompt clearly.]"
            messages[-1]["content"] += instruction
    
    elif state.stage == ConversationStage.PRODUCT_MATCHING:
        if state.matched_products:
            products_summary = _format_products_for_prompt(state.matched_products)
            instruction = f"\n\n[SYSTEM INSTRUCTION: Present these matched products: {products_summary}. Explain why each matches their needs.]"
            messages[-1]["content"] += instruction
    
    elif state.stage == ConversationStage.GAP_ANALYSIS:
        if state.gaps:
            instruction = f"\n\n[SYSTEM INSTRUCTION: Address these gaps: {state.gaps}. Offer solutions or alternatives.]"
            messages[-1]["content"] += instruction
    
    return messages

async def _handle_product_matching(state: ConversationState) -> dict:
    """Handle product matching logic"""
    try:
        # Convert state to format expected by product matcher
        user_profile = {
            "ABN_years": state.mvp_fields.get("ABN_years", 0),
            "GST_years": state.mvp_fields.get("GST_years", 0),
            "property_status": state.mvp_fields.get("property_status", "unknown"),
            "credit_score": 600,  # Default assumption
            "loan_type": state.mvp_fields.get("loan_type", "consumer")
        }
        
        # Call product matching service
        matching_result = product_matcher.find_best_loan_product(
            user_profile=user_profile,
            soft_prefs=state.preferences
        )
        
        return matching_result
        
    except Exception as e:
        print(f"Product matching error: {e}")
        return {
            "status": "error",
            "message": "Unable to match products at this time",
            "matches": []
        }

def _extract_gaps_from_matches(matches: list) -> list:
    """Extract gaps from product matches"""
    gaps = []
    for match in matches:
        if hasattr(match, 'gaps') and match.gaps:
            gaps.extend(match.gaps)
    return list(set(gaps))  # Remove duplicates

def _format_products_for_prompt(products: list) -> str:
    """Format matched products for inclusion in prompt"""
    if not products:
        return "No suitable products found."
    
    formatted = []
    for i, product in enumerate(products[:3], 1):
        if hasattr(product, 'product_name'):
            formatted.append(f"{i}. {product.product_name} - {product.interest_rate}% interest rate")
        else:
            formatted.append(f"{i}. {product.get('name', 'Unknown Product')}")
    
    return "; ".join(formatted)

def _create_error_response(error_message: str) -> dict:
    """Create standardized error response"""
    return {
        "reply": "I apologize, but I'm experiencing a technical issue. Please try again or contact our support team if the problem persists.",
        "status": "error",
        "error_detail": error_message,
        "conversation_stage": "error",
        "mvp_progress": {"completed_fields": [], "missing_fields": [], "is_complete": False},
        "preferences_collected": {},
        "matched_products_count": 0
    }