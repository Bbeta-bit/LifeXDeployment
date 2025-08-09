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
                                 chat_history: List[Dict] = None) -> Dict[str, Any]:
        """处理对话的主入口函数"""
        
        # 获取或创建会话状态
        if session_id not in self.conversation_states:
            self.conversation_states[session_id] = {
                "stage": ConversationStage.MVP_COLLECTION,
                "customer_profile": CustomerProfile(),
                "conversation_history": [],
                "asked_fields": set(),
                "round_count": 0
            }
        
        state = self.conversation_states[session_id]
        state["round_count"] += 1
        
        # 重要：使用完整的聊天历史，而不是覆盖
        if chat_history:
            # 如果前端提供了完整历史，使用它
            state["conversation_history"] = chat_history[:]
        
        # 添加当前消息到历史
        state["conversation_history"].append({"role": "user", "content": user_message})
        
        # 使用完整的对话历史提取信息
        extracted_info = await self._extract_mvp_and_preferences(state["conversation_history"])
        print(f"🔍 Extracted info: {extracted_info}")  # 调试信息
        
        # 更新客户档案 - 保留已有信息
        self._update_customer_profile_preserve(state["customer_profile"], extracted_info)
        print(f"📊 Updated profile: {self._serialize_customer_profile(state['customer_profile'])}")  # 调试信息
        
        # 检查已经有值的字段，自动标记为已问过
        required_mvp_fields = self._get_required_mvp_fields(state["customer_profile"])
        for field in required_mvp_fields:
            if getattr(state["customer_profile"], field) is not None:
                state["asked_fields"].add(field)
                print(f"✅ Auto-marked {field} as asked")
        
        # 检查用户是否要求最低利率或推荐
        user_message_lower = user_message.lower()
        wants_lowest_rate = any(phrase in user_message_lower for phrase in [
            "lowest interest rate", "lowest rate", "best rate", "cheapest rate",
            "show me options", "see recommendations", "recommend products", "show options"
        ])
        
        # 确定对话阶段
        new_stage = self._determine_conversation_stage(state, wants_lowest_rate)
        print(f"🎯 Current stage: {new_stage}")  # 调试信息
        print(f"📝 Asked fields: {state['asked_fields']}")  # 调试信息
        state["stage"] = new_stage
        
        # 生成响应
        if new_stage == ConversationStage.MVP_COLLECTION:
            response = await self._handle_mvp_collection(state)
        elif new_stage == ConversationStage.PREFERENCE_COLLECTION:
            response = await self._handle_preference_collection(state, wants_lowest_rate)
        elif new_stage == ConversationStage.PRODUCT_MATCHING:
            response = await self._handle_product_matching(state)
        elif new_stage == ConversationStage.RECOMMENDATION:
            response = await self._handle_recommendation(state)
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

    async def _extract_mvp_and_preferences(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """使用Claude提取MVP信息和偏好，带fallback机制"""
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using rule-based extraction")
                return self._rule_based_extraction(conversation_history)
            
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]  # 最近6轮对话
            ])
            
            system_prompt = """Extract customer loan information from the conversation. Return ONLY valid JSON.

Required JSON structure:
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
    "purchase_price": number or null,
    "deposit_amount": number or null
}

Extraction rules:
- loan_type: "commercial" if business/company mentioned, "consumer" if personal
- asset_type: "motor_vehicle" for cars/trucks/vans, "primary" for main equipment
- property_status: "property_owner" if they own property, "non_property_owner" if not
- Only extract explicitly mentioned information"""

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
                    {"role": "user", "content": f"Extract from:\n{conversation_text}"}
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
                    return self._rule_based_extraction(conversation_history)
                    
        except httpx.TimeoutException:
            print("⏰ Anthropic API timeout - falling back to rule-based extraction")
            return self._rule_based_extraction(conversation_history)
            
        except Exception as e:
            print(f"❌ Claude extraction failed: {e}")
            return self._rule_based_extraction(conversation_history)

    def _rule_based_extraction(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """规则后备提取方法"""
        conversation_text = " ".join([msg.get("content", "") for msg in conversation_history]).lower()
        
        extracted = {}
        
        # 贷款类型
        if any(word in conversation_text for word in ["business", "company", "commercial"]):
            extracted["loan_type"] = "commercial"
        elif any(word in conversation_text for word in ["personal", "consumer", "private"]):
            extracted["loan_type"] = "consumer"
        
        # 资产类型
        if any(word in conversation_text for word in ["car", "vehicle", "truck", "van", "motorcycle"]):
            extracted["asset_type"] = "motor_vehicle"
        elif any(word in conversation_text for word in ["equipment", "machinery", "primary"]):
            extracted["asset_type"] = "primary"
        
        # 房产状态
        if any(phrase in conversation_text for phrase in ["own property", "property owner", "have property", "property backed"]):
            extracted["property_status"] = "property_owner"
        elif any(phrase in conversation_text for phrase in ["no property", "don't own", "rent"]):
            extracted["property_status"] = "non_property_owner"
        
        # ABN年数
        abn_patterns = [
            r"(\d+)\s*years?\s*abn",
            r"abn.*?(\d+)\s*years?",
            r"(\d+)\s*years?.*?abn"
        ]
        for pattern in abn_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 50:
                    extracted["ABN_years"] = years
                break
        
        # GST年数
        gst_patterns = [
            r"(\d+)\s*years?\s*gst",
            r"gst.*?(\d+)\s*years?",
            r"(\d+)\s*years?.*?gst"
        ]
        for pattern in gst_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 50:
                    extracted["GST_years"] = years
                break
        
        # 信用分数
        credit_patterns = [
            r"credit.{0,20}?(\d{3,4})",
            r"score.{0,20}?(\d{3,4})",
            r"(\d{3,4}).{0,20}?credit"
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
        
        # 贷款金额
        amount_patterns = [
            r"[\$]?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            r"(\d+)k",
            r"(\d+)\s*thousand"
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                amount_str = match.group(1).replace(',', '')
                if 'k' in match.group(0) or 'thousand' in match.group(0):
                    amount = float(amount_str) * 1000
                else:
                    amount = float(amount_str)
                if 1000 <= amount <= 10000000:
                    extracted["desired_loan_amount"] = amount
                break
        
        print(f"🔍 Rule-based extraction result: {extracted}")  # 调试信息
        return extracted

    def _update_customer_profile_preserve(self, profile: CustomerProfile, extracted_info: Dict[str, Any]):
        """更新客户档案，保留已有信息"""
        for field, value in extracted_info.items():
            if value is not None and hasattr(profile, field):
                # 只有当前值为None时才更新，保留已有信息
                current_value = getattr(profile, field)
                if current_value is None:
                    setattr(profile, field, value)
                    print(f"🆕 Set {field} = {value}")
                else:
                    print(f"🔒 Kept existing {field} = {current_value} (ignored new: {value})")

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
        
        # 检查已经有值的字段，自动标记为已问过
        for field in required_mvp_fields:
            if getattr(profile, field) is not None:
                asked_fields.add(field)
                print(f"✅ Auto-marked {field} as asked (has value: {getattr(profile, field)})")
        
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

    async def _handle_product_matching(self, state: Dict) -> Dict[str, Any]:
        """处理产品匹配阶段 - 直接进行匹配"""
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
        
        # 更新状态为推荐阶段
        state["stage"] = ConversationStage.RECOMMENDATION
        state["last_recommendations"] = recommendations
        
        return await self._handle_recommendation(state)

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

    async def _handle_recommendation(self, state: Dict) -> Dict[str, Any]:
        """处理推荐阶段 - 确保只推荐一个最佳产品"""
        recommendations = state.get("last_recommendations", [])
        
        if not recommendations:
            return {
                "message": "I'm still analyzing the best options for you. Could you provide a bit more information about your requirements?",
                "recommendations": []
            }
        
        # 确保只有一个推荐
        best_recommendation = recommendations[0] if isinstance(recommendations, list) else recommendations
        
        message = self._format_comprehensive_recommendation_message(best_recommendation, state["customer_profile"])
        
        return {
            "message": message,
            "recommendations": [best_recommendation]  # 只返回一个推荐
        }

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

            # 增强的系统提示 - 要求完整产品信息，去除推荐理由
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
- Include ALL eligibility requirements, fees, and conditions
- DO NOT include why_recommended field"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1500,  # 增加token限制以容纳完整信息
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

    def _format_comprehensive_recommendation_message(self, recommendation: Dict[str, Any], profile: CustomerProfile) -> str:
        """格式化完整推荐消息 - 去除推荐理由，包含所有信息"""
        try:
            lender = recommendation.get("lender_name", "Unknown")
            product = recommendation.get("product_name", "Unknown Product")
            base_rate = recommendation.get("base_rate", 0)
            comparison_rate = recommendation.get("comparison_rate", 0)
            monthly_payment = recommendation.get("monthly_payment", 0)
            
            message = f"**{lender} - {product}**\n\n"
            
            # 核心贷款信息
            message += f"**💰 LOAN DETAILS:**\n"
            message += f"• Interest Rate: {base_rate}% p.a.\n"
            if comparison_rate:
                message += f"• Comparison Rate: {comparison_rate}% p.a.*\n"
            if monthly_payment:
                loan_amount = profile.desired_loan_amount or 50000
                message += f"• Monthly Payment: ${monthly_payment:,.2f}** (${loan_amount:,.0f} over 60 months)\n"
            if recommendation.get("max_loan_amount"):
                message += f"• Maximum Loan: {recommendation['max_loan_amount']}\n"
            if recommendation.get("loan_term_options"):
                message += f"• Loan Terms: {recommendation['loan_term_options']}\n"
            
            # 详细要求
            detailed_req = recommendation.get("detailed_requirements", {})
            if detailed_req:
                message += f"\n**📋 ELIGIBILITY REQUIREMENTS:**\n"
                for req_key, req_value in detailed_req.items():
                    readable_key = req_key.replace("_", " ").title()
                    message += f"• {readable_key}: {req_value}\n"
            
            # 费用明细
            fees = recommendation.get("fees_breakdown", {})
            if fees:
                message += f"\n**💳 FEES:**\n"
                for fee_key, fee_value in fees.items():
                    readable_key = fee_key.replace("_", " ").title()
                    message += f"• {readable_key}: {fee_value}\n"
            
            # 利率条件
            rate_conditions = recommendation.get("rate_conditions", {})
            if rate_conditions:
                message += f"\n**📊 RATE CONDITIONS:**\n"
                for rate_key, rate_value in rate_conditions.items():
                    readable_key = rate_key.replace("_", " ").title()
                    message += f"• {readable_key}: {rate_value}\n"
            
            # 文档要求
            doc_requirements = recommendation.get("documentation_requirements", [])
            if doc_requirements:
                message += f"\n**📄 DOCUMENTATION REQUIRED:**\n"
                for doc in doc_requirements:
                    message += f"• {doc}\n"
            
            # 免责声明
            message += f"\n*Comparison rate includes fees and charges"
            message += f"\n**Monthly payment estimate - actual may vary based on final terms"
            
            return message
            
        except Exception as e:
            print(f"Error formatting comprehensive recommendation: {e}")
            return "I found a suitable loan product for you. Please contact us for more details."

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
            "monthly_budget": profile.monthly_budget
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