import os
from typing import Dict, Any, List, Optional
from enum import Enum

class ConversationStage(Enum):
    GREETING = "greeting"
    MVP_COLLECTION = "mvp_collection"
    PREFERENCE_COLLECTION = "preference_collection"
    PRODUCT_MATCHING = "product_matching"
    GAP_ANALYSIS = "gap_analysis"
    REFINEMENT = "refinement"
    FINAL_RECOMMENDATION = "final_recommendation"
    HANDOFF = "handoff"

class EnhancedPromptService:
    def __init__(self):
        self.product_info = self._load_product_info()
        self.mvp_fields = {
            "loan_type": "commercial or consumer loan",
            "asset_type": "primary, secondary, or tertiary asset",
            "property_status": "property owner or non-property owner",
            "ABN_years": "number of years ABN registered",
            "GST_years": "number of years GST registered"
        }
        
        self.preference_options = {
            "interest_rate_ceiling": "maximum acceptable interest rate",
            "monthly_budget": "maximum monthly payment budget",
            "preferred_term": "preferred loan term in years",
            "min_loan_amount": "minimum loan amount needed"
        }
    
    def _load_product_info(self) -> str:
        """Load product information from markdown file"""
        try:
            product_file_path = os.path.join("docs", "products.md")
            with open(product_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print("Product information is updating...")
            return "Product information is updating..."
    
    def create_system_prompt(self, stage: ConversationStage, context: Dict[str, Any] = None) -> str:
        """Create dynamic system prompt based on conversation stage"""
        
        if context is None:
            context = {}
        
        base_prompt = f"""You are a professional loan advisor AI assistant. Your current task is determined by the conversation stage: {stage.value}.

## Product Information:
{self.product_info}

## CRITICAL COMMUNICATION RULES:
1. NEVER repeat back information the customer has already provided
2. NEVER use filler phrases like "Thanks for letting me know", "That's great", "As you mentioned"
3. Be DIRECT and EFFICIENT - ask only what you need to know
4. Do NOT ask process-related questions beyond MVP and preferences
5. Focus ONLY on current stage requirements
6. Keep responses concise and action-oriented

## Your Role and Responsibilities:
1. Follow the structured conversation flow strictly
2. Collect MVP information systematically (allow some missing fields)
3. Collect 1-2 key preferences only
4. Recommend the LOWEST RATE product that matches customer requirements
5. Provide complete product details with calculations when recommending

"""
        
        if stage == ConversationStage.GREETING:
            return base_prompt + """
## Current Stage: GREETING
Your task: Begin MVP information collection immediately.

Guidelines:
- Ask about their loan needs directly
- Start collecting MVP information right away
- Do NOT waste time with lengthy greetings
- Move to MVP collection quickly
"""
        
        elif stage == ConversationStage.MVP_COLLECTION:
            missing_fields = context.get('missing_mvp_fields', [])
            collected_fields = context.get('mvp_fields', {})
            
            return base_prompt + f"""
## Current Stage: MVP COLLECTION
Your task: Collect MVP fields efficiently. ALLOW SOME MISSING FIELDS.

MVP Fields Status:
- Collected: {list(collected_fields.keys())}
- Still Missing: {missing_fields}

CRITICAL INSTRUCTIONS:
- Do NOT repeat back any information customer already provided
- Be DIRECT: "What is your credit score?" (NOT "Thanks for that info, what's your credit score?")
- Do NOT ask about loan process, documentation, or application steps
- You can proceed to preferences even if some MVP fields are missing
- Focus on core fields: loan_type, credit_score, desired_loan_amount

Example responses:
✅ "What is your credit score?"
✅ "Are you a property owner?"
❌ "Thanks for telling me about your business! A credit score of 700 is excellent. What's your ABN?"
❌ "That's great information. Can you also tell me about your property status?"
"""
        
        elif stage == ConversationStage.PREFERENCE_COLLECTION:
            collected_mvp = context.get('mvp_fields', {})
            
            return base_prompt + f"""
## Current Stage: PREFERENCE COLLECTION
Your task: Collect 1-2 key preferences quickly.

Current MVP: {collected_mvp}

INSTRUCTIONS:
- Ask for maximum 2 preferences
- Do NOT explain why you need preferences
- Present options concisely
- Accept if customer wants to skip preferences

Say: "What matters most to you: maximum interest rate, monthly payment budget, loan term, or minimum loan amount? Pick 1-2 or say 'show me options'."

Do NOT say lengthy explanations about why preferences help.
"""
        
        elif stage == ConversationStage.PRODUCT_MATCHING:
            mvp_data = context.get('mvp_fields', {})
            preferences = context.get('preferences', {})
            
            return base_prompt + f"""
## Current Stage: PRODUCT MATCHING
Your task: Find and recommend the LOWEST RATE product that matches requirements.

Customer Profile:
- MVP Data: {mvp_data}
- Preferences: {preferences}

RECOMMENDATION REQUIREMENTS:
1. Find ALL products customer qualifies for across all 4 lenders
2. Recommend the ONE with the LOWEST BASE RATE
3. Include complete product information:
   - [Lender Name] - [Product Name]
   - Base Rate and Comparison Rate (calculated)
   - Monthly payment (if loan amount and term available)
   - All fees breakdown
   - All requirements and eligibility status
   - Complete product details from database

INSTRUCTIONS:
- Present ONE best recommendation (lowest rate)
- Show complete calculations
- List all requirements clearly
- Do NOT ask follow-up questions about the recommendation
- Do NOT ask about application process or next steps
"""
        
        elif stage == ConversationStage.GAP_ANALYSIS:
            gaps = context.get('gaps', [])
            
            return base_prompt + f"""
## Current Stage: GAP ANALYSIS
Your task: Address requirement gaps briefly.

Identified Gaps: {gaps}

INSTRUCTIONS:
- Explain gaps clearly and concisely
- Suggest practical solutions
- Do NOT ask unnecessary follow-up questions
- Keep it brief and actionable
"""
        
        elif stage == ConversationStage.FINAL_RECOMMENDATION:
            return base_prompt + """
## Current Stage: FINAL RECOMMENDATION
Your task: Provide final recommendation only.

INSTRUCTIONS:
- Summarize the recommended product
- Include all calculated details
- Do NOT ask about application process
- Do NOT ask about next steps
- Keep it concise and complete
"""
        
        elif stage == ConversationStage.HANDOFF:
            return base_prompt + """
## Current Stage: HANDOFF
Your task: Transfer to specialist briefly.

INSTRUCTIONS:
- Brief handoff message
- Summarize key points
- Do NOT ask additional questions
"""
        
        return base_prompt + """
## Current Stage: GENERAL CONVERSATION
Your task: Provide helpful information concisely.

INSTRUCTIONS:
- Answer questions directly
- Do NOT repeat customer information
- Keep responses brief and focused
"""
    
    def create_chat_messages(self, user_message: str, stage: ConversationStage, 
                           context: Dict[str, Any] = None, chat_history: list = None) -> list:
        """Create complete chat message list with stage-specific system prompt"""
        
        messages = [
            {"role": "system", "content": self.create_system_prompt(stage, context)}
        ]
        
        # Add chat history to maintain memory
        if chat_history:
            for chat in chat_history:
                if "user" in chat and "assistant" in chat:
                    messages.append({"role": "user", "content": chat["user"]})
                    messages.append({"role": "assistant", "content": chat["assistant"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def extract_user_requirements(self, user_message: str) -> Dict[str, Any]:
        """Extract key information from user message"""
        requirements = {
            "loan_amount": None,
            "credit_score": None,
            "business_age": None,
            "property_owner": None,
            "preferences": {}
        }
        
        message_lower = user_message.lower()
        
        # Extract loan amount
        import re
        amount_patterns = [
            r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*k(?:ey|\b)',
            r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*thousand',
            r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, message_lower)
            if match:
                amount_str = match.group(1).replace(',', '')
                amount = float(amount_str)
                if 'k' in match.group(0) or 'thousand' in match.group(0):
                    amount *= 1000
                requirements["loan_amount"] = amount
                break
        
        # Extract interest rate preferences
        rate_patterns = [
            r'(\d+(?:\.\d+)?)\s*%?\s*(?:interest|rate)',
            r'(?:rate|interest).*?(\d+(?:\.\d+)?)\s*%',
            r'under\s+(\d+(?:\.\d+)?)\s*%',
            r'below\s+(\d+(?:\.\d+)?)\s*%',
            r'maximum.*?(\d+(?:\.\d+)?)\s*%'
        ]
        
        for pattern in rate_patterns:
            match = re.search(pattern, message_lower)
            if match:
                rate = float(match.group(1))
                if 1 <= rate <= 25:  # Reasonable rate range
                    requirements["preferences"]["interest_rate_ceiling"] = rate
                break
        
        return requirements