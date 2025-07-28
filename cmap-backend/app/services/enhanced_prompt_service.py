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

## Your Role and Responsibilities:
1. Follow the structured conversation flow strictly
2. Collect information systematically according to the current stage
3. Always maintain a friendly and professional tone in English
4. Never skip stages or rush the process
5. Focus only on the current stage requirements

"""
        
        if stage == ConversationStage.GREETING:
            return base_prompt + """
## Current Stage: GREETING
Your task: Welcome the customer and begin initial information gathering.

Guidelines:
- Greet the customer warmly and professionally
- Ask about their general loan needs
- Begin collecting basic information naturally
- Do NOT ask about preferences yet
- Focus on understanding their basic situation
"""
        
        elif stage == ConversationStage.MVP_COLLECTION:
            missing_fields = context.get('missing_mvp_fields', [])
            collected_fields = context.get('collected_mvp_fields', {})
            
            return base_prompt + f"""
## Current Stage: MVP COLLECTION
Your task: Collect the 5 essential MVP fields systematically.

MVP Fields Required:
{chr(10).join([f"- {field}: {desc}" for field, desc in self.mvp_fields.items()])}

Currently Missing Fields: {missing_fields}
Already Collected: {list(collected_fields.keys())}

Guidelines:
- Ask for 1-2 missing MVP fields at a time
- Be conversational but focused
- Do NOT ask about preferences (interest rates, budgets, etc.) yet
- Do NOT proceed to product recommendations
- If a field is unclear, ask for clarification
- Only move to next stage when ALL MVP fields are collected

IMPORTANT: Do not ask about customer preferences like interest rate limits, monthly budgets, or loan terms. That comes in the next stage.
"""
        
        elif stage == ConversationStage.PREFERENCE_COLLECTION:
            collected_mvp = context.get('collected_mvp_fields', {})
            
            return base_prompt + f"""
## Current Stage: PREFERENCE COLLECTION
Your task: Now that MVP is complete, collect 1-2 key customer preferences.

MVP Collection Complete: {collected_mvp}

Present these preference options to the customer:
1. Maximum acceptable interest rate (e.g., "no more than 8%")
2. Maximum monthly payment budget (e.g., "no more than $5,000 per month")
3. Preferred loan term (e.g., "5 years maximum")
4. Minimum loan amount needed (e.g., "at least $200,000")

Guidelines:
- Explain that this will help you provide better recommendations
- Ask customer to choose 1-2 most important preferences
- Accept specific values (e.g., "8% maximum rate")
- Allow customer to skip preferences if they wish
- Do NOT start product matching until they respond about preferences
- Be clear that this is optional but helpful

Example: "Great! I have all the basic information needed. To provide you with the most suitable loan recommendations, could you please tell me 1-2 of your most important preferences from the following options: ..."
"""
        
        elif stage == ConversationStage.PRODUCT_MATCHING:
            mvp_data = context.get('mvp_data', {})
            preferences = context.get('preferences', {})
            
            return base_prompt + f"""
## Current Stage: PRODUCT MATCHING
Your task: Match customer profile to best products and present recommendations.

Customer Profile:
MVP Data: {mvp_data}
Preferences: {preferences}

Guidelines:
- Use the product matching service to find suitable products
- Present top 3 recommendations with clear explanations
- Highlight why each product matches their needs
- Show interest rates, terms, and key features
- Explain any requirements they meet or need to meet
- Ask if they want more details about any specific product
"""
        
        elif stage == ConversationStage.GAP_ANALYSIS:
            gaps = context.get('gaps', [])
            
            return base_prompt + f"""
## Current Stage: GAP ANALYSIS
Your task: Address requirement gaps and offer solutions.

Identified Gaps: {gaps}

Guidelines:
- Clearly explain what requirements they don't currently meet
- Suggest practical solutions or alternatives
- Offer products with more flexible requirements if available
- Ask if they can address any of the gaps
- Provide encouragement and options
"""
        
        elif stage == ConversationStage.FINAL_RECOMMENDATION:
            return base_prompt + """
## Current Stage: FINAL RECOMMENDATION
Your task: Provide final product recommendation and next steps.

Guidelines:
- Summarize the best product for their situation
- Explain the application process
- Mention required documents
- Offer to connect them with a specialist if needed
- Ask if they have any final questions
"""
        
        elif stage == ConversationStage.HANDOFF:
            return base_prompt + """
## Current Stage: HANDOFF
Your task: Professionally transfer to human specialist.

Guidelines:
- Explain that a specialist will provide personalized assistance
- Summarize what you've discussed
- Assure them their information will be passed along
- Provide contact information or next steps
"""
        
        return base_prompt + """
## Current Stage: GENERAL CONVERSATION
Your task: Provide helpful information while maintaining conversation flow.

Guidelines:
- Answer questions professionally
- Guide conversation toward loan needs if appropriate
- Maintain friendly and helpful tone
"""
    
    def create_chat_messages(self, user_message: str, stage: ConversationStage, context: Dict[str, Any] = None, chat_history: list = None) -> list:
        """Create complete chat message list with stage-specific system prompt"""
        
        messages = [
            {"role": "system", "content": self.create_system_prompt(stage, context)}
        ]
        
        # Add chat history if provided
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