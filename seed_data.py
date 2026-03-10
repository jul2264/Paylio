from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from datetime import datetime, timedelta
import uuid

DATABASE_URL = "sqlite:///./backend/finance.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def seed():
    db = SessionLocal()
    
    # Check if user exists
    user = db.query(models.User).first()
    if not user:
        user = models.User(email="test@example.com", password_hash="hashed_pw")
        db.add(user)
        db.commit()
    
    # Categories
    cats = {c.category_name: c.category_id for c in db.query(models.Category).all()}
    
    # Accounts
    if not db.query(models.Account).first():
        acc1 = models.Account(user_id=user.user_id, account_name="HDFC Savings", account_type="bank", balance=85000.00)
        acc2 = models.Account(user_id=user.user_id, account_name="Credit Card", account_type="credit", balance=-12000.00)
        db.add_all([acc1, acc2])
        db.commit()
        
        # Transactions
        today = datetime.utcnow().date()
        txs = [
            # Income
            models.Transaction(account_id=acc1.account_id, amount=80000, transaction_type="credit", category_id=cats.get('Income'), merchant="Salary", description="Monthly Pay", transaction_date=today - timedelta(days=5)),
            # Expenses
            models.Transaction(account_id=acc1.account_id, amount=25000, transaction_type="debit", category_id=cats.get('Rent'), merchant="House Owner", description="Rent", transaction_date=today - timedelta(days=4)),
            models.Transaction(account_id=acc1.account_id, amount=450, transaction_type="debit", category_id=cats.get('Food'), merchant="Starbucks", description="Coffee", transaction_date=today - timedelta(days=3)),
            models.Transaction(account_id=acc1.account_id, amount=1200, transaction_type="debit", category_id=cats.get('Transport'), merchant="Uber", description="Ride to office", transaction_date=today - timedelta(days=2)),
            models.Transaction(account_id=acc1.account_id, amount=800, transaction_type="debit", category_id=cats.get('Shopping'), merchant="Amazon", description="Books", transaction_date=today - timedelta(days=1)),
            # Recurring
            models.Transaction(account_id=acc1.account_id, amount=499, transaction_type="debit", category_id=cats.get('Subscription'), merchant="Netflix", transaction_date=today - timedelta(days=10)),
            models.Transaction(account_id=acc1.account_id, amount=499, transaction_type="debit", category_id=cats.get('Subscription'), merchant="Netflix", transaction_date=today - timedelta(days=40)),
        ]
        db.add_all(txs)
        db.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed()
