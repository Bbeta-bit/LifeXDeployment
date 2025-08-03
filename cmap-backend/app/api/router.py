from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from app.services.prompt_service import PromptService
from app.services.enhanced_prompt_service import EnhancedPromptService

# 安全导入conversation flow service
try:
    from app.services.conversation_flow_service import ConversationFlowService, ConversationStage
    CONVERSATION_FLOW_AVAILABLE = True
except ImportError:
    print("⚠️ ConversationFlowService not available - some features will be limited")
    CONVERSATION_FLOW_AVAILABLE = False
    # 创建一个简单的替代类
    class ConversationStage:
        GREETING = "greeting"
        MVP_COLLECTION = "mvp_collection"
        PREFERENCE_COLLECTION = "preference_collection"
        PRODUCT_MATCHING = "product_matching"

from app.services.mvp_preference_extractor import MVPPreferenceExtractor

# 尝试导入增强的产品匹配服务
try:
    from app.services.enhanced_product_matching_service import (
        IntegratedLoanMatchingService,
        MultiLenderProductMatcher,
        MonthlyPaymentCalculator
    )
    ENHANCED_MATCHING_AVAILABLE = True
except ImportError:
    print("⚠️ Enhanced product matching services not available")
    ENHANCED_MATCHING_AVAILABLE = False

router = APIRouter()

# Initialize services (keep old ones for compatibility)
prompt_service = PromptService()

# Initialize new services with error handling
try:
    enhanced_prompt_service = EnhancedPromptService()
    if CONVERSATION_FLOW_AVAILABLE:
        flow_service = ConversationFlowService()
    mvp_extractor = MVPPreferenceExtractor()
    new_services_available = True
    print("✅ New services loaded successfully")
except ImportError as e:
    print(f"⚠️ New services not available: {e}")
    print("🔄 Using legacy services only")
    new_services_available = False

# Initialize enhanced services if available
if ENHANCED_MATCHING_AVAILABLE:
    try:
        integrated_matcher = IntegratedLoanMatchingService()
        multi_lender_matcher = MultiLenderProductMatcher()
        payment_calculator = MonthlyPaymentCalculator()
        print("✅ Enhanced multi-lender services loaded")
    except Exception as e:
        print(f"⚠️ Error loading enhanced services: {e}")
        ENHANCED_MATCHING_AVAILABLE = False

class ProductMatchRequest(BaseModel):
    user_profile: Dict[str, Any]
    preferences: Optional[Dict[str, Any]] = None
    refine_params: Optional[Dict[str, Any]] = None

class CalculatorRequest(BaseModel):
    loan_amount: float
    interest_rate: float
    loan_term_months: int
    balloon_payment: Optional[float] = 0

class EnhancedCalculatorRequest(BaseModel):
    principal: float
    annual_rate: float
    term_months: int
    balloon_amount: Optional[float] = 0
    fees: Optional[Dict[str, float]] = {}

class ConversationStateRequest(BaseModel):
    session_id: str

class MultiLenderSearchRequest(BaseModel):
    user_profile: Dict[str, Any]
    preferences: Optional[Dict[str, Any]] = None

@router.get("/")
async def root():
    return {
        "message": "Hello from the AI Agent!",
        "services_available": {
            "basic_services": True,
            "enhanced_services": new_services_available,
            "conversation_flow": CONVERSATION_FLOW_AVAILABLE,
            "multi_lender_matching": ENHANCED_MATCHING_AVAILABLE
        }
    }

@router.post("/find_products")
async def find_products(request: ProductMatchRequest):
    """Find matching loan products based on user requirements (original single-lender)"""
    try:
        # 使用原有的产品匹配逻辑
        if hasattr(prompt_service, 'find_matching_products'):
            result = prompt_service.find_matching_products(
                user_requirements=request.user_profile,
                preferences=request.preferences
            )
        else:
            # 如果原有服务没有这个方法，使用产品匹配服务
            from app.services.product_matching_service import ProductMatchingService
            product_matcher = ProductMatchingService()
            result = product_matcher.find_best_loan_product(
                user_profile=request.user_profile,
                soft_prefs=request.preferences,
                refine_params=request.refine_params
            )
        
        return {
            **result,
            "service_type": "single_lender",
            "enhanced_available": ENHANCED_MATCHING_AVAILABLE
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding products: {str(e)}")

@router.post("/find_products_multi_lender")
async def find_products_multi_lender(request: MultiLenderSearchRequest):
    """Enhanced multi-lender product search (new feature)"""
    if not ENHANCED_MATCHING_AVAILABLE:
        raise HTTPException(
            status_code=503, 
            detail="Multi-lender search not available. Enhanced services not loaded."
        )
    
    try:
        # 使用增强的多lender匹配服务
        conversation_history = [{"role": "user", "content": f"Profile: {request.user_profile}"}]
        
        result = await integrated_matcher.process_loan_request(
            conversation_history=conversation_history,
            user_preferences=request.preferences
        )
        
        return {
            **result,
            "service_type": "multi_lender",
            "lenders_checked": result.get("lenders_checked", ["Angle", "BFS", "FCAU", "RAF"]),
            "total_products_checked": result.get("total_products_checked", 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi-lender search error: {str(e)}")

@router.post("/calculate_payment")
async def calculate_payment(request: CalculatorRequest):
    """Calculate monthly loan payment (original method)"""
    try:
        if hasattr(prompt_service, 'calculate_monthly_payment'):
            result = prompt_service.calculate_monthly_payment(
                loan_amount=request.loan_amount,
                interest_rate=request.interest_rate,
                loan_term_months=request.loan_term_months,
                balloon_payment=request.balloon_payment
            )
        else:
            # 简单的月付计算
            monthly_rate = request.interest_rate / 100 / 12
            num_payments = request.loan_term_months
            
            if monthly_rate == 0:
                monthly_payment = (request.loan_amount - request.balloon_payment) / num_payments
            else:
                monthly_payment = (request.loan_amount - request.balloon_payment) * \
                                (monthly_rate * (1 + monthly_rate) ** num_payments) / \
                                ((1 + monthly_rate) ** num_payments - 1)
            
            result = {
                "monthly_payment": round(monthly_payment, 2),
                "total_interest": round((monthly_payment * num_payments) - (request.loan_amount - request.balloon_payment), 2),
                "loan_amount": request.loan_amount,
                "interest_rate": request.interest_rate,
                "term_months": request.loan_term_months,
                "balloon_payment": request.balloon_payment
            }
        
        return {
            **result,
            "calculation_type": "basic",
            "enhanced_available": ENHANCED_MATCHING_AVAILABLE
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating payment: {str(e)}")

@router.post("/calculate_payment_enhanced")
async def calculate_payment_enhanced(request: EnhancedCalculatorRequest):
    """Enhanced payment calculation with comparison rates and multi-lender support"""
    if not ENHANCED_MATCHING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Enhanced calculation not available. Enhanced services not loaded."
        )
    
    try:
        # 使用增强的计算器
        monthly_payment = payment_calculator.calculate_monthly_payment(
            principal=request.principal,
            annual_rate=request.annual_rate,
            term_months=request.term_months,
            balloon_amount=request.balloon_amount
        )
        
        # 计算比较利率
        comparison_rate = payment_calculator.calculate_comparison_rate(
            base_rate=request.annual_rate,
            fees=request.fees,
            loan_amount=request.principal,
            term_months=request.term_months
        )
        
        return {
            "monthly_payment": monthly_payment,
            "comparison_rate": comparison_rate,
            "total_interest": (monthly_payment * request.term_months) - (request.principal - request.balloon_amount),
            "total_fees": sum(request.fees.values()),
            "calculation_type": "enhanced",
            "calculation_parameters": {
                "principal": request.principal,
                "annual_rate": request.annual_rate,
                "term_months": request.term_months,
                "balloon_amount": request.balloon_amount,
                "fees_included": list(request.fees.keys())
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced calculation error: {str(e)}")

@router.post("/extract-mvp-preferences")
async def extract_mvp_preferences(request: Dict[str, Any]):
    """Extract MVP fields and preferences from conversation"""
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
            "extraction_method": "enhanced",
            "enhanced_mode": ENHANCED_MATCHING_AVAILABLE
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"MVP/Preference extraction failed: {str(e)}"
        )

@router.get("/conversation-stages")
async def get_conversation_stages():
    """Get available conversation stages"""
    if not CONVERSATION_FLOW_AVAILABLE:
        return {
            "stages": ["greeting", "information_collection", "product_matching", "recommendation"],
            "mode": "basic",
            "note": "Enhanced conversation flow not available"
        }
    
    return {
        "stages": [stage.value for stage in ConversationStage],
        "mode": "enhanced",
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

@router.get("/lenders-available")
async def get_lenders_available():
    """Get information about available lenders"""
    if ENHANCED_MATCHING_AVAILABLE:
        try:
            lender_info = {}
            for lender_type, lender_data in multi_lender_matcher.lenders.items():
                lender_info[lender_type.value] = {
                    "status": "available" if lender_data and "products" in lender_data else "error",
                    "products_count": len(lender_data.get("products", [])) if lender_data else 0,
                    "rules_count": len(lender_data.get("rules", {})) if lender_data else 0
                }
            
            return {
                "multi_lender_support": True,
                "lenders": lender_info,
                "total_products": sum(info["products_count"] for info in lender_info.values())
            }
        except Exception as e:
            return {
                "multi_lender_support": False,
                "error": str(e),
                "fallback": "Single lender mode available"
            }
    else:
        return {
            "multi_lender_support": False,
            "lenders": {"legacy": {"status": "available", "products_count": "unknown"}},
            "note": "Enhanced multi-lender services not loaded"
        }

@router.get("/health_detailed")
async def health_detailed():
    """Detailed health check including all services"""
    try:
        health_data = {
            "status": "healthy",
            "message": "Car Loan AI Agent is running",
            "timestamp": "2025-08-03",
            "services": {
                "prompt_system": "loaded",
                "basic_services": True,
                "enhanced_services": new_services_available,
                "conversation_flow": CONVERSATION_FLOW_AVAILABLE,
                "multi_lender_matching": ENHANCED_MATCHING_AVAILABLE
            }
        }
        
        # Test original prompt service
        try:
            product_status = "loaded" if hasattr(prompt_service, 'product_info') else "limited"
            health_data["services"]["prompt_system"] = product_status
        except:
            health_data["services"]["prompt_system"] = "error"
        
        # Test enhanced services if available
        if new_services_available:
            health_data["services"]["enhanced_prompt"] = "loaded"
            health_data["services"]["mvp_extractor"] = "loaded"
            
            if CONVERSATION_FLOW_AVAILABLE:
                health_data["services"]["conversation_flow"] = "loaded"
            
        # Test multi-lender services if available
        if ENHANCED_MATCHING_AVAILABLE:
            try:
                total_products = 0
                lender_status = {}
                for lender_type, lender_data in multi_lender_matcher.lenders.items():
                    lender_name = lender_type.value
                    if lender_data and "products" in lender_data:
                        product_count = len(lender_data["products"])
                        total_products += product_count
                        lender_status[lender_name] = {
                            "status": "loaded",
                            "products": product_count,
                            "rules": len(lender_data.get("rules", {}))
                        }
                    else:
                        lender_status[lender_name] = {"status": "error", "products": 0}
                
                health_data["multi_lender_details"] = {
                    "total_products": total_products,
                    "lenders": lender_status
                }
            except Exception as e:
                health_data["multi_lender_details"] = {"error": str(e)}
        
        # Available endpoints
        health_data["available_endpoints"] = {
            "basic": ["/find_products", "/calculate_payment", "/extract-mvp-preferences"],
            "enhanced": []
        }
        
        if ENHANCED_MATCHING_AVAILABLE:
            health_data["available_endpoints"]["enhanced"].extend([
                "/find_products_multi_lender", 
                "/calculate_payment_enhanced",
                "/lenders-available"
            ])
        
        return health_data
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "services": {
                "basic_services": False,
                "enhanced_services": False,
                "error_detail": str(e)
            }
        }

@router.get("/system-capabilities")
async def get_system_capabilities():
    """Get comprehensive system capabilities"""
    capabilities = {
        "conversation_management": {
            "basic_flow": True,
            "enhanced_flow": CONVERSATION_FLOW_AVAILABLE,
            "stage_management": CONVERSATION_FLOW_AVAILABLE,
            "mvp_extraction": new_services_available
        },
        "product_matching": {
            "single_lender": True,
            "multi_lender": ENHANCED_MATCHING_AVAILABLE,
            "gap_analysis": ENHANCED_MATCHING_AVAILABLE,
            "preference_matching": True
        },
        "calculations": {
            "basic_payment": True,
            "enhanced_payment": ENHANCED_MATCHING_AVAILABLE,
            "comparison_rates": ENHANCED_MATCHING_AVAILABLE,
            "fee_breakdown": ENHANCED_MATCHING_AVAILABLE
        },
        "lenders": {
            "supported": ["Angle", "BFS", "FCAU", "RAF"] if ENHANCED_MATCHING_AVAILABLE else ["Legacy"],
            "multi_lender_search": ENHANCED_MATCHING_AVAILABLE,
            "lender_specific_rules": ENHANCED_MATCHING_AVAILABLE
        }
    }
    
    return {
        "system_version": "1.5" if ENHANCED_MATCHING_AVAILABLE else "1.0",
        "capabilities": capabilities,
        "upgrade_status": {
            "enhanced_services_loaded": new_services_available,
            "multi_lender_support": ENHANCED_MATCHING_AVAILABLE,
            "conversation_flow": CONVERSATION_FLOW_AVAILABLE,
            "ready_for_production": ENHANCED_MATCHING_AVAILABLE and CONVERSATION_FLOW_AVAILABLE
        }
    }

# Legacy compatibility endpoints
@router.post("/legacy/find_products")
async def legacy_find_products(request: ProductMatchRequest):
    """Legacy product finding endpoint for backward compatibility"""
    return await find_products(request)

@router.post("/legacy/calculate_payment") 
async def legacy_calculate_payment(request: CalculatorRequest):
    """Legacy payment calculation for backward compatibility"""
    return await calculate_payment(request)