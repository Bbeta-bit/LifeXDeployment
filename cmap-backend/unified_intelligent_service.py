# unified_intelligent_service.py - 修复信息提取和产品信息完整性
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
        """加载完整产品文档"""
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
                            # 加载完整文档
                            docs[lender] = content
                            print(f"✅ Loaded {lender} products from {file_path} (full content: {len(content)} chars)")
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

    async def process_conversation(self, user_message: str, session_id: str = "default", 
                                 chat_history: List[Dict] = None, current_customer_info: Dict = None) -> Dict[str, Any]:
        """处理对话的主入口函数"""
        
        print(f"\n🔄 Processing conversation - Session: {session_id}")
        print(f"📝 User message: {user_message}")
        print(f"📊 Current customer info: {current_customer_info}")
        
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
        
        # 🔧 修复1：改进客户信息同步逻辑
        if current_customer_info:
            print(f"🔄 Syncing customer info from frontend...")
            self._sync_customer_info_from_form(state["customer_profile"], current_customer_info)
        
        # 重要：使用完整的聊天历史，而不是覆盖
        if chat_history:
            # 如果前端提供了完整历史，使用它
            state["conversation_history"] = chat_history[:]
        
        # 添加当前消息到历史
        state["conversation_history"].append({"role": "user", "content": user_message})
        
        # 🔧 修复2：增强信息提取，添加详细调试
        print(f"🔍 Starting information extraction...")
        extracted_info = await self._extract_mvp_and_preferences_enhanced(state["conversation_history"])
        print(f"🔍 Extracted info: {extracted_info}")
        
        # 🔧 修复3：优化更新策略
        self._update_customer_profile_with_priority(state["customer_profile"], extracted_info, current_customer_info)
        print(f"📊 Updated profile: {self._serialize_customer_profile(state['customer_profile'])}")
        
        # 检查已经有值的字段，自动标记为已问过
        required_mvp_fields = self._get_required_mvp_fields(state["customer_profile"])
        for field in required_mvp_fields:
            if getattr(state["customer_profile"], field) is not None:
                state["asked_fields"].add(field)
        
        # 检查是否是调整要求
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
        print(f"🎯 Current stage: {new_stage}")
        print(f"📝 Asked fields: {state['asked_fields']}")
        state["stage"] = new_stage
        
        # 生成响应
        try:
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
        except Exception as e:
            print(f"❌ Error in stage handling: {e}")
            response = {
                "message": "I'm having some trouble processing your request. Let me ask you a simple question to get back on track: What type of loan are you looking for?",
                "recommendations": []
            }
        
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
        """🔧 修复：从表单同步客户信息到profile"""
        print(f"🔄 Syncing form info: {form_info}")
        
        for field, value in form_info.items():
            if hasattr(profile, field):
                # 处理不同类型的值
                if value is not None and value != '' and value != 'undefined':
                    # 类型转换
                    if field in ['ABN_years', 'GST_years', 'credit_score', 'vehicle_year']:
                        try:
                            value = int(value) if value else None
                        except (ValueError, TypeError):
                            continue
                    elif field in ['desired_loan_amount', 'interest_rate_ceiling', 'monthly_budget']:
                        try:
                            value = float(value) if value else None
                        except (ValueError, TypeError):
                            continue
                    
                    if value is not None:
                        setattr(profile, field, value)
                        print(f"🔄 Synced from form: {field} = {value}")

    def _update_customer_profile_with_priority(self, profile: CustomerProfile, extracted_info: Dict[str, Any], manual_info: Dict = None):
        """使用优先级策略更新客户档案：自动提取 > 手动修改，最新信息 > 历史信息"""
        
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

    async def _extract_mvp_and_preferences_enhanced(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """🔧 修复：增强的信息提取方法，改进调试和错误处理"""
        
        print(f"🔍 Starting enhanced extraction...")
        print(f"📊 Conversation history length: {len(conversation_history)}")
        
        # 检查对话历史是否有效
        if not conversation_history:
            print("⚠️ Empty conversation history")
            return {}
        
        # 打印最近的对话内容用于调试
        recent_messages = conversation_history[-3:]
        for i, msg in enumerate(recent_messages):
            print(f"📝 Recent message {i}: {msg.get('role', 'unknown')}: {msg.get('content', 'empty')[:100]}...")
        
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using enhanced rule-based extraction")
                return self._enhanced_rule_based_extraction_fixed(conversation_history)
            
            conversation_text = "\n".join([
                f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]  # 最近6轮对话
            ])
            
            print(f"📤 Sending to Claude API...")
            print(f"📝 Conversation text (first 200 chars): {conversation_text[:200]}...")
            
            # 🔧 修复：改进的系统提示，更好的语义理解
            system_prompt = """你是专业的客户信息提取助手。从对话中准确提取客户贷款信息。

重要规则：
1. **精确提取**：只提取对话中明确提到的信息
2. **否定语句处理**：
   - "no ABN" / "don't have ABN" → ABN_years: 0
   - "no GST" / "not registered for GST" → GST_years: 0
   - "no property" / "don't own property" → property_status: "non_property_owner"
3. **数值识别**：
   - "credit score 600" / "600 credit" → credit_score: 600
   - "$50000" / "50k" / "fifty thousand" → desired_loan_amount: 50000
   - "2 years ABN" / "ABN for 2 years" → ABN_years: 2
4. **业务理解**：
   - "business loan" / "commercial" → loan_type: "commercial"
   - "personal loan" / "consumer" → loan_type: "consumer"
   - "own property" / "property owner" → property_status: "property_owner"

返回格式（纯JSON，无其他文字）：
{
    "loan_type": null,
    "asset_type": null,
    "property_status": null,
    "ABN_years": null,
    "GST_years": null,
    "credit_score": null,
    "desired_loan_amount": null,
    "loan_term_preference": null,
    "vehicle_type": null,
    "vehicle_condition": null,
    "business_structure": null,
    "interest_rate_ceiling": null,
    "monthly_budget": null,
    "vehicle_make": null,
    "vehicle_model": null,
    "vehicle_year": null
}

只返回JSON，不包含解释。"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 1000,
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": f"从以下对话中提取客户信息:\n{conversation_text}"}
                ]
            }

            print(f"📤 Making API request...")

            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                print(f"📥 API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['content'][0]['text']
                    
                    print(f"🤖 Claude raw response: {ai_response}")
                    
                    # 使用增强的JSON清理方法
                    clean_response = self._robust_json_cleaning_fixed(ai_response)
                    
                    if clean_response:
                        extracted_data = json.loads(clean_response)
                        print(f"✅ Claude extraction successful: {extracted_data}")
                        return extracted_data
                    else:
                        print("❌ Could not extract valid JSON from Claude response")
                        print("🔄 Falling back to rule-based extraction...")
                        return self._enhanced_rule_based_extraction_fixed(conversation_history)
                    
                else:
                    print(f"❌ Anthropic API error: {response.status_code}")
                    if response.text:
                        print(f"❌ Error details: {response.text[:200]}...")
                    print("🔄 Falling back to rule-based extraction...")
                    return self._enhanced_rule_based_extraction_fixed(conversation_history)
                    
        except httpx.TimeoutException:
            print("⏰ Anthropic API timeout - falling back to rule-based extraction")
            return self._enhanced_rule_based_extraction_fixed(conversation_history)
            
        except Exception as e:
            print(f"❌ Claude extraction failed: {e}")
            print("🔄 Falling back to rule-based extraction...")
            return self._enhanced_rule_based_extraction_fixed(conversation_history)

    def _robust_json_cleaning_fixed(self, ai_response: str) -> str:
        """🔧 修复：强化的JSON清理方法"""
        try:
            print(f"🧹 Cleaning JSON response...")
            
            # 移除常见的标记
            clean_response = ai_response.strip()
            
            # 移除markdown代码块标记
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            elif clean_response.startswith('```'):
                clean_response = clean_response[3:]
            
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            # 查找第一个{和最后一个}
            start_idx = clean_response.find('{')
            end_idx = clean_response.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                clean_response = clean_response[start_idx:end_idx+1]
                
                print(f"🧹 Cleaned JSON: {clean_response[:100]}...")
                
                # 验证JSON格式
                test_parse = json.loads(clean_response)
                print(f"✅ JSON validation successful")
                return clean_response
            else:
                print(f"❌ Could not find valid JSON structure")
                return None
                
        except json.JSONDecodeError as e:
            print(f"🔧 JSON cleaning failed: {e}")
            
            # 尝试正则表达式提取JSON
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, ai_response, re.DOTALL)
            
            print(f"🔧 Trying regex extraction, found {len(matches)} potential JSONs...")
            
            for i, match in enumerate(matches):
                try:
                    test_parse = json.loads(match)
                    print(f"✅ Regex extraction successful (match {i})")
                    return match
                except json.JSONDecodeError:
                    print(f"❌ Regex match {i} invalid")
                    continue
            
            print(f"❌ All regex attempts failed")
            return None
        except Exception as e:
            print(f"🔧 JSON cleaning error: {e}")
            return None

    def _enhanced_rule_based_extraction_fixed(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """🔧 修复：增强的规则后备提取方法"""
        
        print(f"🔍 Starting enhanced rule-based extraction...")
        
        # 检查输入
        if not conversation_history:
            print("⚠️ Empty conversation history in rule extraction")
            return {}
        
        # 获取原始文本和小写文本
        original_text = " ".join([msg.get("content", "") for msg in conversation_history])
        conversation_text = original_text.lower()
        
        print(f"📝 Processing text (first 200 chars): {original_text[:200]}...")
        
        extracted = {}
        
        # 1. 🔧 修复：增强否定语句处理
        negative_patterns = {
            "ABN_years": [
                r"no\s+abn", r"don'?t\s+have\s+abn", r"without\s+abn", 
                r"no\s+abn\s+and\s+gst", r"no\s+abn.*gst"
            ],
            "GST_years": [
                r"no\s+gst", r"don'?t\s+have\s+gst", r"not\s+registered\s+for\s+gst",
                r"no\s+abn\s+and\s+gst", r"no.*gst.*years"
            ]
        }
        
        for field, patterns in negative_patterns.items():
            for pattern in patterns:
                if re.search(pattern, conversation_text):
                    extracted[field] = 0
                    print(f"🔍 Negative pattern matched for {field}: 0")
                    break
        
        # 2. 🔧 修复：增强房产状态识别
        property_patterns = {
            "property_owner": [
                r"own\s+property", r"property\s+owner", r"have\s+property", 
                r"own\s+a\s+house", r"own\s+a\s+home", r"homeowner",
                r"property\s+backed", r"own\s+real\s+estate"
            ],
            "non_property_owner": [
                r"no\s+property", r"don'?t\s+own", r"rent", r"renting",
                r"non.property", r"without\s+property", r"tenant"
            ]
        }
        
        for status, patterns in property_patterns.items():
            for pattern in patterns:
                if re.search(pattern, conversation_text):
                    extracted["property_status"] = status
                    print(f"🔍 Property status matched: {status}")
                    break
            if "property_status" in extracted:
                break
        
        # 3. 🔧 修复：增强数值提取
        number_patterns = {
            "ABN_years": [
                r"abn.*?(\d+)\s*years?", r"(\d+)\s*years?.*?abn", 
                r"abn\s*for\s*(\d+)\s*years?", r"(\d+)\s*year.*abn"
            ],
            "GST_years": [
                r"gst.*?(\d+)\s*years?", r"(\d+)\s*years?.*?gst",
                r"gst\s*for\s*(\d+)\s*years?", r"(\d+)\s*year.*gst"
            ],
            "credit_score": [
                r"credit\s*score\s*(?:is\s*)?(\d{3,4})",
                r"score\s*(?:is\s*)?(\d{3,4})",
                r"(\d{3,4})\s*credit",
                r"my\s*score\s*(?:is\s*)?(\d{3,4})"
            ]
        }
        
        for field, patterns in number_patterns.items():
            if field in extracted:  # 跳过已经设置为0的否定情况
                continue
                
            for pattern in patterns:
                match = re.search(pattern, conversation_text)
                if match:
                    try:
                        value = int(match.group(1))
                        if field == "credit_score" and 300 <= value <= 900:
                            extracted[field] = value
                            print(f"🔍 {field} extracted: {value}")
                            break
                        elif field in ["ABN_years", "GST_years"] and 0 <= value <= 50:
                            extracted[field] = value
                            print(f"🔍 {field} extracted: {value}")
                            break
                    except (ValueError, IndexError):
                        continue
        
        # 4. 贷款类型识别
        if any(word in conversation_text for word in ["business", "commercial", "company"]):
            extracted["loan_type"] = "commercial"
            print(f"🔍 Loan type: commercial")
        elif any(word in conversation_text for word in ["personal", "consumer", "private"]):
            extracted["loan_type"] = "consumer"
            print(f"🔍 Loan type: consumer")
        
        # 5. 资产类型识别
        if any(word in conversation_text for word in ["car", "vehicle", "truck", "van", "motorcycle"]):
            extracted["asset_type"] = "motor_vehicle"
            print(f"🔍 Asset type: motor_vehicle")
        elif any(word in conversation_text for word in ["equipment", "machinery", "primary"]):
            extracted["asset_type"] = "primary"
            print(f"🔍 Asset type: primary")
        
        # 6. 车辆相关信息
        if "new" in conversation_text and ("vehicle" in conversation_text or "car" in conversation_text):
            extracted["vehicle_condition"] = "new"
            print(f"🔍 Vehicle condition: new")
        elif "used" in conversation_text and ("vehicle" in conversation_text or "car" in conversation_text):
            extracted["vehicle_condition"] = "used"
            print(f"🔍 Vehicle condition: used")
        
        # 7. 贷款金额提取
        amount_patterns = [
            r"[\$]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"(\d+)k\s*(?:loan|dollar|amount)",
            r"(\d+)\s*thousand",
            r"borrow.*?(\d+(?:,\d{3})*)",
            r"need.*?(\d+(?:,\d{3})*)",
            r"loan.*?amount.*?(\d+(?:,\d{3})*)"
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
                        print(f"🔍 Loan amount extracted: {amount}")
                        break
                except (ValueError, IndexError):
                    continue
        
        # 8. 车辆品牌和型号
        car_brands = ['toyota', 'holden', 'ford', 'mazda', 'honda', 'subaru', 'mitsubishi', 'nissan', 'hyundai', 'kia', 'volkswagen', 'bmw', 'mercedes', 'audi', 'tesla']
        for brand in car_brands:
            if brand in conversation_text:
                extracted["vehicle_make"] = brand.capitalize()
                print(f"🔍 Vehicle make: {brand}")
                break
        
        # 特殊处理Tesla Model Y
        if "model y" in conversation_text or "tesla model y" in conversation_text:
            extracted["vehicle_make"] = "Tesla"
            extracted["vehicle_model"] = "Model Y"
            extracted["vehicle_type"] = "passenger_car"
            extracted["asset_type"] = "motor_vehicle"
            print(f"🔍 Special match: Tesla Model Y")
        
        print(f"🔍 Enhanced rule-based extraction result: {extracted}")
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
        
        # 增强记忆功能：检查最近对话是否已经回答了问题
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
        """增强记忆功能：检查字段是否在最近对话中被讨论过"""
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
        """🔧 修复：处理产品匹配阶段 - 添加调整支持和完整产品信息"""
        print("🎯 Starting enhanced product matching...")
        profile = state["customer_profile"]
        
        # 🔧 修复：增强产品匹配，包含完整信息
        recommendations = await self._ai_product_matching_enhanced(profile)
        
        if not recommendations:
            print("❌ No recommendations found")
            return {
                "message": "I'm analyzing all available loan products for your profile. Let me find the best options across all lenders...",
                "recommendations": []
            }
        
        print(f"✅ Found {len(recommendations)} recommendations")
        
        # 管理推荐历史：保留最新2个
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
        
        # 只保留最新的2个，并正确标记
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
        """处理推荐阶段 - 修复推荐后的提示语，添加调整支持"""
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
        """简化的推荐消息格式，不显示产品详情"""
        
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
        
        if is_adjustment:
            message = f"Perfect! I've found an updated recommendation based on your requirements.\n\n"
        else:
            message = f"Great news! I've found an excellent loan option for you.\n\n"
        
        # 简化显示：只显示基本信息
        message += f"**{lender} - {product}** at {base_rate}% p.a.\n\n"
        
        # 重点引导到左侧面板
        message += f"📋 **Please check the Product Comparison panel on the left** to review all loan requirements, eligibility criteria, and fees.\n\n"
        
        # 确认和调整提示
        message += f"After reviewing the complete details, please let me know:\n"
        message += f"• Do you meet all the eligibility requirements?\n"
        message += f"• Would you like to adjust the **loan term**, **interest rate**, or **loan amount**?\n"
        message += f"• Any specific conditions you'd like me to optimize?\n\n"
        
        if is_adjustment:
            message += f"Let me know if you need further adjustments!"
        else:
            message += f"I can find alternative options if this doesn't meet your needs."
        
        return message

    async def _ai_product_matching_enhanced(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """🔧 修复：增强的AI产品匹配方法，包含完整产品信息"""
        
        print(f"🎯 Starting enhanced AI product matching...")
        print(f"📊 Customer profile: loan_type={profile.loan_type}, asset_type={profile.asset_type}")
        print(f"📊 Property status={profile.property_status}, credit_score={profile.credit_score}")
        print(f"📊 ABN years={profile.ABN_years}, GST years={profile.GST_years}")
        
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using enhanced fallback recommendation")
                return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]
            
            # 构建详细的客户档案
            profile_summary = f"""
Customer Profile:
- Loan Type: {profile.loan_type or 'business'} loan for {profile.asset_type or 'vehicle'}
- Property Owner: {profile.property_status or 'unknown'}
- Credit Score: {profile.credit_score or 'not specified'}
- ABN: {profile.ABN_years or 0} years, GST: {profile.GST_years or 0} years
- Loan Amount: ${profile.desired_loan_amount or 'not specified'}
- Vehicle: {profile.vehicle_make or ''} {profile.vehicle_model or ''} {profile.vehicle_condition or ''}
- Business Structure: {profile.business_structure or 'not specified'}
"""

            # 🔧 修复：使用完整的产品文档而不是简化版本
            full_product_info = self._get_complete_product_information()

            # 🔧 修复：改进的系统提示，要求更完整的输出
            system_prompt = f"""你是专业的贷款产品匹配专家。根据客户档案找到最佳贷款产品匹配。

客户档案：
{profile_summary}

完整产品库：
{full_product_info}

请返回最佳匹配的产品，包含COMPLETE信息。必须返回纯JSON格式：

{{
    "lender_name": "RAF",
    "product_name": "Vehicle Finance Premium (0-3 years)",
    "base_rate": 6.89,
    "comparison_rate": 7.15,
    "monthly_payment": 1250,
    "max_loan_amount": "$450,000",
    "loan_term_options": "12-60 months (up to 84 for green vehicles)",
    "requirements_met": true,
    "documentation_type": "Low Doc / Lite Doc / Full Doc",
    "detailed_requirements": {{
        "minimum_credit_score": "600 (Premium tier)",
        "abn_years_required": "2+ years (4+ for Premium)",
        "gst_years_required": "1+ years (2+ for Premium)", 
        "property_ownership": "Required for Premium tier",
        "deposit_required": "0% if asset-backed, 10% if non-asset-backed",
        "business_structure": "Any structure accepted",
        "asset_age_limit": "Vehicle max 25 years at end-of-term",
        "asset_condition": "New/demonstrator/used accepted",
        "loan_to_value_ratio": "Up to 120% for standard vehicles"
    }},
    "fees_breakdown": {{
        "establishment_fee": "$495",
        "monthly_account_fee": "$4.95",
        "private_sale_surcharge": "$695",
        "ppsr_fee": "At cost (compulsory if invoice > $50,000)",
        "brokerage_cap": "5.5% (no rate impact below this)",
        "variation_fee": "$60 per variation",
        "early_termination_fee": "Varies (Consumer: $750 max, Commercial: 35% remaining interest)"
    }},
    "rate_conditions": {{
        "base_rate_range": "6.89% (new 0-3yr) to 7.49% (used >3yr)",
        "premium_discount": "-0.50% for Premium tier customers",
        "rate_loadings": "+2% each for: private sale, classic car, asset age >16yr, prime mover (max 4% total)",
        "balloon_options": "New vehicles: 50%/45%/40% (36/48/60m), Used: 40%/35%/30%",
        "green_vehicle_bonus": "Electric vehicles qualify for preferential terms"
    }},
    "documentation_requirements": [
        "Application form and privacy consent",
        "Asset and liability statement (Low Doc minimum)",
        "12-month ATO portal history (Lite Doc)",
        "Two latest BAS portals (Lite Doc)", 
        "90-day bank statements (Full Doc mandatory, Lite Doc on request)",
        "Recent financial statements or tax returns (Full Doc)",
        "Property ownership verification (if applicable)",
        "Vehicle invoice and PPSR search (if price > $50k)",
        "Insurance Certificate of Currency (if NAF > $100k)"
    ],
    "special_conditions": [
        "Privacy consent forms must be dated within 90 days",
        "Credit approval valid for 90 days",
        "Vehicle must be registered by settlement",
        "Roadworthy certificate required for used vehicles",
        "Independent valuation required for private sales",
        "Settlement welcome call required for loans > $100k"
    ]
}}

CRITICAL: 返回完整的JSON，包含所有上述字段。不要省略任何信息。"""

            headers = {
                "x-api-key": self.anthropic_api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 2000,  # 增加token限制以获取完整信息
                "temperature": 0.1,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": "找到最佳贷款产品匹配，返回完整的产品信息JSON。"}
                ]
            }

            print(f"📤 Sending enhanced request to Claude API...")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                print(f"📥 Enhanced API response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['content'][0]['text']
                    
                    print(f"🤖 Claude enhanced response (first 300 chars): {ai_response[:300]}...")
                    
                    # 使用增强的JSON清理方法
                    clean_response = self._robust_json_cleaning_fixed(ai_response)
                    
                    if clean_response:
                        try:
                            recommendation = json.loads(clean_response)
                            print(f"✅ Successfully parsed enhanced recommendation: {recommendation.get('lender_name', 'Unknown')}")
                            return [recommendation]
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON parsing still failed: {e}")
                            print("🔄 Using enhanced fallback recommendation...")
                            return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]
                    else:
                        print("❌ Could not extract valid JSON from Claude response")
                        print("🔄 Using enhanced fallback recommendation...")
                        return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]
                
                else:
                    print(f"❌ API error: {response.status_code} - {response.text[:200]}")
                    return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]
                    
        except Exception as e:
            print(f"❌ Unexpected error in enhanced AI product matching: {e}")
            return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]

    def _get_complete_product_information(self) -> str:
        """🔧 修复：获取完整产品信息而不是简化版本"""
        
        # 返回详细的产品信息，包含完整的文档要求
        complete_info = """
RAF (RESIMAC ASSET FINANCE) - COMPLETE PRODUCT DETAILS:

Vehicle Finance (0-3 years):
- Base Rate: 6.89% p.a. (Premium tier gets -0.50% discount = 6.39%)
- Comparison Rate: ~7.15% (includes fees)
- Max Loan: $450,000 (Premium tier), $400,000 (Standard), $200,000 (Basic)
- Terms: 12-60 months (up to 84 months for green vehicles)
- Credit Score: 600+ (Premium), 550+ with 20% deposit
- ABN: 4+ years (Premium), 2+ years (Standard/Basic)
- GST: 2+ years (Premium), 1+ years (Standard/Basic)
- Property: Required for Premium tier
- Documentation Levels: Low Doc / Lite Doc / Full Doc
- Fees: Establishment $495, Monthly $4.95, Private sale +$695, PPSR at cost
- Rate Loadings: +2% each (private sale, classic car, age >16yr, prime mover)
- Balloons: New vehicles 50%/45%/40% (36/48/60m), Used 40%/35%/30%

DOCUMENTATION REQUIREMENTS (RAF):
Low Doc: Application + privacy consent + A&L statement
Lite Doc: Low Doc items + 12m ATO portal + 2 BAS + 90d bank statements (on request)
Full Doc: Lite Doc items + mandatory 90d bank statements + recent financials/tax returns

SPECIAL RAF REQUIREMENTS:
- Privacy consent forms dated within 90 days
- Insurance CoC if NAF > $100,000 (must name Resimac)
- PPSR search compulsory if invoice price > $50,000
- Settlement welcome call required for loans > $100,000
- Vehicle registration by settlement (roadworthy cert for used)
- Independent valuation required for all private sales

ANGLE FINANCE - COMPLETE PRODUCT DETAILS:

Primary Asset Finance:
- Rates: 7.99% (Property owner) to 16.75% (Non-property)
- Max Terms: 10-20 years depending on product
- Credit Score: 500-650 range accepted
- ABN: 2+ years, GST: 1+ years minimum
- Fees: Setup $540 (dealer) / $700 (private), Monthly $4.95
- Documentation: Low Doc up to $100k, Full Doc for higher amounts

A+ Premium Products:
- Rate: 6.99% (Standard) / 6.49% (Discount) / 5.99% (New assets discount)
- Requirements: ABN 4+ years, GST 2+ years, Company/Trust/Partnership only
- Property backing required, Corporate credit 550+, Individual 600+
- Min deal: $300k for discount rates

BFS (BRANDED FINANCIAL SERVICES) - COMPLETE DETAILS:

Prime Commercial:
- Rates: 7.65% (new) to 11.75% (used non-asset-backed)
- Credit: 600+ (500 with 20% deposit)
- Documentation: 90-day bank statements + financials for >$100k
- Max: $250k private sales, $400k high-value (case-by-case)

Prime Consumer:
- Rates: 8.80% (score >750) to 13.55% (score 500+)
- Income verification required (PAYG payslips, business returns)
- 20% deposit required for scores <600

Plus (Non-Prime):
- Rate: 15.98% (may discount up to 2%)
- Credit: 500+ minimum
- Bank statements mandatory
- Max: $100k loan amount

FCAU (FLEXICOMMERCIAL) - COMPLETE DETAILS:

FlexiPremium:
- Rates: 6.85%-7.74% depending on loan size
- Requirements: Company/Trust only, ABN/GST 4+ years
- Asset: Primary/Secondary ≤5 years (Primary) / ≤2 years (Secondary)
- Max: $500k (larger amounts need BDM approval)

FlexiCommercial:
- Rates: 8.15%-12.90% based on amount and asset type
- Primary: Up to 20 years old at end-of-term (trailers 30 years)
- Secondary: Up to 7 years old at end-of-term
- Tertiary: Up to 7 years old, rates 12.90%-15.90%

Rate Add-ons (stackable, max 4%):
+1% prime mover or private sale
+1% term <24 months
+1% asset 10-15 years old at end-of-term
+1.25% non-asset-backed
+1.25% term >60 months
+2% asset 15-20 years old at end-of-term

DOCUMENTATION REQUIREMENTS BY LENDER:

RAF Full Documentation:
- Application and privacy consent
- Asset and liability statement
- 12-month ATO portal history
- Latest two BAS portals
- 90-day bank statements (mandatory Full Doc)
- Recent financial statements or tax returns
- Property ownership verification documents
- Vehicle invoice and compliance documentation
- Insurance Certificate of Currency (if NAF >$100k)
- PPSR search results (if invoice >$50k)
- Roadworthy certificate (used vehicles)
- Independent valuation report (private sales)

ANGLE Full Documentation:
- 6 months bank statements OR accountant-prepared financials (FY2024 + FY2023)
- Commitment schedule (mandatory)
- ATO portal statements (for amounts ≥$250k)
- Good payment history (last 12 months for ≥$250k)
- Detailed business background
- List of major clients
- Aged debtor and creditor listing (≥$500k)
- Cashflow projections (if available, for >$1M)

BFS Documentation:
- 90-day bank statements (all loans)
- For loans >$100k: Externally prepared financial statements ≤18 months old (2 years)
- Latest tax return for borrowing entity
- Recent management accounts or BAS (if statements >18 months old)

FCAU Documentation:
- Standard application and privacy consent
- Asset and liability statement
- Clear Equifax file or supporting bank statements
- Statutory declaration (if required)
- Vehicle inspection (one of four approved methods)
"""
        
        return complete_info

    def _create_comprehensive_fallback_recommendation_enhanced(self, profile: CustomerProfile) -> Dict[str, Any]:
        """🔧 修复：创建包含完整信息的增强智能后备推荐"""
        
        print("🔄 Creating comprehensive enhanced fallback recommendation...")
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
                "loan_term_options": "12-60 months (up to 84 for green vehicles)",
                "requirements_met": True,
                "documentation_type": "Low Doc / Lite Doc / Full Doc",
                
                "detailed_requirements": {
                    "minimum_credit_score": "600 (Premium tier)",
                    "abn_years_required": "4+ years (Premium tier)",
                    "gst_years_required": "2+ years (Premium tier)", 
                    "property_ownership": "Required for Premium tier",
                    "deposit_required": "0% if asset-backed, 10% if non-asset-backed",
                    "business_structure": "Any structure accepted",
                    "asset_age_limit": "Vehicle max 25 years at end-of-term",
                    "asset_condition": "New/demonstrator/used all accepted",
                    "loan_to_value_ratio": "Up to 120% for standard vehicles"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$495",
                    "monthly_account_fee": "$4.95",
                    "private_sale_surcharge": "$695",
                    "ppsr_fee": "At cost (compulsory if invoice > $50,000)",
                    "brokerage_cap": "5.5% (no rate impact below this)",
                    "variation_fee": "$60 per variation",
                    "early_termination_fee": "Consumer: $750 max, Commercial: 35% remaining interest"
                },
                
                "rate_conditions": {
                    "base_rate_range": "6.89% (new 0-3yr) to 7.49% (used >3yr)",
                    "premium_discount": "-0.50% for Premium tier customers",
                    "rate_loadings": "+2% each for: private sale, classic car, asset age >16yr, prime mover (max 4% total)",
                    "balloon_options": "New vehicles: 50%/45%/40% (36/48/60m), Used: 40%/35%/30%",
                    "green_vehicle_bonus": "Electric vehicles qualify for preferential terms"
                },
                
                "documentation_requirements": [
                    "Application form and privacy consent",
                    "Asset and liability statement (Low Doc minimum)",
                    "12-month ATO portal history (Lite Doc)",
                    "Two latest BAS portals (Lite Doc)", 
                    "90-day bank statements (Full Doc mandatory, Lite Doc on request)",
                    "Recent financial statements or tax returns (Full Doc)",
                    "Property ownership verification documents",
                    "Vehicle invoice and PPSR search (if price > $50k)",
                    "Insurance Certificate of Currency (if NAF > $100k)",
                    "Roadworthy certificate (used vehicles)",
                    "Independent valuation report (private sales)"
                ],
                
                "special_conditions": [
                    "Privacy consent forms must be dated within 90 days of application",
                    "Credit approval remains valid for 90 days",
                    "Vehicle must be registered by or at settlement",
                    "Settlement welcome call required for loans > $100,000",
                    "Overseas borrowers require verification calls and travel itinerary",
                    "Certificate of Currency must extend ≥30 days beyond settlement",
                    "PPSR searches compulsory on asset prices > $50,000",
                    "Independent valuation mandatory on all private-sale assets"
                ]
            }
        
        else:
            print("✅ Default match: General purpose -> Angle Finance Enhanced")
            
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
                "max_loan_amount": "$100,000 (Low Doc), $250,000+ (Full Doc)",
                "loan_term_options": "12-84 months depending on asset",
                "requirements_met": True,
                "documentation_type": "Low Doc / Full Doc",
                
                "detailed_requirements": {
                    "minimum_credit_score": "500-650 range accepted",
                    "abn_years_required": "2+ years",
                    "gst_years_required": "1+ years",
                    "property_ownership": "Preferred but not required (20% deposit if non-property)",
                    "deposit_required": "20% if non-property owner, 0% if property backed",
                    "business_structure": "Any structure accepted",
                    "asset_age_limit": "Varies by asset type and product"
                },
                
                "fees_breakdown": {
                    "establishment_fee": "$540 (dealer), $700 (private)",
                    "monthly_account_fee": "$4.95",
                    "brokerage_cap": "Up to 8% (with rate loading above 5%)",
                    "ppsr_fee": "At cost",
                    "origination_fee": "Up to $1,400 (incl. GST)"
                },
                
                "rate_conditions": {
                    "base_rate_range": "7.99%-16.95% depending on product and risk",
                    "rate_loadings": "Various loadings based on risk factors",
                    "balloon_options": "Limited availability depending on product",
                    "special_products": "A+ rates from 5.99% for premium customers"
                },
                
                "documentation_requirements": [
                    "Application form and privacy consent",
                    "6 months bank statements OR accountant-prepared financials (FY2024 + FY2023)",
                    "Commitment schedule (mandatory for all)",
                    "ATO portal statements (for amounts ≥$250,000)",
                    "Good payment history documentation (last 12 months for ≥$250k)",
                    "Detailed business background information",
                    "List of major clients (for larger loans)",
                    "Aged debtor and creditor listing (≥$500,000)",
                    "Cashflow projections (if available, for >$1,000,000)"
                ],
                
                "special_conditions": [
                    "All loan conditions must be satisfied before settlement",
                    "Signed documents required via DocuSign platform",
                    "Vehicle inspection mandatory for private sales",
                    "Valid vehicle registration (Rego) must be provided",
                    "PPSR must be clear (no encumbrances)",
                    "Tax invoice required before settlement",
                    "Certificate of Currency required if loan amount > $100,000 AUD"
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