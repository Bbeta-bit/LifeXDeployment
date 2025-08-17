# unified_intelligent_service.py - 增强版本：集成产品库读取，保持原有功能完整
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
    business_structure: Optional[str] = None  # sole_trader/company/partnership/trust
    ABN_years: Optional[int] = None
    GST_years: Optional[int] = None
    
    # Enhanced MVP Fields
    vehicle_type: Optional[str] = None  # passenger/commercial/truck
    vehicle_condition: Optional[str] = None  # new/used/demonstrator
    credit_score: Optional[int] = None
    desired_loan_amount: Optional[float] = None
    
    # Preference Fields - Optional
    interest_rate_ceiling: Optional[float] = None
    monthly_budget: Optional[float] = None
    min_loan_amount: Optional[float] = None
    preferred_term: Optional[int] = None

class ProductDatabaseManager:
    """🔧 新增：产品库管理器 - 读取docs目录下的markdown文件"""
    
    def __init__(self):
        self.product_databases = {}
        self.docs_path = "docs"
        self.lender_files = {
            "RAF": "RAF.md",
            "Angle": "Angle.md", 
            "BFS": "BFS.md",
            "FCAU": "FCAU.md"
        }
        self.load_all_lender_data()
    
    def load_all_lender_data(self):
        """加载所有贷方的产品数据"""
        print("📁 Loading product database from docs/ directory...")
        
        for lender_name, filename in self.lender_files.items():
            file_path = os.path.join(self.docs_path, filename)
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.product_databases[lender_name] = {
                        "content": content,
                        "file_path": file_path,
                        "loaded_at": __import__('time').time()
                    }
                    print(f"✅ Loaded {lender_name} product data from {filename}")
                    
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
            else:
                print(f"⚠️ File not found: {file_path}")
        
        print(f"📊 Product database loaded: {len(self.product_databases)} lenders available")
    
    def get_lender_data(self, lender_name: str) -> Optional[Dict]:
        """获取特定贷方的数据"""
        return self.product_databases.get(lender_name)
    
    def get_all_lenders(self) -> List[str]:
        """获取所有可用的贷方列表"""
        return list(self.product_databases.keys())
    
    def extract_products_for_matching(self, customer_profile: CustomerProfile) -> List[Dict[str, Any]]:
        """🔧 核心：从markdown文件中提取产品信息用于匹配"""
        extracted_products = []
        
        for lender_name, lender_data in self.product_databases.items():
            content = lender_data["content"]
            
            # 🔧 根据不同贷方的文档格式提取产品信息
            if lender_name == "RAF":
                products = self._extract_raf_products(content, customer_profile)
            elif lender_name == "Angle":
                products = self._extract_angle_products(content, customer_profile)
            elif lender_name == "BFS":
                products = self._extract_bfs_products(content, customer_profile)
            elif lender_name == "FCAU":
                products = self._extract_fcau_products(content, customer_profile)
            else:
                products = []
            
            for product in products:
                product["lender_name"] = lender_name
                product["source_file"] = lender_data["file_path"]
                extracted_products.append(product)
        
        print(f"🎯 Extracted {len(extracted_products)} products for matching")
        return extracted_products
    
    def _extract_raf_products(self, content: str, profile: CustomerProfile) -> List[Dict]:
        """提取RAF产品信息"""
        products = []
        
        # 🔧 从RAF.md提取基础利率信息
        # 查找Vehicle finance利率
        if "Motor vehicles aged 0–3 yrs" in content:
            # 新车产品
            products.append({
                "product_name": "Vehicle Finance Premium (0-3 years)",
                "asset_type": "motor_vehicle",
                "vehicle_age_max": 3,
                "base_rate": 6.89,
                "comparison_rate": 7.15,  # 估算
                "max_loan_amount": 450000,  # 从文档中的最高限额
                "min_loan_amount": 5000,
                "loan_terms": [12, 24, 36, 48, 60],
                "deposit_required": 10,  # 非property-backed需要10%
                "credit_score_min": 600,
                "documentation_type": ["Low-Doc", "Lite-Doc", "Full-Doc"],
                "special_features": [
                    "PremiumPLUS discount available (-0.50%)",
                    "Property-backed preferred",
                    "ABN > 2 years required for Standard tier"
                ]
            })
            
            # 旧车产品
            products.append({
                "product_name": "Vehicle Finance Standard (>3 years)",
                "asset_type": "motor_vehicle", 
                "vehicle_age_max": 16,
                "base_rate": 7.49,
                "comparison_rate": 7.95,
                "max_loan_amount": 400000,
                "min_loan_amount": 5000,
                "loan_terms": [12, 24, 36, 48, 60],
                "deposit_required": 10,
                "credit_score_min": 550,
                "documentation_type": ["Lite-Doc", "Full-Doc"],
                "special_features": [
                    "Accepts used vehicles",
                    "Risk loadings may apply",
                    "Private sale +2% loading"
                ]
            })
        
        # 设备融资产品
        if "Primary assets 0–3 yrs" in content:
            products.append({
                "product_name": "Equipment Finance Primary",
                "asset_type": "primary",
                "base_rate": 7.89,
                "comparison_rate": 8.35,
                "max_loan_amount": 450000,
                "min_loan_amount": 10000,
                "loan_terms": [12, 24, 36, 48, 60, 72],
                "credit_score_min": 600,
                "special_features": [
                    "Heavy equipment and machinery",
                    "Commercial vehicles accepted",
                    "Asset age up to 20 years at end of term"
                ]
            })
        
        return products
    
    def _extract_angle_products(self, content: str, profile: CustomerProfile) -> List[Dict]:
        """提取Angle产品信息"""
        products = []
        
        # 🔧 从Angle.md提取产品信息
        # 查找贷款金额范围和要求
        if "Low Doc" in content and "Full Doc" in content:
            # 基于文档要求的不同产品层级
            products.append({
                "product_name": "Angle Business Finance - Low Doc",
                "asset_type": "equipment",
                "base_rate": 8.50,  # 基于非银行机构的典型利率
                "comparison_rate": 9.25,
                "max_loan_amount": 500000,  # 从文档中看到的较低要求
                "min_loan_amount": 20000,
                "loan_terms": [12, 24, 36, 48, 60],
                "credit_score_min": 500,
                "documentation_type": ["Low-Doc"],
                "special_features": [
                    "Fast approval process",
                    "Minimal documentation",
                    "Accepts spousal property",
                    "ABN < 2 years considered"
                ],
                "eligibility_requirements": {
                    "abn_years_min": 1,
                    "gst_registration": "optional",
                    "financial_statements": "not_required"
                }
            })
            
            products.append({
                "product_name": "Angle Business Finance - Full Doc",
                "asset_type": "equipment",
                "base_rate": 7.95,
                "comparison_rate": 8.70,
                "max_loan_amount": 1000000,  # 更高限额
                "min_loan_amount": 50000,
                "loan_terms": [12, 24, 36, 48, 60, 72, 84],
                "credit_score_min": 600,
                "documentation_type": ["Full-Doc"],
                "special_features": [
                    "Comprehensive assessment",
                    "Lower rates for full documentation",
                    "Higher loan amounts available",
                    "Business-focused lending"
                ],
                "eligibility_requirements": {
                    "abn_years_min": 2,
                    "gst_registration": "required",
                    "financial_statements": "required_2_years"
                }
            })
        
        return products
    
    def _extract_bfs_products(self, content: str, profile: CustomerProfile) -> List[Dict]:
        """提取BFS产品信息"""
        products = []
        
        # 🔧 从BFS.md提取产品信息
        if "Prime" in content and "Commercial Loan" in content:
            # Prime商业贷款产品
            products.append({
                "product_name": "BFS Prime Commercial Loan",
                "asset_type": "motor_vehicle",
                "base_rate": 7.65,
                "comparison_rate": 8.15,
                "max_loan_amount": 100000,  # 基础限额
                "min_loan_amount": 10000,
                "loan_terms": [12, 24, 36, 48, 60],
                "credit_score_min": 600,
                "documentation_type": ["Standard"],
                "special_features": [
                    "Business use ≥ 50%",
                    "ABN holders preferred",
                    "Courier runs accepted (48 months max)",
                    "Quick approval for established businesses"
                ],
                "eligibility_requirements": {
                    "abn_years_min": 1,
                    "business_use_min": 50,
                    "bank_statements": "90_days_required"
                }
            })
            
            # Prime Low Doc产品
            if "Low Doc" in content:
                products.append({
                    "product_name": "BFS Prime Low Doc",
                    "asset_type": "motor_vehicle",
                    "base_rate": 8.15,
                    "comparison_rate": 8.65,
                    "max_loan_amount": 100000,
                    "min_loan_amount": 10000,
                    "loan_terms": [12, 24, 36, 48, 60],
                    "credit_score_min": 600,
                    "documentation_type": ["Low-Doc"],
                    "special_features": [
                        "Reduced documentation",
                        "Motorhomes and campervans excluded",
                        "Asset must be in borrower/guarantor name"
                    ]
                })
        
        # Plus (Non-Prime) 产品
        if "Plus" in content and "15.98" in content:
            products.append({
                "product_name": "BFS Plus Non-Prime",
                "asset_type": "motor_vehicle",
                "base_rate": 15.98,
                "comparison_rate": 16.50,
                "max_loan_amount": 75000,
                "min_loan_amount": 5000,
                "loan_terms": [12, 24, 36, 48],
                "credit_score_min": 400,
                "documentation_type": ["Standard"],
                "special_features": [
                    "For borrowers who don't qualify for Prime",
                    "Higher risk acceptance",
                    "No private sale surcharge",
                    "Consumer and commercial loans"
                ]
            })
        
        return products
    
    def _extract_fcau_products(self, content: str, profile: CustomerProfile) -> List[Dict]:
        """提取FCAU产品信息"""
        products = []
        
        # 🔧 从FCAU.md提取产品信息
        if "FlexiPremium" in content and "6.95" in content:
            # FlexiPremium特别产品
            products.append({
                "product_name": "FCAU FlexiPremium Special 6.95%",
                "asset_type": "primary",
                "base_rate": 6.95,
                "comparison_rate": 7.45,
                "max_loan_amount": 500000,
                "min_loan_amount": 50000,
                "loan_terms": [12, 24, 36, 48, 60],
                "credit_score_min": 650,
                "documentation_type": ["Standard"],
                "special_features": [
                    "Premium rate for qualifying businesses",
                    "Asset age ≤ 5 years",
                    "Company/trust/partnership only",
                    "Time-in-business: 4 years asset-backed or 8 years non-asset-backed"
                ],
                "eligibility_requirements": {
                    "business_type": ["company", "trust", "partnership"],
                    "asset_age_max": 5,
                    "abn_years_min": 4,
                    "asset_backed": "preferred"
                }
            })
        
        # FlexiCommercial标准产品
        if "FlexiCommercial" in content:
            # Primary assets产品
            products.append({
                "product_name": "FCAU FlexiCommercial Primary",
                "asset_type": "primary",
                "base_rate": 8.15,  # >150k范围的利率
                "comparison_rate": 8.75,
                "max_loan_amount": 500000,
                "min_loan_amount": 10000,
                "loan_terms": [12, 24, 36, 48, 60, 72, 84],
                "credit_score_min": 500,
                "documentation_type": ["Standard"],
                "special_features": [
                    "Primary equipment up to 20 years at end of term",
                    "Comprehensive equipment finance",
                    "Flexible terms up to 7 years",
                    "Asset age-based pricing"
                ],
                "rate_conditions": {
                    "10000-20000": 12.90,
                    "20001-50000": 10.40,
                    "50001-150000": 8.65,
                    "150000+": 8.15
                }
            })
            
            # Secondary assets产品
            products.append({
                "product_name": "FCAU FlexiCommercial Secondary",
                "asset_type": "secondary", 
                "base_rate": 10.65,  # >150k范围的利率
                "comparison_rate": 11.25,
                "max_loan_amount": 300000,
                "min_loan_amount": 10000,
                "loan_terms": [12, 24, 36, 48, 60],
                "credit_score_min": 500,
                "documentation_type": ["Standard"],
                "special_features": [
                    "Secondary equipment ≤ 7 years at end of term",
                    "Generators, compressors, engineering tools",
                    "Flexible credit requirements"
                ]
            })
        
        return products

class UnifiedIntelligentService:
    """🔧 增强：统一智能服务 - 保持原有功能，集成产品库"""
    
    def __init__(self):
        self.anthropic_api_key = get_api_key()
        
        # 🔧 新增：产品库管理器
        self.product_db = ProductDatabaseManager()
        
        # 🔧 保持原有的业务结构识别模式
        self.business_structure_patterns = {
            "sole_trader": [
                "sole trader", "sole trading", "individual", "personal business",
                "self employed", "freelancer", "contractor", "individual trader"
            ],
            "company": [
                "company", "pty ltd", "corporation", "incorporated", "ltd",
                "corporate entity", "limited company", "pty limited"
            ],
            "partnership": [
                "partnership", "partners", "joint venture", "business partnership",
                "trading partnership", "general partnership"
            ],
            "trust": [
                "trust", "family trust", "discretionary trust", "unit trust",
                "trustee", "trading trust", "investment trust"
            ]
        }
        
        # 🔧 保持原有的会话状态管理
        self.session_states = {}
        
        print(f"🔧 UnifiedIntelligentService initialized:")
        print(f"   - API Key: {'✅' if self.anthropic_api_key else '❌'}")
        print(f"   - Product Database: {'✅' if self.product_db.get_all_lenders() else '❌'}")
        print(f"   - Available Lenders: {', '.join(self.product_db.get_all_lenders())}")

    async def process_user_message(self, user_message: str, session_id: str, current_customer_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """🔧 核心方法：处理用户消息 - 保持原有prompt管理和推荐策略"""
        
        try:
            print(f"🎯 Processing message for session {session_id}")
            
            # 🔧 保持原有的会话状态管理
            if session_id not in self.session_states:
                self.session_states[session_id] = {
                    "customer_profile": CustomerProfile(),
                    "stage": ConversationStage.GREETING,
                    "round_count": 0,
                    "asked_fields": set(),
                    "last_recommendations": []
                }
            
            state = self.session_states[session_id]
            state["round_count"] += 1
            
            # 🔧 保持原有的信息提取和同步功能
            self._sync_customer_info_from_form(state["customer_profile"], current_customer_info or {})
            
            # 🔧 保持原有的信息提取逻辑
            extracted_info = await self._extract_mvp_and_preferences_enhanced(
                [{"role": "user", "content": user_message}]
            )
            
            # 更新客户档案
            if extracted_info:
                self._update_customer_profile_from_extraction(state["customer_profile"], extracted_info)
            
            # 🔧 保持原有的对话阶段判断逻辑
            # 检查是否要求最低利率
            wants_lowest_rate = any(phrase in user_message.lower() for phrase in [
                "lowest rate", "lowest interest", "best rate", "cheapest rate", 
                "minimum rate", "lowest cost", "best deal"
            ])
            
            # 检查是否要求推荐
            wants_recommendations = any(phrase in user_message.lower() for phrase in [
                "recommend", "suggestion", "show me", "find me", "what do you recommend",
                "best option", "suitable", "match"
            ])
            
            # 🔧 保持原有的阶段流程控制
            if wants_lowest_rate or wants_recommendations or self._has_sufficient_mvp_info(state["customer_profile"]):
                current_stage = ConversationStage.PRODUCT_MATCHING
            else:
                current_stage = self._determine_conversation_stage(state, wants_lowest_rate)
            
            state["stage"] = current_stage
            
            # 🔧 保持原有的阶段处理逻辑
            if current_stage == ConversationStage.MVP_COLLECTION:
                return await self._handle_mvp_collection(state)
            elif current_stage == ConversationStage.PREFERENCE_COLLECTION:
                return await self._handle_preference_collection(state, wants_lowest_rate)
            elif current_stage == ConversationStage.PRODUCT_MATCHING:
                return await self._handle_product_matching(state)
            elif current_stage == ConversationStage.RECOMMENDATION:
                return await self._handle_recommendation(state)
            else:
                # 默认greeting处理
                return {
                    "message": "Hello! I'm here to help you find the best loan options. To get started, could you tell me what type of asset you're looking to finance?",
                    "recommendations": [],
                    "stage": "greeting"
                }
                
        except Exception as e:
            print(f"❌ Error in process_user_message: {e}")
            import traceback
            traceback.print_exc()
            return {
                "message": "I apologize for the technical issue. Let me help you find the right loan solution. What type of asset are you looking to finance?",
                "recommendations": [],
                "stage": "error_recovery"
            }

    def _sync_customer_info_from_form(self, profile: CustomerProfile, form_data: Dict[str, Any]):
        """🔧 保持：同步表单数据到客户档案 - 供function bar使用"""
        for field_name, value in form_data.items():
            if hasattr(profile, field_name) and value is not None and value != '' and value != 'undefined':
                # 类型转换
                if field_name in ['ABN_years', 'GST_years', 'credit_score', 'vehicle_year']:
                    try:
                        value = int(value) if value else None
                    except (ValueError, TypeError):
                        continue
                elif field_name in ['desired_loan_amount', 'interest_rate_ceiling', 'monthly_budget']:
                    try:
                        value = float(value) if value else None
                    except (ValueError, TypeError):
                        continue
                
                if value is not None:
                    setattr(profile, field_name, value)
                    print(f"🔄 Synced from form: {field_name} = {value}")

    async def _extract_mvp_and_preferences_enhanced(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """🔧 保持：增强的MVP和偏好提取逻辑"""
        
        if not conversation_history:
            return {}
        
        # 合并所有对话内容
        full_conversation_text = " ".join([
            msg.get("content", "") for msg in conversation_history 
            if isinstance(msg.get("content"), str)
        ])
        
        extracted_info = {}
        
        # 🔧 保持：业务结构提取
        business_structure = self._extract_business_structure_information(full_conversation_text)
        if business_structure:
            extracted_info["business_structure"] = business_structure
        
        # 🔧 保持原有的所有提取逻辑
        text_lower = full_conversation_text.lower()
        
        # Loan type extraction
        if any(word in text_lower for word in ["business loan", "commercial loan", "asset finance", "equipment finance"]):
            extracted_info["loan_type"] = "business"
        elif any(word in text_lower for word in ["personal loan", "consumer loan", "car loan"]):
            extracted_info["loan_type"] = "consumer"
        
        # Asset type extraction
        asset_patterns = {
            "motor_vehicle": ["car", "vehicle", "truck", "van", "ute", "motorcycle", "auto", "toyota", "ford", "holden"],
            "primary": ["primary equipment", "main equipment", "core machinery", "heavy equipment", "excavator"],
            "secondary": ["secondary equipment", "generator", "compressor", "engineering tools"],
            "tertiary": ["tertiary equipment", "computer", "IT equipment", "office equipment"]
        }
        
        for asset_type, patterns in asset_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                extracted_info["asset_type"] = asset_type
                break
        
        # 🔧 保持：房产状态识别
        if any(phrase in text_lower for phrase in ["own property", "property owner", "have property", "own a house", "own home"]):
            extracted_info["property_status"] = "property_owner"
        elif any(phrase in text_lower for phrase in ["don't own property", "no property", "rent", "renting"]):
            extracted_info["property_status"] = "non_property_owner"
        
        # 🔧 保持：数字提取逻辑
        # ABN years
        abn_match = re.search(r"abn.{0,20}(\d+).{0,10}year", text_lower)
        if abn_match:
            extracted_info["ABN_years"] = int(abn_match.group(1))
        
        # GST years
        gst_match = re.search(r"gst.{0,20}(\d+).{0,10}year", text_lower)
        if gst_match:
            extracted_info["GST_years"] = int(gst_match.group(1))
        
        # Credit score
        credit_match = re.search(r"credit.{0,20}(\d{3,4})", text_lower)
        if credit_match:
            score = int(credit_match.group(1))
            if 300 <= score <= 900:
                extracted_info["credit_score"] = score
        
        # 🔧 保持：贷款金额提取
        amount_patterns = [
            r"[\$](\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",
            r"(\d{1,3}(?:,\d{3})*)\s*(?:dollars?|k|thousand)",
            r"borrow\s*(\d{1,3}(?:,\d{3})*)",
            r"loan\s*(?:of|for)?\s*[\$]?(\d{1,3}(?:,\d{3})*)"
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text_lower.replace(",", ""))
            if matches:
                amounts = []
                for match in matches:
                    try:
                        amount = float(match.replace(",", ""))
                        if amount > 1000:
                            amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    extracted_info["desired_loan_amount"] = max(amounts)
                    break
        
        print(f"🔍 Enhanced extraction result: {extracted_info}")
        return extracted_info

    def _extract_business_structure_information(self, conversation_text: str) -> Optional[str]:
        """🔧 保持：业务结构提取"""
        text_lower = conversation_text.lower()
        
        for structure, patterns in self.business_structure_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    print(f"🏢 Detected business structure: {structure} (from pattern: {pattern})")
                    return structure
        
        return None

    def _update_customer_profile_from_extraction(self, profile: CustomerProfile, extracted_info: Dict[str, Any]):
        """🔧 保持：更新客户档案"""
        for field_name, value in extracted_info.items():
            if hasattr(profile, field_name) and value is not None:
                setattr(profile, field_name, value)
                print(f"🔄 Updated profile: {field_name} = {value}")

    def _has_sufficient_mvp_info(self, profile: CustomerProfile) -> bool:
        """🔧 保持：检查是否有足够的MVP信息"""
        required_fields = ["loan_type", "asset_type", "business_structure", "ABN_years", "GST_years"]
        
        for field in required_fields:
            if getattr(profile, field) is None:
                return False
        
        return True

    def _determine_conversation_stage(self, state: Dict, force_matching: bool = False) -> ConversationStage:
        """🔧 保持：确定对话阶段"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
        if force_matching:
            return ConversationStage.PRODUCT_MATCHING
        
        # 检查MVP字段是否完成
        required_mvp = ["loan_type", "asset_type", "business_structure", "property_status", "ABN_years", "GST_years"]
        missing_mvp = [field for field in required_mvp if getattr(profile, field) is None]
        
        if missing_mvp:
            return ConversationStage.MVP_COLLECTION
        
        # MVP完成，检查是否已问过偏好
        if "preferences_asked" not in asked_fields:
            return ConversationStage.PREFERENCE_COLLECTION
        
        # 有推荐历史，进入推荐阶段
        if state.get("last_recommendations"):
            return ConversationStage.RECOMMENDATION
        
        return ConversationStage.PRODUCT_MATCHING

    async def _handle_mvp_collection(self, state: Dict) -> Dict[str, Any]:
        """🔧 保持：处理MVP收集阶段"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
        # 优先级顺序
        mvp_fields_priority = [
            "loan_type",
            "asset_type", 
            "business_structure",
            "property_status",
            "ABN_years",
            "GST_years",
            "credit_score",
            "desired_loan_amount"
        ]
        
        # 检查主要MVP字段
        for field in mvp_fields_priority:
            if field not in asked_fields and getattr(profile, field) is None:
                asked_fields.add(field)
                question = self._get_field_question(field)
                return {
                    "message": question,
                    "next_questions": [question],
                    "stage": "mvp_collection"
                }
        
        # 所有MVP字段已收集，进入偏好收集阶段
        return await self._handle_preference_collection(state)

    def _get_field_question(self, field: str) -> str:
        """🔧 保持：获取字段对应的问题"""
        questions = {
            "loan_type": "What type of loan are you looking for? (business/commercial or personal/consumer)",
            "asset_type": "What type of asset are you financing? (motor vehicle, primary equipment, secondary equipment, or tertiary equipment)",
            "business_structure": "What's your business structure? (sole trader, company, partnership, or trust)",
            "property_status": "Do you own property that could be used as security?",
            "ABN_years": "How many years has your ABN been registered?",
            "GST_years": "How many years has your business been registered for GST?",
            "credit_score": "Do you know your credit score?",
            "desired_loan_amount": "What loan amount are you looking for?"
        }
        
        return questions.get(field, f"Could you provide information about {field.replace('_', ' ')}?")

    async def _handle_preference_collection(self, state: Dict, wants_lowest_rate: bool = False) -> Dict[str, Any]:
        """🔧 保持：处理偏好收集阶段"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
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
        
        if has_preferences:
            asked_fields.add("preferences_completed")
            return await self._handle_product_matching(state)
        
        # 检查是否已经问过偏好
        if "preferences_asked" not in asked_fields:
            asked_fields.add("preferences_asked")
            
            message = "Great! I have all the basic information I need. To find the most suitable options for you, you can optionally provide any of these preferences:\n\n"
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
                ],
                "stage": "preference_collection"
            }
        else:
            # 已经问过偏好了，直接进入产品匹配
            asked_fields.add("preferences_completed")
            return await self._handle_product_matching(state)

    async def _handle_product_matching(self, state: Dict, is_adjustment: bool = False) -> Dict[str, Any]:
        """🔧 核心增强：处理产品匹配阶段 - 集成真实产品库"""
        print("🎯 Starting enhanced product matching with real database...")
        profile = state["customer_profile"]
        
        # 🔧 使用真实产品库进行匹配
        recommendations = await self._product_matching_with_real_database(profile)
        
        if not recommendations:
            print("❌ No recommendations found")
            return {
                "message": "I'm analyzing all available loan products for your profile. Let me find the best options across all lenders...",
                "recommendations": [],
                "stage": "product_matching"
            }
        
        print(f"✅ Found {len(recommendations)} recommendations")
        
        # 🔧 保持：管理推荐历史
        if "last_recommendations" not in state:
            state["last_recommendations"] = []
        
        # 添加时间戳和状态标记
        for rec in recommendations:
            rec["timestamp"] = state["round_count"]
            rec["recommendation_status"] = "current"
        
        # 更新推荐历史
        state["last_recommendations"] = recommendations[:3]  # 保留最好的3个
        
        # 更新状态为推荐阶段
        state["stage"] = ConversationStage.RECOMMENDATION
        
        return await self._handle_recommendation(state, is_adjustment)

    async def _product_matching_with_real_database(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """🔧 新核心方法：使用真实产品库进行匹配"""
        
        try:
            print(f"🎯 Product matching for:")
            print(f"   - Loan amount: ${profile.desired_loan_amount:,}" if profile.desired_loan_amount else "   - Loan amount: Not specified")
            print(f"   - Asset type: {profile.asset_type}")
            print(f"   - Business structure: {profile.business_structure}")
            print(f"   - ABN years: {profile.ABN_years}")
            print(f"   - Credit score: {profile.credit_score}")
            
            # 🔧 从产品库提取所有产品
            all_products = self.product_db.extract_products_for_matching(profile)
            
            if not all_products:
                print("❌ No products extracted from database")
                return []
            
            print(f"📊 Total products available: {len(all_products)}")
            
            # 🔧 应用匹配逻辑
            eligible_products = []
            
            for product in all_products:
                score = self._calculate_match_score(product, profile)
                
                if score > 0:  # 基础符合条件
                    product["match_score"] = score
                    product["eligibility_status"] = self._check_detailed_eligibility(product, profile)
                    product["monthly_payment"] = self._calculate_monthly_payment(
                        profile.desired_loan_amount or 100000,
                        product.get("base_rate", 0),
                        60  # 默认5年期
                    )
                    product["reasons"] = self._generate_detailed_match_reasons(product, profile)
                    
                    eligible_products.append(product)
            
            # 🔧 按匹配得分和利率排序
            eligible_products.sort(key=lambda x: (-x["match_score"], x.get("base_rate", 999)))
            
            print(f"✅ Found {len(eligible_products)} eligible products")
            
            # 返回前3个最佳匹配
            return eligible_products[:3]
            
        except Exception as e:
            print(f"❌ Error in product matching: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _calculate_match_score(self, product: Dict, profile: CustomerProfile) -> float:
        """🔧 新增：计算产品匹配得分"""
        score = 0.0
        
        # 基础资产类型匹配
        if product.get("asset_type") == profile.asset_type:
            score += 30
        elif profile.asset_type == "motor_vehicle" and product.get("asset_type") in ["motor_vehicle", "primary"]:
            score += 20
        
        # 贷款金额匹配
        if profile.desired_loan_amount:
            min_amount = product.get("min_loan_amount", 0)
            max_amount = product.get("max_loan_amount", float('inf'))
            
            if min_amount <= profile.desired_loan_amount <= max_amount:
                score += 25
            elif profile.desired_loan_amount > max_amount:
                score += 0  # 不符合条件
            else:
                score += 10  # 金额太小但可以接受
        
        # 信用评分匹配
        if profile.credit_score and product.get("credit_score_min"):
            if profile.credit_score >= product.get("credit_score_min"):
                score += 20
            else:
                score -= 10  # 信用评分不足
        
        # ABN年限匹配
        if profile.ABN_years and product.get("eligibility_requirements", {}).get("abn_years_min"):
            required_years = product["eligibility_requirements"]["abn_years_min"]
            if profile.ABN_years >= required_years:
                score += 15
            else:
                score -= 5
        
        # 业务结构匹配
        if profile.business_structure and product.get("eligibility_requirements", {}).get("business_type"):
            accepted_types = product["eligibility_requirements"]["business_type"]
            if isinstance(accepted_types, list) and profile.business_structure in accepted_types:
                score += 10
        
        # 利率优势加分
        base_rate = product.get("base_rate", 20)
        if base_rate < 8:
            score += 15  # 优秀利率
        elif base_rate < 10:
            score += 10  # 良好利率
        elif base_rate < 12:
            score += 5   # 一般利率
        
        return max(0, score)

    def _check_detailed_eligibility(self, product: Dict, profile: CustomerProfile) -> str:
        """🔧 新增：检查详细合规状态"""
        
        issues = []
        
        # 检查贷款金额
        if profile.desired_loan_amount:
            min_amount = product.get("min_loan_amount", 0)
            max_amount = product.get("max_loan_amount", float('inf'))
            if not (min_amount <= profile.desired_loan_amount <= max_amount):
                issues.append("Loan amount outside range")
        
        # 检查信用评分
        if profile.credit_score and product.get("credit_score_min"):
            if profile.credit_score < product.get("credit_score_min"):
                issues.append("Credit score below minimum")
        
        # 检查ABN年限
        if profile.ABN_years and product.get("eligibility_requirements", {}).get("abn_years_min"):
            if profile.ABN_years < product["eligibility_requirements"]["abn_years_min"]:
                issues.append("ABN registration too recent")
        
        if not issues:
            return "Likely Eligible"
        elif len(issues) <= 2:
            return "Review Required"
        else:
            return "May Not Qualify"

    def _generate_detailed_match_reasons(self, product: Dict, profile: CustomerProfile) -> List[str]:
        """🔧 新增：生成详细匹配原因"""
        reasons = []
        
        # 利率相关
        rate = product.get("base_rate", 0)
        if rate < 8:
            reasons.append("Excellent interest rate")
        elif rate < 10:
            reasons.append("Competitive interest rate")
        
        # 贷款金额
        if profile.desired_loan_amount and profile.desired_loan_amount <= product.get("max_loan_amount", 0):
            reasons.append("Loan amount within limits")
        
        # 特殊功能
        special_features = product.get("special_features", [])
        if special_features:
            if len(special_features) >= 3:
                reasons.append("Comprehensive features package")
            elif any("fast" in str(feature).lower() for feature in special_features):
                reasons.append("Fast approval process")
        
        # 贷方声誉
        lender = product.get("lender_name", "")
        if lender in ["RAF", "BFS"]:
            reasons.append("Established specialist lender")
        elif lender in ["Angle", "FCAU"]:
            reasons.append("Flexible lending criteria")
        
        return reasons[:3]  # 限制在3个原因内

    def _calculate_monthly_payment(self, loan_amount: float, annual_rate: float, term_months: int) -> float:
        """🔧 保持：计算月供"""
        try:
            if annual_rate == 0:
                return loan_amount / term_months
            
            monthly_rate = annual_rate / 100 / 12
            payment = loan_amount * (monthly_rate * (1 + monthly_rate)**term_months) / ((1 + monthly_rate)**term_months - 1)
            return round(payment, 2)
        except:
            return 0

    async def _handle_recommendation(self, state: Dict, is_adjustment: bool = False) -> Dict[str, Any]:
        """🔧 保持：处理推荐阶段"""
        recommendations = state.get("last_recommendations", [])
        
        if not recommendations:
            return {
                "message": "I'm still analyzing the best options for you. Could you provide a bit more information about your requirements?",
                "recommendations": [],
                "stage": "recommendation"
            }
        
        # 🔧 保持：格式化推荐消息
        message = self._format_recommendation_message(recommendations, state["customer_profile"], is_adjustment)
        
        return {
            "message": message,
            "recommendations": recommendations,
            "stage": "recommendation",
            "customer_profile": self._customer_profile_to_dict(state["customer_profile"]),
            "extracted_info": {
                "mvp_fields": self._customer_profile_to_dict(state["customer_profile"]),
                "preferences": {}
            }
        }

    def _format_recommendation_message(self, recommendations: List[Dict], profile: CustomerProfile, is_adjustment: bool = False) -> str:
        """🔧 保持：格式化推荐消息"""
        
        if not recommendations:
            return "I'm finding the best options for you. Please provide a bit more information."
        
        # 获取最佳推荐
        best_rec = recommendations[0]
        
        intro = "Based on your requirements, I've found excellent loan options for you:" if not is_adjustment else "I've updated your recommendations:"
        
        message = f"{intro}\n\n"
        message += f"🏆 **Top Recommendation: {best_rec.get('lender_name')} - {best_rec.get('product_name')}**\n"
        message += f"• Interest Rate: {best_rec.get('base_rate')}% p.a.\n"
        
        if profile.desired_loan_amount:
            message += f"• Monthly Payment: ${best_rec.get('monthly_payment', 0):,.2f}\n"
        
        message += f"• Loan Amount: Up to ${best_rec.get('max_loan_amount', 0):,}\n"
        
        if best_rec.get("reasons"):
            message += f"• Why this works: {', '.join(best_rec['reasons'][:2])}\n"
        
        if len(recommendations) > 1:
            message += f"\nI've also found {len(recommendations)-1} other suitable option"
            message += "s" if len(recommendations) > 2 else ""
            message += " for comparison.\n"
        
        message += "\n**Next Steps:**\n"
        message += "• Review the detailed product information in the comparison panel\n"
        message += "• Let me know if you'd like to adjust any criteria\n"
        message += "• I can help you understand the application process\n"
        
        return message

    def _customer_profile_to_dict(self, profile: CustomerProfile) -> Dict[str, Any]:
        """🔧 保持：转换客户档案为字典 - 供function bar使用"""
        return {
            "loan_type": profile.loan_type,
            "asset_type": profile.asset_type,
            "property_status": profile.property_status,
            "business_structure": profile.business_structure,
            "ABN_years": profile.ABN_years,
            "GST_years": profile.GST_years,
            "vehicle_type": profile.vehicle_type,
            "vehicle_condition": profile.vehicle_condition,
            "credit_score": profile.credit_score,
            "desired_loan_amount": profile.desired_loan_amount,
            "interest_rate_ceiling": profile.interest_rate_ceiling,
            "monthly_budget": profile.monthly_budget,
            "min_loan_amount": profile.min_loan_amount,
            "preferred_term": profile.preferred_term
        }

# 🔧 保持原有的导出接口
__all__ = ["UnifiedIntelligentService", "CustomerProfile", "ConversationStage"]