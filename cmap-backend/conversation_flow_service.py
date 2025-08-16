# enhanced_memory_conversation_service.py - 修复后的完整版本
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime

class ConversationStage(Enum):
    GREETING = "greeting"
    MVP_COLLECTION = "mvp_collection"
    PREFERENCE_COLLECTION = "preference_collection"
    PRODUCT_MATCHING = "product_matching"
    CALCULATION = "calculation"
    REFINEMENT = "refinement"
    FINAL_RECOMMENDATION = "final_recommendation"
    HANDOFF = "handoff"

@dataclass
class CustomerInformation:
    """Customer information storage with memory tracking"""
    # Basic MVP fields
    loan_type: Optional[str] = None
    asset_type: Optional[str] = None
    property_status: Optional[str] = None
    ABN_years: Optional[int] = None
    GST_years: Optional[int] = None
    credit_score: Optional[int] = None
    desired_loan_amount: Optional[float] = None
    loan_term_preference: Optional[int] = None
    
    # Vehicle information
    vehicle_type: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_condition: Optional[str] = None
    
    # Business information
    business_type: Optional[str] = None
    business_age: Optional[int] = None
    business_structure: Optional[str] = None  # 🔧 修复：确保business_structure字段存在
    
    # Preferences
    interest_rate_ceiling: Optional[float] = None
    monthly_budget: Optional[float] = None
    preferred_term: Optional[int] = None
    min_loan_amount: Optional[float] = None
    documentation_preference: Optional[str] = None
    
    # Memory tracking fields
    asked_fields: Set[str] = field(default_factory=set)
    confirmed_fields: Set[str] = field(default_factory=set)
    
    def update_field(self, field_name: str, value: Any) -> bool:
        """Update field value and mark as confirmed"""
        if hasattr(self, field_name) and value is not None:
            setattr(self, field_name, value)
            self.confirmed_fields.add(field_name)
            return True
        return False
    
    def mark_field_asked(self, field_name: str):
        """Mark field as having been asked"""
        self.asked_fields.add(field_name)
    
    def is_field_complete(self, field_name: str) -> bool:
        """Check if field is complete (has value and confirmed)"""
        return (hasattr(self, field_name) and 
                getattr(self, field_name) is not None and 
                field_name in self.confirmed_fields)
    
    def get_missing_core_fields(self) -> List[str]:
        """🔧 修复：获取缺失的核心MVP字段，包含business_structure"""
        core_fields = [
            "loan_type", 
            "asset_type", 
            "business_structure",  # 🔧 修复：添加为核心字段
            "property_status", 
            "ABN_years", 
            "GST_years"
        ]
        return [field for field in core_fields if not self.is_field_complete(field)]
    
    def get_missing_important_fields(self) -> List[str]:
        """Get missing important fields for product matching"""
        important_fields = ["credit_score", "desired_loan_amount"]
        return [field for field in important_fields if not self.is_field_complete(field)]

@dataclass 
class ConversationMemory:
    """Conversation memory management"""
    session_id: str
    customer_info: CustomerInformation = field(default_factory=CustomerInformation)
    stage: ConversationStage = ConversationStage.GREETING
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    last_questions: List[str] = field(default_factory=list)  # Recently asked questions
    topics_discussed: Set[str] = field(default_factory=set)  # Topics covered
    clarifications_needed: Dict[str, str] = field(default_factory=dict)  # Field -> reason
    conversation_round: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.conversation_round += 1
        self.last_updated = datetime.now()
    
    def add_question_asked(self, question: str):
        """Track questions that have been asked"""
        self.last_questions.append(question)
        # Keep only last 5 questions to avoid memory bloat
        if len(self.last_questions) > 5:
            self.last_questions = self.last_questions[-5:]

class EnhancedMemoryService:
    """Enhanced memory service with anti-repetition and context awareness"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationMemory] = {}
        
        # 🔧 修复：增强的业务结构提取模式
        self.business_structure_patterns = {
            'sole_trader': [
                r'sole\s*trader', r'individual\s*trader', r'self\s*employed',
                r'operating\s*as\s*an\s*individual', r'trading\s*individually'
            ],
            'company': [
                r'company', r'pty\s*ltd', r'corporation', r'incorporated',
                r'\bltd\b', r'corporate\s*entity', r'limited\s*company'
            ],
            'partnership': [
                r'partnership', r'partners', r'joint\s*venture',
                r'business\s*partnership', r'trading\s*partnership'
            ],
            'trust': [
                r'trust', r'family\s*trust', r'discretionary\s*trust',
                r'unit\s*trust', r'trustee', r'trading\s*trust'
            ]
        }
    
    def get_or_create_session(self, session_id: str) -> ConversationMemory:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory(session_id=session_id)
        return self.sessions[session_id]
    
    def update_customer_information(self, session_id: str, extracted_info: Dict[str, Any]):
        """🔧 修复：更新客户信息，包含业务结构处理"""
        memory = self.get_or_create_session(session_id)
        
        for field, value in extracted_info.items():
            if hasattr(memory.customer_info, field) and value is not None:
                # 验证业务结构值
                if field == 'business_structure':
                    if value in ['sole_trader', 'company', 'partnership', 'trust']:
                        memory.customer_info.update_field(field, value)
                        print(f"🏢 Updated business structure: {value}")
                    else:
                        print(f"⚠️ Invalid business structure value: {value}")
                else:
                    memory.customer_info.update_field(field, value)
    
    def extract_information_from_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """🔧 修复：从用户消息中提取信息，包含增强的业务结构提取"""
        extracted = {}
        message_lower = user_message.lower()
        
        # 🔧 修复：业务结构提取
        for structure, patterns in self.business_structure_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    extracted['business_structure'] = structure
                    print(f"🏢 Extracted business structure: {structure}")
                    break
            if 'business_structure' in extracted:
                break
        
        # 贷款类型提取
        if any(phrase in message_lower for phrase in ['business loan', 'commercial loan', 'asset finance']):
            extracted['loan_type'] = 'business'
        elif any(phrase in message_lower for phrase in ['personal loan', 'consumer loan']):
            extracted['loan_type'] = 'consumer'
        
        # 资产类型提取
        asset_keywords = {
            'motor_vehicle': ['car', 'vehicle', 'truck', 'van', 'ute', 'motorcycle', 'auto'],
            'primary': ['primary equipment', 'main equipment', 'core machinery'],
            'secondary': ['secondary equipment', 'generator', 'compressor'],
            'tertiary': ['tertiary equipment', 'computer', 'IT equipment']
        }
        
        for asset_type, keywords in asset_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                extracted['asset_type'] = asset_type
                break
        
        # 房产状态提取
        if any(phrase in message_lower for phrase in ['own property', 'property owner', 'have property']):
            extracted['property_status'] = 'property_owner'
        elif any(phrase in message_lower for phrase in ["don't own property", "no property", 'rent']):
            extracted['property_status'] = 'non_property_owner'
        
        # 车辆状况提取
        if any(phrase in message_lower for phrase in ['new car', 'brand new', 'new vehicle']):
            extracted['vehicle_condition'] = 'new'
        elif any(phrase in message_lower for phrase in ['used car', 'second hand', 'pre-owned']):
            extracted['vehicle_condition'] = 'used'
        elif any(phrase in message_lower for phrase in ['demo', 'demonstrator']):
            extracted['vehicle_condition'] = 'demonstrator'
        
        # 数值提取
        # ABN年限
        abn_match = re.search(r'abn.{0,20}(\d+).{0,10}year', message_lower)
        if abn_match:
            extracted['ABN_years'] = int(abn_match.group(1))
        
        # GST年限
        gst_match = re.search(r'gst.{0,20}(\d+).{0,10}year', message_lower)
        if gst_match:
            extracted['GST_years'] = int(gst_match.group(1))
        
        # 信用分数
        credit_match = re.search(r'credit.{0,20}(\d{3,4})', message_lower)
        if credit_match:
            score = int(credit_match.group(1))
            if 300 <= score <= 900:
                extracted['credit_score'] = score
        
        # 🔧 修复：增强的贷款金额提取
        amount_patterns = [
            r'[\$](\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:,\d{3})*)\s*(?:dollars?|k|thousand)',
            r'borrow\s*(\d{1,3}(?:,\d{3})*)',
            r'loan\s*(?:of|for)?\s*[\$]?(\d{1,3}(?:,\d{3})*)'
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, user_message.replace(',', ''))
            if matches:
                amounts = []
                for match in matches:
                    try:
                        amount = float(match.replace(',', ''))
                        if amount > 1000:  # 过滤小数字
                            amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    extracted['desired_loan_amount'] = max(amounts)
                    break
        
        # 更新内存中的客户信息
        if extracted:
            self.update_customer_information(session_id, extracted)
        
        return extracted
    
    def get_next_questions(self, session_id: str, max_questions: int = 2) -> List[str]:
        """🔧 修复：获取下一个要问的问题，优先business_structure"""
        memory = self.get_or_create_session(session_id)
        
        # 定义问题优先级，business_structure提前
        question_priority = [
            ("loan_type", "What type of loan are you looking for? (business/consumer)"),
            ("asset_type", "What type of asset are you looking to finance?"),
            ("business_structure", "What is your business structure? (sole trader/company/partnership/trust)"),
            ("property_status", "Do you own property?"),
            ("ABN_years", "How many years has your ABN been registered?"),
            ("GST_years", "How many years have you been registered for GST?"),
            ("credit_score", "What is your current credit score?"),
            ("desired_loan_amount", "How much would you like to borrow?")
        ]
        
        # 添加车辆相关问题（如果适用）
        if memory.customer_info.asset_type == 'motor_vehicle':
            vehicle_questions = [
                ("vehicle_type", "What type of vehicle? (passenger car/truck/van/motorcycle)"),
                ("vehicle_condition", "Are you looking at new or used vehicles?"),
                ("vehicle_make", "What make of vehicle?"),
                ("vehicle_model", "What model of vehicle?")
            ]
            # 在credit_score之前插入车辆问题
            insert_index = next(i for i, (field, _) in enumerate(question_priority) if field == "credit_score")
            for i, (field, question) in enumerate(vehicle_questions):
                question_priority.insert(insert_index + i, (field, question))
        
        next_questions = []
        
        for field, question in question_priority:
            # 检查字段是否已完成或最近已问过
            if (not memory.customer_info.is_field_complete(field) and 
                field not in memory.customer_info.asked_fields and
                question not in memory.last_questions[-2:]):  # 避免重复最近2个问题
                
                next_questions.append(question)
                memory.customer_info.mark_field_asked(field)
                memory.add_question_asked(question)
                
                if len(next_questions) >= max_questions:
                    break
        
        return next_questions
    
    def should_reset_session(self, session_id: str, user_message: str) -> bool:
        """🔧 修复2：检测是否应该重置会话"""
        reset_patterns = [
            r'new\s*(loan|application)',
            r'different\s*(loan|finance)', 
            r'start\s*over',
            r'fresh\s*start',
            r'another\s*(loan|quote)',
            r'completely\s*different'
        ]
        
        message_lower = user_message.lower()
        
        for pattern in reset_patterns:
            if re.search(pattern, message_lower):
                print(f"🔄 Session reset detected: {pattern}")
                return True
        
        return False
    
    def reset_session(self, session_id: str):
        """🔧 修复2：重置会话状态"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🔄 Session {session_id} has been reset")
    
    def detect_loan_amount_change(self, session_id: str, user_message: str) -> Optional[float]:
        """🔧 修复3：检测贷款金额变更请求"""
        change_patterns = [
            r'change.{0,20}amount.{0,20}to.{0,10}[\$]?(\d{1,3}(?:,?\d{3})*)',
            r'loan.{0,20}amount.{0,20}[\$]?(\d{1,3}(?:,?\d{3})*)',
            r'(\d{1,3}(?:,?\d{3})*).{0,20}instead',
            r'update.{0,20}to.{0,10}[\$]?(\d{1,3}(?:,?\d{3})*)'
        ]
        
        message_lower = user_message.lower().replace(',', '')
        
        for pattern in change_patterns:
            match = re.search(pattern, message_lower)
            if match:
                try:
                    new_amount = float(match.group(1).replace(',', ''))
                    if new_amount > 10000:  # 确保是合理的金额
                        print(f"💰 Detected loan amount change request: ${new_amount:,}")
                        return new_amount
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def create_context_aware_prompt(self, session_id: str, user_message: str) -> str:
        """Create context-aware prompt with memory and anti-repetition"""
        memory = self.get_or_create_session(session_id)
        
        # 检查是否需要重置会话
        if self.should_reset_session(session_id, user_message):
            self.reset_session(session_id)
            memory = self.get_or_create_session(session_id)  # 创建新会话
        
        # 提取当前消息中的信息
        extracted_info = self.extract_information_from_message(session_id, user_message)
        
        # 检查贷款金额变更
        amount_change = self.detect_loan_amount_change(session_id, user_message)
        if amount_change:
            memory.customer_info.update_field('desired_loan_amount', amount_change)
            extracted_info['desired_loan_amount'] = amount_change
            extracted_info['_amount_change_request'] = True
        
        # 构建上下文感知提示
        context_sections = []
        
        # 会话基本信息
        context_sections.append(f"""
## SESSION CONTEXT
Session ID: {session_id}
Conversation Round: {memory.conversation_round}
Current Stage: {memory.stage.value}
Last Updated: {memory.last_updated.strftime('%Y-%m-%d %H:%M:%S')}
""")
        
        # 已收集的客户信息
        collected_info = self._format_collected_info(memory)
        if collected_info:
            context_sections.append(f"""
## COLLECTED CUSTOMER INFORMATION
{json.dumps(collected_info, ensure_ascii=False, indent=2)}
""")
        
        # 缺失信息
        missing_info = self._format_missing_info(memory)
        if missing_info:
            context_sections.append(f"""
## MISSING INFORMATION
Core Fields: {memory.customer_info.get_missing_core_fields()}
Important Fields: {memory.customer_info.get_missing_important_fields()}
""")
        
        # 防重复指令
        repetition_instructions = self._generate_avoid_repetition_instruction(memory)
        context_sections.append(f"""
## ANTI-REPETITION GUIDELINES
{repetition_instructions}
""")
        
        # 下一步建议
        next_questions = self.get_next_questions(memory.session_id, max_questions=2)
        if next_questions:
            context_sections.append(f"➡️ NEXT QUESTIONS TO ASK: {next_questions}")
        else:
            context_sections.append("➡️ INFORMATION COLLECTION COMPLETE - PROCEED TO PRODUCT MATCHING")
        
        # 当前提取的信息
        if extracted_info:
            context_sections.append(f"""
## NEWLY EXTRACTED INFORMATION
{json.dumps(extracted_info, ensure_ascii=False, indent=2)}
""")
        
        context_sections.append(f"""
## CURRENT USER MESSAGE
{user_message}
""")
        
        return "\n".join(context_sections)
    
    def _format_collected_info(self, memory: ConversationMemory) -> Dict[str, Any]:
        """Format collected information"""
        info = {}
        for field in memory.customer_info.confirmed_fields:
            value = getattr(memory.customer_info, field, None)
            if value is not None:
                info[field] = value
        return info
    
    def _format_missing_info(self, memory: ConversationMemory) -> List[str]:
        """Format missing information"""
        missing = []
        missing.extend(memory.customer_info.get_missing_core_fields())
        missing.extend(memory.customer_info.get_missing_important_fields())
        return list(set(missing))
    
    def _generate_avoid_repetition_instruction(self, memory: ConversationMemory) -> str:
        """Generate anti-repetition instructions"""
        instructions = [
            "❌ NEVER repeat questions about information the customer has already provided",
            "❌ DO NOT ask again about fields that were asked in the last 2 conversation rounds"
        ]
        
        if memory.customer_info.confirmed_fields:
            confirmed_list = ", ".join(memory.customer_info.confirmed_fields)
            instructions.append(f"✅ CONFIRMED FIELDS (DO NOT ASK AGAIN): {confirmed_list}")
        
        if memory.last_questions:
            recent_questions = memory.last_questions[-2:]
            instructions.append(f"🚫 RECENTLY ASKED (DO NOT REPEAT): {recent_questions}")
        
        return "\n".join(instructions)
    
    def update_conversation_stage(self, session_id: str, new_stage: ConversationStage):
        """Update conversation stage"""
        memory = self.get_or_create_session(session_id)
        memory.stage = new_stage
    
    def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get conversation summary"""
        memory = self.get_or_create_session(session_id)
        
        return {
            "session_id": session_id,
            "stage": memory.stage.value,
            "conversation_rounds": memory.conversation_round,
            "collected_info_count": len(memory.customer_info.confirmed_fields),
            "missing_core_fields": memory.customer_info.get_missing_core_fields(),
            "missing_important_fields": memory.customer_info.get_missing_important_fields(),
            "recent_questions": memory.last_questions[-3:],
            "last_updated": memory.last_updated.isoformat(),
            "customer_profile": {
                field: getattr(memory.customer_info, field) 
                for field in memory.customer_info.confirmed_fields
            }
        }
    
    def clear_session(self, session_id: str):
        """Clear session memory"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🗑️ Cleared session: {session_id}")

# 保持向后兼容性的别名
ConversationFlowService = EnhancedMemoryService