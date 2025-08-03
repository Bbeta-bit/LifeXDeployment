# app/config/config.py
import os
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class LenderConfig:
    """Configuration for each lender"""
    name: str
    file_path: str
    enabled: bool = True
    priority: int = 1  # Lower number = higher priority

@dataclass
class MVPFieldConfig:
    """Configuration for MVP fields"""
    field_name: str
    field_type: str  # "string", "number", "boolean", "enum"
    required: bool
    priority: int
    options: List[str] = None  # For enum types
    validation_rules: Dict = None

@dataclass
class ConversationConfig:
    """Configuration for conversation flow"""
    max_ask_attempts: int = 2
    max_conversation_rounds: int = 10
    fields_per_question: int = 2
    enable_gap_analysis: bool = True
    enable_payment_calculation: bool = True

class SystemConfig:
    """Main system configuration"""
    
    def __init__(self):
        self.version = "2.0"
        self.app_name = "Multi-Lender Loan AI Agent"
        
        # Lender configurations
        self.lenders = {
            "angle": LenderConfig(
                name="Angle",
                file_path="docs/Angle.md",
                enabled=True,
                priority=1
            ),
            "bfs": LenderConfig(
                name="BFS", 
                file_path="docs/BFS.md",
                enabled=True,
                priority=2
            ),
            "fcau": LenderConfig(
                name="FCAU",
                file_path="docs/FCAU.md", 
                enabled=True,
                priority=3
            ),
            "raf": LenderConfig(
                name="RAF",
                file_path="docs/RAF.md",
                enabled=True,
                priority=4
            )
        }
        
        # MVP field configurations
        self.mvp_fields = {
            # Core MVP fields (must collect)
            "loan_type": MVPFieldConfig(
                field_name="loan_type",
                field_type="enum",
                required=True,
                priority=1,
                options=["commercial", "consumer"],
                validation_rules={"not_empty": True}
            ),
            "asset_type": MVPFieldConfig(
                field_name="asset_type", 
                field_type="enum",
                required=True,
                priority=2,
                options=["primary", "secondary", "tertiary", "motor_vehicle"],
                validation_rules={"not_empty": True}
            ),
            "property_status": MVPFieldConfig(
                field_name="property_status",
                field_type="enum", 
                required=True,
                priority=3,
                options=["property_owner", "non_property_owner"],
                validation_rules={"not_empty": True}
            ),
            "ABN_years": MVPFieldConfig(
                field_name="ABN_years",
                field_type="number",
                required=True,
                priority=4,
                validation_rules={"min": 0, "max": 50, "integer": True}
            ),
            "GST_years": MVPFieldConfig(
                field_name="GST_years", 
                field_type="number",
                required=True,
                priority=5,
                validation_rules={"min": 0, "max": 50, "integer": True}
            ),
            
            # Additional MVP fields (important for matching)
            "credit_score": MVPFieldConfig(
                field_name="credit_score",
                field_type="number",
                required=False,
                priority=6,
                validation_rules={"min": 300, "max": 900, "integer": True}
            ),
            "desired_loan_amount": MVPFieldConfig(
                field_name="desired_loan_amount",
                field_type="number", 
                required=False,
                priority=7,
                validation_rules={"min": 5000, "max": 10000000}
            ),
            "loan_term_preference": MVPFieldConfig(
                field_name="loan_term_preference",
                field_type="number",
                required=False,
                priority=8,
                validation_rules={"min": 1, "max": 30, "integer": True}
            ),
            
            # Asset-specific fields
            "vehicle_type": MVPFieldConfig(
                field_name="vehicle_type",
                field_type="enum",
                required=False,
                priority=9,
                options=["passenger_car", "light_truck", "van_ute", "motorcycle", "motorhome", "caravan", "heavy_truck"],
                validation_rules={"conditional": "asset_type == 'motor_vehicle'"}
            ),
            "vehicle_condition": MVPFieldConfig(
                field_name="vehicle_condition",
                field_type="enum",
                required=False, 
                priority=10,
                options=["new", "demonstrator", "used"],
                validation_rules={"conditional": "asset_type == 'motor_vehicle'"}
            ),
            
            # Business-specific fields
            "business_structure": MVPFieldConfig(
                field_name="business_structure",
                field_type="enum",
                required=False,
                priority=11,
                options=["sole_trader", "company", "trust", "partnership"],
                validation_rules={"conditional": "loan_type == 'commercial'"}
            ),
            "business_years_operating": MVPFieldConfig(
                field_name="business_years_operating",
                field_type="number",
                required=False,
                priority=12,
                validation_rules={"min": 0, "max": 100, "integer": True}
            )
        }
        
        # Preference configurations
        self.preferences = {
            "interest_rate_ceiling": {
                "name": "Maximum acceptable interest rate",
                "type": "number",
                "unit": "percentage",
                "validation": {"min": 1.0, "max": 30.0}
            },
            "monthly_budget": {
                "name": "Maximum monthly payment budget", 
                "type": "number",
                "unit": "currency",
                "validation": {"min": 100, "max": 100000}
            },
            "min_loan_amount": {
                "name": "Minimum loan amount needed",
                "type": "number", 
                "unit": "currency",
                "validation": {"min": 5000, "max": 10000000}
            },
            "preferred_term": {
                "name": "Preferred loan term",
                "type": "number",
                "unit": "years", 
                "validation": {"min": 1, "max": 30}
            },
            "repayment_type_preference": {
                "name": "Repayment type preference",
                "type": "enum",
                "options": ["principal_and_interest", "interest_only", "balloon"],
                "validation": {}
            },
            "early_repay_ok": {
                "name": "Early repayment flexibility important",
                "type": "boolean",
                "validation": {}
            },
            "documentation_preference": {
                "name": "Documentation preference", 
                "type": "enum",
                "options": ["low_doc", "full_doc", "no_preference"],
                "validation": {}
            }
        }
        
        # Conversation flow configuration
        self.conversation = ConversationConfig()
        
        # API configurations
        self.api = {
            "openrouter": {
                "api_key_env": "OPENROUTER_API_KEY",
                "base_url": "https://openrouter.ai/api/v1/chat/completions",
                "model": "google/gemini-2.0-flash-exp:free",
                "temperature": 0.7,
                "max_tokens": 1500
            },
            "cors_origins": [
                "http://localhost:5173",
                "https://cmap-frontend.onrender.com", 
                "https://*.onrender.com"
            ]
        }
        
        # Product matching configurations
        self.matching = {
            "hard_match_weight": 1.0,
            "soft_match_weight": 0.3,
            "max_recommendations": 3,
            "gap_analysis_threshold": 2,  # Max gaps to show alternative products
            "enable_relaxed_matching": True,
            "calculation_precision": 2  # Decimal places for financial calculations
        }
        
        # File paths
        self.file_paths = {
            "main_prompt": "docs/promptv29.md",
            "lender_docs": "docs/",
            "log_directory": "logs/",
            "cache_directory": "cache/"
        }
        
        # Feature flags
        self.features = {
            "enable_payment_calculation": True,
            "enable_comparison_rate": True,
            "enable_gap_analysis": True,
            "enable_multi_lender_comparison": True,
            "enable_rate_loadings": True,
            "enable_documentation_matching": True,
            "enable_conversation_memory": True,
            "enable_preference_learning": True
        }
        
        # Logging configuration
        self.logging = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_rotation": "midnight",
            "retention_days": 30
        }
    
    def get_core_mvp_fields(self) -> List[str]:
        """Get list of core MVP fields that must be collected"""
        return [field_name for field_name, config in self.mvp_fields.items() 
                if config.required]
    
    def get_additional_mvp_fields(self) -> List[str]:
        """Get list of additional MVP fields"""
        return [field_name for field_name, config in self.mvp_fields.items() 
                if not config.required]
    
    def get_mvp_fields_by_priority(self) -> List[str]:
        """Get MVP fields sorted by priority"""
        return sorted(self.mvp_fields.keys(), 
                     key=lambda x: self.mvp_fields[x].priority)
    
    def get_enabled_lenders(self) -> List[str]:
        """Get list of enabled lenders"""
        return [lender_name for lender_name, config in self.lenders.items() 
                if config.enabled]
    
    def get_lenders_by_priority(self) -> List[str]:
        """Get lenders sorted by priority"""
        return sorted([name for name, config in self.lenders.items() if config.enabled],
                     key=lambda x: self.lenders[x].priority)
    
    def validate_mvp_field(self, field_name: str, value: any) -> Dict[str, any]:
        """Validate MVP field value against configuration"""
        if field_name not in self.mvp_fields:
            return {"valid": False, "error": f"Unknown field: {field_name}"}
        
        config = self.mvp_fields[field_name]
        validation_rules = config.validation_rules or {}
        
        # Type validation
        if config.field_type == "number":
            try:
                value = float(value)
                if validation_rules.get("integer", False):
                    value = int(value)
            except (ValueError, TypeError):
                return {"valid": False, "error": f"{field_name} must be a number"}
        
        elif config.field_type == "enum":
            if value not in config.options:
                return {"valid": False, "error": f"{field_name} must be one of: {config.options}"}
        
        # Range validation
        if "min" in validation_rules and value < validation_rules["min"]:
            return {"valid": False, "error": f"{field_name} must be at least {validation_rules['min']}"}
        
        if "max" in validation_rules and value > validation_rules["max"]:
            return {"valid": False, "error": f"{field_name} must be at most {validation_rules['max']}"}
        
        return {"valid": True, "value": value}
    
    def get_questions_for_fields(self, field_names: List[str]) -> Dict[str, str]:
        """Get user-friendly questions for MVP fields"""
        questions = {
            "loan_type": "Is this loan for business/commercial use or personal use?",
            "asset_type": "What type of asset are you looking to finance?",
            "property_status": "Do you currently own property?", 
            "ABN_years": "How many years has your ABN been registered?",
            "GST_years": "How many years have you been registered for GST? (Enter 0 if not registered)",
            "credit_score": "What is your current credit score?",
            "desired_loan_amount": "How much are you looking to borrow?",
            "loan_term_preference": "What loan term would you prefer (in years)?",
            "vehicle_type": "What type of vehicle are you financing?",
            "vehicle_condition": "Is the vehicle new, demonstrator, or used?",
            "business_structure": "How is your business structured?",
            "business_years_operating": "How many years has your business been operating?"
        }
        
        return {field: questions.get(field, f"Please provide {field}") 
                for field in field_names}


# Global configuration instance
config = SystemConfig()

# Environment-specific overrides
def load_environment_config():
    """Load environment-specific configuration overrides"""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        config.logging["level"] = "WARNING"
        config.api["max_tokens"] = 2000
        config.conversation.max_conversation_rounds = 15
    
    elif env == "staging":
        config.logging["level"] = "DEBUG"
        config.features["enable_conversation_memory"] = True
    
    elif env == "development":
        config.logging["level"] = "DEBUG"
        config.api["temperature"] = 0.8  # More creative for testing

# Load environment config on import
load_environment_config()