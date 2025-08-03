# enhanced_memory_conversation_service.py
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
    business_structure: Optional[str] = None
    
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
        """Get missing core MVP fields"""
        core_fields = ["loan_type", "asset_type", "property_status", "ABN_years", "GST_years"]
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
    clarifications_needed: Dict[str, str] = field(default_factory=dict)  # Info needing clarification
    conversation_round: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str):
        """Add conversation record"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_updated = datetime.now()
    
    def add_question(self, question: str):
        """Record question asked"""
        self.last_questions.append(question)
        # Keep only last 5 questions
        if len(self.last_questions) > 5:
            self.last_questions.pop(0)
    
    def was_recently_asked(self, field_name: str) -> bool:
        """Check if field was asked in recent questions"""
        field_keywords = {
            "credit_score": ["credit", "score"],
            "loan_amount": ["amount", "borrow"],
            "property_status": ["property", "own"],
            "ABN_years": ["ABN", "years"],
            "GST_years": ["GST", "registered"]
        }
        
        keywords = field_keywords.get(field_name, [field_name])
        recent_questions = " ".join(self.last_questions[-3:])  # Check last 3 questions
        
        return any(keyword.lower() in recent_questions.lower() for keyword in keywords)

class EnhancedMemoryService:
    """Enhanced memory service with anti-repetition capabilities"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationMemory] = {}
        self.field_patterns = self._init_field_patterns()
    
    def _init_field_patterns(self) -> Dict[str, List[str]]:
        """Initialize field recognition patterns"""
        return {
            "credit_score": [
                r"credit score.{0,20}?(\d{3,4})",
                r"score.{0,10}?(\d{3,4})",
                r"my score is (\d{3,4})"
            ],
            "desired_loan_amount": [
                r"(?:need|want|looking for|borrow).{0,20}?\$?(\d+(?:,\d{3})*)",
                r"\$(\d+(?:,\d{3})*)",
                r"(\d+)k",
                r"(\d+) thousand"
            ],
            "ABN_years": [
                r"ABN.{0,20}?(\d+)\s*years?",
                r"registered.{0,20}?(\d+)\s*years?",
                r"(\d+)\s*years?.{0,20}?ABN"
            ],
            "GST_years": [
                r"GST.{0,20}?(\d+)\s*years?",
                r"(\d+)\s*years?.{0,20}?GST"
            ],
            "property_status": [
                r"(?:own|have).{0,10}?property",
                r"property owner",
                r"no property",
                r"don't own",
                r"rent"
            ]
        }
    
    def get_or_create_session(self, session_id: str) -> ConversationMemory:
        """Get or create session memory"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory(session_id=session_id)
        return self.sessions[session_id]
    
    def extract_information_from_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Extract information from user message"""
        memory = self.get_or_create_session(session_id)
        extracted = {}
        
        # Use regex patterns to extract information
        for field_name, patterns in self.field_patterns.items():
            if not memory.customer_info.is_field_complete(field_name):
                for pattern in patterns:
                    match = re.search(pattern, user_message, re.IGNORECASE)
                    if match:
                        try:
                            if field_name in ["credit_score", "ABN_years", "GST_years"]:
                                extracted[field_name] = int(match.group(1))
                            elif field_name == "desired_loan_amount":
                                amount_str = match.group(1).replace(",", "")
                                if "k" in user_message.lower() or "thousand" in user_message.lower():
                                    extracted[field_name] = float(amount_str) * 1000
                                else:
                                    extracted[field_name] = float(amount_str)
                            elif field_name == "property_status":
                                if any(word in match.group(0).lower() for word in ["own", "have"]):
                                    extracted[field_name] = "property_owner"
                                else:
                                    extracted[field_name] = "non_property_owner"
                            break
                        except (ValueError, IndexError):
                            continue
        
        # Update customer information
        for field_name, value in extracted.items():
            memory.customer_info.update_field(field_name, value)
        
        return extracted
    
    def should_ask_field(self, session_id: str, field_name: str) -> bool:
        """Determine if field should be asked"""
        memory = self.get_or_create_session(session_id)
        
        # Don't ask if field is already complete
        if memory.customer_info.is_field_complete(field_name):
            return False
        
        # Don't ask if recently asked
        if memory.was_recently_asked(field_name):
            return False
        
        # Don't ask if asked too many times already
        if field_name in memory.customer_info.asked_fields:
            asked_count = sum(1 for q in memory.last_questions 
                            if any(keyword in q.lower() 
                                 for keyword in self._get_field_keywords(field_name)))
            if asked_count >= 2:  # Maximum 2 attempts
                return False
        
        return True
    
    def _get_field_keywords(self, field_name: str) -> List[str]:
        """Get keywords related to field"""
        keywords_map = {
            "credit_score": ["credit", "score"],
            "desired_loan_amount": ["amount", "borrow", "loan"],
            "property_status": ["property", "own"],
            "ABN_years": ["ABN", "years"],
            "GST_years": ["GST", "years"]
        }
        return keywords_map.get(field_name, [field_name])
    
    def get_next_questions(self, session_id: str, max_questions: int = 1) -> List[str]:
        """Get next questions to ask"""
        memory = self.get_or_create_session(session_id)
        questions = []
        
        # Priority order
        field_priority = [
            ("loan_type", "Is this loan for business/commercial use or personal use?"),
            ("credit_score", "What is your current credit score?"),
            ("desired_loan_amount", "How much are you looking to borrow?"),
            ("asset_type", "What type of asset are you looking to finance? (e.g., vehicle, primary equipment, secondary equipment)"),
            ("property_status", "Do you currently own property?"),
            ("ABN_years", "How many years has your ABN been registered?"),
            ("GST_years", "How many years have you been registered for GST? (Enter 0 if not registered)")
        ]
        
        for field_name, question in field_priority:
            if len(questions) >= max_questions:
                break
            if self.should_ask_field(session_id, field_name):
                questions.append(question)
                memory.customer_info.mark_field_asked(field_name)
                memory.add_question(question)
        
        return questions
    
    def create_context_aware_prompt(self, session_id: str, user_message: str) -> str:
        """Create context-aware prompt with memory"""
        memory = self.get_or_create_session(session_id)
        
        # Add user message to history
        memory.add_message("user", user_message)
        memory.conversation_round += 1
        
        # Extract information
        extracted_info = self.extract_information_from_message(session_id, user_message)
        
        # Build context information
        context_info = {
            "collected_information": self._format_collected_info(memory),
            "missing_information": self._format_missing_info(memory),
            "recent_questions": memory.last_questions[-2:] if memory.last_questions else [],
            "conversation_round": memory.conversation_round,
            "current_stage": memory.stage.value
        }
        
        # Generate anti-repetition instructions
        avoid_repetition_instruction = self._generate_avoid_repetition_instruction(memory)
        
        return f"""
## CONVERSATION MEMORY CONTEXT
{json.dumps(context_info, ensure_ascii=False, indent=2)}

## CRITICAL ANTI-REPETITION INSTRUCTIONS
{avoid_repetition_instruction}

## NEWLY EXTRACTED INFORMATION
{json.dumps(extracted_info, ensure_ascii=False, indent=2) if extracted_info else "No new information"}

## CURRENT USER MESSAGE
{user_message}
"""
    
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
        
        # Add next step suggestions
        next_questions = self.get_next_questions(memory.session_id, max_questions=2)
        if next_questions:
            instructions.append(f"➡️ NEXT QUESTIONS TO ASK: {next_questions}")
        else:
            instructions.append("➡️ INFORMATION COLLECTION COMPLETE - PROCEED TO PRODUCT MATCHING")
        
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