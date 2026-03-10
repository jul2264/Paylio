import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
from decimal import Decimal

class AnalyticsEngine:
    @staticmethod
    def get_financial_summary(transactions: List[Dict]) -> Dict:
        if not transactions:
            return {
                "total_income": 0,
                "total_expenses": 0,
                "savings_rate": 0,
                "top_categories": {},
                "recurring_subscriptions": []
            }

        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].apply(float)
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])

        # Income vs Expenses
        income = df[df['transaction_type'] == 'credit']['amount'].sum()
        expenses = df[df['transaction_type'] == 'debit']['amount'].sum()
        
        savings = income - expenses
        savings_rate = (savings / income * 100) if income > 0 else 0

        # Category Breakdown
        category_spend = df[df['transaction_type'] == 'debit'].groupby('category_name')['amount'].sum().to_dict()
        
        # Recurring Patterns (Simple logic: similar amount, same merchant, approx 30 days)
        # In a real app, this would be more complex
        recurring = []
        merchant_groups = df[df['transaction_type'] == 'debit'].groupby('merchant')
        for merchant, group in merchant_groups:
            if len(group) >= 2:
                group = group.sort_values('transaction_date')
                diffs = group['transaction_date'].diff().dt.days.dropna()
                if all(25 <= d <= 35 for d in diffs):
                    avg_amount = group['amount'].mean()
                    recurring.append({
                        "merchant": merchant,
                        "amount": avg_amount,
                        "frequency": "monthly"
                    })

        return {
            "total_income": income,
            "total_expenses": expenses,
            "savings": savings,
            "savings_rate": round(savings_rate, 2),
            "top_categories": category_spend,
            "recurring_subscriptions": recurring
        }

    @staticmethod
    def detect_anomalies(transactions: List[Dict]) -> List[Dict]:
        if len(transactions) < 5:
            return []
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].apply(float)
        
        # Simple Z-score or 3x Average anomaly detection
        avg_spend = df[df['transaction_type'] == 'debit']['amount'].mean()
        anomalies = df[(df['transaction_type'] == 'debit') & (df['amount'] > avg_spend * 3)]
        
        return anomalies.to_dict('records')
