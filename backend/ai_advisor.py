from typing import Dict, List, Optional
import json
import requests

class AIAdvisorService:
    @staticmethod
    def generate_advice(financial_summary: Dict, question: Optional[str] = None) -> str:
        prompt = AIAdvisorService.get_structured_prompt(financial_summary, question or "Please provide a brief general analysis of my financial health.")
        
        try:
            res = requests.post("http://localhost:11434/api/generate", json={
                "model": "qwen:4b",
                "prompt": prompt,
                "stream": False
            }, timeout=15)
            
            if res.status_code == 200:
                return res.json().get("response", "No response from AI.")
        except Exception as e:
            print(f"Ollama connection error: {e}")
            
        # Fallback Mock Logic
        income = financial_summary.get("total_income", 0)
        expenses = financial_summary.get("total_expenses", 0)
        savings_rate = financial_summary.get("savings_rate", 0)
        recurring = financial_summary.get("recurring_subscriptions", [])
        top_categories = financial_summary.get("top_categories", {})
        
        if question and "afford" in question.lower():
            import re
            amounts = re.findall(r'\d+', question.lower())
            if amounts:
                cost = float(amounts[0])
                monthly_savings = income - expenses
                impact = (monthly_savings - cost) / income * 100 if income > 0 else -100
                if impact >= 10:
                    return f"(Fallback) You can afford this. Your savings rate would drop from {savings_rate}% to {round(impact, 2)}%."
                elif impact >= 0:
                    return f"(Fallback) You can afford it, but it reduces your savings rate to {round(impact, 2)}%."
                else:
                    return f"(Fallback) Buying this would put you in a deficit of ₹{abs(monthly_savings - cost):.2f}."
            
        return "(Fallback) Make sure Ollama (qwen:4b) is running locally for full AI advice. You're doing well!"

    @staticmethod
    def get_structured_prompt(financial_summary: Dict, question: str) -> str:
        """Helper for Ollama/OpenAI integration"""
        return f"""
You are a financial advisor. Based on the user's data, answer: "{question}"

User Data:
- Monthly Income: ₹{financial_summary.get('total_income')}
- Monthly Expenses: ₹{financial_summary.get('total_expenses')}
- Savings Rate: {financial_summary.get('savings_rate')}%
- Top Categories: {json.dumps(financial_summary.get('top_categories'))}

Provide concise, data-driven advice.
"""
