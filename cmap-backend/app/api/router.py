from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.services.prompt_service import PromptService
from app.services.enhanced_prompt_service import EnhancedPromptService
from app.services.conversation_flow_service import ConversationFlowService
from app.services.mvp_preference_extractor import MVPPreferenceExtractor

router = APIRouter()

# Initialize services (keep old ones for compatibility)
prompt_service = PromptService()

# Initialize new services
try:
    enhanced_prompt_service = EnhancedPromptService()
    flow_service = ConversationFlowService()
    mvp_extractor = MVPPreferenceExtractor()
    new_services_available = True
except ImportError:
    print("New services not available, using legacy services only")
    new_services_available = False

class ProductMatchRequest(BaseModel):
    user_profile: Dict[str, Any]
    preferences: Optional[Dict[str, Any]] = None
    refine_params: Optional[Dict[str, Any]] = None

class CalculatorRequest(BaseModel):
    loan_amount: float
    interest_rate: float
    loan_term_months: int
    balloon_payment: Optional[float] = 0

class ConversationStateRequest(BaseModel):
    session_id: str

@router.get("/")
async def root():
    return {"message": "Hello from the AI Agent!"}

@router.post("/find_products")
async def find_products(request: ProductMatchRequest):
    """Find matching loan products based on user requirements"""
    try:
        result = prompt_service.find_matching_products(
            user_requirements=request.user_profile,
            preferences=request.preferences
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding products: {str(e)}")

@router.post("/calculate_payment")
async def calculate_payment(request: CalculatorRequest):
    """Calculate monthly loan payment"""
    try:
        result = prompt_service.calculate_monthly_payment(
            loan_amount=request.loan_amount,
            interest_rate=request.interest_rate,
            loan_term_months=request.loan_term_months,
            balloon_payment=request.balloon_payment
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating payment: {str(e)}")

@router.post("/extract-mvp-preferences")
async def extract_mvp_preferences(request: Dict[str, Any]):
    """Extract MVP fields and preferences from conversation (new endpoint)"""
    if not new_services_available:
        raise HTTPException(status_code=503, detail="Enhanced services not available")
    
    try:
        conversation_history = request.get("conversation_history", [])
        
        if not conversation_history:
            raise HTTPException(status_code=400, detail="Conversation history cannot be empty")

        extracted_data = await mvp_extractor.extract_mvp_and_preferences(conversation_history)
        
        return {
            "status": "success",
            "mvp_fields": extracted_data.get("mvp_fields", {}),
            "preferences": extracted_data.get("preferences", {}),
            "extraction_method": "enhanced"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"MVP/Preference extraction failed: {str(e)}"
        )

@router.get("/conversation-stages")
async def get_conversation_stages():
    """Get available conversation stages"""
    if not new_services_available:
        return {"stages": ["legacy_mode"]}
    
    from app.services.conversation_flow_service import ConversationStage
    return {
        "stages": [stage.value for stage in ConversationStage],
        "descriptions": {
            "greeting": "Initial greeting and welcome",
            "mvp_collection": "Collecting minimum viable profile information",
            "preference_collection": "Understanding customer preferences",
            "product_matching": "Finding suitable loan products",
            "gap_analysis": "Analyzing requirement gaps",
            "refinement": "Refining product recommendations",
            "final_recommendation": "Final product recommendation",
            "handoff": "Transfer to human specialist"
        }
    }

@router.get("/health_detailed")
async def health_detailed():
    """Detailed health check including all services"""
    try:
        # Test original product matching service
        product_status = "loaded" if prompt_service.product_matcher.products_parsed else "error"
        product_count = len(prompt_service.product_matcher.products_parsed)
        
        health_data = {
            "status": "healthy",
            "message": "Car Loan AI Agent is running",
            "services": {
                "prompt_system": "loaded" if prompt_service.product_info != "Product information temporarily unavailable" else "error",
                "product_matching": product_status,
                "product_count": product_count,
                "enhanced_services": new_services_available
            }
        }
        
        # Add enhanced services status if available
        if new_services_available:
            health_data["services"]["enhanced_prompt"] = "loaded"
            health_data["services"]["conversation_flow"] = "loaded"
            health_data["services"]["mvp_extractor"] = "loaded"
        
        return health_data
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }