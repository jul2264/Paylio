from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional
from datetime import datetime
import models
import analytics
import ai_advisor
from pydantic import BaseModel
from decimal import Decimal

# --- Configuration ---
DATABASE_URL = "sqlite:///./finance.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Money Management AI API")

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Pydantic Schemas ---
class TransactionCreate(BaseModel):
    account_id: str
    amount: float
    transaction_type: str
    category_id: Optional[str] = None
    merchant: Optional[str] = None
    description: Optional[str] = None
    transaction_date: str

class AccountCreate(BaseModel):
    user_id: str
    account_name: str
    account_type: str
    balance: float

class QuestionRequest(BaseModel):
    question: str

# --- Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Money Management AI API"}

# Accounts
@app.post("/accounts")
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    db_account = models.Account(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@app.get("/accounts")
def get_accounts(db: Session = Depends(get_db)):
    return db.query(models.Account).all()

# Categories
@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).all()

# Transactions
@app.post("/transactions")
def add_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    tx_dict = transaction.dict()
    # Convert date string to date object
    tx_dict['transaction_date'] = datetime.strptime(tx_dict['transaction_date'], "%Y-%m-%d").date()
    db_tx = models.Transaction(**tx_dict)
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    return db_tx

@app.get("/transactions")
def get_transactions(db: Session = Depends(get_db)):
    transactions = db.query(models.Transaction).order_by(models.Transaction.transaction_date.desc()).all()
    result = []
    for tx in transactions:
        cat = db.query(models.Category).filter(models.Category.category_id == tx.category_id).first()
        tx_dict = {
            "transaction_id": tx.transaction_id,
            "account_id": tx.account_id,
            "amount": float(tx.amount),
            "transaction_type": tx.transaction_type,
            "category_id": tx.category_id,
            "category_name": cat.category_name if cat else ("Income" if tx.transaction_type == 'credit' else "Uncategorized"),
            "merchant": tx.merchant,
            "description": tx.description,
            "transaction_date": tx.transaction_date.isoformat()
        }
        result.append(tx_dict)
    return result

# Analytics
@app.get("/analytics/summary")
def get_analytics(db: Session = Depends(get_db)):
    txs = db.query(models.Transaction).all()
    # Join with category to get names
    tx_list = []
    for t in txs:
        cat = db.query(models.Category).filter(models.Category.category_id == t.category_id).first()
        tx_list.append({
            "amount": float(t.amount),
            "transaction_type": t.transaction_type,
            "category_name": cat.category_name if cat else "Other",
            "merchant": t.merchant or "Unknown",
            "transaction_date": t.transaction_date.isoformat()
        })
    
    summary = analytics.AnalyticsEngine.get_financial_summary(tx_list)
    return summary

# AI Advice
@app.post("/ai/advice")
def get_ai_advice(req: QuestionRequest, db: Session = Depends(get_db)):
    # Get current summary
    summary_data = get_analytics(db)
    advice = ai_advisor.AIAdvisorService.generate_advice(summary_data, req.question)
    return {"answer": advice}

# Seed Categories if empty
@app.on_event("startup")
def seed_data():
    db = SessionLocal()
    if not db.query(models.Category).first():
        cats = ['Food', 'Transport', 'Rent', 'Shopping', 'Entertainment', 'Subscription', 'Utilities', 'Healthcare', 'Savings', 'Income']
        for c in cats:
            db.add(models.Category(category_name=c))
        db.commit()
    db.close()
