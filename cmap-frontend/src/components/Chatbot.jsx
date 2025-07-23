import React, { useState, useRef, useEffect } from 'react';
import { sendMessageToChatAPI } from '../services/api';

export default function Chatbot({ selectedLang }) {
  const [messages, setMessages] = useState([
    { sender: 'ai', text: 'Hello! How can I help you with your loan application?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatRef = useRef(null);

  const scrollToBottom = () => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = { sender: 'user', text: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const reply = await sendMessageToChatAPI(input.trim(), selectedLang);
      setMessages(prev => [...prev, { sender: 'ai', text: reply }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { sender: 'ai', text: 'Error: Failed to connect to server.' }]);
    }

    setLoading(false);
  };

  return (
    <div className="flex flex-col h-full">
      {/* 聊天框主体 */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto bg-gray-100 p-4 rounded border border-gray-300 shadow-inner"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`mb-3 flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`rounded-lg px-4 py-2 max-w-[70%] text-sm whitespace-pre-wrap
                ${m.sender === 'user' ? 'bg-green-200 text-right' : 'bg-white border border-gray-300'}
              `}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-gray-500 mt-2">AgentX is thinking...</div>}
      </div>

      {/* 输入栏 */}
      <div className="mt-4 flex items-center">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Enter your loan preferences, such as rate or term"
          disabled={loading}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 mr-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className={`px-4 py-2 rounded-lg font-semibold ${
            input.trim()
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-600 cursor-not-allowed'
          }`}
        >
          Send
        </button>
      </div>
    </div>
  );
}


