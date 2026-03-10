import React, { useState } from 'react';
import axios from 'axios';
import { Send, User, Bot, Sparkles } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

function AICoach({ summary }) {
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
        <div className="glass-card" style={{ height: '600px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ paddingBottom: '1rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={20} color="var(--primary)" />
                <h3 style={{ margin: 0 }}>AI Financial Advisor</h3>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem 0', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {messages.map((m, i) => (
                    <div key={i} style={{
                        alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                        maxWidth: '80%',
                        background: m.role === 'user' ? 'var(--primary)' : 'rgba(255,255,255,0.05)',
                        padding: '12px 16px',
                        borderRadius: m.role === 'user' ? '16px 16px 0 16px' : '16px 16px 16px 0',
                        border: m.role === 'bot' ? '1px solid var(--border)' : 'none'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', fontSize: '0.75rem', opacity: 0.7 }}>
                            {m.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                            {m.role === 'user' ? 'You' : 'Coach'}
                        </div>
                        {m.content}
                    </div>
                ))}
                {loading && <div style={{ opacity: 0.5, fontSize: '0.9rem' }}>Coach is thinking...</div>}
            </div>

            <form onSubmit={sendMessage} style={{ display: 'flex', gap: '10px', marginTop: '1rem' }}>
                <input
                    type="text"
                    placeholder="Can I afford a 40,000 phone?"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    style={{
                        flex: 1,
                        background: 'rgba(0,0,0,0.2)',
                        border: '1px solid var(--border)',
                        borderRadius: '10px',
                        padding: '12px',
                        color: 'white',
                        outline: 'none'
                    }}
                />
                <button type="submit" className="button-primary" style={{ padding: '10px' }}>
                    <Send size={20} />
                </button>
            </form>
        </div>
    );
}

export default AICoach;
