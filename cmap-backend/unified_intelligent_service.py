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
    business_structure: Optional[str] = None  # 🔧 修复1：添加为核心字段
    
    # Vehicle-Specific MVP Fields (only asked if asset_type is motor_vehicle)
    vehicle_type: Optional[str] = None  # passenger_car/light_truck/van_ute/etc
    vehicle_condition: Optional[str] = None  # new/demonstrator/used
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    
    # Important but not MVP
    desired_loan_amount: Optional[float] = None
    loan_term_preference: Optional[int] = None
    
    # Preference Fields - Optional
    interest_rate_ceiling: Optional[float] = None
    monthly_budget: Optional[float] = None
    preferred_term: Optional[int] = None
    min_loan_amount: Optional[float] = None
    documentation_preference: Optional[str] = None

class UnifiedIntelligentService:
    def __init__(self):
        self.anthropic_api_key = get_api_key()
        self.conversation_states = {}
        
        # 🔧 修复：增强的业务结构模式
        self.business_structure_patterns = {
            'sole_trader': [
                'sole trader', 'sole trading', 'individual trader', 'self employed',
                'operating as an individual', 'trading individually', 'personal trading'
            ],
            'company': [
                'company', 'pty ltd', 'corporation', 'incorporated', 'ltd',
                'corporate entity', 'limited company', 'proprietary limited'
            ],
            'partnership': [
                'partnership', 'partners', 'joint venture', 'business partnership',
                'trading partnership', 'general partnership'
            ],
            'trust': [
                'trust', 'family trust', 'discretionary trust', 'unit trust',
                'trustee', 'trading trust', 'investment trust'
            ]
        }

    def _extract_business_structure_information(self, conversation_text: str) -> Optional[str]:
        """🔧 修复1：增强的业务结构提取"""
        text_lower = conversation_text.lower()
        
        for structure, patterns in self.business_structure_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    print(f"🏢 Detected business structure: {structure} (from pattern: {pattern})")
                    return structure
        
        return None

    def _detect_session_reset_needed(self, user_message: str, current_profile: CustomerProfile) -> bool:
        """🔧 修复2：检测是否需要重置会话"""
        reset_patterns = [
            'new loan', 'different loan', 'start over', 'fresh start', 
            'another loan', 'different case', 'new application', 'completely different'
        ]
        
        message_lower = user_message.lower()
        should_reset = any(pattern in message_lower for pattern in reset_patterns)
        
        if should_reset:
            print(f"🔄 Session reset detected: {user_message}")
        
        return should_reset

    async def _extract_mvp_and_preferences_enhanced(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """🔧 修复：增强的MVP和偏好提取，包含业务结构"""
        
        if not conversation_history:
            return {}
        
        # 合并所有对话内容
        full_conversation_text = " ".join([
            msg.get("content", "") for msg in conversation_history 
            if isinstance(msg.get("content"), str)
        ])
        
        extracted_info = {}
        
        # 🔧 修复：业务结构提取
        business_structure = self._extract_business_structure_information(full_conversation_text)
        if business_structure:
            extracted_info["business_structure"] = business_structure
        
        # 现有的提取逻辑保持不变...
        text_lower = full_conversation_text.lower()
        
        # Loan type extraction
        if any(word in text_lower for word in ["business loan", "commercial loan", "asset finance"]):
            extracted_info["loan_type"] = "business"
        elif any(word in text_lower for word in ["personal loan", "consumer loan"]):
            extracted_info["loan_type"] = "consumer"
        
        # Asset type extraction with enhanced patterns
        asset_patterns = {
            "motor_vehicle": ["car", "vehicle", "truck", "van", "ute", "motorcycle", "auto", "toyota", "ford", "holden"],
            "primary": ["primary equipment", "main equipment", "core machinery"],
            "secondary": ["secondary equipment", "generator", "compressor"],
            "tertiary": ["tertiary equipment", "computer", "IT equipment"]
        }
        
        for asset_type, patterns in asset_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                extracted_info["asset_type"] = asset_type
                break
        
        # Property status extraction
        if any(phrase in text_lower for phrase in ["own property", "property owner", "have property", "own a house", "own home"]):
            extracted_info["property_status"] = "property_owner"
        elif any(phrase in text_lower for phrase in ["don't own property", "no property", "rent", "renting"]):
            extracted_info["property_status"] = "non_property_owner"
        
        # Vehicle condition extraction
        if any(word in text_lower for word in ["new car", "brand new", "new vehicle"]):
            extracted_info["vehicle_condition"] = "new"
        elif any(word in text_lower for word in ["used car", "second hand", "pre-owned"]):
            extracted_info["vehicle_condition"] = "used"
        elif any(word in text_lower for word in ["demo", "demonstrator"]):
            extracted_info["vehicle_condition"] = "demonstrator"
        
        # Numeric extractions with enhanced patterns
        
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
        
        # Loan amount - 🔧 修复3：增强贷款金额提取
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
                        if amount > 1000:  # 过滤掉小额数字
                            amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    extracted_info["desired_loan_amount"] = max(amounts)  # 使用最大的金额
                    break
        
        print(f"🔍 Enhanced extraction result: {extracted_info}")
        return extracted_info

    def _get_required_mvp_fields(self, profile: CustomerProfile) -> List[str]:
        """🔧 修复：获取必需的MVP字段，包含业务结构"""
        base_fields = ["loan_type", "asset_type", "business_structure", "property_status", "ABN_years", "GST_years"]
        
        # 如果是motor_vehicle，添加车辆相关字段
        if profile.asset_type == "motor_vehicle":
            base_fields.extend(["vehicle_type", "vehicle_condition"])
        
        return base_fields

    async def _handle_mvp_collection(self, state: Dict) -> Dict[str, Any]:
        """🔧 修复：处理MVP收集阶段，优先业务结构"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
        # 🔧 修复：优先级顺序，业务结构提前
        mvp_fields_priority = [
            "loan_type",
            "asset_type", 
            "business_structure",  # 提高优先级
            "property_status",
            "ABN_years",
            "GST_years",
            "credit_score",
            "desired_loan_amount"
        ]
        
        # 检查vehicle相关字段
        if profile.asset_type == "motor_vehicle":
            vehicle_fields = ["vehicle_type", "vehicle_condition"]
            for field in vehicle_fields:
                if field not in asked_fields and getattr(profile, field) is None:
                    asked_fields.add(field)
                    question = self._get_field_question(field)
                    return {
                        "message": question,
                        "next_questions": [question]
                    }
        
        # 检查主要MVP字段
        for field in mvp_fields_priority:
            if field not in asked_fields and getattr(profile, field) is None:
                asked_fields.add(field)
                question = self._get_field_question(field)
                return {
                    "message": question,
                    "next_questions": [question]
                }
        
        # 所有MVP字段已收集，进入偏好收集阶段
        return await self._handle_preference_collection(state)

    def _get_field_question(self, field: str) -> str:
        """获取字段对应的问题"""
        questions = {
            "loan_type": "What type of loan are you looking for? (business/consumer)",
            "asset_type": "What type of asset are you looking to finance? (vehicle/equipment/machinery)",
            "business_structure": "What is your business structure? (sole trader/company/partnership/trust)",  # 🔧 修复
            "property_status": "Do you own property?",
            "ABN_years": "How many years has your ABN been registered?",
            "GST_years": "How many years have you been registered for GST?",
            "credit_score": "What is your current credit score?",
            "desired_loan_amount": "How much would you like to borrow?",
            "vehicle_type": "What type of vehicle? (passenger car/truck/van/motorcycle)",
            "vehicle_condition": "Are you looking at new or used vehicles?",
            "vehicle_make": "What make of vehicle?",
            "vehicle_model": "What model of vehicle?"
        }
        return questions.get(field, f"Please provide your {field}")

    async def _handle_loan_amount_update(self, state: Dict, new_amount: float) -> Dict[str, Any]:
        """🔧 修复3：处理贷款金额更新并触发重新匹配"""
        profile = state["customer_profile"]
        old_amount = profile.desired_loan_amount
        
        # 更新贷款金额
        profile.desired_loan_amount = new_amount
        print(f"💰 Loan amount updated: ${old_amount:,} → ${new_amount:,}")
        
        # 清除之前的推荐，强制重新匹配
        state["last_recommendations"] = []
        
        # 触发新的产品匹配
        new_recommendations = await self._ai_product_matching_with_lowest_rate_priority(profile)
        
        # 标记为调整
        for rec in new_recommendations:
            rec["is_adjustment"] = True
            rec["adjustment_reason"] = f"Loan amount changed to ${new_amount:,}"
        
        # 更新状态
        state["last_recommendations"] = new_recommendations
        
        return {
            "message": f"Perfect! I've updated your loan amount to ${new_amount:,} and found new recommendations that can handle this amount.",
            "recommendations": new_recommendations,
            "adjustment_made": True
        }

    async def _ai_product_matching_with_lowest_rate_priority(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """🔧 修复4：增强的产品匹配，优先最低利率"""
        
        print(f"🎯 Enhanced product matching for loan amount: ${profile.desired_loan_amount:,}")
        print(f"📊 Business structure: {profile.business_structure}")
        
        try:
            # 检查API密钥
            if not self.anthropic_api_key:
                print("⚠️ No Anthropic API key - using enhanced fallback recommendation")
                return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]
            
            # 获取所有符合条件的产品
            eligible_products = self._get_all_eligible_products_enhanced(profile)
            
            # 🔧 修复：按贷款金额容量过滤
            if profile.desired_loan_amount:
                eligible_products = [
                    p for p in eligible_products 
                    if p.get('max_loan_amount', 0) >= profile.desired_loan_amount
                ]
                print(f"📊 Products after loan amount filter: {len(eligible_products)}")
            
            # 🔧 修复：按利率排序（最低优先）
            eligible_products.sort(key=lambda x: x.get('base_rate', 999))
            
            # 构建推荐
            recommendations = []
            for i, product in enumerate(eligible_products[:3]):  # 取前3个最低利率
                
                # 计算月供
                monthly_payment = self._calculate_monthly_payment(
                    profile.desired_loan_amount or 100000,
                    product.get('base_rate', 0),
                    60  # 默认期限
                )
                
                recommendation = {
                    "lender_name": product.get('lender_name', 'Unknown'),
                    "product_name": product.get('product_name', 'Unknown Product'),
                    "base_rate": product.get('base_rate', 0),
                    "comparison_rate": product.get('comparison_rate', product.get('base_rate', 0)),
                    "max_loan_amount": product.get('max_loan_amount', 0),
                    "monthly_payment": monthly_payment,
                    "loan_terms": product.get('loan_terms', '12-84 months'),
                    "eligibility_status": self._check_eligibility_status(product, profile),
                    "reasons": self._generate_match_reasons(product, profile),
                    "rank": i + 1,
                    "rate_tier": "premium" if product.get('base_rate', 0) < 8 else "competitive"
                }
                
                recommendations.append(recommendation)
            
            print(f"✅ Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            print(f"❌ Error in product matching: {e}")
            return [self._create_comprehensive_fallback_recommendation_enhanced(profile)]

    def _get_all_eligible_products_enhanced(self, profile: CustomerProfile) -> List[Dict[str, Any]]:
        """🔧 修复：获取所有符合条件的产品，包含业务结构检查"""
        
        # 模拟产品数据库 - 这里应该连接到您的实际产品数据库
        all_products = [
            {
                "lender_name": "RAF",
                "product_name": "Vehicle Finance Premium",
                "base_rate": 6.89,
                "comparison_rate": 7.15,
                "max_loan_amount": 400000,
                "min_abn_years": 2,
                "min_gst_years": 1,
                "min_credit_score": 600,
                "accepted_business_structures": ["company", "trust", "partnership"],  # 不接受sole trader
                "property_required": False
            },
            {
                "lender_name": "BFS",
                "product_name": "Prime Commercial",
                "base_rate": 7.65,
                "comparison_rate": 7.95,
                "max_loan_amount": 600000,  # 🔧 修复：更高的贷款限额
                "min_abn_years": 1,
                "min_gst_years": 1,
                "min_credit_score": 500,
                "accepted_business_structures": ["sole_trader", "company", "trust", "partnership"],
                "property_required": False
            },
            {
                "lender_name": "Angle",
                "product_name": "Primary Asset Finance",
                "base_rate": 7.99,
                "comparison_rate": 8.25,
                "max_loan_amount": 500000,
                "min_abn_years": 2,
                "min_gst_years": 1,
                "min_credit_score": 500,
                "accepted_business_structures": ["sole_trader", "company", "trust", "partnership"],
                "property_required": True
            }
        ]
        
        # 过滤符合条件的产品
        eligible_products = []
        
        for product in all_products:
            eligible = True
            reasons = []
            
            # 检查ABN年限
            if profile.ABN_years and profile.ABN_years < product.get('min_abn_years', 0):
                eligible = False
                reasons.append(f"ABN years {profile.ABN_years} < required {product.get('min_abn_years')}")
            
            # 检查GST年限
            if profile.GST_years and profile.GST_years < product.get('min_gst_years', 0):
                eligible = False
                reasons.append(f"GST years {profile.GST_years} < required {product.get('min_gst_years')}")
            
            # 检查信用分数
            if profile.credit_score and profile.credit_score < product.get('min_credit_score', 0):
                eligible = False
                reasons.append(f"Credit score {profile.credit_score} < required {product.get('min_credit_score')}")
            
            # 🔧 修复：检查业务结构
            if profile.business_structure and product.get('accepted_business_structures'):
                if profile.business_structure not in product.get('accepted_business_structures', []):
                    eligible = False
                    reasons.append(f"Business structure '{profile.business_structure}' not accepted")
            
            # 检查房产要求
            if product.get('property_required', False) and profile.property_status == "non_property_owner":
                eligible = False
                reasons.append("Property ownership required")
            
            if eligible:
                eligible_products.append(product)
            else:
                print(f"❌ Product {product['product_name']} not eligible: {reasons}")
        
        print(f"✅ Found {len(eligible_products)} eligible products")
        return eligible_products

    def _check_eligibility_status(self, product: Dict, profile: CustomerProfile) -> str:
        """检查产品的合规状态"""
        
        # 检查所有要求是否满足
        requirements_met = True
        
        if profile.ABN_years and profile.ABN_years < product.get('min_abn_years', 0):
            requirements_met = False
        
        if profile.GST_years and profile.GST_years < product.get('min_gst_years', 0):
            requirements_met = False
        
        if profile.credit_score and profile.credit_score < product.get('min_credit_score', 0):
            requirements_met = False
        
        if profile.business_structure and product.get('accepted_business_structures'):
            if profile.business_structure not in product.get('accepted_business_structures', []):
                requirements_met = False
        
        return "Likely Eligible" if requirements_met else "Requires Review"

    def _generate_match_reasons(self, product: Dict, profile: CustomerProfile) -> List[str]:
        """生成匹配原因"""
        reasons = []
        
        # 利率相关
        rate = product.get('base_rate', 0)
        if rate < 8:
            reasons.append("Excellent interest rate")
        elif rate < 10:
            reasons.append("Competitive interest rate")
        
        # 贷款金额
        if profile.desired_loan_amount and profile.desired_loan_amount <= product.get('max_loan_amount', 0):
            reasons.append("Loan amount within limits")
        
        # 业务结构匹配
        if profile.business_structure and product.get('accepted_business_structures'):
            if profile.business_structure in product.get('accepted_business_structures', []):
                reasons.append("Business structure accepted")
        
        return reasons[:3]  # 最多返回3个原因

    def _create_comprehensive_fallback_recommendation_enhanced(self, profile: CustomerProfile) -> Dict[str, Any]:
        """🔧 修复：增强的备用推荐"""
        
        # 根据客户档案选择最合适的备用产品
        if profile.business_structure == "sole_trader":
            lender = "BFS"
            product = "Prime Commercial"
            rate = 7.65
            max_amount = 600000
        elif profile.property_status == "property_owner":
            lender = "Angle"
            product = "Primary Asset Finance"
            rate = 7.99
            max_amount = 500000
        else:
            lender = "RAF"
            product = "Vehicle Finance Premium"
            rate = 6.89
            max_amount = 400000
        
        monthly_payment = self._calculate_monthly_payment(
            profile.desired_loan_amount or 100000,
            rate,
            60
        )
        
        return {
            "lender_name": lender,
            "product_name": product,
            "base_rate": rate,
            "comparison_rate": rate + 0.3,
            "max_loan_amount": max_amount,
            "monthly_payment": monthly_payment,
            "loan_terms": "12-84 months",
            "eligibility_status": "Likely Eligible",
            "reasons": ["Fallback recommendation", "Good match for your profile"],
            "is_fallback": True
        }

    def _calculate_monthly_payment(self, loan_amount: float, annual_rate: float, term_months: int) -> float:
        """计算月供"""
        if not loan_amount or not annual_rate or not term_months:
            return 0
        
        monthly_rate = annual_rate / 100 / 12
        if monthly_rate == 0:
            return loan_amount / term_months
        
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
        return round(monthly_payment, 2)

    def _update_customer_profile_with_priority(self, profile: CustomerProfile, extracted_info: Dict[str, Any], manual_info: Dict = None):
        """使用优先级策略更新客户档案"""
        
        # 1. 先应用手动修改（较低优先级）
        if manual_info:
            for field, value in manual_info.items():
                if value is not None and value != '' and hasattr(profile, field):
                    current_value = getattr(profile, field)
                    if current_value != value:  # 只有值不同时才更新
                        setattr(profile, field, value)
                        print(f"📝 Manual update: {field} = {value}")
        
        # 2. 再应用自动提取（较高优先级）
        for field, value in extracted_info.items():
            if value is not None and value != '' and hasattr(profile, field):
                current_value = getattr(profile, field)
                # 自动提取总是覆盖现有值（除非是明显错误的值）
                if self._validate_extracted_value(field, value):
                    setattr(profile, field, value)
                    print(f"🤖 Auto-extracted: {field} = {value}")

    def _validate_extracted_value(self, field: str, value: Any) -> bool:
        """验证提取的值是否合理"""
        
        if field == "credit_score":
            return isinstance(value, int) and 300 <= value <= 900
        elif field == "ABN_years":
            return isinstance(value, int) and 0 <= value <= 50
        elif field == "GST_years":
            return isinstance(value, int) and 0 <= value <= 50
        elif field == "desired_loan_amount":
            return isinstance(value, (int, float)) and value > 0
        elif field == "business_structure":
            return value in ["sole_trader", "company", "partnership", "trust"]
        
        return True  # 默认接受其他字段

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

    def _determine_conversation_stage(self, state: Dict, force_matching: bool = False) -> ConversationStage:
        """确定对话阶段"""
        profile = state["customer_profile"]
        asked_fields = state["asked_fields"]
        
        if force_matching:
            return ConversationStage.PRODUCT_MATCHING
        
        # 检查MVP字段是否完成
        required_mvp = self._get_required_mvp_fields(profile)
        missing_mvp = [field for field in required_mvp if getattr(profile, field) is None]
        
        if missing_mvp:
            return ConversationStage.MVP_COLLECTION
        
        # MVP完成，检查是否已问过偏好
        if "preferences_asked" not in asked_fields:
            return ConversationStage.PREFERENCE_COLLECTION
        
        # 有推荐历史，进入推荐阶段
        if state.get("last_recommendations"):
            return ConversationStage.RECOMMENDATION
        
        # 否则进入产品匹配
        return ConversationStage.PRODUCT_MATCHING

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
        if has_preferences:
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

    async def _handle_product_matching(self, state: Dict, is_adjustment: bool = False) -> Dict[str, Any]:
        """🔧 修复：处理产品匹配阶段 - 添加调整支持和完整产品信息"""
        print("🎯 Starting enhanced product matching...")
        profile = state["customer_profile"]
        
        # 🔧 修复：增强产品匹配，包含完整信息
        recommendations = await self._ai_product_matching_with_lowest_rate_priority(profile)
        
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

    async def _handle_general_conversation(self, state: Dict) -> Dict[str, Any]:
        """处理一般对话"""
        return {
            "message": "I'm here to help you find the best loan options. What would you like to know about financing?",
            "next_questions": []
        }

    def _serialize_customer_profile(self, profile: CustomerProfile) -> Dict[str, Any]:
        """序列化客户档案"""
        return {
            "loan_type": profile.loan_type,
            "asset_type": profile.asset_type,
            "property_status": profile.property_status,
            "ABN_years": profile.ABN_years,
            "GST_years": profile.GST_years,
            "credit_score": profile.credit_score,
            "business_structure": profile.business_structure,
            "vehicle_type": profile.vehicle_type,
            "vehicle_condition": profile.vehicle_condition,
            "vehicle_make": profile.vehicle_make,
            "vehicle_model": profile.vehicle_model,
            "vehicle_year": profile.vehicle_year,
            "desired_loan_amount": profile.desired_loan_amount,
            "loan_term_preference": profile.loan_term_preference,
            "interest_rate_ceiling": profile.interest_rate_ceiling,
            "monthly_budget": profile.monthly_budget,
            "preferred_term": profile.preferred_term,
            "min_loan_amount": profile.min_loan_amount,
            "documentation_preference": profile.documentation_preference
        }

    async def process_conversation(self, user_message: str, session_id: str = "default", 
                                 chat_history: List[Dict] = None, current_customer_info: Dict = None) -> Dict[str, Any]:
        """处理对话的主入口函数"""
        
        print(f"\n🔄 Processing conversation - Session: {session_id}")
        print(f"📝 User message: {user_message}")
        print(f"📊 Current customer info: {current_customer_info}")
        
        # 🔧 修复2：检查是否需要重置会话
        if session_id in self.conversation_states:
            current_profile = self.conversation_states[session_id]["customer_profile"]
            if self._detect_session_reset_needed(user_message, current_profile):
                print("🔄 Resetting session for new case")
                del self.conversation_states[session_id]
        
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
        
        # 🔧 修复3：检查是否是贷款金额调整
        amount_change_patterns = [
            r"change.{0,20}amount.{0,20}(\d{1,3}(?:,?\d{3})*)",
            r"loan.{0,20}amount.{0,20}(\d{1,3}(?:,?\d{3})*)",
            r"(\d{1,3}(?:,?\d{3})*).{0,20}instead",
            r"update.{0,20}(\d{1,3}(?:,?\d{3})*)"
        ]
        
        for pattern in amount_change_patterns:
            match = re.search(pattern, user_message.lower().replace(",", ""))
            if match:
                try:
                    new_amount = float(match.group(1).replace(",", ""))
                    if new_amount > 10000:  # 确保是合理的贷款金额
                        return await self._handle_loan_amount_update(state, new_amount)
                except (ValueError, IndexError):
                    continue
        
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