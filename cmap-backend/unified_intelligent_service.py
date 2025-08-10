import os
import json
import re
import httpx
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

def get_api_key():
    """安全地获取API密钥"""
    
    # 方式1：从系统环境变量获取（Render生产环境）
    key = os.getenv("ANTHROPIC_API_KEY")
    
    if key:
        print(f"✅ API密钥已从环境变量加载: {key[:10]}...{key[-4:]}")
        return key
    
    # 方式2：从本地API.env文件获取（开发环境）
    env_file = "API.env"
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        key = line.split("=", 1)[1].strip()
                        print(f"✅ API密钥已从{env_file}加载: {key[:10]}...{key[-4:]}")
                        return key
        except Exception as e:
            print(f"⚠️ 读取{env_file}文件失败: {e}")
    
    # 方式3：从python-dotenv加载（如果安装了的话）
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path="API.env")
        key = os.getenv("ANTHROPIC_API_KEY")
        if key:
            print("✅ API密钥已通过dotenv加载")
            return key
    except ImportError:
        print("ℹ️ python-dotenv not available, using direct file reading")
    except Exception as e:
        print(f"⚠️ dotenv加载失败: {e}")
    
    # 没找到密钥
    print("❌ 未找到ANTHROPIC_API_KEY")
    print("📋 请设置环境变量或创建API.env文件")
    return None

class ConversationStage(Enum):
    GREETING = "greeting"
    MVP_COLLECTION = "mvp_collection"
    PREFERENCE_COLLECTION = "preference_collection"
    PRODUCT_MATCHING = "product_matching"
    RECOMMENDATION = "recommendation"
    REFINEMENT = "refinement"

@dataclass
class CustomerProfile:
    # MVP Fields - Must Ask Questions
    loan_type: Optional[str] = None  # consumer/commercial
    asset_type: Optional[str] = None  # primary/secondary/tertiary/motor_vehicle
    property_status: Optional[str] = None  # property_owner/non_property_owner
    ABN_years: Optional[int] = None
    GST_years: Optional[int] = None
    credit_score: Optional[int] = None
    
    # Vehicle-Specific MVP Fields (only asked if asset_type is motor_vehicle)
    vehicle_type: Optional[str] = None  # passenger_car/light_truck/van_ute/etc
    vehicle_condition: Optional[str] = None  # new/demonstrator/used
    
    # Additional Information Fields
    desired_loan_amount: Optional[float] = None
    loan_term_preference: Optional[int] = None
    business_structure: Optional[str] = None  # sole_trader/company/trust/partnership
    business_years_operating: Optional[int] = None
    
    # User Preferences (optional, collected after MVP)
    interest_rate_ceiling: Optional[float] = None
    monthly_budget: Optional[float] = None
    min_loan_amount: Optional[float] = None
    preferred_term: Optional[int] = None
    
    # Asset Information (extracted automatically if mentioned)
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    purchase_price: Optional[float] = None
    deposit_amount: Optional[float] = None
    balloon_preference: Optional[float] = None

@dataclass
class ProductRecommendation:
    lender_name: str
    product_name: str
    base_rate: float
    comparison_rate: float
    max_loan_amount: str
    loan_term_options: str
    monthly_payment: Optional[float]
    requirements_met: bool
    requirements_detail: Dict[str, Any]
    fees_breakdown: Dict[str, float]
    documentation_type: str
    rate_loadings: Dict[str, float]
    gaps: List[str]
    match_score: float

class UnifiedIntelligentService:
    """统一的智能服务，集成MVP提取、产品匹配、和对话管理"""
    
    def __init__(self):
        # 使用安全的API密钥加载
        self.anthropic_api_key = get_api_key()
        self.api_url = "https://api.anthropic.com/v1/messages"
        
        # 加载产品文档
        self.product_docs = self._load_all_product_docs()
        
        # 对话状态存储
        self.conversation_states = {}
        self.max_conversation_rounds = 4  # 最多4轮对话后必须给推荐
        
        # MVP字段定义 - 统一管理，根据资产类型动态调整
        self.mvp_fields = ["loan_type", "asset_type", "property_status", "ABN_years", "GST_years", "credit_score"]
        self.vehicle_specific_fields = ["vehicle_type", "vehicle_condition"]  # 只有motor_vehicle时才问
        
        # 偏好字段 - 用户提供的偏好享有相同权重
        self.preference_fields = ["interest_rate_ceiling", "monthly_budget", "min_loan_amount", "preferred_term"]
        
    
        
    def _load_all_product_docs(self) -> Dict[str, str]:
        """加载所有lender的产品文档"""
        docs = {}
        lender_files = {
            "Angle": "Angle.md",
            "BFS": "BFS.md", 
            "FCAU": "FCAU.md",
            "RAF": "RAF.md"
        }
        
        for lender, filename in lender_files.items():
            try:
                possible_paths = [
                    filename,
                    f"docs/{filename}",
                    f"documents/{filename}",
                    f"../docs/{filename}"
                ]
                
                for file_path in possible_paths:
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                            # 限制文档长度以节省tokens
                            docs[lender] = content[:1500] + "..." if len(content) > 1500 else content
                            print(f"✅ Loaded {lender} products from {file_path}")
                        break
                else:
                    print(f"⚠️ {lender} product file not found: {filename}")
                    docs[lender] = f"{lender} products (documentation not available)"
                    
            except FileNotFoundError:
                print(f"⚠️ {lender} product file not found: {filename}")
                docs[lender] = f"{lender} products (documentation not available)"
            except Exception as e:
                print(f"❌ Error loading {lender}: {e}")
                docs[lender] = f"{lender} products (error loading documentation)"
        
        return docs

    def _get_required_mvp_fields(self, profile: CustomerProfile) -> List[str]:
        """根据资产类型获取需要问的MVP字段"""
        required_fields = self.mvp_fields.copy()
        
        # 如果是motor_vehicle，添加车辆特定字段
        if profile.asset_type == "motor_vehicle" or any(word in str(profile.asset_type or "").lower() for word in ["car", "vehicle", "truck"]):
            required_fields.extend(self.vehicle_specific_fields)
        
        return required_fields

    def _calculate_monthly_payment(self, loan_amount: float, annual_rate: float, term_months: int) -> float:
        """计算月供"""
        if loan_amount <= 0 or annual_rate <= 0 or term_months <= 0:
            return 0
        
        monthly_rate = annual_rate / 100 / 12
        
        if monthly_rate == 0:
            return loan_amount / term_months
        
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
        return round(monthly_payment, 2)

    def _calculate_comparison_rate(self, base_rate: float, establishment_fee: float, monthly_fee: float, 
                                 loan_amount: float, term_months: int) -> float:
        """计算包含费用的comparison rate"""
        if loan_amount <= 0 or term_months <= 0:
            return base_rate
        
        # 计算总费用
        total_fees = establishment_fee + (monthly_fee * term_months)
        
        # 费用对利率的影响 (简化计算)
        fee_rate_impact = (total_fees / loan_amount) * (12 / term_months) * 100
        
        comparison_rate = base_rate + fee_rate_impact
        return round(comparison_rate, 2)

    def _get_structured_product_info(self) -> str:
        """从产品文档中提取结构化信息"""
        
        structured_info = """
ANGLE FINANCE:
- Primary01: 7.99%, 10yr max, Property+Credit 500-650, ABN>=2yr, GST>=1yr, Max $100k Low Doc
- Primary04: 10.05%, 10yr max, Non-property, ABN>=2yr, GST>=1yr
- Secondary01: 10.45%, 10yr max, Property+Credit 500-650
- Tertiary01: 12.95%, 10yr max, Property+Credit 500-650
- Startup01: 12.95%, Property, ABN<2yr, Full Doc only
- A+ Rate: 6.99%, Property+Company/Trust/Partnership, ABN>=4yr, GST>=2yr, Credit 550+
- Fees: Setup $540/$700, Monthly $4.95, Brokerage up to 8%

RAF (RESIMAC):
- Vehicle 0-3yr: 6.89%, Property Premium tier, Credit 600+, Max $450k
- Vehicle >3yr: 7.49%, Property Premium tier, Credit 600+, Max $450k  
- Equipment Primary: 7.89%, Property Premium, Max $450k
- Secured Business: 8.99%-9.50%, 1st mortgage, Max $5M, LVR 70%
- Fees: Setup $495, Monthly $4.95, Private sale +$695, Brokerage 5.5%

FCAU (FLEXICOMMERCIAL):
- FlexiPremium: 6.85%-7.74%, Company/Trust only, ABN>=4yr, GST>=4yr, Max $500k
- FlexiCommercial Primary: 8.15%-12.90%, ABN>=4yr, Max $500k single deal
- FlexiAssist: 15%-18%, Credit 300+, Max $150k, Past defaults accepted
- Fees: Setup $495/$745, Monthly $4.95, Brokerage 3-6%

BFS (BRANDED FINANCIAL):
- Prime Commercial: 7.65%-9.80%, ABN holders, Credit 600+ (500 with 20% deposit)
- Prime Consumer: 8.80%-12.40%, PAYG income, Credit 600+ (500 with 20% deposit)  
- Plus: 15.98%, Credit 500+, Bank statements mandatory, Max $100k
- Fees: Setup $490-$650, Monthly $8, Early termination varies
"""
        return structured_info

    async def process_conversation(self, user_message: str, session_id: str = "default", 
                                 chat_history: List[Dict] = None, current_customer_info: Dict = None) -> Dict[str, Any]:
        """🔧 处理对话的主入口函数 - 添加current_customer_info参数"""
        
        # 获取或创建会话状态
        if session_id not in self.conversation_states:
            self.conversation_states[session_id] = {
                "stage": ConversationStage.MVP_COLLECTION,
                "customer_profile": CustomerProfile(),
                "conversation_history": [],
                "asked_fields": set(),
                "round_count": 0,
                "last_recommendations": []
            }
        
        state = self.conversation_states[session_id]
        state["round_count"] += 1
        
        # 🔧 同步最新的客户信息（来自DynamicForm的手动修改）
        if current_customer_info:
            self._sync_customer_info_from_form(state["customer_profile"], current_customer_info)
            print(f"🔄 Synced customer info from form: {current_customer_info}")
        
        # 重要：使用完整的聊天历史，而不是覆盖
        if chat_history:
            # 如果前端提供了完整历史，使用它
            state["conversation_history"] = chat_history[:]
        
        # 添加当前消息到历史
        state["conversation_history"].append({"role": "user", "content": user_message})
        
        # 使用完整的对话历史提取信息
        extracted_info = await self._extract_mvp_and_preferences(state["conversation_history"])
        print(f"🔍 Extracted info: {extracted_info}")  # 调试信息
        
        # 🔧 使用新的优先级更新策略：自动提取 > 手动修改
        self._update_customer_profile_with_priority(state["customer_profile"], extracted_info, current_customer_info)
        print(f"📊 Updated profile: {self._serialize_customer_profile(state['customer_profile'])}")  # 调试信息
        
        # 检查已经有值的字段，自动标记为已问过
        required_mvp_fields = self._get_required_mvp_fields(state["customer_profile"])
        for field in required_mvp_fields:
            if getattr(state["customer_profile"], field) is not None:
                state["asked_fields"].add(field)
                print(f"✅ Auto-marked {field} as asked")
        
        # 🔧 检查是否是调整要求
        user_message_lower = user_message.lower()
        is_adjustment_request = any(phrase in user_message_lower for phrase in [
            "adjust", "change", "modify", "different", "lower rate", "higher amount", 
            "longer term", "shorter term", "better option", "other option"
        ])
        
        # 检查用户是否要求最低利率或推荐
        wants_lowest_rate = any(phrase in user_message_lower for phrase in [
            "lowest interest rate", "lowest rate", "best rate", "cheapest rate",
            "show me options", "see recommendations", "recommend products", "show options"
        ])
        
        # 确定对话阶段
        new_stage = self._determine_conversation_stage(state, wants_lowest_rate or is_adjustment_request)
        print(f"🎯 Current stage: {new_stage}")  # 调试信息
        print(f"📝 Asked fields: {state['asked_fields']}")  # 调试信息
        state["stage"] = new_stage
        
        # 生成响应
        if new_stage == ConversationStage.MVP_COLLECTION:
            response = await self._handle_mvp_collection(state)
        elif new_stage == ConversationStage.PREFERENCE_COLLECTION:
            response = await self._handle_preference_collection(state, wants_lowest_rate)
        elif new_stage == ConversationStage.PRODUCT_MATCHING:
            response = await self._handle_product_matching(state, is_adjustment_request)
        elif new_stage == ConversationStage.RECOMMENDATION:
            response = await self._handle_recommendation(state, is_adjustment_request)
        else:
            response = await self._handle_general_conversation(state)
        
        # 添加助手回复到历史
        state["conversation_history"].append({"role": "assistant", "content": response["message"]})
        
        return {
            "reply": response["message"],
            "session_id": session_id,
            "stage": new_stage.value,
            "customer_profile": self._serialize_customer_profile(state["customer_profile"]),
            "recommendations": response.get("recommendations", []),
            "next_questions": response.get("next_questions", []),
            "round_count": state["round_count"],
            "status": "success"
        }

    def _sync_customer_info_from_form(self, profile: CustomerProfile, form_info: Dict):
        """🔧 从表单同步客户信息到profile"""
        for field, value in form_info.items():
            if hasattr(profile, field) and value is not None and value != '':
                setattr(profile, field, value)
                print(f"🔄 Synced from form: {field} = {value}")

    def _update_customer_profile_with_priority(self, profile: CustomerProfile, extracted_info: Dict[str, Any], manual_info: Dict = None):
        """🔧 使用优先级策略更新客户档案：自动提取 > 手动修改，最新信息 > 历史信息"""
        
        # 1. 先应用手动修改（较低优先级）
        if manual_info:
            for field, value in manual_info.items():
                if value is not None and value != '' and hasattr(profile, field):
                    current_value = getattr(profile, field)
                    if current_value != value:  # 只有值不同时才更新
                        setattr(profile, field, value)
                        print(f"📝 Manual update: {field} = {value}")
        
        # 2. 再应用自动提取（更高优先级，会覆盖手动修改）
        for field, value in extracted_info.items():
            if value is not None and hasattr(profile, field):
                current_value = getattr(profile, field)
                # 自动提取的信息总是应用（最新信息优先）
                setattr(profile, field, value)
                if current_value != value:
                    print(f"🤖 Auto-extracted (priority): {field} = {value} (was: {current_value})")

    async def _extract_mvp_and_preferences(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """使用Claude提取MVP信息和偏好，带fallback机制"""
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using rule-based extraction")
                return self._enhanced_rule_based_extraction(conversation_history)
            
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]  # 最近6轮对话
            ])
            
            # 🔧 修复后的Prompt - 重点提高语义理解和否定语句处理
            system_prompt = """你是专业的客户信息提取助手。从对话中灵活提取客户贷款信息，重点理解语义而非严格匹配格式。

核心提取规则：
1. **否定语句处理**：
   - "no ABN" / "don't have ABN" / "no abn and gst years" → ABN_years: 0
   - "no GST" / "not registered for GST" → GST_years: 0
   - "no property" / "don't own property" → property_status: "non_property_owner"

2. **灵活数值识别**：
   - "credit score 600" / "600 credit" / "score is 600" → credit_score: 600
   - "$20000" / "20000" / "20k" / "twenty thousand" → desired_loan_amount: 20000
   - "2 years ABN" / "ABN for 2 years" → ABN_years: 2

3. **业务术语理解**：
   - "sole trader" / "self employed" → business_structure: "sole_trader"
   - "company" / "pty ltd" → business_structure: "company"
   - "commercial loan" / "business use" → loan_type: "commercial"
   - "personal loan" / "personal use" → loan_type: "consumer"

4. **调整要求识别**：
   - "lower rate" / "better rate" → interest_rate_ceiling: (current_rate - 1)
   - "higher amount" / "more money" → 提取新的loan amount
   - "longer term" / "shorter term" → 提取新的loan term

5. **语义理解**：
   - 理解上下文关系，不仅匹配关键词
   - 处理用户的完整回答，提取所有相关信息
   - 识别隐含信息和业务逻辑

返回有效JSON格式：
{
    "loan_type": "consumer" or "commercial" or null,
    "asset_type": "primary" or "secondary" or "tertiary" or "motor_vehicle" or null,
    "property_status": "property_owner" or "non_property_owner" or null,
    "ABN_years": number or null,
    "GST_years": number or null,
    "credit_score": number or null,
    "desired_loan_amount": number or null,
    "loan_term_preference": number or null,
    "vehicle_type": "passenger_car" or "light_truck" or "van_ute" or "motorcycle" or "heavy_truck" or null,
    "vehicle_condition": "new" or "demonstrator" or "used" or null,
    "business_structure": "sole_trader" or "company" or "trust" or "partnership" or null,
    "interest_rate_ceiling": number or null,
    "monthly_budget": number or null,
    "vehicle_make": string or null,
    "vehicle_model": string or null,
    "vehicle_year": number or null,
    "purchase_price": number or null
}

重要：只提取明确提到的信息，不确定的字段设为null。优先理解语义，灵活处理各种表达方式。"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 800,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": f"从以下对话中提取客户信息:\n{conversation_text}"}
                ]
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['content'][0]['text']
                    
                    # 清理和解析JSON
                    clean_response = ai_response.strip()
                    if clean_response.startswith('```json'):
                        clean_response = clean_response[7:-3]
                    elif clean_response.startswith('```'):
                        clean_response = clean_response[3:-3]
                    
                    extracted_data = json.loads(clean_response)
                    print(f"✅ Claude extraction successful: {extracted_data}")
                    return extracted_data
                    
                else:
                    print(f"❌ Anthropic API error: {response.status_code} - {response.text}")
                    return self._enhanced_rule_based_extraction(conversation_history)
                    
        except httpx.TimeoutException:
            print("⏰ Anthropic API timeout - falling back to rule-based extraction")
            return self._enhanced_rule_based_extraction(conversation_history)
            
        except Exception as e:
            print(f"❌ Claude extraction failed: {e}")
            return self._enhanced_rule_based_extraction(conversation_history)

    def _enhanced_rule_based_extraction(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """🔧 修复和增强的规则后备提取方法"""
        conversation_text = " ".join([msg.get("content", "") for msg in conversation_history]).lower()
        
        extracted = {}
        
        # 🔧 1. 增强否定语句处理
        negative_abn_patterns = [
            r"no\s+abn", r"don't\s+have\s+abn", r"without\s+abn", 
            r"no\s+abn\s+and\s+gst", r"no\s+abn.*gst"
        ]
        negative_gst_patterns = [
            r"no\s+gst", r"don't\s+have\s+gst", r"not\s+registered\s+for\s+gst",
            r"no\s+abn\s+and\s+gst", r"no.*gst.*years"
        ]
        
        for pattern in negative_abn_patterns:
            if re.search(pattern, conversation_text):
                extracted["ABN_years"] = 0
                break
                
        for pattern in negative_gst_patterns:
            if re.search(pattern, conversation_text):
                extracted["GST_years"] = 0
                break
        
        # 🔧 2. 增强业务结构识别
        business_structure_patterns = {
            "sole_trader": [r"sole\s*trader", r"self\s*employed", r"individual\s*business"],
            "company": [r"company", r"corporation", r"pty\s*ltd", r"limited"],
            "trust": [r"trust", r"family\s*trust", r"discretionary\s*trust"],
            "partnership": [r"partnership", r"partners", r"joint\s*business"]
        }
        
        for structure, patterns in business_structure_patterns.items():
            for pattern in patterns:
                if re.search(pattern, conversation_text):
                    extracted["business_structure"] = structure
                    break
            if "business_structure" in extracted:
                break
        
        # 🔧 3. 增强贷款类型识别
        if any(word in conversation_text for word in ["business", "company", "commercial"]):
            extracted["loan_type"] = "commercial"
        elif any(word in conversation_text for word in ["personal", "consumer", "private"]):
            extracted["loan_type"] = "consumer"
        
        # 🔧 4. 增强资产类型识别
        if any(word in conversation_text for word in ["car", "vehicle", "truck", "van", "motorcycle"]):
            extracted["asset_type"] = "motor_vehicle"
        elif any(word in conversation_text for word in ["equipment", "machinery", "primary"]):
            extracted["asset_type"] = "primary"
        
        # 🔧 5. 增强房产状态识别
        property_owner_patterns = [
            r"own\s+property", r"property\s+owner", r"have\s+property", 
            r"property\s+backed", r"own\s+a\s+house"
        ]
        property_non_owner_patterns = [
            r"no\s+property", r"don't\s+own", r"rent", r"renting",
            r"non.property", r"without\s+property"
        ]
        
        for pattern in property_owner_patterns:
            if re.search(pattern, conversation_text):
                extracted["property_status"] = "property_owner"
                break
        
        if "property_status" not in extracted:
            for pattern in property_non_owner_patterns:
                if re.search(pattern, conversation_text):
                    extracted["property_status"] = "non_property_owner"
                    break
        
        # 🔧 6. 增强数值提取
        # ABN年数 - 增强模式
        abn_patterns = [
            r"(\d+)\s*years?\s*abn", r"abn.*?(\d+)\s*years?", 
            r"(\d+)\s*years?.*?abn", r"abn\s*for\s*(\d+)\s*years?"
        ]
        for pattern in abn_patterns:
            match = re.search(pattern, conversation_text)
            if match and "ABN_years" not in extracted:  # 不覆盖否定语句的结果
                years = int(match.group(1))
                if 0 <= years <= 50:
                    extracted["ABN_years"] = years
                break
        
        # GST年数 - 增强模式
        gst_patterns = [
            r"(\d+)\s*years?\s*gst", r"gst.*?(\d+)\s*years?",
            r"(\d+)\s*years?.*?gst", r"gst\s*for\s*(\d+)\s*years?"
        ]
        for pattern in gst_patterns:
            match = re.search(pattern, conversation_text)
            if match and "GST_years" not in extracted:  # 不覆盖否定语句的结果
                years = int(match.group(1))
                if 0 <= years <= 50:
                    extracted["GST_years"] = years
                break
        
        # 🔧 7. 增强信用分数提取
        credit_patterns = [
            r"credit\s*score\s*(?:is\s*)?(\d{3,4})",
            r"score\s*(?:is\s*)?(\d{3,4})",
            r"(\d{3,4})\s*credit",
            r"my\s*score\s*(?:is\s*)?(\d{3,4})",
            r"(\d{3,4})\s*score"
        ]
        for pattern in credit_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                score = int(match.group(1))
                if 300 <= score <= 900:
                    extracted["credit_score"] = score
                break
        
        # 车辆条件
        if "new" in conversation_text and "vehicle" in conversation_text:
            extracted["vehicle_condition"] = "new"
        elif "used" in conversation_text and "vehicle" in conversation_text:
            extracted["vehicle_condition"] = "used"
        
        # 车辆类型
        if any(word in conversation_text for word in ["model y", "tesla", "passenger car"]):
            extracted["vehicle_type"] = "passenger_car"
        elif any(word in conversation_text for word in ["truck", "heavy vehicle"]):
            extracted["vehicle_type"] = "light_truck"
        elif any(word in conversation_text for word in ["van", "ute"]):
            extracted["vehicle_type"] = "van_ute"
        
        # 🔧 8. 增强贷款金额提取
        amount_patterns = [
            r"loan\s*amount.*?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"borrow.*?(\d+(?:,\d{3})*)",
            r"need.*?(\d+(?:,\d{3})*)",
            r"want.*?(\d+(?:,\d{3})*)",
            r"looking\s*for.*?(\d+(?:,\d{3})*)",
            r"[\$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"(\d+)k\s*(?:loan|dollar)",
            r"(\d+)\s*thousand"
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    if 'k' in match.group(0) or 'thousand' in match.group(0):
                        amount = float(amount_str) * 1000
                    else:
                        amount = float(amount_str)
                    if 1000 <= amount <= 10000000:
                        extracted["desired_loan_amount"] = amount
                    break
                except (ValueError, IndexError):
                    continue
        
        print(f"🔍 Enhanced rule-based extraction result: {extracted}")  # 调试信息
        return extracted

    def _determine_conversation_stage(self, state: Dict, wants_lowest_rate: bool = False) -> ConversationStage:
        """确定对话阶段 - MVP是必问问题，4轮后强制推荐"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        round_count = state["round_count"]
        
        # 获取当前需要问的MVP字段
        required_mvp_fields = self._get_required_mvp_fields(profile)
        
        # 检查已经有值的字段，自动标记为已问过
        for field in required_mvp_fields:
            if getattr(profile, field) is not None:
                asked_fields.add(field)
        
        # 4轮对话限制：第4轮后必须给推荐
        if round_count >= self.max_conversation_rounds:
            print(f"🕒 Reached {self.max_conversation_rounds} rounds - forcing product matching")
            return ConversationStage.PRODUCT_MATCHING
        
        # 如果用户要求推荐，无论MVP状态如何都直接进入产品匹配
        if wants_lowest_rate:
            print("🚀 User wants recommendations - jumping to product matching")
            return ConversationStage.PRODUCT_MATCHING
        
        # 检查是否所有必要的MVP字段都已经问过
        mvp_all_asked = all(field in asked_fields for field in required_mvp_fields)
        
        if mvp_all_asked:
            # 所有MVP问题都问过了，检查偏好收集状态
            preferences_completed = "preferences_completed" in asked_fields
            if not preferences_completed:
                return ConversationStage.PREFERENCE_COLLECTION
            else:
                return ConversationStage.PRODUCT_MATCHING
        else:
            # 还有MVP问题没问，继续收集MVP
            return ConversationStage.MVP_COLLECTION

    async def _handle_mvp_collection(self, state: Dict) -> Dict[str, Any]:
        """处理MVP收集阶段 - MVP是必问问题，每个字段只问一次"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        round_count = state["round_count"]
        
        # 获取当前需要问的MVP字段
        required_mvp_fields = self._get_required_mvp_fields(profile)
        
        # 🔧 增强记忆功能：检查最近对话是否已经回答了问题
        recent_context = " ".join([msg.get("content", "") for msg in state["conversation_history"][-4:]]).lower()
        
        for field in required_mvp_fields:
            field_value = getattr(profile, field)
            if field_value is not None:
                asked_fields.add(field)
                print(f"✅ Auto-marked {field} as asked (has value: {field_value})")
            elif self._was_field_discussed_recently(field, recent_context):
                asked_fields.add(field)
                print(f"🧠 Auto-marked {field} as asked (recently discussed)")
        
        # 找出还没问过的字段
        unasked_fields = [field for field in required_mvp_fields if field not in asked_fields]
        print(f"📝 Unasked MVP fields: {unasked_fields}")
        
        # 4轮限制检查
        if round_count >= self.max_conversation_rounds:
            print(f"🕒 Round {round_count} reached limit - moving to product matching")
            return await self._handle_product_matching(state)
        
        if not unasked_fields:
            # 所有MVP字段都问过了，进入偏好收集
            print("✅ All MVP questions asked, moving to preference collection")
            return await self._handle_preference_collection(state)
        
        # 按优先级选择字段询问 - 根据剩余轮数动态调整问题数量
        priority_order = [
            "loan_type", 
            "asset_type", 
            "credit_score", 
            "property_status",
            "ABN_years",
            "GST_years",
            "vehicle_type", 
            "vehicle_condition"
        ]
        
        # 根据剩余轮数决定一次问几个字段
        rounds_left = self.max_conversation_rounds - round_count
        unasked_count = len(unasked_fields)
        
        if rounds_left <= 1:
            # 最后一轮，问完所有剩余字段
            fields_per_round = unasked_count
        elif rounds_left == 2:
            # 倒数第二轮，问一半以上
            fields_per_round = max(3, (unasked_count + 1) // 2)
        else:
            # 还有多轮，可以少问一些
            fields_per_round = max(2, unasked_count // rounds_left)
        
        print(f"📊 Rounds left: {rounds_left}, Unasked fields: {unasked_count}, Will ask: {fields_per_round}")
        
        # 按优先级排序未问过的字段
        next_fields = []
        for priority_field in priority_order:
            if priority_field in unasked_fields:
                next_fields.append(priority_field)
                if len(next_fields) >= fields_per_round:
                    break
        
        # 如果优先级字段不够，取剩余的字段
        if len(next_fields) < fields_per_round:
            remaining_fields = [f for f in unasked_fields if f not in next_fields]
            next_fields.extend(remaining_fields[:fields_per_round-len(next_fields)])
        
        # 生成问题并标记为已问过
        questions = []
        for field in next_fields:
            question = self._generate_field_question(field, profile)
            if question:
                questions.append(question)
                asked_fields.add(field)  # 重要：问了就标记为已问过，不管客户是否回答
                print(f"❓ Asking MVP question for {field}: {question}")
        
        if not questions:
            # 没有问题要问，直接进入偏好收集
            return await self._handle_preference_collection(state)
        
        rounds_left = self.max_conversation_rounds - round_count
        message = f"To find the best loan products for you, I need to ask a few questions (Round {round_count}/{self.max_conversation_rounds}):\n\n"
        message += "\n".join(f"• {q}" for q in questions)
        
        if rounds_left > 1:
            message += "\n\nYou can also say 'show me options' to see recommendations with the information provided so far."
        
        return {
            "message": message,
            "next_questions": questions
        }

    def _was_field_discussed_recently(self, field_name: str, recent_context: str) -> bool:
        """🔧 增强记忆功能：检查字段是否在最近对话中被讨论过"""
        field_keywords = {
            "ABN_years": ["abn", "business number", "australian business number"],
            "GST_years": ["gst", "goods and services tax", "tax registration"],
            "credit_score": ["credit", "score", "rating"],
            "property_status": ["property", "own", "house", "home"],
            "loan_type": ["business", "commercial", "personal", "consumer"],
            "asset_type": ["vehicle", "car", "equipment", "machinery"],
            "vehicle_type": ["passenger", "truck", "van", "motorcycle"],
            "vehicle_condition": ["new", "used", "demonstrator"],
            "business_structure": ["sole trader", "company", "trust", "partnership"]
        }
        
        keywords = field_keywords.get(field_name, [field_name.replace("_", " ")])
        return any(keyword in recent_context for keyword in keywords)

    def _generate_field_question(self, field: str, profile: CustomerProfile) -> str:
        """为特定字段生成问题"""
        questions = {
            "loan_type": "Is this for personal use or business use?",
            "asset_type": "What type of asset are you looking to finance? (vehicle/equipment/machinery)",
            "property_status": "Do you own property?",
            "ABN_years": "How many years has your ABN been registered?",
            "GST_years": "How many years have you been registered for GST?",
            "credit_score": "What is your current credit score?",
            "desired_loan_amount": "How much would you like to borrow?",
            "vehicle_type": "What type of vehicle? (passenger car/truck/van/motorcycle)",
            "vehicle_condition": "Are you looking at new or used vehicles?",
            "business_structure": "Is your business a company, trust, partnership, or sole trader?"
        }
        return questions.get(field, f"Please provide your {field}")

    async def _handle_product_matching(self, state: Dict, is_adjustment: bool = False) -> Dict[str, Any]:
        """🔧 处理产品匹配阶段 - 添加调整支持"""
        print("🎯 Starting product matching...")
        profile = state["customer_profile"]
        
        # 直接进行产品匹配
        recommendations = await self._ai_product_matching(profile)
        
        if not recommendations:
            print("❌ No recommendations found")
            return {
                "message": "I'm analyzing all available loan products for your profile. Let me find the best options across all lenders...",
                "recommendations": []
            }
        
        print(f"✅ Found {len(recommendations)} recommendations")
        
        # 🔧 管理推荐历史：保留最新2个
        if "last_recommendations" not in state:
            state["last_recommendations"] = []
        
        # 添加时间戳和状态标记
        for rec in recommendations:
            rec["timestamp"] = state["round_count"]
            rec["recommendation_status"] = "current"
        
        # 更新推荐历史
        all_recommendations = recommendations + state["last_recommendations"]
        
        # 去重并保留最新2个
        unique_recommendations = []
        seen = set()
        for rec in all_recommendations:
            key = f"{rec['lender_name']}_{rec['product_name']}"
            if key not in seen:
                unique_recommendations.append(rec)
                seen.add(key)
        
        # 只保留最新2个，并正确标记
        state["last_recommendations"] = unique_recommendations[:2]
        if len(state["last_recommendations"]) > 1:
            state["last_recommendations"][0]["recommendation_status"] = "current"
            state["last_recommendations"][1]["recommendation_status"] = "previous"
        elif len(state["last_recommendations"]) == 1:
            state["last_recommendations"][0]["recommendation_status"] = "current"
        
        # 更新状态为推荐阶段
        state["stage"] = ConversationStage.RECOMMENDATION
        
        return await self._handle_recommendation(state, is_adjustment)

    async def _handle_preference_collection(self, state: Dict, wants_lowest_rate: bool = False) -> Dict[str, Any]:
        """处理偏好收集阶段"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
        # 如果用户要求最低利率，直接跳过偏好收集
        if wants_lowest_rate:
            print("🚀 User wants lowest rate - skipping preference collection")
            asked_fields.add("preferences_completed")
            return await self._handle_product_matching(state)
        
        # 检查用户是否已经提供了偏好信息
        has_preferences = any([
            profile.interest_rate_ceiling,
            profile.monthly_budget,
            profile.min_loan_amount,
            profile.preferred_term
        ])
        
        # 如果用户已经提供了偏好，直接进入产品匹配
        last_message = state["conversation_history"][-1]["content"].lower() if state["conversation_history"] else ""
        if has_preferences or "show me options" in last_message:
            asked_fields.add("preferences_completed")
            return await self._handle_product_matching(state)
        
        # 检查是否已经问过偏好
        if "preferences_asked" not in asked_fields:
            # 第一次问偏好 - 列出所有4个偏好字段让客户选择
            asked_fields.add("preferences_asked")
            
            message = "Great! I have all the basic information I need. To find the most suitable options for you, you can optionally provide any of these preferences (answer whichever ones are important to you):\n\n"
            message += "• **Maximum interest rate**: What's the highest interest rate you'd be comfortable with?\n"
            message += "• **Monthly budget**: What's your preferred maximum monthly payment?\n"
            message += "• **Minimum loan amount**: Do you need a minimum loan amount?\n"
            message += "• **Preferred loan term**: How many years would you prefer for the loan term?\n\n"
            message += "You can answer any, all, or none of these - just tell me what matters to you, or say 'lowest interest rate' to see recommendations now."
            
            return {
                "message": message,
                "next_questions": [
                    "Maximum interest rate you'd accept",
                    "Preferred monthly payment budget", 
                    "Minimum loan amount needed",
                    "Preferred loan term in years"
                ]
            }
        else:
            # 已经问过偏好了，直接进入产品匹配
            asked_fields.add("preferences_completed")
            return await self._handle_product_matching(state)

    async def _handle_recommendation(self, state: Dict, is_adjustment: bool = False) -> Dict[str, Any]:
        """🔧 处理推荐阶段 - 修复推荐后的提示语，添加调整支持"""
        recommendations = state.get("last_recommendations", [])
        
        if not recommendations:
            return {
                "message": "I'm still analyzing the best options for you. Could you provide a bit more information about your requirements?",
                "recommendations": []
            }
        
        # 格式化推荐消息
        message = self._format_recommendation_with_comparison_guide(recommendations, state["customer_profile"], is_adjustment)
        
        return {
            "message": message,
            "recommendations": recommendations
        }

    def _format_recommendation_with_comparison_guide(self, recommendations: List[Dict], profile: CustomerProfile, is_adjustment: bool = False) -> str:
        """🔧 格式化推荐消息，包含ProductComparison交互指导"""
        
        # 获取当前推荐
        current_rec = None
        for rec in recommendations:
            if rec.get("recommendation_status") == "current":
                current_rec = rec
                break
        
        if not current_rec:
            current_rec = recommendations[0] if recommendations else None
        
        if not current_rec:
            return "I'm finding the best options for you. Please provide a bit more information."
        
        # 基础推荐信息
        lender = current_rec.get("lender_name", "Unknown")
        product = current_rec.get("product_name", "Unknown Product")
        base_rate = current_rec.get("base_rate", 0)
        comparison_rate = current_rec.get("comparison_rate", 0)
        monthly_payment = current_rec.get("monthly_payment", 0)
        
        if is_adjustment:
            message = f"Perfect! I've found an updated option based on your requirements:\n\n"
        else:
            message = f"Great news! I've found an excellent loan option for you:\n\n"
        
        message += f"**{lender} - {product}**\n"
        message += f"• Interest Rate: {base_rate}% p.a.\n"
        if comparison_rate:
            message += f"• Comparison Rate: {comparison_rate}% p.a.*\n"
        if monthly_payment:
            loan_amount = profile.desired_loan_amount or 50000
            message += f"• Monthly Payment: ${monthly_payment:,.2f}** (${loan_amount:,.0f} over 60 months)\n"
        if current_rec.get("max_loan_amount"):
            message += f"• Maximum Loan: {current_rec['max_loan_amount']}\n"
        
        # 🔧 ProductComparison交互指导
        message += f"\n**📋 What's Next:**\n"
        message += f"Your personalized recommendation is now displayed in the **Product Comparison panel** on the left. "
        message += f"Please review the complete details and let me know:\n\n"
        message += f"• Does this meet all your requirements?\n"
        message += f"• Would you like a **lower interest rate**, **different loan term**, or **adjusted monthly payment**?\n"
        message += f"• Any other specific conditions you'd like me to optimize for?\n\n"
        
        if is_adjustment:
            # 🔧 调整后的确认提示
            message += f"Is there anything else you'd like me to adjust or optimize for?"
        else:
            message += f"Just tell me what you'd like to adjust, and I'll find better options tailored to your needs!"
        
        # 免责声明
        message += f"\n\n*Comparison rate includes fees and charges"
        message += f"\n**Monthly payment estimate - actual may vary based on final terms"
        
        return message

    async def _ai_product_matching(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """增强的产品匹配方法 - 包含完整产品信息"""
        
        print(f"🎯 Starting enhanced AI product matching...")
        print(f"📊 Customer profile: loan_type={profile.loan_type}, asset_type={profile.asset_type}")
        print(f"📊 Property status={profile.property_status}, credit_score={profile.credit_score}")
        print(f"📊 ABN years={profile.ABN_years}, GST years={profile.GST_years}")
        
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using fallback recommendation")
                return [self._create_comprehensive_fallback_recommendation(profile)]
            
            # 简化的客户档案描述
            profile_summary = f"""
Customer Profile:
- Type: {profile.loan_type or 'business'} loan for {profile.asset_type or 'vehicle'}
- Property Owner: {profile.property_status or 'unknown'}
- Credit Score: {profile.credit_score or 'not specified'}
- ABN: {profile.ABN_years or 0} years, GST: {profile.GST_years or 0} years
- Loan Amount: ${profile.desired_loan_amount or 'not specified'}
- Vehicle: {profile.vehicle_make or ''} {profile.vehicle_model or ''}
"""

            # 获取结构化产品信息
            condensed_products = self._get_structured_product_info()

            # 增强的系统提示 - 要求完整产品信息
            system_prompt = f"""Find the best loan product match for this customer.

CUSTOMER PROFILE:
{profile_summary}

PRODUCT DATABASE:
{condensed_products}

Return ONLY a JSON object with COMPLETE information:
{{
    "lender_name": "RAF",
    "product_name": "Vehicle Finance Premium",
    "base_rate": 6.89,
    "comparison_rate": 7.12,
    "monthly_payment": 1250,
    "max_loan_amount": "$450,000",
    "loan_term_options": "12-60 months",
    "requirements_met": true,
    "documentation_type": "Low Doc",
    
    "detailed_requirements": {{
        "minimum_credit_score": "600",
        "abn_years_required": "2+",
        "gst_years_required": "1+", 
        "property_ownership": "Required",
        "deposit_required": "0% (asset-backed)",
        "asset_age_limit": "25 years at end-of-term"
    }},
    
    "fees_breakdown": {{
        "establishment_fee": "$495",
        "monthly_account_fee": "$4.95",
        "private_sale_surcharge": "$695",
        "brokerage_cap": "5.5%"
    }},
    
    "rate_conditions": {{
        "rate_loadings": "+2% private sale, +2% classic car",
        "balloon_options": "Up to 50% (36m), 45% (48m), 40% (60m)"
    }},
    
    "documentation_requirements": [
        "Application and privacy consent",
        "Asset and liability statement",
        "90-day bank statements (if Full Doc)"
    ]
}}

IMPORTANT: 
- comparison_rate = base_rate + fees impact (typically +0.2% to +0.5%)
- monthly_payment calculated for ${profile.desired_loan_amount or 50000} over 60 months
- Include ALL eligibility requirements, fees, and conditions"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1500,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": "Find the best loan product for this customer with complete details."}
                ]
            }

            print(f"📤 Sending enhanced request to Claude API...")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                print(f"📥 Claude API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['content'][0]['text']
                    
                    print(f"🤖 Claude raw response (first 300 chars): {ai_response[:300]}...")
                    
                    # 强健的JSON清理和解析
                    clean_response = ai_response.strip()
                    
                    # 移除各种可能的标记
                    markers_to_remove = ['```json', '```', '`']
                    for marker in markers_to_remove:
                        if clean_response.startswith(marker):
                            clean_response = clean_response[len(marker):]
                        if clean_response.endswith(marker):
                            clean_response = clean_response[:-len(marker)]
                    
                    clean_response = clean_response.strip()
                    print(f"🧹 Cleaned response (first 200 chars): {clean_response[:200]}...")
                    
                    try:
                        recommendation = json.loads(clean_response)
                        print(f"✅ Successfully parsed enhanced recommendation: {recommendation.get('lender_name', 'Unknown')}")
                        print(f"📋 Product: {recommendation.get('product_name', 'Unknown')}")
                        print(f"💰 Base Rate: {recommendation.get('base_rate', 'Unknown')}%")
                        print(f"💳 Comparison Rate: {recommendation.get('comparison_rate', 'Unknown')}%")
                        print(f"💵 Monthly Payment: ${recommendation.get('monthly_payment', 'Unknown')}")
                        return [recommendation]
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing failed: {e}")
                        print(f"📝 Failed content: {clean_response}")
                        print("🔄 Using comprehensive fallback recommendation...")
                        return [self._create_comprehensive_fallback_recommendation(profile)]
                
                else:
                    print(f"❌ API error: {response.status_code} - {response.text[:200]}")
                    return [self._create_comprehensive_fallback_recommendation(profile)]
                    
        except Exception as e:
            print(f"❌ Unexpected error in enhanced AI product matching: {e}")
            return [self._create_comprehensive_fallback_recommendation(profile)]

    def _create_comprehensive_fallback_recommendation(self, profile: CustomerProfile) -> Dict[str, Any]:
        """创建包含完整信息的智能后备推荐"""
        
        print("🔄 Creating comprehensive fallback recommendation...")
        print(f"📊 Profile analysis: property={profile.property_status}, credit={profile.credit_score}")
        
        # 估算贷款金额用于月供计算
        loan_amount = profile.desired_loan_amount or 50000
        term_months = 60
        
        # 智能规则匹配
        if (profile.property_status == "property_owner" and 
            profile.credit_score and profile.credit_score >= 600):
            print("✅ Matched: Property owner with good credit -> RAF Premium")
            
            base_rate = 6.89
            establishment_fee = 495
            monthly_fee = 4.95
            comparison_rate = self._calculate_comparison_rate(base_rate, establishment_fee, monthly_fee, loan_amount, term_months)
            monthly_payment = self._calculate_monthly_payment(loan_amount, base_rate, term_months)
            
            return {
                "lender_name": "RAF",
                "product_name": "Vehicle Finance Premium (0-3 years)",
                "base_rate": base_rate,
                "comparison_rate": comparison_rate,
                "monthly_payment": monthly_payment,
                "max_loan_amount": "$450,000",
                "loan_term_options": "12-60 months",
                "requirements_met": True,
                "documentation_type": "Low Doc",
                
                "detailed_requirements": {
                    "minimum_credit_score": "600 (Premium tier)",
                    "abn_years_required": "2+ years",
                    "gst_years_required": "2+ years", 
                    "property_ownership": "Required (or spouse property)",
                    "deposit_required": "0% if asset-backed, 10% if non-asset-backed",
                    "business_structure": "Any structure accepted",
                    "asset_age_limit": "Vehicle max 25 years at end-of-term"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$495",
                    "monthly_account_fee": "$4.95",
                    "private_sale_surcharge": "$695",
                    "ppsr_fee": "At cost",
                    "brokerage_cap": "5.5% (no rate impact)"
                },
                
                "rate_conditions": {
                    "base_rate_range": "6.89% (new vehicles 0-3 years)",
                    "premium_discount": "-0.50% for Premium tier customers",
                    "rate_loadings": "+2% private sale, +2% classic car, +2% prime mover",
                    "balloon_options": "Up to 50% (36m), 45% (48m), 40% (60m)"
                },
                
                "documentation_requirements": [
                    "Application and privacy consent",
                    "Asset and liability statement",
                    "12-month ATO portal history (Lite-Doc)",
                    "2 latest BAS portals",
                    "90-day bank statements (Full-Doc only)",
                    "Recent financial statements (Full-Doc)"
                ]
            }
        
        elif profile.loan_type == "commercial" and profile.ABN_years and profile.ABN_years >= 4:
            print("✅ Matched: Established business -> FCAU FlexiPremium")
            
            base_rate = 6.85
            establishment_fee = 495
            monthly_fee = 4.95
            comparison_rate = self._calculate_comparison_rate(base_rate, establishment_fee, monthly_fee, loan_amount, term_months)
            monthly_payment = self._calculate_monthly_payment(loan_amount, base_rate, term_months)
            
            return {
                "lender_name": "FCAU",
                "product_name": "FlexiPremium Standard",
                "base_rate": base_rate,
                "comparison_rate": comparison_rate,
                "monthly_payment": monthly_payment,
                "max_loan_amount": "$500,000",
                "loan_term_options": "12-84 months",
                "requirements_met": True,
                "documentation_type": "Standard",
                
                "detailed_requirements": {
                    "minimum_credit_score": "Clear Equifax file required",
                    "abn_years_required": "4+ years (asset-backed) or 8+ years (non-asset-backed)",
                    "gst_years_required": "4+ years",
                    "property_ownership": "Asset-backed or non-asset-backed accepted",
                    "business_structure": "Company, Trust, or Partnership only",
                    "asset_age_limit": "Primary: 20 years, Secondary: 7 years"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$495 (dealer), $745 (private)",
                    "monthly_account_fee": "$4.95",
                    "ppsr_fee": "At cost",
                    "brokerage_cap": "3% (FlexiPremium special cap)"
                },
                
                "rate_conditions": {
                    "base_rate_grid": "6.85% (50k-100k), 6.85% (100k-500k)",
                    "rate_loadings": "+1% prime mover/private sale, +1.25% non-asset-backed",
                    "maximum_cumulative_uplift": "4%"
                },
                
                "documentation_requirements": [
                    "Standard application",
                    "Privacy consent",
                    "Asset and liability statement", 
                    "Clear Equifax file",
                    "Asset inspection (broker or digital)",
                    "Statutory declaration (if required)"
                ]
            }
        
        elif (profile.asset_type == "motor_vehicle" and 
              profile.credit_score and profile.credit_score >= 550):
            print("✅ Matched: Vehicle loan with decent credit -> BFS Prime")
            
            base_rate = 9.50
            establishment_fee = 490
            monthly_fee = 8.00
            comparison_rate = self._calculate_comparison_rate(base_rate, establishment_fee, monthly_fee, loan_amount, term_months)
            monthly_payment = self._calculate_monthly_payment(loan_amount, base_rate, term_months)
            
            return {
                "lender_name": "BFS",
                "product_name": "Prime Consumer Vehicle Loan",
                "base_rate": base_rate,
                "comparison_rate": comparison_rate,
                "monthly_payment": monthly_payment,
                "max_loan_amount": "$250,000",
                "loan_term_options": "12-84 months",
                "requirements_met": True,
                "documentation_type": "Standard",
                
                "detailed_requirements": {
                    "minimum_credit_score": "600 (or 500 with 20% deposit)",
                    "income_verification": "Most recent payslip with YTD figures",
                    "deposit_required": "20% if credit score 500-599",
                    "vehicle_usage": "50%+ personal use",
                    "asset_age_limit": "13 years (≤60m terms), 7 years (>60m terms)"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$490 (consumer), $590 (private sale)",
                    "monthly_account_fee": "$8.00",
                    "early_termination_fee": "$750 reducing over time",
                    "private_sale_surcharge": "+0.50% rate loading"
                },
                
                "rate_conditions": {
                    "base_rate_range": "8.80%-12.40% based on credit score",
                    "asset_backed_rates": "Lower rates for asset-backed loans",
                    "balloon_options": "Limited commercial use only"
                },
                
                "documentation_requirements": [
                    "Most recent payslip (including YTD)",
                    "Proof of identity and residency",
                    "Vehicle purchase contract/invoice",
                    "Insurance certificate of currency",
                    "Bank statements (if required for capacity)"
                ]
            }
        
        else:
            print("✅ Default match: General purpose -> Angle Finance")
            
            base_rate = 10.75
            establishment_fee = 540
            monthly_fee = 4.95
            comparison_rate = self._calculate_comparison_rate(base_rate, establishment_fee, monthly_fee, loan_amount, term_months)
            monthly_payment = self._calculate_monthly_payment(loan_amount, base_rate, term_months)
            
            return {
                "lender_name": "Angle",
                "product_name": "Primary Asset Finance",
                "base_rate": base_rate,
                "comparison_rate": comparison_rate,
                "monthly_payment": monthly_payment,
                "max_loan_amount": "$100,000 (Low Doc)",
                "loan_term_options": "12-60 months",
                "requirements_met": True,
                "documentation_type": "Low Doc",
                
                "detailed_requirements": {
                    "minimum_credit_score": "500-650 range",
                    "abn_years_required": "2+ years",
                    "gst_years_required": "1+ years",
                    "property_ownership": "Preferred but not required",
                    "deposit_required": "20% if non-property owner",
                    "business_structure": "Any structure",
                    "asset_age_limit": "Varies by asset type"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$540 (dealer), $700 (private)",
                    "monthly_account_fee": "$4.95",
                    "brokerage_cap": "Up to 8% (with rate loading)"
                },
                
                "rate_conditions": {
                    "base_rate_range": "7.99%-16.95% depending on product",
                    "rate_loadings": "Various based on risk factors",
                    "balloon_options": "Limited availability"
                },
                
                "documentation_requirements": [
                    "Application form",
                    "Privacy consent", 
                    "6 months bank statements (Full Doc)",
                    "Financial statements (if required)",
                    "Asset inspection reports"
                ]
            }

    def _serialize_customer_profile(self, profile: CustomerProfile) -> Dict[str, Any]:
        """序列化客户档案为字典"""
        return {
            "loan_type": profile.loan_type,
            "asset_type": profile.asset_type,
            "property_status": profile.property_status,
            "ABN_years": profile.ABN_years,
            "GST_years": profile.GST_years,
            "credit_score": profile.credit_score,
            "desired_loan_amount": profile.desired_loan_amount,
            "vehicle_type": profile.vehicle_type,
            "vehicle_condition": profile.vehicle_condition,
            "vehicle_make": profile.vehicle_make,
            "vehicle_model": profile.vehicle_model,
            "interest_rate_ceiling": profile.interest_rate_ceiling,
            "monthly_budget": profile.monthly_budget,
            "business_structure": profile.business_structure
        }

    async def _handle_general_conversation(self, state: Dict) -> Dict[str, Any]:
        """处理一般对话"""
        return {
            "message": "How can I help you with your loan requirements today?",
            "next_questions": []
        }

    async def get_conversation_status(self, session_id: str) -> Dict[str, Any]:
        """获取对话状态"""
        if session_id not in self.conversation_states:
            return {"status": "no_session", "message": "No active conversation"}
        
        state = self.conversation_states[session_id]
        return {
            "status": "active",
            "stage": state["stage"].value,
            "customer_profile": self._serialize_customer_profile(state["customer_profile"]),
            "round_count": state["round_count"]
        }