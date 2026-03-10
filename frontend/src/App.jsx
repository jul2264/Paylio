import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  LayoutDashboard,
  Receipt,
  User as UserIcon,
  TrendingUp,
  Plus
} from 'lucide-react';
import Dashboard from './components/Dashboard';
import TransactionList from './components/TransactionList';
import ProfileOverlay from './components/Profile';
import FloatingChatbot from './components/FloatingChatbot';
import AddTransactionModal from './components/AddTransactionModal';

const API_BASE = 'http://localhost:8000';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [categories, setCategories] = useState([]);

  const [theme, setTheme] = useState('dark');
  const [currency, setCurrency] = useState('INR');
  const currencySymbol = currency === 'INR' ? '₹' : (currency === 'USD' ? '$' : (currency === 'EUR' ? '€' : '£'));

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isTxModalOpen, setIsTxModalOpen] = useState(false);

  useEffect(() => {
    document.body.className = theme === 'light' ? 'light-mode' : '';
  }, [theme]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [summRes, txRes, accRes, catRes] = await Promise.all([
        axios.get(`${API_BASE}/analytics/summary`),
        axios.get(`${API_BASE}/transactions`),
        axios.get(`${API_BASE}/accounts`),
        axios.get(`${API_BASE}/categories`)
      ]);
      setSummary(summRes.data);
      setTransactions(txRes.data);
      setAccounts(accRes.data);
      setCategories(catRes.data);
    } catch (err) {
      console.error("Error fetching data:", err);
    }
  };

  const currentTabName = () => {
    if (activeTab === 'dashboard') return 'My Analytics';
    if (activeTab === 'transactions') return 'Transaction History';
    return '';
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '3rem', paddingLeft: '8px' }}>
          <div style={{ background: 'var(--accent-lime)', padding: '10px', borderRadius: '12px', color: '#111' }}>
            <TrendingUp size={24} strokeWidth={2.5} />
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, letterSpacing: '-0.03em' }}>Paylio.</h2>
        </div>

        <nav style={{ flex: 1, marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={() => setActiveTab('dashboard')}
            className="btn"
            style={{
              justifyContent: 'flex-start',
              background: activeTab === 'dashboard' ? (theme === 'light' ? 'rgba(0,0,0,0.05)' : 'var(--border-color)') : 'transparent',
              color: activeTab === 'dashboard' ? 'var(--accent-lime)' : (theme === 'light' ? 'var(--text-main)' : 'var(--text-muted)')
            }}
          >
            <LayoutDashboard size={20} /> Dashboard
          </button>
          <button
            onClick={() => setActiveTab('transactions')}
            className="btn"
            style={{
              justifyContent: 'flex-start',
              background: activeTab === 'transactions' ? (theme === 'light' ? 'rgba(0,0,0,0.05)' : 'var(--border-color)') : 'transparent',
              color: activeTab === 'transactions' ? 'var(--accent-lime)' : (theme === 'light' ? 'var(--text-main)' : 'var(--text-muted)')
            }}
          >
            <Receipt size={20} /> Transactions
          </button>
        </nav>

        {/* Bottom profile preview in sidebar -> Opens Settings Modal */}
        <div
          onClick={() => setIsProfileOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: '12px', marginTop: 'auto',
            padding: '1rem', background: 'var(--card-hover)', borderRadius: '16px',
            cursor: 'pointer', transition: 'all 0.2s'
          }}
          onMouseOver={(e) => e.currentTarget.style.background = 'var(--border-color)'}
          onMouseOut={(e) => e.currentTarget.style.background = 'var(--card-hover)'}
        >
          <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--accent-purple)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <UserIcon size={20} color="white" />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>John Doe</div>
            <div className="text-muted" style={{ fontSize: '0.8rem' }}>Settings & Profile</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-wrapper">
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
          <div>
            <h1 style={{ fontSize: '2.2rem', margin: 0, color: 'var(--text-main)' }}>{currentTabName()}</h1>
            <p className="text-muted" style={{ marginTop: '0.5rem' }}>Here's what's happening with your money today.</p>
          </div>

          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            {/* Action button moved to Transactions tab */}
          </div>
        </header>

        {/* Views */}
        {activeTab === 'dashboard' && <Dashboard summary={summary} transactions={transactions} accounts={accounts} currencySymbol={currencySymbol} />}
        {activeTab === 'transactions' && <TransactionList transactions={transactions} currencySymbol={currencySymbol} setIsTxModalOpen={setIsTxModalOpen} />}

        {/* Global Floating Chatbot & Modals */}
        <FloatingChatbot />
        <AddTransactionModal
          isOpen={isTxModalOpen}
          onClose={() => setIsTxModalOpen(false)}
          onTransactionAdded={fetchData}
          accounts={accounts}
          categories={categories}
          currencySymbol={currencySymbol}
        />
        <ProfileOverlay
          isOpen={isProfileOpen}
          onClose={() => setIsProfileOpen(false)}
          accounts={accounts}
          theme={theme}
          setTheme={setTheme}
          currency={currency}
          setCurrency={setCurrency}
          currencySymbol={currencySymbol}
        />
      </main>
    </div>
  );
}

function SidebarItem({ icon, label, active, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        padding: '14px 20px',
        borderRadius: '16px',
        cursor: 'pointer',
        background: active ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
        color: active ? 'white' : 'var(--text-muted)',
        transition: 'all 0.2s ease',
        fontWeight: active ? 600 : 500,
        boxShadow: active ? 'var(--shadow-sm)' : 'none'
      }}
    >
      <div style={{ color: active ? 'var(--accent-lime)' : 'inherit' }}>
        {icon}
      </div>
      <span style={{ fontSize: '1.05rem' }}>{label}</span>
      {active && <div style={{ marginLeft: 'auto', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-lime)' }} />}
    </div>
  );
}

export default App;
