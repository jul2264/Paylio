import React from 'react';
import { ShoppingBag, Coffee, Car, Home, TrendingUp, Filter, Smartphone, MonitorPlay, Plus } from 'lucide-react';

const getIconForCategory = (categoryName) => {
    if (!categoryName) return <ShoppingBag />;
    const lower = categoryName.toLowerCase();
    if (lower.includes('food')) return <Coffee />;
    if (lower.includes('transport')) return <Car />;
    if (lower.includes('rent')) return <Home />;
    if (lower.includes('subscription')) return <MonitorPlay />;
    if (lower.includes('shopping')) return <Smartphone />;
    if (lower.includes('income')) return <TrendingUp />;
    return <ShoppingBag />;
};
function TransactionList({ transactions, currencySymbol, setIsTxModalOpen }) {
    if (transactions.length === 0) {
        return (
            <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
                <div style={{ marginBottom: '1.5rem' }}>
                    <button className="btn btn-primary" onClick={() => setIsTxModalOpen(true)}>
                        <Plus size={20} /> Add Transaction
                    </button>
                </div>
                <p className="text-muted">No transactions found. Start by adding one!</p>
            </div>
        );
    }

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ margin: 0 }}>Recent Transactions</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <button className="btn btn-primary" onClick={() => setIsTxModalOpen(true)}>
                        <Plus size={20} /> Add Transaction
                    </button>
                    <button className="btn" style={{ background: 'var(--card-hover)', color: 'var(--text-main)', padding: '8px 16px' }}>
                        <Filter size={16} style={{ marginRight: '8px' }} /> Filter
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                {transactions.map((tx) => {
                    const isIncome = tx.transaction_type === 'credit';
                    const icon = getIconForCategory(tx.category_name);
                    const dateStr = new Date(tx.transaction_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

                    return (
                        <div key={tx.transaction_id} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '1.2rem', background: 'var(--card-hover)', borderRadius: '16px',
                            transition: 'all 0.2s ease', cursor: 'pointer'
                        }}
                            onMouseOver={(e) => e.currentTarget.style.transform = 'translateX(5px)'}
                            onMouseOut={(e) => e.currentTarget.style.transform = 'translateX(0)'}
                        >

                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{
                                    width: '48px', height: '48px', borderRadius: '14px',
                                    background: isIncome ? 'rgba(201, 244, 92, 0.1)' : 'rgba(123, 66, 246, 0.1)',
                                    color: isIncome ? 'var(--accent-lime)' : 'var(--accent-purple)',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}>
                                    {icon}
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '1.05rem', marginBottom: '0.2rem', color: 'var(--text-main)' }}>
                                        {tx.merchant || 'General Transaction'}
                                    </div>
                                    <div className="text-muted" style={{ fontSize: '0.85rem', display: 'flex', gap: '10px' }}>
                                        <span>{dateStr}</span>
                                        <span style={{ color: isIncome ? 'var(--accent-lime)' : 'var(--accent-purple)' }}>• {tx.category_name}</span>
                                    </div>
                                </div>
                            </div>

                            <div style={{
                                fontWeight: 700, fontSize: '1.1rem',
                                color: isIncome ? 'var(--accent-lime)' : 'var(--text-main)'
                            }}>                                {isIncome ? '+' : '-'}{currencySymbol}{parseFloat(tx.amount).toLocaleString()}
                            </div>

                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default TransactionList;
