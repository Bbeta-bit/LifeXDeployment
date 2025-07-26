from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.services.prompt_service import PromptService

router = APIRouter()

# Initialize services
prompt_service = PromptService()

class ProductMatchRequest(BaseModel):
    user_profile: Dict[str, Any]
    preferences: Optional[Dict[str, Any]] = None
    refine_params: Optional[Dict[str, Any]] = None

class CalculatorRequest(BaseModel):
    loan_amount: float
    interest_rate: float
    loan_term_months: int
    balloon_payment: Optional[float] = 0

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

@router.get("/health_detailed")
async def health_detailed():
    """Detailed health check including all services"""
    try:
        # Test product matching service
        product_status = "loaded" if prompt_service.product_matcher.products_parsed else "error"
        product_count = len(prompt_service.product_matcher.products_parsed)
        
        return {
            "status": "healthy",
            "message": "Car Loan AI Agent is running",
            "services": {
                "prompt_system": "loaded" if prompt_service.product_info != "Product information temporarily unavailable" else "error",
                "product_matching": product_status,
                "product_count": product_count
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }