import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { sendEnhancedMessage, checkConnection, performHealthChecks } from '../services/api.js';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate, onError }) => {
  // 状态管理
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [connectionState, setConnectionState] = useState({
    isConnected: false,
    isChecking: false,
    lastCheck: null,
    retryCount: 0
  });
  const [sessionId, setSessionId] = useState('');
  const [debugInfo, setDebugInfo] = useState({
    lastSync: null,
    customerInfoReceived: null,
    lastApiCall: null,
    responseTime: null
  });

  // Refs
  const chatRef = useRef(null);
  const textareaRef = useRef(null);
  const connectionCheckInterval = useRef(null);
  const retryTimeoutRef = useRef(null);

  // 生成唯一会话ID
  const generateSessionId = useCallback(() => {
    return `session_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  }, []);

  // 初始化
  useEffect(() => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    
    // 欢迎消息
    const welcomeMessage = {
      sender: 'bot',
      text: "Hello! I'm Agent X, here to help you find the perfect loan product. Tell me about what you're looking to finance and I'll find the best options for you.",
      timestamp: new Date().toISOString(),
      type: 'welcome'
    };
    setMessages([welcomeMessage]);
    
    // 初始化连接
    initializeConnection();
    
    // 清理函数
    return () => {
      if (connectionCheckInterval.current) {
        clearInterval(connectionCheckInterval.current);
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [generateSessionId]);

  // 智能连接管理
  const initializeConnection = useCallback(async () => {
    setConnectionState(prev => ({ ...prev, isChecking: true }));
    
    try {
      console.log('🔄 Initializing connection...');
      const healthChecks = await performHealthChecks();
      
      const isConnected = healthChecks.api_health;
      
      setConnectionState({
        isConnected,
        isChecking: false,
        lastCheck: Date.now(),
        retryCount: isConnected ? 0 : prev => prev.retryCount + 1
      });

      setDebugInfo(prev => ({
        ...prev,
        responseTime: healthChecks.response_time
      }));

      if (isConnected) {
        console.log('✅ Connection established');
        // 设置定期健康检查（每2分钟）
        if (connectionCheckInterval.current) {
          clearInterval(connectionCheckInterval.current);
        }
        connectionCheckInterval.current = setInterval(performPeriodicHealthCheck, 120000);
      } else {
        console.warn('⚠️ Connection failed, will retry...');
        scheduleRetry();
      }
      
    } catch (error) {
      console.error('❌ Connection initialization error:', error);
      setConnectionState(prev => ({
        ...prev,
        isConnected: false,
        isChecking: false,
        retryCount: prev.retryCount + 1
      }));
      
      if (onError) {
        onError(error);
      }
      scheduleRetry();
    }
  }, [onError]);

  // 定期健康检查
  const performPeriodicHealthCheck = useCallback(async () => {
    try {
      const result = await checkConnection();
      if (!result.connected && connectionState.isConnected) {
        console.warn('⚠️ Connection lost during periodic check');
        setConnectionState(prev => ({ ...prev, isConnected: false }));
        scheduleRetry();
      }
    } catch (error) {
      console.warn('⚠️ Periodic health check failed:', error);
    }
  }, [connectionState.isConnected]);

  // 智能重试调度
  const scheduleRetry = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }

    // 指数退避：3秒、6秒、12秒、30秒后停止
    const delays = [3000, 6000, 12000, 30000];
    const retryCount = connectionState.retryCount;
    
    if (retryCount < delays.length) {
      const delay = delays[retryCount];
      console.log(`🔄 Scheduling retry ${retryCount + 1} in ${delay}ms`);
      
      retryTimeoutRef.current = setTimeout(() => {
        initializeConnection();
      }, delay);
    } else {
      console.log('🛑 Max retry attempts reached, stopping retries');
    }
  }, [connectionState.retryCount, initializeConnection]);

  // 客户信息同步监控
  useEffect(() => {
    if (customerInfo && Object.keys(customerInfo).length > 0) {
      setDebugInfo(prev => ({
        ...prev,
        lastSync: new Date().toISOString(),
        customerInfoReceived: Object.keys(customerInfo).length
      }));
      console.log('📊 Customer info updated:', Object.keys(customerInfo).length, 'fields');
    }
  }, [customerInfo]);

  // 优化的消息发送
  const handleSend = useCallback(async () => {
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
      const startTime = Date.now();
      
      // 构建完整对话历史
      const fullChatHistory = [
        ...conversationHistory,
        {
          role: 'user',
          content: currentInput,
          timestamp: new Date().toISOString()
        }
      ];

      console.log('📤 Sending message with context:', {
        messageLength: currentInput.length,
        historyLength: fullChatHistory.length,
        customerFields: Object.keys(customerInfo || {}).length
      });

      const apiResponse = await sendEnhancedMessage(
        currentInput, 
        sessionId, 
        fullChatHistory, 
        customerInfo
      );

      const responseTime = Date.now() - startTime;
      setDebugInfo(prev => ({
        ...prev,
        lastApiCall: new Date().toISOString(),
        responseTime
      }));

      // 验证响应
      if (!apiResponse || !apiResponse.reply) {
        throw new Error('Invalid response from server');
      }

      const { reply, recommendations } = apiResponse;

      // 处理推荐
      if (recommendations && Array.isArray(recommendations) && recommendations.length > 0) {
        console.log('📋 Processing recommendations:', recommendations.length);
        
        const validRecommendations = recommendations.filter(rec => 
          rec && 
          rec.lender_name && 
          rec.product_name && 
          rec.base_rate !== undefined
        );

        if (validRecommendations.length > 0 && onRecommendationUpdate) {
          console.log('📋 Updating with valid recommendations:', validRecommendations.length);
          onRecommendationUpdate(validRecommendations);
        }
      }

      // 添加机器人回复（移除status相关逻辑）
      const botMessage = {
        sender: 'bot',
        text: reply,
        timestamp: new Date().toISOString(),
        responseTime
      };
      setMessages(prev => [...prev, botMessage]);

      // 通知父组件
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: reply,
          timestamp: new Date().toISOString()
        });
      }

      // 更新连接状态（成功的API调用表示连接正常）
      if (!connectionState.isConnected) {
        setConnectionState(prev => ({
          ...prev,
          isConnected: true,
          retryCount: 0
        }));
      }

    } catch (error) {
      console.error('❌ Send failed:', error);

      // 智能错误处理
      let errorMessage = "I'm having trouble connecting to our AI service. Please try again in a moment.";

      if (error.message.includes('timeout') || error.message.includes('AbortError')) {
        errorMessage = "Request timed out. Please try again.";
      } else if (error.message.includes('HTTP 429')) {
        errorMessage = "Server is currently busy. Please wait a moment and try again.";
      } else if (error.message.includes('HTTP 503')) {
        errorMessage = "AI service is temporarily unavailable. Please try again in a few minutes.";
      } else if (error.message.includes('HTTP 504')) {
        errorMessage = "Request timed out. Please try again.";
      } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        errorMessage = "Network connection issue. Please check your connection.";
      }

      // 添加错误消息
      const errorBotMessage = {
        sender: 'bot',
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorBotMessage]);

      // 更新连接状态
      setConnectionState(prev => ({
        ...prev,
        isConnected: false,
        retryCount: prev.retryCount + 1
      }));

    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, sessionId, conversationHistory, customerInfo, onNewMessage, onRecommendationUpdate, connectionState.isConnected]);

  // 手动重连
  const handleReconnect = useCallback(() => {
    console.log('🔄 Manual reconnection triggered');
    setConnectionState(prev => ({ ...prev, retryCount: 0 }));
    initializeConnection();
  }, [initializeConnection]);

  // 处理输入
  const handleInputChange = useCallback((e) => {
    setInput(e.target.value);
    // 自动调整文本框高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, []);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  // 自动滚动
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // 连接状态指示器
  const connectionIndicator = useMemo(() => {
    if (connectionState.isChecking) {
      return { color: 'bg-yellow-500', text: 'Connecting...' };
    } else if (connectionState.isConnected) {
      return { color: 'bg-green-500', text: 'Connected' };
    } else {
      return { color: 'bg-red-500', text: 'Disconnected' };
    }
  }, [connectionState]);

  // 消息渲染组件（移除Basic Mode状态显示）
  const MessageComponent = useCallback(({ message }) => (
    <div
      className={`flex mb-4 ${
        message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`px-5 py-3 rounded-2xl max-w-[75%] whitespace-pre-wrap text-base ${
          message.sender === 'user' 
            ? 'bg-blue-600 text-white shadow-lg' 
            : message.isError
            ? 'bg-red-50 border border-red-200 text-red-700'
            : 'bg-white border shadow-lg'
        }`}
      >
        {message.text}
        
        {/* 仅显示错误状态 */}
        {message.isError && (
          <div className="text-xs mt-1 opacity-60">
            (Error)
          </div>
        )}
        
        {/* 响应时间（开发模式） */}
        {process.env.NODE_ENV === 'development' && message.responseTime && (
          <div className="text-xs mt-1 opacity-50">
            {message.responseTime}ms
          </div>
        )}
      </div>
    </div>
  ), []);

  const renderMessage = useCallback((message, index) => (
    <MessageComponent key={`${message.timestamp}-${index}`} message={message} />
  ), [MessageComponent]);

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b" style={{ backgroundColor: '#fef7e8' }}>
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
          
          {/* 连接状态 */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connectionIndicator.color}`}></div>
            <span className="text-xs text-gray-600">
              {connectionIndicator.text}
            </span>
            {!connectionState.isConnected && !connectionState.isChecking && (
              <button
                onClick={handleReconnect}
                className="text-xs text-blue-600 hover:text-blue-800 ml-2"
              >
                Retry
              </button>
            )}
          </div>
          
          {/* 调试信息 */}
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-gray-500 text-right">
              <div>Sync: {debugInfo.lastSync ? new Date(debugInfo.lastSync).toLocaleTimeString() : 'None'}</div>
              <div>Fields: {debugInfo.customerInfoReceived || 0}</div>
              <div>Response: {debugInfo.responseTime ? `${debugInfo.responseTime}ms` : 'N/A'}</div>
            </div>
          )}
        </div>
      </div>

      {/* 聊天区域 */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
        style={{ backgroundColor: '#fef7e8' }}
      >
        {messages.map(renderMessage)}
        
        {/* 加载指示器 */}
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
              connectionState.isChecking ? "Connecting..." :
              !connectionState.isConnected ? "Reconnecting..." :
              "Type your message..."
            }
            disabled={isLoading || connectionState.isChecking}
            className="w-full p-4 pr-16 rounded-xl border border-gray-300 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed transition-all"
            style={{ 
              maxHeight: '120px',
              minHeight: '52px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !connectionState.isConnected}
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

export default React.memo(Chatbot);