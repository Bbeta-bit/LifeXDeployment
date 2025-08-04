

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
        
        message = self._format_recommendation_message(best_recommendation, state["customer_profile"])
        
        return {
            "message": message,
            "recommendations": [best_recommendation]  # 只返回一个推荐
        }

    async def _ai_product_matching(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """修复后的产品匹配方法 - 带详细调试和fallback"""
        
        print(f"🎯 Starting AI product matching...")
        print(f"📊 Customer profile: loan_type={profile.loan_type}, asset_type={profile.asset_type}")
        print(f"📊 Property status={profile.property_status}, credit_score={profile.credit_score}")
        print(f"📊 ABN years={profile.ABN_years}, GST years={profile.GST_years}")
        
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using fallback recommendation")
                return [self._create_smart_fallback_recommendation(profile)]
            
            # 简化的客户档案描述 - 减少token使用
            profile_summary = f"""
Customer Profile:
- Type: {profile.loan_type or 'business'} loan for {profile.asset_type or 'vehicle'}
- Property Owner: {profile.property_status or 'unknown'}
- Credit Score: {profile.credit_score or 'not specified'}
- ABN: {profile.ABN_years or 0} years, GST: {profile.GST_years or 0} years
- Loan Amount: ${profile.desired_loan_amount or 'not specified'}
- Vehicle: {profile.vehicle_make or ''} {profile.vehicle_model or ''}
"""

            # 大幅简化的系统提示
            system_prompt = f"""You are a loan product expert. Based on the customer profile, recommend the BEST single product.

{profile_summary}

Available Lenders:
- RAF: Best rates 6.89%-7.49% for property owners, vehicle finance specialist
- FCAU: Commercial equipment 6.85%-15.90%, business customers only
- BFS: Vehicle loans 8.80%-15.98%, flexible consumer and commercial
- Angle: Asset finance 7.99%-16.95%, includes startups

Return ONLY a JSON object:
{{
    "lender_name": "RAF",
    "product_name": "Vehicle Finance Premium",
    "base_rate": 6.89,
    "max_loan_amount": "$450,000",
    "loan_term_options": "12-60 months",
    "requirements_met": true,
    "documentation_type": "Low Doc",
    "why_recommended": "Best rate for property owners"
}}"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,  # 增加token限制
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": "Find the best loan product for this customer."}
                ]
            }

            print(f"📤 Sending request to Claude API...")
            print(f"📏 System prompt length: {len(system_prompt)} characters")

            async with httpx.AsyncClient(timeout=60.0) as client:  # 增加超时时间
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
                        print(f"✅ Successfully parsed recommendation: {recommendation.get('lender_name', 'Unknown')}")
                        print(f"📋 Product: {recommendation.get('product_name', 'Unknown')}")
                        print(f"💰 Rate: {recommendation.get('base_rate', 'Unknown')}%")
                        return [recommendation]
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON parsing failed: {e}")
                        print(f"📝 Failed content: {clean_response}")
                        print("🔄 Using fallback recommendation...")
                        return [self._create_smart_fallback_recommendation(profile)]
                
                elif response.status_code == 401:
                    print("❌ API Authentication failed - check your API key")
                    return [self._create_smart_fallback_recommendation(profile)]
                
                elif response.status_code == 429:
                    print("❌ API Rate limit exceeded")
                    return [self._create_smart_fallback_recommendation(profile)]
                
                else:
                    print(f"❌ API error: {response.status_code} - {response.text[:200]}")
                    return [self._create_smart_fallback_recommendation(profile)]
                    
        except httpx.TimeoutException:
            print("⏰ API request timed out")
            return [self._create_smart_fallback_recommendation(profile)]
            
        except Exception as e:
            print(f"❌ Unexpected error in AI product matching: {e}")
            import traceback
            traceback.print_exc()
            return [self._create_smart_fallback_recommendation(profile)]

    def _create_smart_fallback_recommendation(self, profile: CustomerProfile) -> Dict[str, Any]:
        """创建智能的fallback推荐"""
        
        print("🔄 Creating smart fallback recommendation...")
        print(f"📊 Profile analysis: property={profile.property_status}, credit={profile.credit_score}")
        
        # 智能规则匹配
        if (profile.property_status == "property_owner" and 
            profile.credit_score and profile.credit_score >= 600):
            print("✅ Matched: Property owner with good credit -> RAF Premium")
            return {
                "lender_name": "RAF",
                "product_name": "Vehicle Finance Premium",
                "base_rate": 6.89,
                "max_loan_amount": "$450,000",
                "loan_term_options": "12-60 months",
                "requirements_met": True,
                "documentation_type": "Low Doc",
                "why_recommended": "Excellent rates for property owners with strong credit profile"
            }
        
        elif profile.loan_type == "commercial" and profile.ABN_years and profile.ABN_years >= 2:
            print("✅ Matched: Established business -> FCAU Commercial")
            return {
                "lender_name": "FCAU",
                "product_name": "FlexiCommercial Primary",
                "base_rate": 8.65,
                "max_loan_amount": "$500,000",
                "loan_term_options": "12-84 months",
                "requirements_met": True,
                "documentation_type": "Standard",
                "why_recommended": "Competitive commercial vehicle finance for established businesses"
            }
        
        elif (profile.asset_type == "motor_vehicle" and 
              profile.credit_score and profile.credit_score >= 550):
            print("✅ Matched: Vehicle loan with decent credit -> BFS Prime")
            return {
                "lender_name": "BFS",
                "product_name": "Prime Vehicle Loan",
                "base_rate": 9.50,
                "max_loan_amount": "$250,000",
                "loan_term_options": "12-84 months",
                "requirements_met": True,
                "documentation_type": "Standard",
                "why_recommended": "Flexible vehicle financing with good rates for your credit profile"
            }
        
        else:
            print("✅ Default match: General purpose -> Angle Finance")
            return {
                "lender_name": "Angle",
                "product_name": "Primary Asset Finance",
                "base_rate": 10.75,
                "max_loan_amount": "$100,000",
                "loan_term_options": "12-60 months",
                "requirements_met": True,
                "documentation_type": "Low Doc",
                "why_recommended": "Flexible asset financing solution suitable for your requirements"
            }

    def _get_condensed_product_docs(self) -> str:
        """获取压缩的产品文档用于AI匹配"""
        condensed = ""
        for lender, doc in self.product_docs.items():
            if doc:
                # 只取前1000字符避免token超限
                condensed += f"\n## {lender} Products:\n{doc[:1000]}\n"
        return condensed

    def _format_recommendation_message(self, recommendation: Dict[str, Any], profile: CustomerProfile) -> str:
        """格式化推荐消息"""
        try:
            lender = recommendation.get("lender_name", "Unknown")
            product = recommendation.get("product_name", "Unknown Product")
            rate = recommendation.get("base_rate", 0)
            
            message = f"Based on your profile, I recommend:\n\n"
            message += f"**{lender} - {product}**\n"
            message += f"• Interest Rate: {rate}% p.a.\n"
            
            if recommendation.get("max_loan_amount"):
                message += f"• Maximum Loan: {recommendation['max_loan_amount']}\n"
            
            if recommendation.get("loan_term_options"):
                message += f"• Loan Terms: {recommendation['loan_term_options']}\n"
            
            if recommendation.get("documentation_type"):
                message += f"• Documentation: {recommendation['documentation_type']}\n"
            
            if recommendation.get("why_recommended"):
                message += f"\n{recommendation['why_recommended']}"
            
            return message
            
        except Exception as e:
            print(f"Error formatting recommendation: {e}")
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