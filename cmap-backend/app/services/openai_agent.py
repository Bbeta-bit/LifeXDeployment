# app/services/openai_agent.py
import openai
import os

# 推荐将 API Key 存储为环境变量（更安全）
openai.api_key = os.getenv("OPENAI_API_KEY")

def ask_gpt(message: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}]
        )
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        return f"Error: {str(e)}"
