import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';
import { DollarSign, ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

const COLORS = ['#c9f45c', '#7b42f6', '#3b82f6', '#ef4444', '#10b981', '#f59e0b'];

function Dashboard({ summary, transactions, accounts, currencySymbol }) {
    if (!summary) return (
        <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px' }}>
            <Activity className="text-lime" size={48} style={{ animation: 'pulse 2s infinite' }} />
        </div>
    );

    const accountBalances = accounts.reduce((acc, curr) => acc + parseFloat(curr.balance), 0);
    const totalBalance = accountBalances + (summary.savings || 0);

    const categoryData = Object.keys(summary.top_categories).map(cat => ({
        name: cat,
        value: summary.top_categories[cat]
    }));

    const pieData = Object.keys(summary.top_categories).map(cat => ({
        name: cat,
        value: summary.top_categories[cat]
    }));

    return (
        <>
            {/* Top Stats */}
            <div className="dashboard-top">
                <div className="card card-lime" style={{ position: 'relative', overflow: 'hidden' }}>
                    <div className="stat-title" style={{ color: 'rgba(0,0,0,0.6)' }}>Total Balance</div>
                    <div className="stat-value">{currencySymbol}{totalBalance.toLocaleString()}</div>
                    <DollarSign size={80} style={{ position: 'absolute', right: '-10px', bottom: '-10px', opacity: 0.2 }} />
                </div>

                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <div className="stat-title">Monthly Income</div>
                            <div className="stat-value">{currencySymbol}{summary.total_income.toLocaleString()}</div>
                        </div>
                        <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '10px', borderRadius: '50%' }}>
                            <ArrowUpRight size={24} color="#10b981" />
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <div className="stat-title">Monthly Expenses</div>
                            <div className="stat-value text-red">{currencySymbol}{summary.total_expenses.toLocaleString()}</div>
                        </div>
                        <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '50%' }}>
                            <ArrowDownRight size={24} color="#ef4444" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Charts */}
            <div className="dashboard-main">
                <div className="card" style={{ padding: '2rem' }}>
                    <h3 style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        Spending Overview
                    </h3>
                    <div style={{ width: '100%', height: 320 }}>
                        <ResponsiveContainer>
                            <BarChart data={categoryData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                                <XAxis dataKey="name" stroke="var(--text-muted)" axisLine={false} tickLine={false} dy={10} />
                                <YAxis stroke="var(--text-muted)" axisLine={false} tickLine={false} dx={-10} />
                                <Tooltip
                                    cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                                    contentStyle={{ background: 'var(--card-hover)', border: '1px solid var(--border-color)', borderRadius: '16px', boxShadow: 'var(--shadow-lg)' }}
                                    itemStyle={{ color: 'var(--text-main)', fontWeight: 600 }}
                                />
                                <Bar dataKey="value" fill="url(#colorUv)" radius={[8, 8, 8, 8]} barSize={40} />
                                <defs>
                                    <linearGradient id="colorUv" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="var(--accent-purple)" stopOpacity={1} />
                                        <stop offset="100%" stopColor="var(--accent-purple-light)" stopOpacity={1} />
                                    </linearGradient>
                                </defs>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
                    <h3 style={{ marginBottom: '1rem' }}>Expense Breakdown</h3>
                    <div style={{ flex: 1, position: 'relative' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={pieData}
                                    innerRadius={70}
                                    outerRadius={100}
                                    paddingAngle={5}
                                    dataKey="value"
                                    stroke="none"
                                >
                                    {pieData.map((entry, index) => (
                                        <Cell key={`cell - ${index} `} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    contentStyle={{ background: 'var(--card-bg)', border: 'none', borderRadius: '12px', color: 'var(--text-main)' }}
                                    itemStyle={{ color: 'var(--text-main)' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                        <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center' }}>
                            <div style={{ fontSize: '2rem', fontWeight: 700 }}>{Object.keys(summary.top_categories).length}</div>
                            <div className="text-muted" style={{ fontSize: '0.8rem' }}>Sectors</div>
                        </div>
                    </div>
                    <div style={{ textAlign: 'center', marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                        <p style={{ margin: 0, fontSize: '0.9rem', color: summary.savings_rate >= 20 ? 'var(--accent-lime)' : 'var(--accent-red)' }}>
                            {summary.savings_rate >= 20 ? "You're hitting your 20% savings goal!" : "Watch your spending to hit your 20% goal."}
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}

export default Dashboard;
