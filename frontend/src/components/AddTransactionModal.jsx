import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Plus, IndianRupee, Tag, Store, Calendar as CalendarIcon } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function AddTransactionModal({ isOpen, onClose, onTransactionAdded, accounts, categories = [], currencySymbol = '₹' }) {
    const [formData, setFormData] = useState({
        account_id: '',
        amount: '',
        transaction_type: 'debit',
        category_id: '',
        merchant: '',
        transaction_date: new Date().toISOString().split('T')[0]
    });
    const [loading, setLoading] = useState(false);

    // Reset form when modal opens with fresh defaults
    useEffect(() => {
        if (isOpen) {
            const expenseCategories = categories.filter(c => c.category_name !== 'Income');
            setFormData({
                account_id: accounts.length > 0 ? accounts[0].account_id : '',
                amount: '',
                transaction_type: 'debit',
                category_id: expenseCategories.length > 0 ? expenseCategories[0].category_id : '',
                merchant: '',
                transaction_date: new Date().toISOString().split('T')[0]
            });
        }
    }, [isOpen, accounts, categories]);

    if (!isOpen) return null;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            // Ensure values exist
            let finalAccountId = formData.account_id || (accounts.length > 0 ? accounts[0].account_id : '');
            let finalCategoryId = formData.category_id;

            // If credit, find the 'Income' category ID
            if (formData.transaction_type === 'credit') {
                const incomeCat = categories.find(c => c.category_name === 'Income');
                finalCategoryId = incomeCat ? incomeCat.category_id : null;
            } else if (!finalCategoryId) {
                const expenseCategories = categories.filter(c => c.category_name !== 'Income');
                finalCategoryId = expenseCategories.length > 0 ? expenseCategories[0].category_id : '';
            }

            const payload = {
                ...formData,
                account_id: finalAccountId,
                category_id: finalCategoryId,
                amount: parseFloat(formData.amount)
            };

            await axios.post(`${API_BASE}/transactions`, payload);
            onTransactionAdded();
            onClose();
        } catch (err) {
            console.error("Failed to add transaction", err);
            alert("Failed to add transaction. Check console.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(5px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
            <div className="card" style={{ width: '450px', background: 'var(--card-bg)', animation: 'slideUp 0.3s ease-out' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Plus className="text-lime" /> Add Transaction
                    </h2>
                    <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                        <X size={24} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {/* Amount & Type */}
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Amount ({currencySymbol})</label>
                            <div style={{ position: 'relative' }}>
                                <span style={{ position: 'absolute', left: '15px', top: '11px', color: 'var(--text-muted)', fontSize: '1.1rem', fontWeight: '500' }}>{currencySymbol}</span>
                                <input
                                    type="number" required min="0.01" step="0.01"
                                    name="amount" value={formData.amount} onChange={handleChange}
                                    style={{ width: '100%', padding: '10px 10px 10px 38px', borderRadius: '12px', background: 'var(--card-hover)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                                />
                            </div>
                        </div>
                        <div style={{ width: '130px' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Type</label>
                            <select
                                name="transaction_type" value={formData.transaction_type} onChange={handleChange}
                                style={{ width: '100%', padding: '11px', borderRadius: '12px', background: 'var(--card-hover)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                            >
                                <option value="debit">Expense</option>
                                <option value="credit">Income</option>
                            </select>
                        </div>
                    </div>

                    {/* Merchant */}
                    <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Merchant / Title</label>
                        <div style={{ position: 'relative' }}>
                            <Store size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                            <input
                                type="text" required placeholder="e.g. Starbucks or Salary"
                                name="merchant" value={formData.merchant} onChange={handleChange}
                                style={{ width: '100%', padding: '10px 10px 10px 38px', borderRadius: '12px', background: 'var(--card-hover)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                            />
                        </div>
                    </div>

                    {/* Category & Date */}
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        {formData.transaction_type === 'debit' && (
                            <div style={{ flex: 1 }}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Category</label>
                                <div style={{ position: 'relative' }}>
                                    <Tag size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                                    <select
                                        name="category_id" value={formData.category_id} onChange={handleChange}
                                        style={{ width: '100%', padding: '11px 11px 11px 38px', borderRadius: '12px', background: 'var(--card-hover)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                                    >
                                        {categories.filter(c => c.category_name !== 'Income').map(c => (
                                            <option key={c.category_id} value={c.category_id}>{c.category_name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                        )}
                        <div style={{ flex: 1 }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem', color: 'var(--text-muted)' }}>Date</label>
                            <div style={{ position: 'relative' }}>
                                <CalendarIcon size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                                <input
                                    type="date" required
                                    name="transaction_date" value={formData.transaction_date} onChange={handleChange}
                                    style={{ width: '100%', padding: '10px 10px 10px 38px', borderRadius: '12px', background: 'var(--card-hover)', border: '1px solid var(--border-color)', color: 'var(--text-main)' }}
                                />
                            </div>
                        </div>
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
                        {loading ? 'Adding...' : 'Save Transaction'}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default AddTransactionModal;
