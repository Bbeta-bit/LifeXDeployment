import React, { useState, useRef, useEffect } from 'react';
import { sendMessageToChatAPI } from '../services/api.js';

const Chatbot = ({ onNewMessage, conversationHistory }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // 自动滚动到底部
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: 'user', text: input };
    setMessages((prev) => [...prev, userMessage]);
    
    // 通知父组件有新的用户消息
    if (onNewMessage) {
      onNewMessage({
        role: 'user',
        content: input,
        timestamp: new Date().toISOString()
      });
    }
    
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    try {
      // 调用后端API
      const reply = await sendMessageToChatAPI(currentInput);
      
      // 添加AI回复
      const botMessage = { sender: 'bot', text: reply };
      setMessages((prev) => [...prev, botMessage]);
      
      // 通知父组件有新的AI回复
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: reply,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Error calling API:', error);
      
      // 显示错误信息
      const errorMessage = 'Sorry, we encountered a technical issue. Please try again later. If the problem persists, please contact customer service.';
      const botErrorMessage = { sender: 'bot', text: errorMessage };
      
      setMessages((prev) => [...prev, botErrorMessage]);
      
      // 通知父组件错误消息
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: errorMessage,
          timestamp: new Date().toISOString()
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header with Logo and Title */}
      <div className="relative px-4 py-3 border-b bg-white shadow-sm">
        {/* Logo - 固定在左上角 */}
        <a 
          href="https://lifex.com.au/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="absolute left-4 top-2 z-10"
        >
          <img 
            src="/lifex-logo.png" 
            alt="LIFEX Logo" 
            className="h-6 w-auto hover:opacity-80 transition-opacity"
          />
        </a>
        
        {/* Centered Title - 位置更低 */}
        <div className="flex justify-center items-center pt-6">
          <h1 className="text-lg font-semibold text-gray-800">Agent X</h1>
        </div>
      </div>

      {/* Chat Messages */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-4 py-4 bg-gray-100 space-y-3"
      >
        {messages.length === 0 && (
          <div className="flex justify-center items-center h-full">
            <div className="text-center text-gray-500">
              <p className="text-lg mb-2">Hello, how can I help you today?</p>
              <p className="text-sm">Start by telling us about your loan preferences</p>
            </div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-4 py-2 rounded-lg max-w-[70%] whitespace-pre-wrap text-sm ${
                m.sender === 'user' ? 'bg-green-200' : 'bg-white border'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-lg bg-white border text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="px-4 py-3 bg-white border-t shadow-sm">
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Tell us your loan preferences, like interest rate or repayment term"
            className="w-full resize-none overflow-hidden rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`absolute right-2 bottom-2 text-sm font-semibold ${
              isLoading || !input.trim() 
                ? 'text-gray-400 cursor-not-allowed' 
                : 'text-blue-600 hover:underline'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;