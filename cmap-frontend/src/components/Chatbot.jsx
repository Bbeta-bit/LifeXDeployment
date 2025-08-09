import React, { useState, useRef, useEffect } from 'react';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // 固定后端URL
  const API_BASE_URL = 'https://lifex-backend.onrender.com';
  
  // 初始化
  useEffect(() => {
    // 创建会话ID
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
    setSessionId(newSessionId);
    
    // 添加欢迎消息
    const welcomeMessage = {
      sender: 'bot',
      text: "Hello! I'm Agent X, here to help you find the perfect loan product. Tell me about what you're looking to finance and I'll find the best options for you.",
      timestamp: new Date().toISOString()
    };
    setMessages([welcomeMessage]);
    
    // 检查连接
    checkConnection();
  }, []);

  // 简单的连接检查
  const checkConnection = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        mode: 'cors',
      });
      
      if (response.ok) {
        setIsConnected(true);
      }
    } catch (error) {
      console.log('Connection check failed:', error);
      setIsConnected(false);
    }
  };

  // 发送消息
  const sendMessage = async (message, sessionId, chatHistory = []) => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message,
        session_id: sessionId,
        history: chatHistory
      }),
      mode: 'cors',
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  };

  // 处理发送
  const handleSend = async () => {
    if (!input.trim() || isLoading || !sessionId) return;

    const userMessage = { 
      sender: 'user', 
      text: input,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    // 通知父组件
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
      // 构建完整对话历史
      const fullChatHistory = [
        ...conversationHistory,
        {
          role: 'user',
          content: currentInput,
          timestamp: new Date().toISOString()
        }
      ];
      
      // 发送到后端
      const apiResponse = await sendMessage(currentInput, sessionId, fullChatHistory);
      
      if (apiResponse && apiResponse.status === 'success') {
        const replyText = apiResponse.reply;
        
        // 处理推荐
        if (apiResponse.recommendations && apiResponse.recommendations.length > 0) {
          if (onRecommendationUpdate) {
            onRecommendationUpdate(apiResponse.recommendations);
          }
        }
        
        // 添加回复
        const botMessage = { 
          sender: 'bot', 
          text: replyText,
          timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, botMessage]);
        
        // 通知父组件
        if (onNewMessage) {
          onNewMessage({
            role: 'assistant',
            content: replyText,
            timestamp: new Date().toISOString()
          });
        }
      } else {
        throw new Error('API returned error status');
      }
      
    } catch (error) {
      console.error('Send failed:', error);
      
      let errorMessage = "I'm having trouble connecting. Please try again in a moment.";
      if (error.message.includes('timeout')) {
        errorMessage = "Request timed out. Please try again.";
      }
      
      const botErrorMessage = { 
        sender: 'bot', 
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages(prev => [...prev, botErrorMessage]);
      
    } finally {
      setIsLoading(false);
    }
  };

  // 自动滚动
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // 输入处理
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
    <div className="flex flex-col h-full" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b" style={{ backgroundColor: '#fef7e8' }}>
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
          <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
        </div>
      </div>

      {/* 连接状态 */}
      {!isConnected && (
        <div className="px-6 py-2 bg-yellow-50 border-b border-yellow-200">
          <div className="text-yellow-700 text-sm">
            ⚠️ Connecting to service... Please wait
          </div>
        </div>
      )}

      {/* 聊天区域 */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
        style={{ backgroundColor: '#fef7e8' }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-5 py-3 rounded-2xl max-w-[75%] whitespace-pre-wrap text-base ${
                m.sender === 'user' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : m.isError
                  ? 'bg-red-50 border border-red-200 text-red-700'
                  : 'bg-white border shadow-lg'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-5 py-3 rounded-2xl bg-white border text-gray-500 shadow-lg">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 输入区域 */}
      <div className="px-6 py-4 border-t" style={{ backgroundColor: '#fef7e8' }}>
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={isConnected ? "Tell me about your loan requirements..." : "Connecting..."}
            className="w-full resize-none rounded-xl border border-gray-300 px-5 py-4 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
            disabled={isLoading || !sessionId || !isConnected}
            style={{ minHeight: '56px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || !sessionId || !isConnected}
            className={`absolute right-3 bottom-3 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              isLoading || !input.trim() || !sessionId || !isConnected
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        
        {/* 状态信息 */}
        <div className="mt-2 text-xs text-gray-500 text-center">
          {isConnected ? `Connected • Session: ${sessionId.slice(-6)}` : 'Connecting to service...'}
        </div>
      </div>
    </div>
  );
};

export default Chatbot;