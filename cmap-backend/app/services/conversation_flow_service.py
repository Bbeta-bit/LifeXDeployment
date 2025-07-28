from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

class ConversationStage(Enum):
    GREETING = "greeting"
    MVP_COLLECTION = "mvp_collection"
    PREFERENCE_COLLECTION = "preference_collection"
    PRODUCT_MATCHING = "product_matching"
    GAP_ANALYSIS = "gap_analysis"
    REFINEMENT = "refinement"
    FINAL_RECOMMENDATION = "final_recommendation"
    HANDOFF = "handoff"

@dataclass
class ConversationState:
    stage: ConversationStage
    mvp_fields: Dict[str, Any]
    missing_mvp_fields: List[str]
    preferences: Dict[str, Any]
    missing_preferences: List[str]
    ask_attempts: Dict[str, int]
    matched_products: List[Dict[str, Any]]
    gaps: List[str]
    conversation_round: int

class ConversationFlowService:
    """Manages the entire conversation flow service"""
    
    def __init__(self):
        self.mvp_fields = [
            "loan_type", "asset_type", "property_status", 
            "ABN_years", "GST_years"
        ]
        
        self.preference_options = {
            "interest_rate_ceiling": "Maximum acceptable interest rate",
            "monthly_budget": "Maximum monthly payment budget",
            "preferred_term": "Preferred loan term",
            "min_loan_amount": "Minimum loan amount needed"
        }
        
        self.max_ask_attempts = 2
        self.max_conversation_rounds = 8
    
    def init_conversation_state(self) -> ConversationState:
        """Initialize conversation state"""
        return ConversationState(
            stage=ConversationStage.GREETING,
            mvp_fields={},
            missing_mvp_fields=self.mvp_fields.copy(),
            preferences={},
            missing_preferences=[],
            ask_attempts={},
            matched_products=[],
            gaps=[],
            conversation_round=0
        )
    
    def update_conversation_state(self, 
                                state: ConversationState, 
                                extracted_info: Dict[str, Any]) -> ConversationState:
        """Update conversation state based on extracted information"""
        
        # Update MVP fields
        for field in self.mvp_fields:
            if field in extracted_info and extracted_info[field] is not None:
                state.mvp_fields[field] = extracted_info[field]
                if field in state.missing_mvp_fields:
                    state.missing_mvp_fields.remove(field)
        
        # Update preference fields
        for field in self.preference_options.keys():
            if field in extracted_info and extracted_info[field] is not None:
                state.preferences[field] = extracted_info[field]
                if field in state.missing_preferences:
                    state.missing_preferences.remove(field)
        
        # Determine next stage
        new_stage = self._determine_next_stage(state)
        
        # Only advance stage if we're progressing forward
        if self._stage_order(new_stage) > self._stage_order(state.stage):
            state.stage = new_stage
        
        return state
    
    def _stage_order(self, stage: ConversationStage) -> int:
        """Return numeric order of stages"""
        order = {
            ConversationStage.GREETING: 1,
            ConversationStage.MVP_COLLECTION: 2,
            ConversationStage.PREFERENCE_COLLECTION: 3,
            ConversationStage.PRODUCT_MATCHING: 4,
            ConversationStage.GAP_ANALYSIS: 5,
            ConversationStage.REFINEMENT: 6,
            ConversationStage.FINAL_RECOMMENDATION: 7,
            ConversationStage.HANDOFF: 8
        }
        return order.get(stage, 0)
    
    def _determine_next_stage(self, state: ConversationState) -> ConversationStage:
        """Determine next conversation stage"""
        
        # Check if we should move to handoff due to too many rounds
        if state.conversation_round >= self.max_conversation_rounds:
            return ConversationStage.HANDOFF
        
        # If we're in greeting and have some info, move to MVP collection
        if state.stage == ConversationStage.GREETING and state.mvp_fields:
            return ConversationStage.MVP_COLLECTION
        
        # MVP collection logic
        if state.missing_mvp_fields:
            # Check if we've exceeded max attempts for remaining fields
            remaining_fields = []
            for field in state.missing_mvp_fields:
                if state.ask_attempts.get(field, 0) < self.max_ask_attempts:
                    remaining_fields.append(field)
            
            state.missing_mvp_fields = remaining_fields
            
            if remaining_fields:
                return ConversationStage.MVP_COLLECTION
        
        # If MVP is complete and we haven't collected preferences yet
        if (not state.missing_mvp_fields and 
            state.stage in [ConversationStage.GREETING, ConversationStage.MVP_COLLECTION] and
            not state.preferences):
            return ConversationStage.PREFERENCE_COLLECTION
        
        # If we've asked about preferences or user has provided them, move to matching
        if (state.stage == ConversationStage.PREFERENCE_COLLECTION and 
            (state.preferences or state.conversation_round > 2)):
            return ConversationStage.PRODUCT_MATCHING
        
        # Handle product matching results
        if state.stage == ConversationStage.PRODUCT_MATCHING:
            if state.gaps:
                return ConversationStage.GAP_ANALYSIS
            elif state.matched_products:
                return ConversationStage.FINAL_RECOMMENDATION
        
        # If we're in gap analysis and user responds, try refinement
        if state.stage == ConversationStage.GAP_ANALYSIS:
            return ConversationStage.REFINEMENT
        
        # Default: stay in current stage
        return state.stage
    
    def should_collect_preferences(self, state: ConversationState) -> bool:
        """Check if we should collect preferences now"""
        return (len(state.missing_mvp_fields) == 0 and 
                state.stage == ConversationStage.PREFERENCE_COLLECTION and
                not state.preferences)
    
    def is_mvp_complete(self, state: ConversationState) -> bool:
        """Check if MVP collection is complete"""
        return len(state.missing_mvp_fields) == 0
    
    def get_next_mvp_fields_to_ask(self, state: ConversationState, max_fields: int = 2) -> List[str]:
        """Get the next MVP fields to ask about"""
        fields_to_ask = []
        
        for field in state.missing_mvp_fields:
            if (state.ask_attempts.get(field, 0) < self.max_ask_attempts and 
                len(fields_to_ask) < max_fields):
                fields_to_ask.append(field)
                # Increment attempt counter
                state.ask_attempts[field] = state.ask_attempts.get(field, 0) + 1
        
        return fields_to_ask
    
    def generate_mvp_questions(self, fields: List[str]) -> Dict[str, str]:
        """Generate questions for MVP fields"""
        questions = {
            "loan_type": "Is this for commercial/business use or personal use?",
            "asset_type": "What type of asset are you looking to finance? (Primary equipment, secondary equipment, or vehicle)",
            "property_status": "Do you currently own property?",
            "ABN_years": "How many years has your ABN been registered?",
            "GST_years": "How many years have you been registered for GST?"
        }
        
        return {field: questions.get(field, f"Could you provide information about {field}?") 
                for field in fields}
    
    def format_preference_collection_prompt(self) -> str:
        """Generate the preference collection prompt"""
        return """Perfect! I have all the essential information I need. 

To provide you with the most suitable loan recommendations, I'd like to understand 1-2 of your key preferences. Please choose from the following options:

① **Maximum interest rate** - What's the highest interest rate you'd be comfortable with? (e.g., "no more than 8%")
② **Monthly payment budget** - What's your maximum monthly payment limit? (e.g., "no more than $5,000 per month")  
③ **Loan term preference** - How long would you prefer the loan term to be? (e.g., "5 years maximum")
④ **Minimum loan amount** - What's the minimum amount you need to borrow? (e.g., "at least $200,000")

You can tell me 1-2 of these that are most important to you, or say "no specific preferences" if you'd like me to show you all available options."""
    
    def get_conversation_context(self, state: ConversationState) -> Dict[str, Any]:
        """Get current conversation context for other services"""
        return {
            "stage": state.stage.value,
            "mvp_fields": state.mvp_fields,
            "missing_mvp_fields": state.missing_mvp_fields,
            "preferences": state.preferences,
            "conversation_round": state.conversation_round,
            "gaps": state.gaps,
            "matched_products": state.matched_products,
            "is_mvp_complete": self.is_mvp_complete(state),
            "should_collect_preferences": self.should_collect_preferences(state)
        }