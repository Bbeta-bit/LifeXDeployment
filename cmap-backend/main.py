import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router as api_router
from app.utils.openrouter_client import chat_with_agent
from app.services.prompt_service import PromptService
from app.services.enhanced_customer_extractor import EnhancedCustomerInfoExtractor, CustomerInfo

# 加载环境变量（读取 API.env 文件）
load_dotenv(dotenv_path="API.env")

# 从环境变量中读取 OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# 创建 FastAPI 应用
app = FastAPI(
    title="Car Loan AI Agent",
    description="AI agent backend for car loan company",
    version="0.1"
)

# 更新你的CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",                    # 本地开发
        "https://cmap-frontend.onrender.com",      # 线上前端URL
        "https://*.onrender.com"                    # 允许所有onrender子域名（可选）
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 Prompt 服务
prompt_service = PromptService()
customer_extractor = EnhancedCustomerInfoExtractor()

# 接口挂载
app.include_router(api_router)

# AI 聊天接口 - 使用新的prompt系统
@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_input = data.get("message")
        chat_history = data.get("history", [])  # 获取聊天历史（可选）
        
        if not user_input:
            raise HTTPException(status_code=400, detail="Message content cannot be empty")

        # 使用 prompt_service 创建完整的消息列表
        messages = prompt_service.create_chat_messages(user_input, chat_history)

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": messages,  # 使用新的消息格式
            "temperature": 0.7,  # 添加一些创造性，但保持专业
            "max_tokens": 1000   # 限制回复长度
        }

        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            return {"reply": f"Error: {response.status_code} - {response.text}"}

        result = response.json()
        reply = result['choices'][0]['message']['content']
        
        # 返回回复和用户需求分析（可选）
        user_requirements = prompt_service.extract_user_requirements(user_input)
        
        return {
            "reply": reply,
            "user_requirements": user_requirements,  # 这个信息可以用于后续分析
            "status": "success"
        }
        
    except Exception as e:
        return {
            "reply": "Sorry, we encountered a technical issue. Please try again later.",
            "status": "error",
            "error_detail": str(e)
        }

@app.post("/extract-customer-info")
async def extract_customer_info(request: Request):
    """
    Extract customer information from conversation history
    """
    try:
        data = await request.json()
        conversation_history = data.get("conversation_history", [])
        existing_info_data = data.get("existing_info")
        
        if not conversation_history:
            raise HTTPException(status_code=400, detail="Conversation history cannot be empty")

        # Extract information
        if existing_info_data:
            try:
                existing_info = CustomerInfo(**existing_info_data)
                # For now, just extract fresh info (you can implement update later)
                extracted_info = await customer_extractor.extract_from_conversation(conversation_history)
            except Exception:
                extracted_info = await customer_extractor.extract_from_conversation(conversation_history)
        else:
            extracted_info = await customer_extractor.extract_from_conversation(conversation_history)

        # Get missing fields
        missing_fields = customer_extractor.get_missing_fields(extracted_info)
        
        # Generate follow-up questions
        follow_up_questions = customer_extractor.generate_follow_up_questions(extracted_info)

        return {
            "status": "success",
            "customer_info": extracted_info.dict(),
            "missing_fields": missing_fields,
            "extraction_completeness": min(len(extracted_info.extracted_fields) / 20.0, 1.0),  # 基于更多字段计算
            "suggestions": {
                "next_questions": follow_up_questions,
                "confidence_level": "high" if extracted_info.confidence_score > 0.7 
                                  else "medium" if extracted_info.confidence_score > 0.4 
                                  else "low"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Information extraction failed: {str(e)}"
        )

@app.post("/validate-customer-info")
async def validate_customer_info(request: Request):
    """
    Validate customer information completeness and accuracy
    """
    try:
        data = await request.json()
        customer_info_data = data.get("customer_info")
        
        if not customer_info_data:
            raise HTTPException(status_code=400, detail="Customer information cannot be empty")

        customer_info = CustomerInfo(**customer_info_data)
        missing_fields = customer_extractor.get_missing_fields(customer_info)
        
        # Validation logic
        validation_result = {
            "is_valid": len(missing_fields) <= 3,  # Allow max 3 important fields missing
            "missing_fields": missing_fields,
            "completeness_score": min(len(customer_info.extracted_fields) / 15.0, 1.0),
            "required_fields_missing": [
                field for field in ["name", "income", "desired_loan_amount"] 
                if field in missing_fields
            ]
        }

        return {
            "status": "success",
            "validation": validation_result,
            "recommendations": _generate_completion_recommendations(missing_fields)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Information validation failed: {str(e)}"
        )

# 健康检查接口
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Car Loan AI Agent is running",
        "prompt_system": "loaded" if prompt_service.product_info != "Product information temporarily unavailable" else "error"
    }

def _generate_follow_up_questions(missing_fields: list) -> list:
    """Generate follow-up questions based on missing fields"""
    question_mapping = {
        "name": "What is your full name?",
        "age": "What is your age?",
        "income": "What is your monthly income approximately?",
        "employment_type": "What type of work do you do?",
        "employment_status": "What is your current employment status?",
        "phone": "Could you please provide your contact phone number?",
        "abn": "Do you have an ABN number?",
        "credit_score": "Do you know your credit score?",
        "vehicle_make": "What brand is your vehicle?",
        "vehicle_model": "What model is your vehicle?",
        "vehicle_year": "What year is your vehicle?",
        "vehicle_value": "What is the approximate value of your vehicle?",
        "desired_loan_amount": "How much would you like to borrow?",
        "loan_purpose": "What will you use the loan for?",
        "monthly_expenses": "What are your approximate monthly expenses?",
        "existing_loan_amount": "Do you have any existing loans on the vehicle?"
    }
    
    questions = []
    for field in missing_fields[:4]:  # Suggest max 4 questions
        if field in question_mapping:
            questions.append(question_mapping[field])
    
    return questions

def _generate_completion_recommendations(missing_fields: list) -> list:
    """Generate recommendations for completing information"""
    recommendations = []
    
    if "income" in missing_fields:
        recommendations.append("Recommend collecting customer income information to assess repayment capacity")
    
    if "desired_loan_amount" in missing_fields:
        recommendations.append("Need to confirm customer's desired loan amount")
    
    if any(field in missing_fields for field in ["vehicle_make", "vehicle_model", "vehicle_value"]):
        recommendations.append("Need to complete vehicle information for accurate valuation")
    
    if "phone" in missing_fields:
        recommendations.append("Recommend collecting contact information for follow-up communication")
        
    if "abn" in missing_fields:
        recommendations.append("For business customers, ABN information may be required")
        
    if "credit_score" in missing_fields:
        recommendations.append("Credit score information would help with loan assessment")
    
    return recommendations