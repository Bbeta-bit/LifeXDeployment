import re
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class ProductMatch:
    product_name: str
    interest_rate: float
    loan_amount_max: str
    match_score: float
    reasons: List[str]
    gaps: List[str]
    requirements: Dict[str, Any]

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
            "interest_rate": None,
            "loan_amount": None,
            "abn_years": None,
            "gst_years": None,
            "credit_score_min": None,
            "property_required": None,
            "low_doc_conditions": {},
            "full_doc_conditions": {},
            "additional_notes": {},
            "raw_content": section
        }
        
        # Extract interest rate
        rate_match = re.search(r'\*\*Interest Rate\*\*:\s*([\d.]+)%', section)
        if rate_match:
            product["interest_rate"] = float(rate_match.group(1))
        
        # Extract loan amount
        amount_match = re.search(r'\*\*Loan Amount\*\*:\s*(.+)', section)
        if amount_match:
            product["loan_amount"] = amount_match.group(1).strip()
        
        # Extract ABN requirements
        abn_match = re.search(r'ABN:\s*≥?\s*(\d+)\s*years?', section, re.IGNORECASE)
        if abn_match:
            product["abn_years"] = int(abn_match.group(1))
        
        # Extract GST requirements
        gst_match = re.search(r'GST:\s*≥?\s*(\d+)\s*years?', section, re.IGNORECASE)
        if gst_match:
            product["gst_years"] = int(gst_match.group(1))
        
        # Extract credit score requirements
        credit_matches = re.findall(r'Credit Score[^:]*:\s*(\d+)-?(\d+)?', section, re.IGNORECASE)
        if credit_matches:
            # Take the minimum credit score from all matches
            min_scores = [int(match[0]) for match in credit_matches]
            product["credit_score_min"] = min(min_scores)
        
        # Check if property is required
        if "property owner" in product_name.lower() or "property backed" in section.lower():
            product["property_required"] = True
        elif "non-property owner" in product_name.lower():
            product["property_required"] = False
        
        return product
    
    def find_best_loan_product(self, user_profile: Dict[str, Any], 
                              soft_prefs: Dict[str, Any] = None,
                              refine_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main function to find best matching products"""
        
        if not self.products_parsed:
            return {
                "status": "error",
                "message": "No products available for matching",
                "matches": []
            }
        
        try:
            # Step 1: Hard filtering based on MVP requirements
            eligible_products = self._hard_filter(user_profile)
            
            if not eligible_products:
                return self._handle_no_matches(user_profile, soft_prefs)
            
            # Step 2: Soft scoring based on preferences
            scored_products = self._soft_score(eligible_products, soft_prefs or {})
            
            # Step 3: Apply refinements if provided
            if refine_params:
                scored_products = self._apply_refinements(scored_products, refine_params)
            
            # Step 4: Generate top 3 recommendations
            top_matches = scored_products[:3]
            
            return {
                "status": "success",
                "matches": [self._create_product_match(product, user_profile, soft_prefs) 
                           for product in top_matches],
                "total_found": len(eligible_products)
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
            # Check ABN years requirement
            if (product.get("abn_years") and 
                user_profile.get("ABN_years") and 
                user_profile["ABN_years"] < product["abn_years"]):
                continue
            
            # Check GST years requirement
            if (product.get("gst_years") and 
                user_profile.get("GST_years") and 
                user_profile["GST_years"] < product["gst_years"]):
                continue
            
            # Check credit score requirement
            if (product.get("credit_score_min") and 
                user_profile.get("credit_score") and 
                user_profile["credit_score"] < product["credit_score_min"]):
                continue
            
            # Check property requirement
            if product.get("property_required") is not None:
                user_has_property = user_profile.get("property_status") == "property_owner"
                if product["property_required"] and not user_has_property:
                    continue
                elif not product["property_required"] and user_has_property:
                    # Property owners can generally use non-property products too
                    pass
            
            eligible.append(product)
        
        return eligible
    
    def _soft_score(self, products: List[Dict[str, Any]], 
                   preferences: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Score products based on soft preferences with equal weighting"""
        scored_products = []
        
        # Count active preferences for equal weight distribution
        active_preferences = [key for key in preferences.keys() if preferences.get(key) is not None]
        num_active = len(active_preferences)
        
        if num_active == 0:
            # No preferences provided, sort by interest rate (lower is better)
            for product in products:
                score = 1.0
                if product.get("interest_rate"):
                    # Higher score for lower interest rates
                    score += (15 - product["interest_rate"]) / 15 * 0.5
                product_with_score = product.copy()
                product_with_score["match_score"] = score
                scored_products.append(product_with_score)
        else:
            # Equal weight for each active preference
            weight_per_preference = 1.0 / num_active
            
            for product in products:
                score = 1.0  # Base score
                
                # Interest rate preference (lower is better)
                if (preferences.get("interest_rate_ceiling") and 
                    product.get("interest_rate")):
                    max_rate = preferences["interest_rate_ceiling"]
                    actual_rate = product["interest_rate"]
                    if actual_rate <= max_rate:
                        # Bonus for being under ceiling
                        score += (max_rate - actual_rate) / max_rate * weight_per_preference
                    else:
                        # Penalty for being over ceiling
                        score -= (actual_rate - max_rate) / max_rate * weight_per_preference
                
                # Monthly budget preference
                if preferences.get("monthly_budget"):
                    # This would need loan amount and term to calculate precisely
                    # For now, favor lower interest rates as they generally mean lower payments
                    if product.get("interest_rate"):
                        score += (15 - product["interest_rate"]) / 15 * weight_per_preference
                
                # Minimum loan amount preference
                if preferences.get("min_loan_amount"):
                    loan_max = product.get("loan_amount", "").lower()
                    if "unlimited" in loan_max:
                        score += weight_per_preference
                    else:
                        # Try to extract number from loan_amount
                        amount_match = re.search(r'(\d+)', loan_max.replace(',', ''))
                        if amount_match:
                            max_amount = int(amount_match.group(1))
                            min_needed = preferences["min_loan_amount"]
                            if max_amount >= min_needed:
                                score += weight_per_preference * 0.8
                
                # Preferred term preference
                if preferences.get("preferred_term"):
                    # This would need product term information
                    # For now, give small bonus
                    score += weight_per_preference * 0.5
                
                # Early repayment preference
                if preferences.get("early_repay_ok"):
                    # Most products allow early repayment, small bonus
                    score += weight_per_preference * 0.3
                
                product_with_score = product.copy()
                product_with_score["match_score"] = score
                scored_products.append(product_with_score)
        
        # Sort by score (highest first)
        return sorted(scored_products, key=lambda x: x["match_score"], reverse=True)
    
    def _apply_refinements(self, products: List[Dict[str, Any]], 
                          refinements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply additional refinements to product list"""
        # Apply tolerance for numerical values
        tolerance = self.fallback_params["tolerance_percentage"] / 100
        
        refined = []
        for product in products:
            include = True
            
            # Apply interest rate refinements with tolerance
            if refinements.get("max_interest_rate"):
                max_rate = refinements["max_interest_rate"]
                actual_rate = product.get("interest_rate", 0)
                if actual_rate > max_rate * (1 + tolerance):
                    include = False
            
            if include:
                refined.append(product)
        
        return refined
    
    def _handle_no_matches(self, user_profile: Dict[str, Any], 
                          soft_prefs: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case when no products match"""
        # Try with relaxed criteria
        relaxed_products = []
        
        for product in self.products_parsed:
            gaps = []
            
            # Check what requirements are not met
            if (product.get("abn_years") and 
                user_profile.get("ABN_years") and 
                user_profile["ABN_years"] < product["abn_years"]):
                gaps.append(f"ABN registration needs {product['abn_years']} years (you have {user_profile['ABN_years']})")
            
            if (product.get("credit_score_min") and 
                user_profile.get("credit_score") and 
                user_profile["credit_score"] < product["credit_score_min"]):
                gaps.append(f"Credit score needs to be {product['credit_score_min']} (you have {user_profile['credit_score']})")
            
            if product.get("property_required") and user_profile.get("property_status") != "property_owner":
                gaps.append("Property ownership required")
            
            if len(gaps) <= 2:  # Only show products with 2 or fewer gaps
                product_match = self._create_product_match(product, user_profile, soft_prefs)
                product_match.gaps = gaps
                relaxed_products.append(product_match)
        
        # Sort by number of gaps (fewer gaps first)
        relaxed_products.sort(key=lambda x: len(x.gaps))
        
        return {
            "status": "no_perfect_match",
            "message": "No products meet all your requirements, but here are the closest options:",
            "matches": relaxed_products[:3]
        }
    
    def _create_product_match(self, product: Dict[str, Any], 
                             user_profile: Dict[str, Any],
                             preferences: Dict[str, Any] = None) -> ProductMatch:
        """Create a ProductMatch object from product data"""
        reasons = []
        
        # Generate reasons based on why this product is good
        if product.get("interest_rate"):
            if preferences and preferences.get("interest_rate_ceiling"):
                ceiling = preferences["interest_rate_ceiling"]
                if product["interest_rate"] <= ceiling:
                    diff = ceiling - product["interest_rate"]
                    reasons.append(f"Interest rate {diff:.2f}pp below your maximum")
            else:
                reasons.append(f"Competitive interest rate of {product['interest_rate']}%")
        
        if product.get("loan_amount") == "Unlimited":
            reasons.append("No maximum loan amount limit")
        
        if not product.get("property_required") and user_profile.get("property_status") != "property_owner":
            reasons.append("No property ownership required")
        
        if len(reasons) == 0:
            reasons.append("Meets your basic requirements")
        
        # Ensure we have at most 3 reasons
        reasons = reasons[:3]
        
        return ProductMatch(
            product_name=product["name"],
            interest_rate=product.get("interest_rate", 0),
            loan_amount_max=product.get("loan_amount", "Contact for details"),
            match_score=product.get("match_score", 0.5),
            reasons=reasons,
            gaps=[],
            requirements=product
        )