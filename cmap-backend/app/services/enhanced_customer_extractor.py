# app/services/enhanced_customer_extractor.py
import json
import re
import os
import httpx
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="API.env")

class PersonalInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    employment_status: Optional[str] = None
    employment_type: Optional[str] = None
    work_experience: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    abn: Optional[str] = None
    gst_registered: Optional[str] = None
    credit_score: Optional[int] = None
    marital_status: Optional[str] = None
    dependents: Optional[int] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    bank_statements: Optional[str] = None
    id_verification: Optional[str] = None

class BusinessInfo(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_age: Optional[int] = None
    annual_revenue: Optional[float] = None
    monthly_revenue: Optional[float] = None
    business_address: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[int] = None
    gst_number: Optional[str] = None
    business_registration: Optional[str] = None

class AssetInfo(BaseModel):
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_value: Optional[float] = None
    vehicle_condition: Optional[str] = None
    vehicle_rego: Optional[str] = None
    existing_loan_amount: Optional[float] = None
    desired_loan_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    collateral_type: Optional[str] = None
    collateral_value: Optional[float] = None
    insurance_status: Optional[str] = None

class FinancialInfo(BaseModel):
    monthly_expenses: Optional[float] = None
    rent_mortgage: Optional[float] = None
    other_loans: Optional[float] = None
    credit_cards: Optional[float] = None
    savings: Optional[float] = None
    investments: Optional[float] = None
    financial_commitments: Optional[str] = None
    bankruptcy_history: Optional[str] = None
    payment_defaults: Optional[str] = None

class CustomerInfo(BaseModel):
    loan_type: str = "consumer"  # consumer/commercial
    personal_info: PersonalInfo = PersonalInfo()
    business_info: BusinessInfo = BusinessInfo()
    asset_info: AssetInfo = AssetInfo()
    financial_info: FinancialInfo = FinancialInfo()
    extracted_fields: List[str] = []
    confidence_score: float = 0.0

class EnhancedCustomerInfoExtractor:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
    async def extract_from_conversation_ai(self, conversation_history: List[Dict[str, str]]) -> CustomerInfo:
        """
        Extract customer information from conversation using OpenRouter AI
        """
        try:
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(conversation_history)
            
            # Call OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {
                        "role": "system",
                        "content": """You are a professional financial information extraction expert. Please extract key information from customer conversations with AI assistants.

Please return results strictly in JSON format without any additional text, explanations, or markdown formatting.

Extraction Rules:
1. Only extract explicitly mentioned information, do not guess or assume
2. Set numeric fields to null if not explicitly mentioned
3. Set string fields to null if not explicitly mentioned  
4. Loan type: "commercial" if business/company/commercial use is mentioned, otherwise "consumer"
5. Australian-specific information: ABN numbers, GST registration status, credit scores, etc.
6. Boolean type fields use "yes"/"no" representation

Must return the following JSON format:
{
    "loan_type": "consumer or commercial",
    "personal_info": {
        "name": "customer name or null",
        "age": age number or null,
        "income": income number or null,
        "employment_status": "employment status or null",
        "employment_type": "job type or null", 
        "work_experience": "work experience or null",
        "phone": "phone number or null",
        "email": "email or null",
        "address": "address or null",
        "abn": "ABN number or null",
        "gst_registered": "yes/no or null",
        "credit_score": credit score number or null,
        "marital_status": "marital status or null",
        "dependents": number of dependents or null,
        "assets": total assets or null,
        "liabilities": total liabilities or null,
        "bank_statements": "yes/no or null",
        "id_verification": "yes/no or null"
    },
    "business_info": {
        "business_name": "business name or null",
        "business_type": "business type or null",
        "business_age": business age or null,
        "annual_revenue": annual revenue or null,
        "monthly_revenue": monthly revenue or null,
        "business_address": "business address or null",
        "industry": "industry type or null",
        "employees": number of employees or null,
        "gst_number": "GST number or null",
        "business_registration": "business registration status or null"
    },
    "asset_info": {
        "vehicle_make": "vehicle brand or null",
        "vehicle_model": "vehicle model or null", 
        "vehicle_year": year number or null,
        "vehicle_value": value number or null,
        "vehicle_condition": "vehicle condition or null",
        "vehicle_rego": "vehicle registration or null",
        "existing_loan_amount": existing loan amount or null,
        "desired_loan_amount": desired loan amount or null,
        "loan_purpose": "loan purpose or null",
        "collateral_type": "collateral type or null",
        "collateral_value": collateral value or null,
        "insurance_status": "insurance status or null"
    },
    "financial_info": {
        "monthly_expenses": monthly expenses or null,
        "rent_mortgage": rent/mortgage or null,
        "other_loans": other loans or null,
        "credit_cards": credit card debt or null,
        "savings": savings amount or null,
        "investments": investment amount or null,
        "financial_commitments": "other financial commitments or null",
        "bankruptcy_history": "bankruptcy history or null",
        "payment_defaults": "payment defaults history or null"
    }
}"""
                    },
                    {
                        "role": "user", 
                        "content": extraction_prompt
                    }
                ],
                "temperature": 0.1,  # Low temperature for accuracy
                "max_tokens": 2000
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    # If AI extraction fails, fall back to rule extraction
                    return self._rule_based_extraction(conversation_history)

                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Parse AI returned JSON
                try:
                    # Clean possible markdown formatting
                    clean_response = ai_response.strip()
                    if clean_response.startswith('```json'):
                        clean_response = clean_response[7:-3]
                    elif clean_response.startswith('```'):
                        clean_response = clean_response[3:-3]
                    
                    extracted_data = json.loads(clean_response)
                    return self._build_customer_info_from_dict(extracted_data)
                    
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"AI response parsing failed: {e}, falling back to rule extraction")
                    return self._rule_based_extraction(conversation_history)

        except Exception as e:
            print(f"AI extraction failed: {e}, using rule extraction")
            return self._rule_based_extraction(conversation_history)

    def _build_extraction_prompt(self, conversation_history: List[Dict[str, str]]) -> str:
        """Build extraction prompt"""
        conversation_text = ""
        for i, message in enumerate(conversation_history):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            conversation_text += f"[{i+1}] {role.upper()}: {content}\n"
        
        prompt = f"""
Please extract customer information from the following conversation:

Conversation Content:
{conversation_text}

Please extract customer information and return the result in JSON format.
"""
        return prompt

    def _build_customer_info_from_dict(self, data: Dict) -> CustomerInfo:
        """Build CustomerInfo object from dictionary"""
        try:
            # Build personal information
            personal_data = data.get("personal_info", {})
            personal_info = PersonalInfo(**{k: v for k, v in personal_data.items() if v is not None})
            
            # Build business information
            business_data = data.get("business_info", {})
            business_info = BusinessInfo(**{k: v for k, v in business_data.items() if v is not None})
            
            # Build asset information
            asset_data = data.get("asset_info", {})
            asset_info = AssetInfo(**{k: v for k, v in asset_data.items() if v is not None})
            
            # Build financial information
            financial_data = data.get("financial_info", {})
            financial_info = FinancialInfo(**{k: v for k, v in financial_data.items() if v is not None})
            
            # Calculate extracted fields
            extracted_fields = []
            for field, value in personal_data.items():
                if value is not None:
                    extracted_fields.append(field)
            for field, value in business_data.items():
                if value is not None:
                    extracted_fields.append(field)
            for field, value in asset_data.items():
                if value is not None:
                    extracted_fields.append(field)
            for field, value in financial_data.items():
                if value is not None:
                    extracted_fields.append(field)
            
            # Calculate confidence score
            total_possible_fields = 40  # Approximate total field count
            confidence_score = min(len(extracted_fields) / total_possible_fields, 1.0)
            
            return CustomerInfo(
                loan_type=data.get("loan_type", "consumer"),
                personal_info=personal_info,
                business_info=business_info,
                asset_info=asset_info,
                financial_info=financial_info,
                extracted_fields=extracted_fields,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            print(f"Building CustomerInfo failed: {e}")
            return CustomerInfo()

    def _rule_based_extraction(self, conversation_history: List[Dict[str, str]]) -> CustomerInfo:
        """Rule-based fallback extraction method"""
        conversation_text = " ".join([msg.get("content", "") for msg in conversation_history])
        
        personal_info = PersonalInfo()
        business_info = BusinessInfo()
        asset_info = AssetInfo()
        financial_info = FinancialInfo()
        extracted_fields = []
        
        # Name extraction - English and Chinese patterns
        name_patterns = [
            r"My name is ([A-Za-z\s]+)",
            r"I'm ([A-Za-z\s]+)",
            r"I am ([A-Za-z\s]+)",
            r"Call me ([A-Za-z\s]+)",
            r"我叫(.{2,10})(?:[，。！？\s]|$)",
            r"我的名字是(.{2,10})(?:[，。！？\s]|$)",
            r"名字是(.{2,10})(?:[，。！？\s]|$)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 1 and len(name) < 50:
                    personal_info.name = name
                    extracted_fields.append("name")
                break

        # ABN number extraction
        abn_patterns = [
            r"ABN.{0,10}?(\d{11})",
            r"Australian Business Number.{0,10}?(\d{11})",
            r"ABN号码.{0,5}?(\d{11})",
            r"(\d{11})",  # 11-digit number might be ABN
        ]
        for pattern in abn_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                abn = match.group(1)
                if len(abn) == 11:  # ABN must be 11 digits
                    personal_info.abn = abn
                    extracted_fields.append("abn")
                break

        # GST registration status extraction
        gst_patterns = [
            r"GST registered",
            r"registered for GST",
            r"have GST",
            r"GST注册",
            r"已注册GST",
            r"有GST"
        ]
        gst_negative_patterns = [
            r"not GST registered",
            r"no GST",
            r"没有GST",
            r"未注册GST"
        ]
        
        for pattern in gst_patterns:
            if re.search(pattern, conversation_text, re.IGNORECASE):
                personal_info.gst_registered = "yes"
                extracted_fields.append("gst_registered")
                break
        else:
            for pattern in gst_negative_patterns:
                if re.search(pattern, conversation_text, re.IGNORECASE):
                    personal_info.gst_registered = "no"
                    extracted_fields.append("gst_registered")
                break

        # Credit score extraction
        credit_patterns = [
            r"credit score.{0,10}?(\d{3,4})",
            r"credit rating.{0,10}?(\d{3,4})",
            r"信用分数.{0,5}?(\d{3,4})",
            r"信用分.{0,5}?(\d{3,4})",
            r"credit.{0,10}?(\d{3,4})"
        ]
        for pattern in credit_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                if 300 <= score <= 900:  # Reasonable credit score range
                    personal_info.credit_score = score
                    extracted_fields.append("credit_score")
                break

        # Age extraction
        age_patterns = [
            r"I am (\d+) years old",
            r"I'm (\d+) years old",
            r"I am (\d+)",
            r"(\d+) years old",
            r"age is (\d+)",
            r"我今年(\d+)岁",
            r"年龄是?(\d+)",
            r"(\d+)岁了"
        ]
        for pattern in age_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                if 18 <= age <= 100:
                    personal_info.age = age
                    extracted_fields.append("age")
                break

        # Income extraction
        income_patterns = [
            r"monthly income.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"annual income.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"income.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"salary.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"earn.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"make.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"月收入.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"年收入.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"收入.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"工资.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)"
        ]
        for pattern in income_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                income_str = match.group(1).replace(",", "")
                income = float(income_str)
                if 1000 <= income <= 1000000:
                    personal_info.income = income
                    extracted_fields.append("income")
                break

        # Phone number extraction
        phone_patterns = [
            r"phone.{0,10}?(\d{10,11})",
            r"number.{0,10}?(\d{10,11})",
            r"contact.{0,10}?(\d{10,11})",
            r"call me.{0,10}?(\d{10,11})",
            r"电话.{0,5}?(\d{11})",
            r"手机.{0,5}?(\d{11})",
            r"联系方式.{0,5}?(\d{11})",
            r"(\d{3}[-\s]?\d{4}[-\s]?\d{4})"
        ]
        for pattern in phone_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                phone = match.group(1)
                personal_info.phone = phone
                extracted_fields.append("phone")
                break

        # Vehicle information extraction
        vehicle_patterns = [
            r"I drive a (.+?)(?:[，。！？\s]|$)",
            r"My car is (.+?)(?:[，。！？\s]|$)",
            r"I own a (.+?)(?:[，。！？\s]|$)",
            r"I have a (.+?)(?:[，。！？\s]|$)",
            r"driving a (.+?)(?:[，。！？\s]|$)",
            r"我的车是(.+?)(?:[，。！？\s]|$)",
            r"开的是(.+?)(?:[，。！？\s]|$)",
            r"车子是(.+?)(?:[，。！？\s]|$)"
        ]
        for pattern in vehicle_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                vehicle_info = match.group(1).strip()
                common_brands = ['Mercedes', 'BMW', 'Audi', 'Volkswagen', 'Toyota', 'Honda', 'Nissan', 'Mazda', 'Ford', 'Hyundai',
                               '奔驰', '宝马', '奥迪', '大众', '丰田', '本田', '日产', '马自达', '福特', '现代']
                
                for brand in common_brands:
                    if brand in vehicle_info:
                        asset_info.vehicle_make = brand
                        asset_info.vehicle_model = vehicle_info.replace(brand, '').strip()
                        extracted_fields.extend(["vehicle_make", "vehicle_model"])
                        break
                else:
                    parts = vehicle_info.split()
                    if len(parts) >= 2:
                        asset_info.vehicle_make = parts[0]
                        asset_info.vehicle_model = " ".join(parts[1:])
                        extracted_fields.extend(["vehicle_make", "vehicle_model"])
                    else:
                        asset_info.vehicle_make = vehicle_info
                        extracted_fields.append("vehicle_make")
                break

        # Loan amount extraction
        loan_patterns = [
            r"loan.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"borrow.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"need.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"looking for.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"贷款.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*万",
            r"借.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*万",
            r"需要.{0,10}?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*万"
        ]
        for pattern in loan_patterns:
            match = re.search(pattern, conversation_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                if "万" in conversation_text[match.start():match.end() + 5]:
                    amount = float(amount_str) * 10000
                else:
                    amount = float(amount_str)
                asset_info.desired_loan_amount = amount
                extracted_fields.append("desired_loan_amount")
                break

        # Determine loan type
        loan_type = "consumer"
        business_keywords = ["company", "business", "commercial", "enterprise", "corporation", 
                           "公司", "企业", "商业", "生意"]
        if any(keyword in conversation_text.lower() for keyword in business_keywords):
            loan_type = "commercial"

        confidence_score = min(len(extracted_fields) / 15.0, 1.0)

        return CustomerInfo(
            loan_type=loan_type,
            personal_info=personal_info,
            business_info=business_info,
            asset_info=asset_info,
            financial_info=financial_info,
            extracted_fields=extracted_fields,
            confidence_score=confidence_score
        )

    async def extract_from_conversation(self, conversation_history: List[Dict[str, str]]) -> CustomerInfo:
        """Main extraction method - prioritize AI, fallback to rules"""
        if not conversation_history:
            return CustomerInfo()
            
        # First try AI extraction
        ai_result = await self.extract_from_conversation_ai(conversation_history)
        
        # If AI extraction yields too little information, combine with rule extraction
        if ai_result.confidence_score < 0.3:
            rule_result = self._rule_based_extraction(conversation_history)
            merged_result = self._merge_extraction_results(ai_result, rule_result)
            return merged_result
        
        return ai_result

    def _merge_extraction_results(self, ai_result: CustomerInfo, rule_result: CustomerInfo) -> CustomerInfo:
        """Merge AI and rule extraction results"""
        merged_info = CustomerInfo()
        
        # Merge personal information
        for field in PersonalInfo.__fields__:
            ai_value = getattr(ai_result.personal_info, field)
            rule_value = getattr(rule_result.personal_info, field)
            
            final_value = ai_value if ai_value is not None else rule_value
            setattr(merged_info.personal_info, field, final_value)
            
            if final_value is not None:
                merged_info.extracted_fields.append(field)

        # Merge business information
        for field in BusinessInfo.__fields__:
            ai_value = getattr(ai_result.business_info, field)
            rule_value = getattr(rule_result.business_info, field)
            
            final_value = ai_value if ai_value is not None else rule_value
            setattr(merged_info.business_info, field, final_value)
            
            if final_value is not None:
                merged_info.extracted_fields.append(field)

        # Merge asset information
        for field in AssetInfo.__fields__:
            ai_value = getattr(ai_result.asset_info, field)
            rule_value = getattr(rule_result.asset_info, field)
            
            final_value = ai_value if ai_value is not None else rule_value
            setattr(merged_info.asset_info, field, final_value)
            
            if final_value is not None:
                merged_info.extracted_fields.append(field)

        # Merge financial information
        for field in FinancialInfo.__fields__:
            ai_value = getattr(ai_result.financial_info, field)
            rule_value = getattr(rule_result.financial_info, field)
            
            final_value = ai_value if ai_value is not None else rule_value
            setattr(merged_info.financial_info, field, final_value)
            
            if final_value is not None:
                merged_info.extracted_fields.append(field)

        # Loan type selection
        merged_info.loan_type = ai_result.loan_type if ai_result.loan_type != "consumer" else rule_result.loan_type
        
        # Recalculate confidence score
        merged_info.confidence_score = min(len(merged_info.extracted_fields) / 20.0, 1.0)
        
        return merged_info

    def get_missing_fields(self, customer_info: CustomerInfo) -> List[str]:
        """Get missing important fields"""
        important_fields = [
            "name", "age", "income", "employment_type", "phone", "abn", "credit_score",
            "vehicle_make", "vehicle_model", "desired_loan_amount", "monthly_expenses"
        ]
        
        missing_fields = []
        for field in important_fields:
            if field not in customer_info.extracted_fields:
                missing_fields.append(field)
        
        return missing_fields

    def generate_follow_up_questions(self, customer_info: CustomerInfo) -> List[str]:
        """Generate follow-up question suggestions"""
        missing_fields = self.get_missing_fields(customer_info)
        questions = []
        
        field_questions = {
            "name": "What is your full name?",
            "age": "What is your age?",
            "income": "What is your monthly income?",
            "employment_type": "What type of work do you do?",
            "phone": "Could you provide your contact phone number?",
            "abn": "Do you have an ABN number?",
            "credit_score": "Do you know your credit score?",
            "vehicle_make": "What is the make of your vehicle?",
            "vehicle_model": "What is the model of your vehicle?",
            "desired_loan_amount": "How much would you like to borrow?",
            "monthly_expenses": "What are your monthly basic expenses?"
        }
        
        for field in missing_fields[:5]:  # Show maximum 5 questions
            if field in field_questions:
                questions.append(field_questions[field])
        
        return questions