import re
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ProductMatch:
    product_name: str
    lender_name: str
    interest_rate: float
    comparison_rate: Optional[float]
    loan_amount_max: str
    loan_term_options: str
    match_score: float
    reasons: List[str]
    gaps: List[str]
    requirements: Dict[str, Any]
    monthly_payment: Optional[float]
    fees_breakdown: Dict[str, Any]
    all_requirements_met: bool
    eligibility_details: Dict[str, Any]

class ProductMatchingService:
    def __init__(self):
        self.products_raw = self._load_products()
        self.products_parsed = self._parse_products()
        
        # Fallback parameters
        self.fallback_params = {
            "max_ask_attempts": 2,
            "tolerance_percentage": 10,
            "max_conversation_rounds": 3,
            "timeout_seconds": 100,
        }
    
    def _load_products(self) -> str:
        """Load products from markdown file"""
        try:
            product_file_path = os.path.join("docs", "products.md")
            with open(product_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print("Warning: Product info file not found")
            return ""
    
    def _parse_products(self) -> List[Dict[str, Any]]:
        """Parse markdown products into structured data"""
        products = []
        
        # Split by product headers (##Product:)
        product_sections = re.split(r'##Product:\s*', self.products_raw)
        
        for section in product_sections[1:]:  # Skip first empty section
            product = self._parse_single_product(section)
            if product:
                products.append(product)
        
        return products
    
    def _parse_single_product(self, section: str) -> Optional[Dict[str, Any]]:
        """Parse a single product section"""
        lines = section.strip().split('\n')
        if not lines:
            return None
        
        # Extract product name from first line
        product_name = lines[0].strip()
        
        product = {
            "name": product_name,
            "lender": self._extract_lender_name(product_name),
            "interest_rate": None,
            "loan_amount": None,
            "loan_term": None,
            "abn_years": None,
            "gst_years": None,
            "credit_score_min": None,
            "property_required": None,
            "fees": {},
            "requirements": {},
            "raw_content": section
        }
        
        # Extract interest rate
        rate_match = re.search(r'(?:Interest Rate|Base Rate|Rate).*?(\d+\.?\d*)%', section, re.IGNORECASE)
        if rate_match:
            product["interest_rate"] = float(rate_match.group(1))
        
        # Extract loan amount
        amount_match = re.search(r'(?:Loan Amount|Maximum|Max).*?(?:\$)?([\d,]+)', section, re.IGNORECASE)
        if amount_match:
            product["loan_amount"] = amount_match.group(1).replace(',', '')
        
        # Extract loan term
        term_match = re.search(r'(?:Term|Years).*?(\d+)', section, re.IGNORECASE)
        if term_match:
            product["loan_term"] = int(term_match.group(1))
        
        # Extract ABN requirements
        abn_match = re.search(r'ABN.*?(\d+)\s*years?', section, re.IGNORECASE)
        if abn_match:
            product["abn_years"] = int(abn_match.group(1))
        
        # Extract GST requirements
        gst_match = re.search(r'GST.*?(\d+)\s*years?', section, re.IGNORECASE)
        if gst_match:
            product["gst_years"] = int(gst_match.group(1))
        
        # Extract credit score requirements
        credit_match = re.search(r'Credit Score.*?(\d+)', section, re.IGNORECASE)
        if credit_match:
            product["credit_score_min"] = int(credit_match.group(1))
        
        # Extract property requirement
        if "property owner" in product_name.lower() or "property backed" in section.lower():
            product["property_required"] = True
        elif "non-property owner" in product_name.lower():
            product["property_required"] = False
        
        # Extract fees
        product["fees"] = self._extract_fees(section)
        
        return product
    
    def _extract_lender_name(self, product_name: str) -> str:
        """Extract lender name from product name"""
        lenders = ["Angle", "BFS", "FCAU", "RAF"]
        for lender in lenders:
            if lender.lower() in product_name.lower():
                return lender
        return "Unknown"
    
    def _extract_fees(self, content: str) -> Dict[str, float]:
        """Extract fees from product content"""
        fees = {}
        
        # Common fee patterns
        fee_patterns = {
            "establishment_fee": r'Establishment.*?\$?([\d,]+)',
            "account_fee": r'Account.*?Fee.*?\$?([\d.]+)',
            "origination_fee": r'Origination.*?\$?([\d,]+)',
            "brokerage_fee": r'Brokerage.*?\$?([\d,]+)',
        }
        
        for fee_name, pattern in fee_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    fees[fee_name] = float(match.group(1).replace(',', ''))
                except ValueError:
                    continue
        
        return fees
    
    def find_best_loan_product(self, user_profile: Dict[str, Any], 
                              soft_prefs: Dict[str, Any] = None,
                              refine_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Find the LOWEST RATE product that matches customer requirements"""
        
        if not self.products_parsed:
            return {
                "status": "error",
                "message": "No products available for matching",
                "matches": []
            }
        
        try:
            # Step 1: Find ALL eligible products
            eligible_products = self._hard_filter(user_profile)
            
            if not eligible_products:
                return self._handle_no_matches(user_profile, soft_prefs)
            
            # Step 2: Sort by interest rate (lowest first) - THIS IS THE KEY CHANGE
            eligible_products.sort(key=lambda x: x.get("interest_rate", float('inf')))
            
            # Step 3: Take the lowest rate product
            best_product = eligible_products[0]
            
            # Step 4: Create detailed product match with all information
            detailed_match = self._create_detailed_product_match(
                best_product, user_profile, soft_prefs
            )
            
            return {
                "status": "success",
                "matches": [detailed_match],
                "total_found": len(eligible_products),
                "recommendation_basis": "lowest_rate"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during product matching: {str(e)}",
                "matches": []
            }
    
    def _hard_filter(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply hard filters based on MVP requirements"""
        eligible = []
        
        for product in self.products_parsed:
            is_eligible = True
            
            # Check ABN years requirement
            if (product.get("abn_years") and 
                user_profile.get("ABN_years") and 
                user_profile["ABN_years"] < product["abn_years"]):
                is_eligible = False
            
            # Check GST years requirement
            if (product.get("gst_years") and 
                user_profile.get("GST_years") and 
                user_profile["GST_years"] < product["gst_years"]):
                is_eligible = False
            
            # Check credit score requirement
            if (product.get("credit_score_min") and 
                user_profile.get("credit_score") and 
                user_profile["credit_score"] < product["credit_score_min"]):
                is_eligible = False
            
            # Check property requirement
            if product.get("property_required") is not None:
                user_has_property = user_profile.get("property_status") == "property_owner"
                if product["property_required"] and not user_has_property:
                    is_eligible = False
            
            if is_eligible:
                eligible.append(product)
        
        return eligible
    
    def _create_detailed_product_match(self, product: Dict[str, Any], 
                                     user_profile: Dict[str, Any],
                                     preferences: Dict[str, Any] = None) -> ProductMatch:
        """Create detailed ProductMatch with all required information"""
        
        # Calculate comparison rate
        comparison_rate = self._calculate_comparison_rate(product)
        
        # Calculate monthly payment if possible
        monthly_payment = self._calculate_monthly_payment(product, user_profile)
        
        # Create eligibility details
        eligibility_details = self._create_eligibility_details(product, user_profile)
        
        # Generate reasons why this is the best choice
        reasons = [f"Lowest available rate at {product.get('interest_rate', 0):.2f}%"]
        
        if eligibility_details["all_met"]:
            reasons.append("Meets all requirements")
        
        return ProductMatch(
            product_name=product["name"],
            lender_name=product.get("lender", "Unknown"),
            interest_rate=product.get("interest_rate", 0),
            comparison_rate=comparison_rate,
            loan_amount_max=product.get("loan_amount", "Contact for details"),
            loan_term_options=f"Up to {product.get('loan_term', 'Various')} years",
            match_score=1.0,  # Highest score for lowest rate
            reasons=reasons,
            gaps=eligibility_details["gaps"],
            requirements=product,
            monthly_payment=monthly_payment,
            fees_breakdown=product.get("fees", {}),
            all_requirements_met=eligibility_details["all_met"],
            eligibility_details=eligibility_details
        )
    
    def _calculate_comparison_rate(self, product: Dict[str, Any]) -> float:
        """Calculate comparison rate including fees"""
        base_rate = product.get("interest_rate", 0)
        fees = product.get("fees", {})
        
        # Simplified comparison rate calculation
        # In reality, this would use proper financial formulas
        total_fees = sum(fees.values())
        if total_fees > 0:
            # Rough estimate: add fee impact to base rate
            fee_impact = min(total_fees / 10000, 2.0)  # Cap impact at 2%
            return round(base_rate + fee_impact, 2)
        
        return base_rate
    
    def _calculate_monthly_payment(self, product: Dict[str, Any], 
                                 user_profile: Dict[str, Any]) -> Optional[float]:
        """Calculate monthly payment if sufficient information available"""
        loan_amount = user_profile.get("desired_loan_amount")
        interest_rate = product.get("interest_rate")
        term_years = user_profile.get("loan_term_preference") or product.get("loan_term", 5)
        
        if not all([loan_amount, interest_rate, term_years]):
            return None
        
        try:
            # Convert to monthly values
            monthly_rate = interest_rate / 100 / 12
            term_months = term_years * 12
            
            if monthly_rate == 0:
                return loan_amount / term_months
            
            # Standard loan payment formula
            payment = (loan_amount * monthly_rate * (1 + monthly_rate) ** term_months) / \
                     ((1 + monthly_rate) ** term_months - 1)
            
            return round(payment, 2)
        
        except (ValueError, ZeroDivisionError):
            return None
    
    def _create_eligibility_details(self, product: Dict[str, Any], 
                                  user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed eligibility analysis"""
        details = {
            "requirements": {},
            "gaps": [],
            "all_met": True
        }
        
        # Check ABN requirement
        if product.get("abn_years"):
            user_abn = user_profile.get("ABN_years", 0)
            met = user_abn >= product["abn_years"]
            details["requirements"]["ABN"] = {
                "required": f"≥{product['abn_years']} years",
                "user_has": f"{user_abn} years",
                "met": met
            }
            if not met:
                details["gaps"].append(f"Need {product['abn_years']} years ABN (you have {user_abn})")
                details["all_met"] = False
        
        # Check GST requirement
        if product.get("gst_years"):
            user_gst = user_profile.get("GST_years", 0)
            met = user_gst >= product["gst_years"]
            details["requirements"]["GST"] = {
                "required": f"≥{product['gst_years']} years",
                "user_has": f"{user_gst} years",
                "met": met
            }
            if not met:
                details["gaps"].append(f"Need {product['gst_years']} years GST (you have {user_gst})")
                details["all_met"] = False
        
        # Check credit score requirement
        if product.get("credit_score_min"):
            user_score = user_profile.get("credit_score", 0)
            met = user_score >= product["credit_score_min"]
            details["requirements"]["Credit Score"] = {
                "required": f"≥{product['credit_score_min']}",
                "user_has": str(user_score),
                "met": met
            }
            if not met:
                details["gaps"].append(f"Need credit score {product['credit_score_min']} (you have {user_score})")
                details["all_met"] = False
        
        # Check property requirement
        if product.get("property_required") is not None:
            user_has_property = user_profile.get("property_status") == "property_owner"
            met = product["property_required"] == user_has_property
            details["requirements"]["Property"] = {
                "required": "Required" if product["property_required"] else "Not Required",
                "user_has": "Property Owner" if user_has_property else "Non-Property Owner",
                "met": met
            }
            if not met and product["property_required"]:
                details["gaps"].append("Property ownership required")
                details["all_met"] = False
        
        return details
    
    def _handle_no_matches(self, user_profile: Dict[str, Any], 
                          soft_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case when no products match"""
        # Find closest matches for gap analysis
        closest_products = []
        
        for product in self.products_parsed:
            gaps = []
            
            # Analyze gaps
            if (product.get("abn_years") and 
                user_profile.get("ABN_years") and 
                user_profile["ABN_years"] < product["abn_years"]):
                gaps.append(f"Need {product['abn_years']} years ABN")
            
            if (product.get("credit_score_min") and 
                user_profile.get("credit_score") and 
                user_profile["credit_score"] < product["credit_score_min"]):
                gaps.append(f"Need credit score {product['credit_score_min']}")
            
            if product.get("property_required") and user_profile.get("property_status") != "property_owner":
                gaps.append("Property ownership required")
            
            if len(gaps) <= 2:  # Show products with 2 or fewer gaps
                product_match = self._create_detailed_product_match(product, user_profile, soft_prefs)
                product_match.gaps = gaps
                product_match.all_requirements_met = False
                closest_products.append(product_match)
        
        # Sort by lowest rate among closest matches
        closest_products.sort(key=lambda x: x.interest_rate)
        
        return {
            "status": "no_perfect_match",
            "message": "No products meet all requirements, showing closest option:",
            "matches": closest_products[:1],  # Show only the lowest rate option
            "recommendation_basis": "lowest_rate_with_gaps"
        }