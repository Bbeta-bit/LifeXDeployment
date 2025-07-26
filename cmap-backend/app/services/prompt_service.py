import os
from typing import Dict, Any

class PromptService:
    def __init__(self):
        self.product_info = self._load_product_info()
        self.system_prompt = self._create_system_prompt()
    
    def _load_product_info(self) -> str:
        """从markdown文件加载产品信息"""
        try:
            # 假设你的产品信息文件在 docs 文件夹里
            product_file_path = os.path.join("docs", "products.md")
            with open(product_file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            print(f"警告: 产品信息文件未找到，请确保文件路径正确")
            return "产品信息暂时不可用"
    
    def _create_system_prompt(self) -> str:
        """创建系统prompt"""
        return f"""You are a professional car loan advisor AI assistant. Your task is to help customers understand loan products and provide them with the most suitable loan recommendations.

## Your Role and Responsibilities:
1. Answer customer questions about car loans in a friendly and professional manner
2. Recommend the most suitable loan products based on customers' specific situations
3. Clearly explain loan conditions, interest rates, application requirements, and other information
4. Help customers understand the application process and required documents

## Product Information:
{self.product_info}

## Response Guidelines:
1. Always maintain a friendly and professional tone
2. If the information requested by the customer is not available in the product information, honestly inform them and suggest contacting human customer service
3. When recommending products, consider the customer's specific needs (loan amount, credit score, financial situation, etc.)
4. Explain complex financial concepts in simple and clear language
5. If customers provide specific financial situations, analyze and recommend the most suitable products
6. Be thorough in your explanations but keep responses concise and actionable
7. Always prioritize the customer's best interests when making recommendations

Please respond to all questions in English unless specifically requested otherwise."""
    
    def create_chat_messages(self, user_message: str, chat_history: list = None) -> list:
        """创建完整的聊天消息列表"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 添加历史对话（如果有的话）
        if chat_history:
            for chat in chat_history:
                messages.append({"role": "user", "content": chat["user"]})
                messages.append({"role": "assistant", "content": chat["assistant"]})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": user_message})
        
        return messages
    
    def extract_user_requirements(self, user_message: str) -> Dict[str, Any]:
        """从用户消息中提取关键信息（可选功能）"""
        # 这里可以添加逻辑来解析用户的具体需求
        # 比如贷款金额、信用评分等
        requirements = {
            "loan_amount": None,
            "credit_score": None,
            "business_age": None,
            "property_owner": None
        }
        
        # 简单的关键词匹配（你可以后续优化）
        message_lower = user_message.lower()
        
        if "万" in user_message or "$" in user_message:
            # 可以添加更复杂的金额提取逻辑
            pass
            
        if "信用" in message_lower or "credit" in message_lower:
            # 可以添加信用评分提取逻辑
            pass
            
        return requirements