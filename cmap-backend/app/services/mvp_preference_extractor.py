# app/services/mvp_preference_extractor.py
import json
import re
import os
import httpx
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path="API.env")

class MVPPreferenceExtractor:
    """Enhanced extractor specifically focused on MVP fields and preferences"""
    
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.mvp_fields = {
            "loan_type": ["commercial", "business", "company", "corporate", "consumer", "personal", "individual"],
            "asset_type": ["primary", "secondary", "tertiary", "equipment", "vehicle", "car", "truck", "machinery"],
            "property_status": ["property owner", "own property", "have property", "non-property", "no property", "rent"],
            "ABN_years": ["ABN", "Australian Business Number", "business number", "years registered"],
            "GST_years": ["GST", "goods and services tax", "tax registered", "GST registered"]
        }
        
        self.preference_keywords = {
            "interest_rate_ceiling": ["rate", "interest", "maximum rate", "no more than", "under", "below"],
            "monthly_budget": ["monthly", "payment", "budget", "afford", "per month", "monthly payment"],
            "preferred_term": ["term", "years", "duration", "length", "period"],
            "min_loan_amount": ["amount", "borrow", "loan", "minimum", "at least", "need"]
        }
    
    async def extract_mvp_and_preferences(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract MVP fields and preferences from conversation"""
        
        # Try AI extraction first
        ai_result = await self._ai_extract_mvp_preferences(conversation_history)
        
        # Fallback to rule-based extraction
        rule_result = self._rule_based_extract_mvp_preferences(conversation_history)
        
        # Merge results
        merged_result = self._merge_extraction_results(ai_result, rule_result)
        
        return merged_result
    
    async def _ai_extract_mvp_preferences(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Use AI to extract MVP and preferences"""
        try:
            conversation_text = self._build_conversation_text(conversation_history)
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            }

            system_prompt = """You are an expert at extracting loan application information. Extract MVP fields and customer preferences from the conversation.

Return ONLY a JSON object with this exact structure:
{
    "mvp_fields": {
        "loan_type": "commercial" or "consumer" or null,
        "asset_type": "primary" or "secondary" or "tertiary" or null,
        "property_status": "property_owner" or "non_property_owner" or null,
        "ABN_years": number or null,
        "GST_years": number or null
    },
    "preferences": {
        "interest_rate_ceiling": number or null,
        "monthly_budget": number or null,
        "preferred_term": number or null,
        "min_loan_amount": number or null
    }
}

Extraction rules:
- loan_type: "commercial" if for business/company use, "consumer" if for personal use
- asset_type: "primary" for main equipment/vehicles, "secondary" for older equipment, "tertiary" for very old/basic
- property_status: "property_owner" if they own property, "non_property_owner" if they don't
- ABN_years: number of years ABN registered
- GST_years: number of years GST registered
- interest_rate_ceiling: maximum acceptable interest rate as percentage (e.g., 8.5)
- monthly_budget: maximum monthly payment amount
- preferred_term: preferred loan term in years
- min_loan_amount: minimum loan amount needed

Only extract explicitly mentioned information. Use null for missing data."""

            payload = {
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract MVP and preferences from:\n\n{conversation_text}"}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    return {"mvp_fields": {}, "preferences": {}}

                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
                # Clean and parse JSON
                clean_response = ai_response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:-3]
                elif clean_response.startswith('```'):
                    clean_response = clean_response[3:-3]
                
                extracted_data = json.loads(clean_response)
                return extracted_data
                
        except Exception as e:
            print(f"AI extraction failed: {e}")
            return {"mvp_fields": {}, "preferences": {}}
    
    def _rule_based_extract_mvp_preferences(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Rule-based extraction as fallback"""
        conversation_text = " ".join([msg.get("content", "") for msg in conversation_history]).lower()
        
        mvp_fields = {}
        preferences = {}
        
        # Extract loan type
        if any(word in conversation_text for word in ["business", "company", "commercial", "corporate"]):
            mvp_fields["loan_type"] = "commercial"
        elif any(word in conversation_text for word in ["personal", "individual", "private"]):
            mvp_fields["loan_type"] = "consumer"
        
        # Extract asset type
        if any(word in conversation_text for word in ["new", "latest", "primary", "main"]):
            mvp_fields["asset_type"] = "primary"
        elif any(word in conversation_text for word in ["secondary", "older", "used"]):
            mvp_fields["asset_type"] = "secondary"
        elif any(word in conversation_text for word in ["tertiary", "old", "basic"]):
            mvp_fields["asset_type"] = "tertiary"
        
        # Extract property status
        if any(phrase in conversation_text for phrase in ["own property", "have property", "property owner"]):
            mvp_fields["property_status"] = "property_owner"
        elif any(phrase in conversation_text for phrase in ["no property", "don't own", "rent", "renting"]):
            mvp_fields["property_status"] = "non_property_owner"
        
        # Extract ABN years
        abn_patterns = [
            r"abn.{0,20}?(\d+)\s*years?",
            r"(\d+)\s*years?.{0,20}?abn",
            r"registered.{0,10}?(\d+)\s*years?"
        ]
        for pattern in abn_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 50:
                    mvp_fields["ABN_years"] = years
                break
        
        # Extract GST years
        gst_patterns = [
            r"gst.{0,20}?(\d+)\s*years?",
            r"(\d+)\s*years?.{0,20}?gst"
        ]
        for pattern in gst_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                years = int(match.group(1))
                if 0 <= years <= 50:
                    mvp_fields["GST_years"] = years
                break
        
        # Extract interest rate preference
        rate_patterns = [
            r"(?:maximum|max|no more than|under|below).{0,20}?(\d+(?:\.\d+)?)\s*%?\s*(?:rate|interest)",
            r"(\d+(?:\.\d+)?)\s*%?\s*(?:maximum|max|limit)",
            r"interest.{0,20}?(\d+(?:\.\d+)?)\s*%"
        ]
        for pattern in rate_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                rate = float(match.group(1))
                if 1 <= rate <= 30:
                    preferences["interest_rate_ceiling"] = rate
                break
        
        # Extract monthly budget
        budget_patterns = [
            r"(?:monthly|per month).{0,20}?\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"\$?(\d+(?:,\d{3})*(?:\.\d{2})?).{0,20}?(?:monthly|per month)",
            r"afford.{0,20}?\$?(\d+(?:,\d{3})*(?:\.\d{2})?)"
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)
                if 100 <= amount <= 100000:
                    preferences["monthly_budget"] = amount
                break
        
        # Extract loan term preference
        term_patterns = [
            r"(\d+)\s*years?\s*(?:term|duration|period)",
            r"(?:term|duration|period).{0,20}?(\d+)\s*years?",
            r"over\s+(\d+)\s*years?"
        ]
        for pattern in term_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                years = int(match.group(1))
                if 1 <= years <= 30:
                    preferences["preferred_term"] = years
                break
        
        # Extract minimum loan amount
        amount_patterns = [
            r"(?:minimum|at least|need).{0,20}?\$?(\d+(?:,\d{3})*(?:\.\d{2})?)",
            r"\$?(\d+(?:,\d{3})*(?:\.\d{2})?).{0,20}?(?:minimum|at least)"
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, conversation_text)
            if match:
                amount_str = match.group(1).replace(",", "")
                amount = float(amount_str)
                if 1000 <= amount <= 10000000:
                    preferences["min_loan_amount"] = amount
                break
        
        return {"mvp_fields": mvp_fields, "preferences": preferences}
    
    def _merge_extraction_results(self, ai_result: Dict, rule_result: Dict) -> Dict[str, Any]:
        """Merge AI and rule-based extraction results"""
        merged = {"mvp_fields": {}, "preferences": {}}
        
        # Merge MVP fields - prefer AI result, fallback to rules
        for field in ["loan_type", "asset_type", "property_status", "ABN_years", "GST_years"]:
            ai_value = ai_result.get("mvp_fields", {}).get(field)
            rule_value = rule_result.get("mvp_fields", {}).get(field)
            
            if ai_value is not None:
                merged["mvp_fields"][field] = ai_value
            elif rule_value is not None:
                merged["mvp_fields"][field] = rule_value
        
        # Merge preferences - prefer AI result, fallback to rules
        for field in ["interest_rate_ceiling", "monthly_budget", "preferred_term", "min_loan_amount"]:
            ai_value = ai_result.get("preferences", {}).get(field)
            rule_value = rule_result.get("preferences", {}).get(field)
            
            if ai_value is not None:
                merged["preferences"][field] = ai_value
            elif rule_value is not None:
                merged["preferences"][field] = rule_value
        
        return merged
    
    def _build_conversation_text(self, conversation_history: List[Dict[str, str]]) -> str:
        """Build conversation text for AI processing"""
        conversation_text = ""
        for i, message in enumerate(conversation_history):
            role = message.get("role", "unknown")
            content = message.get("content", "")
            conversation_text += f"[{i+1}] {role.upper()}: {content}\n"
        
        return conversation_text