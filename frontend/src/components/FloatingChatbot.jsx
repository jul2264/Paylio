import React, { useState } from 'react';
import axios from 'axios';
import { MessageSquare, X, Send, User, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function FloatingChatbot() {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'bot', content: "Hello! I'm your AI Financial Coach. Ask me anything about your spending, budgets, or if you can afford that new gadget!" }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg = input;
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setLoading(true);

        try {
            const res = await axios.post(`${API_BASE}/ai/advice`, { question: userMsg });
            setMessages(prev => [...prev, { role: 'bot', content: res.data.answer }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'bot', content: "Sorry, I'm having trouble connecting to my brain right now." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <div className="chatbot-bubble" onClick={() => setIsOpen(!isOpen)}>
                {isOpen ? <X size={28} /> : <MessageSquare size={28} />}
            </div>

            {isOpen && (
                <div className="chatbot-window">
                    {/* Header */}
                    <div style={{
                        background: 'linear-gradient(135deg, var(--accent-purple), var(--accent-purple-light))',
                        padding: '1.2rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        color: 'white'
                    }}>
                        <Sparkles size={24} />
                        <div>
                            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>FinAI Assistant</h3>
                            <span style={{ fontSize: '0.8rem', opacity: 0.8 }}>Online</span>
                        </div>
                    </div>

                    {/* Chat History */}
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1rem'
                    }}>
                        {messages.map((m, i) => (
                            <div key={i} style={{
                                alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                                maxWidth: '85%',
                                background: m.role === 'user' ? 'var(--accent-purple)' : 'var(--card-hover)',
                                color: m.role === 'user' ? 'white' : 'var(--text-main)',
                                padding: '12px 16px',
                                borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                                fontSize: '0.95rem',
                                lineHeight: 1.4,
                                boxShadow: 'var(--shadow-sm)'
                            }}>
                                {m.content}
                            </div>
                        ))}
                        {loading && (
                            <div style={{ alignSelf: 'flex-start', opacity: 0.8, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 15px', background: 'var(--card-hover)', borderRadius: '12px', color: 'var(--accent-purple-light)' }}>
                                <div className="pulse-loader" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor' }}></div>
                                <div className="pulse-loader" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor', animationDelay: '0.2s' }}></div>
                                <div className="pulse-loader" style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'currentColor', animationDelay: '0.4s' }}></div>
                                <span style={{ marginLeft: '5px' }}>FinAI is thinking...</span>
                            </div>
                        )}
                    </div>

                    {/* Input Area */}
                    <form onSubmit={sendMessage} style={{
                        padding: '1rem',
                        borderTop: '1px solid var(--border-color)',
                        display: 'flex',
                        gap: '10px',
                        background: 'var(--card-bg)'
                    }}>
                        <input
                            type="text"
                            placeholder="Type your message here..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            style={{
                                flex: 1,
                                background: 'var(--card-hover)',
                                border: 'none',
                                borderRadius: 'var(--radius-full)',
                                padding: '12px 16px',
                                color: 'var(--text-main)',
                                outline: 'none',
                                fontFamily: 'Outfit, sans-serif'
                            }}
                        />
                        <button type="submit" className="btn-icon-only text-purple" style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }} disabled={loading}>
                            <Send size={24} style={{ opacity: loading ? 0.3 : 1, transition: 'opacity 0.2s' }} />
                        </button>
                    </form>
                </div>
            )}
        </>
    );
}

export default FloatingChatbot;
