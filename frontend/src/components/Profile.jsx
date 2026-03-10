import React, { useState } from 'react';
import { User, Shield, CreditCard, Settings, Bell, ChevronRight, LogOut, X, CheckCircle2, Lock, Smartphone, Globe, Moon, Key } from 'lucide-react';
function ProfileOverlay({ isOpen, onClose, accounts, theme, setTheme, currency, setCurrency, currencySymbol }) {
    const [activeView, setActiveView] = useState('account'); // 'account', 'security', 'notifications', 'settings'
    const [actionFeedback, setActionFeedback] = useState(null);

    if (!isOpen) return null;

    const showFeedback = (message) => {
        setActionFeedback(message);
        setTimeout(() => setActionFeedback(null), 3000);
    };

    const renderAccountDetails = () => (
        <>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Account Details</h3>

            <div style={{ marginBottom: '2rem' }}>
                <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)' }}>
                    <CreditCard size={20} /> Bank Integrations
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {accounts.map(acc => (
                        <div key={acc.account_id} style={{
                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                            padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                                <div style={{ padding: '10px', background: 'var(--card-bg)', borderRadius: '12px' }}>
                                    <CreditCard size={24} className="text-lime" />
                                </div>
                                <div>
                                    <div style={{ fontWeight: 600 }}>{acc.account_name}</div>
                                    <div className="text-muted" style={{ fontSize: '0.85rem' }}>{acc.account_type.toUpperCase()}</div>
                                </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                                <div style={{ fontWeight: 600 }}>{currencySymbol}{parseFloat(acc.balance).toLocaleString()}</div>
                                <ChevronRight size={20} className="text-muted" />
                            </div>
                        </div>
                    ))}
                    <button className="btn" onClick={() => showFeedback('Plaid/Yodlee integration linking started.')} style={{ background: 'transparent', border: '1px dashed var(--accent-purple)', color: 'var(--accent-purple-light)', width: '100%', marginTop: '0.5rem', padding: '14px' }}>
                        + Connect Another Bank
                    </button>
                </div>
            </div>

            <div>
                <h4 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)' }}>
                    Active Subscriptions
                </h4>
                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                        <span>Netflix Premium</span>
                        <span style={{ fontWeight: 600 }}>{currencySymbol}649/mo</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Spotify </span>
                        <span style={{ fontWeight: 600 }}>{currencySymbol}119/mo</span>
                    </div>
                    <div style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '1rem' }}>
                        <button className="btn btn-purple" onClick={() => showFeedback('Subscription manager opened.')} style={{ width: '100%' }}>Manage Auto-Payments</button>
                    </div>
                </div>
            </div>
        </>
    );

    const renderSecurity = () => (
        <>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Security & Privacy</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <Key className="text-lime" />
                        <div>
                            <div style={{ fontWeight: 600 }}>Password Reset</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>Change your account password</div>
                        </div>
                    </div>
                    <button className="btn" onClick={() => showFeedback('Password reset email sent!')} style={{ background: 'rgba(255,255,255,0.1)' }}>Update</button>
                </div>

                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <Smartphone className="text-purple" />
                        <div>
                            <div style={{ fontWeight: 600 }}>Two-Factor Authentication</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>Enhance security with 2FA</div>
                        </div>
                    </div>
                    <button className="btn btn-primary" onClick={() => showFeedback('2FA Configuration Started.')}>Enable</button>
                </div>

                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <Lock className="text-red" />
                        <div>
                            <div style={{ fontWeight: 600 }}>Data Privacy Center</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>Manage how your data is used</div>
                        </div>
                    </div>
                    <button className="btn" onClick={() => showFeedback('Privacy settings exported.')} style={{ background: 'rgba(255,255,255,0.1)' }}>Manage</button>
                </div>
            </div>
        </>
    );

    const renderNotifications = () => (
        <>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>Notifications</h3>

            <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', marginBottom: '1rem' }}>
                <h4 style={{ marginBottom: '1rem', color: 'var(--accent-lime)' }}>Budget Alerts</h4>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <span>80% Budget Exceeded</span>
                    <input type="checkbox" defaultChecked style={{ width: '20px', height: '20px', accentColor: 'var(--accent-lime)' }} onChange={() => showFeedback('Alert setting saved.')} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>100% Budget Exceeded</span>
                    <input type="checkbox" defaultChecked style={{ width: '20px', height: '20px', accentColor: 'var(--accent-lime)' }} onChange={() => showFeedback('Alert setting saved.')} />
                </div>
            </div>

            <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)' }}>
                <h4 style={{ marginBottom: '1rem', color: 'var(--accent-purple-light)' }}>Transaction Alerts</h4>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <span>Unusual Spending Detected</span>
                    <input type="checkbox" defaultChecked style={{ width: '20px', height: '20px', accentColor: 'var(--accent-lime)' }} onChange={() => showFeedback('Alert setting saved.')} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>Weekly Summary Email</span>
                    <input type="checkbox" style={{ width: '20px', height: '20px', accentColor: 'var(--accent-lime)' }} onChange={() => showFeedback('Alert setting saved.')} />
                </div>
            </div>
        </>
    );

    const renderSettings = () => (
        <>
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>General Settings</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <Globe className="text-blue" />
                        <div>
                            <div style={{ fontWeight: 600 }}>Default Currency</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>
                                <select
                                    value={currency}
                                    onChange={(e) => { setCurrency(e.target.value); showFeedback(`Currency changed to ${e.target.value}`); }}
                                    style={{ background: 'var(--card-bg)', color: 'inherit', border: '1px solid var(--border-color)', outline: 'none', cursor: 'pointer', padding: '4px 8px', borderRadius: '8px' }}
                                >
                                    <option value="INR">Indian Rupee (INR)</option>
                                    <option value="USD">US Dollar (USD)</option>
                                    <option value="EUR">Euro (EUR)</option>
                                    <option value="GBP">British Pound (GBP)</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <Moon className="text-purple" />
                        <div>
                            <div style={{ fontWeight: 600 }}>App Theme</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>Currently using {theme === 'dark' ? 'Dark' : 'Light'} Mode</div>
                        </div>
                    </div>
                    <button className="btn" onClick={() => { setTheme(theme === 'dark' ? 'light' : 'dark'); showFeedback(`Switched to ${theme === 'dark' ? 'light' : 'dark'} mode`); }} style={{ background: 'rgba(123, 66, 246, 0.2)', color: 'var(--accent-purple)' }}>{theme === 'dark' ? 'Switch to Light' : 'Switch to Dark'}</button>
                </div>

                <div style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                        <LogOut className="text-red" />
                        <div>
                            <div style={{ fontWeight: 600, color: 'var(--accent-red)' }}>Delete Account</div>
                            <div className="text-muted" style={{ fontSize: '0.85rem' }}>Permanently delete all financial data</div>
                        </div>
                    </div>
                    <button className="btn" onClick={() => showFeedback('Initiating Account Deletion protocol...')} style={{ background: 'var(--accent-red)', color: '#fff' }}>Delete</button>
                </div>
            </div>
        </>
    );

    return (
        <div style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(5px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
            <div className="card" style={{ width: '850px', maxWidth: '95vw', height: '80vh', display: 'grid', gridTemplateColumns: '1fr 1.8fr', padding: 0, overflow: 'hidden', animation: 'slideUp 0.3s ease-out' }}>

                {/* Sidebar portion */}
                <div style={{ background: 'var(--card-hover)', padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', borderRight: '1px solid var(--border-color)' }}>
                    <div
                        onClick={() => setActiveView('account')}
                        style={{
                            width: '120px', height: '120px', borderRadius: '50%',
                            background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-blue))',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            marginBottom: '1.5rem', boxShadow: '0 8px 16px rgba(123, 66, 246, 0.3)',
                            cursor: 'pointer'
                        }}>
                        <User size={60} color="white" />
                    </div>
                    <h2 onClick={() => setActiveView('account')} style={{ fontSize: '1.8rem', marginBottom: '0.2rem', cursor: 'pointer' }}>John Doe</h2>
                    <p className="text-muted" style={{ marginBottom: '2rem' }}>john.doe@example.com</p>

                    <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                        <button className="btn" onClick={() => setActiveView('security')} style={{ background: activeView === 'security' ? (theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)') : 'transparent', color: activeView === 'security' ? 'var(--text-main)' : 'var(--text-muted)', justifyContent: 'flex-start', padding: '12px 16px', border: activeView === 'security' ? '1px solid var(--accent-lime)' : '1px solid var(--border-color)' }}>
                            <Shield size={18} style={{ marginRight: '10px', color: activeView === 'security' ? 'var(--accent-lime)' : 'inherit' }} /> Security & Privacy
                        </button>
                        <button className="btn" onClick={() => setActiveView('notifications')} style={{ background: activeView === 'notifications' ? (theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)') : 'transparent', color: activeView === 'notifications' ? 'var(--text-main)' : 'var(--text-muted)', justifyContent: 'flex-start', padding: '12px 16px', border: activeView === 'notifications' ? '1px solid var(--accent-lime)' : '1px solid var(--border-color)' }}>
                            <Bell size={18} style={{ marginRight: '10px', color: activeView === 'notifications' ? 'var(--accent-lime)' : 'inherit' }} /> Notifications
                        </button>
                        <button className="btn" onClick={() => setActiveView('settings')} style={{ background: activeView === 'settings' ? (theme === 'light' ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.1)') : 'transparent', color: activeView === 'settings' ? 'var(--text-main)' : 'var(--text-muted)', justifyContent: 'flex-start', padding: '12px 16px', border: activeView === 'settings' ? '1px solid var(--accent-lime)' : '1px solid var(--border-color)' }}>
                            <Settings size={18} style={{ marginRight: '10px', color: activeView === 'settings' ? 'var(--accent-lime)' : 'inherit' }} /> General Settings
                        </button>
                    </div>

                    <button className="btn" onClick={() => showFeedback('Signing out entirely...')} style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--accent-red)', marginTop: 'auto', width: '100%' }}>
                        <LogOut size={18} style={{ marginRight: '8px' }} /> Sign Out
                    </button>
                </div>

                {/* Content portion */}
                <div style={{ padding: '2.5rem', overflowY: 'auto', position: 'relative' }}>
                    <button onClick={onClose} style={{ position: 'absolute', top: '20px', right: '20px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                        <X size={24} />
                    </button>

                    {/* Action Feedback Overlay */}
                    {actionFeedback && (
                        <div style={{ position: 'absolute', top: '80px', left: '2.5rem', right: '2.5rem', background: 'rgba(16, 185, 129, 0.9)', color: '#fff', padding: '12px 20px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1.5rem', animation: 'slideDown 0.3s ease-out', zIndex: 10, boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }}>
                            <CheckCircle2 size={20} /> {actionFeedback}
                        </div>
                    )}

                    {/* Render active view */}
                    {activeView === 'account' && renderAccountDetails()}
                    {activeView === 'security' && renderSecurity()}
                    {activeView === 'notifications' && renderNotifications()}
                    {activeView === 'settings' && renderSettings()}

                </div>
            </div>
        </div>
    );
}

export default ProfileOverlay;
