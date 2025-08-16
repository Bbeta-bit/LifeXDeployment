// Chatbot.jsx - Render部署优化版本
import React, { useState, useRef, useEffect } from 'react';
import { sendEnhancedMessage, checkConnection } from '../services/api.js';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate, onError }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [connectionError, setConnectionError] = useState(null);
  const [debugInfo, setDebugInfo] = useState({ lastSync: null, customerInfoReceived: null });
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

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
    initializeConnection();
  }, []);

  // 初始化连接
  const initializeConnection = async () => {
    try {
      console.log('🔄 Initializing connection...');
      const result = await checkConnection();
      
      if (result.connected) {
        setIsConnected(true);
        setConnectionError(null);
        console.log('✅ Connection established');
      } else {
        setIsConnected(false);
        setConnectionError('Unable to connect to server');
        console.warn('⚠️ Connection failed:', result.error);
      }
    } catch (error) {
      setIsConnected(false);
      setConnectionError('Connection initialization failed');
      console.error('❌ Connection initialization error:', error);
      
      if (onError) {
        onError(error);
      }
    }
  };

  // 客户信息同步监控
  useEffect(() => {
    if (customerInfo && Object.keys(customerInfo).length > 0) {
      setDebugInfo(prev => ({
        ...prev,
        lastSync: new Date().toISOString(),
        customerInfoReceived: Object.keys(customerInfo).length
      }));
      console.log('📊 Customer info updated:', customerInfo);
    }
  }, [customerInfo]);

  // 发送消息
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const currentInput = input.trim();
    setInput('');
    setIsLoading(true);

    // 添加用户消息
    const userMessage = { 
      sender: 'user', 
      text: currentInput,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);

    // 通知父组件
    if (onNewMessage) {
      onNewMessage({
        role: 'user',
        content: currentInput,
        timestamp: new Date().toISOString()
      });
    }

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
      
      console.log('📤 Sending with customerInfo:', customerInfo);
      
      const apiResponse = await sendEnhancedMessage(currentInput, sessionId, fullChatHistory, customerInfo);
      
      // 验证响应
      if (!apiResponse) {
        throw new Error('Empty response from server');
      }

      if (apiResponse.status === 'success' || apiResponse.status === 'basic_mode' || apiResponse.status === 'fallback') {
        const replyText = apiResponse.reply;
        
        // 处理推荐
        if (apiResponse.recommendations && Array.isArray(apiResponse.recommendations) && apiResponse.recommendations.length > 0) {
          console.log('📋 Received recommendations:', apiResponse.recommendations);
          
          // 验证推荐数据结构
          const validRecommendations = apiResponse.recommendations.filter(rec => 
            rec && rec.lender_name && rec.product_name && rec.base_rate !== undefined
          );
          
          if (validRecommendations.length > 0 && onRecommendationUpdate) {
            console.log('📋 Updating with valid recommendations:', validRecommendations);
            onRecommendationUpdate(validRecommendations);
          } else {
            console.warn('⚠️ Received invalid recommendation data');
          }
        }
        
        // 添加回复
        const botMessage = { 
          sender: 'bot', 
          text: replyText,
          timestamp: new Date().toISOString(),
          status: apiResponse.status
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
        
        // 更新调试信息
        setDebugInfo(prev => ({
          ...prev,
          lastApiCall: new Date().toISOString(),
          lastResponseStatus: apiResponse.status
        }));
        
      } else {
        // 处理API返回的错误状态
        const errorMessage = apiResponse.reply || 'Server returned an error status';
        throw new Error(errorMessage);
      }
      
    } catch (error) {
      console.error('❌ Send failed:', error);
      
      // 智能的错误处理和用户友好的错误消息
      let errorMessage = "I'm having trouble connecting. Please try again in a moment.";
      
      if (error.name === 'AbortError' || error.message.includes('timeout')) {
        errorMessage = "Request timed out. The server might be busy. Please try again.";
      } else if (error.message.includes('HTTP 429')) {
        errorMessage = "Server is currently busy. Please wait a moment and try again.";
      } else if (error.message.includes('HTTP 500')) {
        errorMessage = "There's a temporary server issue. Please try again in a few minutes.";
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage = "Network connection issue. Please check your internet connection and try again.";
        // 标记为未连接，下次会自动重连
        setIsConnected(false);
      } else if (error.message.includes('Unable to connect')) {
        errorMessage = error.message;
        setIsConnected(false);
      }
      
      const botErrorMessage = { 
        sender: 'bot', 
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages(prev => [...prev, botErrorMessage]);
      
      // 通知父组件错误
      if (onError) {
        onError(error);
      }
      
      // 更新调试信息
      setDebugInfo(prev => ({
        ...prev,
        lastApiCall: new Date().toISOString(),
        lastResponseStatus: 'error',
        lastError: error.message
      }));
      
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

  // 重连功能
  const handleReconnect = async () => {
    setConnectionError(null);
    await initializeConnection();
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b" style={{ backgroundColor: '#fef7e8' }}>
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
          
          {/* 连接状态指示器 */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
            <span className="text-xs text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {/* 调试信息显示（开发模式） */}
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-gray-500">
              <div>Sync: {debugInfo.lastSync ? new Date(debugInfo.lastSync).toLocaleTimeString() : 'None'}</div>
              <div>Info: {debugInfo.customerInfoReceived || 0} fields</div>
            </div>
          )}
        </div>
      </div>

      {/* 连接错误提示 */}
      {connectionError && !isConnected && (
        <div className="mx-6 mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="text-yellow-700 text-sm">
              Connection issue detected. Some features may be limited.
            </div>
            <button
              onClick={handleReconnect}
              className="text-yellow-600 hover:text-yellow-800 text-sm underline"
            >
              Retry
            </button>
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
              {/* 显示状态（如果有） */}
              {m.status && m.status !== 'success' && (
                <div className="text-xs mt-1 opacity-60">
                  {m.status === 'basic_mode' && '(Basic Mode)'}
                  {m.status === 'fallback' && '(Limited Service)'}
                </div>
              )}
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
            placeholder={
              isLoading ? "Sending..." :
              !isConnected ? "Reconnecting..." :
              "Type your message..."
            }
            disabled={isLoading}
            className="w-full p-4 pr-16 rounded-xl border border-gray-300 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            style={{ maxHeight: '150px' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;