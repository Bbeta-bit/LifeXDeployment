import React, { useState, useRef, useEffect } from 'react';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate, onError }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [connectionError, setConnectionError] = useState(null);
  
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

  // 🔧 增强的连接检查，带重试机制
  const checkConnection = async (retries = 3) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        console.log(`🔍 Checking connection (attempt ${attempt}/${retries})...`);
        
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          mode: 'cors',
          signal: AbortSignal.timeout(10000), // 10秒超时
        });
        
        if (response.ok) {
          console.log('✅ Connection successful');
          setIsConnected(true);
          setConnectionError(null);
          return;
        } else {
          console.warn(`⚠️ Health check failed: ${response.status}`);
        }
      } catch (error) {
        console.warn(`❌ Connection attempt ${attempt} failed:`, error.message);
        
        if (attempt === retries) {
          setConnectionError(`Failed to connect after ${retries} attempts`);
          setIsConnected(false);
          
          // 如果有错误回调，通知父组件
          if (onError) {
            onError(new Error(`Connection failed: ${error.message}`));
          }
        } else {
          // 等待后重试
          await new Promise(resolve => setTimeout(resolve, 2000 * attempt));
        }
      }
    }
  };

  // 🔧 修改发送消息函数，添加更强的错误处理
  const sendMessage = async (message, sessionId, chatHistory = [], currentCustomerInfo = null) => {
    const payload = {
      message: message,
      session_id: sessionId,
      history: chatHistory
    };

    // 🔧 添加当前客户信息到请求中
    if (currentCustomerInfo && Object.keys(currentCustomerInfo).length > 0) {
      // 过滤掉空值和undefined值
      const cleanedCustomerInfo = Object.fromEntries(
        Object.entries(currentCustomerInfo).filter(([key, value]) => 
          value !== null && value !== undefined && value !== ''
        )
      );
      
      if (Object.keys(cleanedCustomerInfo).length > 0) {
        payload.current_customer_info = cleanedCustomerInfo;
        console.log('🔄 Sending customer info to backend:', cleanedCustomerInfo);
      }
    }

    console.log('📤 Sending payload:', JSON.stringify(payload, null, 2));

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      mode: 'cors',
      signal: AbortSignal.timeout(30000), // 30秒超时
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const responseData = await response.json();
    console.log('📥 Received response:', responseData);
    return responseData;
  };

  // 🔧 修改处理发送函数，增强错误处理和用户反馈
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
      // 🔧 检查连接状态
      if (!isConnected) {
        console.log('🔄 Not connected, attempting to reconnect...');
        await checkConnection(1); // 快速重连尝试
        
        if (!isConnected) {
          throw new Error('Unable to connect to server. Please check your internet connection.');
        }
      }

      // 构建完整对话历史
      const fullChatHistory = [
        ...conversationHistory,
        {
          role: 'user',
          content: currentInput,
          timestamp: new Date().toISOString()
        }
      ];
      
      // 🔧 发送到后端时包含最新的customerInfo
      console.log('📤 Sending with customerInfo:', customerInfo);
      const apiResponse = await sendMessage(currentInput, sessionId, fullChatHistory, customerInfo);
      
      // 🔧 增强的响应验证
      if (!apiResponse) {
        throw new Error('Empty response from server');
      }

      if (apiResponse.status === 'success' && apiResponse.reply) {
        const replyText = apiResponse.reply;
        
        // 🔧 处理推荐 - 支持多个推荐的管理，增强验证
        if (apiResponse.recommendations && Array.isArray(apiResponse.recommendations) && apiResponse.recommendations.length > 0) {
          console.log('📋 Received recommendations:', apiResponse.recommendations);
          
          // 验证推荐数据结构
          const validRecommendations = apiResponse.recommendations.filter(rec => 
            rec && rec.lender_name && rec.product_name && rec.base_rate
          );
          
          if (validRecommendations.length > 0 && onRecommendationUpdate) {
            onRecommendationUpdate(validRecommendations);
          } else {
            console.warn('⚠️ Received invalid recommendation data');
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
        // 🔧 处理API返回的错误状态
        const errorMessage = apiResponse.reply || 'Server returned an error status';
        throw new Error(errorMessage);
      }
      
    } catch (error) {
      console.error('❌ Send failed:', error);
      
      // 🔧 更智能的错误处理和用户友好的错误消息
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
      
      // 🔧 通知父组件错误（如果有错误处理回调）
      if (onError) {
        onError(error);
      }
      
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

  // 🔧 重连功能
  const handleReconnect = async () => {
    setConnectionError(null);
    await checkConnection(3);
  };

  // 🔧 调试信息：监控customerInfo变化
  useEffect(() => {
    if (customerInfo && Object.keys(customerInfo).length > 0) {
      console.log('🔍 Chatbot received updated customerInfo:', customerInfo);
    }
  }, [customerInfo]);

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b" style={{ backgroundColor: '#fef7e8' }}>
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
          <div className="flex items-center space-x-3">
            {/* 连接状态指示器 */}
            <div className={`flex items-center text-xs ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}></div>
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
            
            {/* 🔧 添加同步状态指示器 */}
            {customerInfo && Object.keys(customerInfo).length > 0 && (
              <div className="text-xs text-blue-600 flex items-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                Form data synced
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 🔧 改进的连接状态显示 */}
      {!isConnected && (
        <div className="px-6 py-3 bg-red-50 border-b border-red-200">
          <div className="flex items-center justify-between">
            <div className="text-red-700 text-sm">
              ⚠️ {connectionError || 'Connecting to service...'}
            </div>
            <button
              onClick={handleReconnect}
              className="text-xs bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700"
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
              {/* 🔧 添加时间戳（开发时可见） */}
              {process.env.NODE_ENV === 'development' && (
                <div className="text-xs opacity-50 mt-1">
                  {new Date(m.timestamp).toLocaleTimeString()}
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
              !isConnected ? "Connecting..." :
              isLoading ? "Sending..." :
              "Tell me about your loan requirements..."
            }
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
          Press Enter to send • Shift+Enter for new line
          {/* 🔧 添加同步状态提示 */}
          {customerInfo && Object.keys(customerInfo).length > 0 && (
            <span className="ml-2 text-blue-600">
              • Form data will be included in requests
            </span>
          )}
          {/* 🔧 显示会话ID（开发时） */}
          {process.env.NODE_ENV === 'development' && sessionId && (
            <span className="ml-2 text-gray-400">
              • Session: {sessionId.split('_')[1]}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chatbot;