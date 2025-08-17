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
    
    // 🔧 确保初始消息传递给App组件
    if (onNewMessage) {
      onNewMessage({
        content: welcomeMessage.text,
        sender: 'bot',
        timestamp: welcomeMessage.timestamp,
        type: 'welcome'
      });
    }
    
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
  }, [generateSessionId, onNewMessage]);

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
      
      if (isConnected) {
        console.log('✅ Connection established successfully');
        // 定期健康检查
        startHealthCheckInterval();
      } else {
        console.log('❌ Connection failed, scheduling retry...');
        scheduleRetry();
      }
      
    } catch (error) {
      console.error('❌ Connection error:', error);
      setConnectionState(prev => ({
        ...prev,
        isConnected: false,
        isChecking: false,
        retryCount: prev.retryCount + 1
      }));
      scheduleRetry();
    }
  }, []);

  // 定期健康检查
  const startHealthCheckInterval = useCallback(() => {
    if (connectionCheckInterval.current) {
      clearInterval(connectionCheckInterval.current);
    }
    
    connectionCheckInterval.current = setInterval(async () => {
      try {
        const healthChecks = await performHealthChecks();
        const isConnected = healthChecks.api_health;
        
        setConnectionState(prev => ({
          ...prev,
          isConnected,
          lastCheck: Date.now()
        }));
        
        if (!isConnected) {
          console.log('🔄 Connection lost, attempting reconnection...');
          scheduleRetry();
        }
      } catch (error) {
        console.error('🔄 Health check failed:', error);
        setConnectionState(prev => ({
          ...prev,
          isConnected: false,
          lastCheck: Date.now()
        }));
        scheduleRetry();
      }
    }, 30000); // 每30秒检查一次
  }, []);

  // 重试机制
  const scheduleRetry = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }
    
    const retryDelay = Math.min(5000 * Math.pow(2, connectionState.retryCount), 30000);
    console.log(`🔄 Scheduling retry in ${retryDelay}ms...`);
    
    retryTimeoutRef.current = setTimeout(() => {
      initializeConnection();
    }, retryDelay);
  }, [connectionState.retryCount, initializeConnection]);

  // 🔧 修复：确保conversationHistory同步到本地messages
  useEffect(() => {
    if (conversationHistory && conversationHistory.length > 0) {
      // 转换格式以匹配本地消息格式
      const convertedMessages = conversationHistory.map((msg, index) => ({
        id: msg.id || `msg_${index}`,
        sender: msg.sender || (msg.role === 'user' ? 'user' : 'bot'),
        text: msg.content || msg.text || '',
        timestamp: msg.timestamp || new Date().toISOString(),
        type: msg.type || 'normal',
        recommendations: msg.recommendations || []
      }));
      
      setMessages(convertedMessages);
      setDebugInfo(prev => ({
        ...prev,
        lastSync: Date.now(),
        customerInfoReceived: Object.keys(customerInfo || {}).length
      }));
    }
  }, [conversationHistory, customerInfo]);

  // 自动滚动到底部
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // 文本区域自动调整高度
  const adjustTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, []);

  // 输入处理
  const handleInputChange = useCallback((e) => {
    setInput(e.target.value);
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  // 键盘事件处理
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, []);

  // 🔧 修复：发送消息处理 - 确保数据正确传递给App组件
  const handleSend = useCallback(async () => {
    if (!input.trim() || isLoading || !connectionState.isConnected) {
      return;
    }

    const userMessage = {
      id: `msg_${Date.now()}_user`,
      sender: 'user',
      text: input.trim(),
      timestamp: new Date().toISOString(),
      type: 'normal'
    };

    // 添加用户消息到本地状态
    setMessages(prev => [...prev, userMessage]);
    
    // 🔧 重要：通知App组件用户发送了新消息
    if (onNewMessage) {
      onNewMessage({
        content: userMessage.text,
        sender: 'user',
        timestamp: userMessage.timestamp,
        type: 'normal'
      });
    }

    setInput('');
    setIsLoading(true);
    
    // 重置文本区域高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      const startTime = Date.now();
      
      // 🔧 确保传递完整的客户信息
      console.log('📤 Sending message with customer info:', customerInfo);
      
      const response = await sendEnhancedMessage(
        userMessage.text,
        sessionId,
        customerInfo || {},  // 确保customerInfo不为空
        conversationHistory || []  // 确保conversationHistory不为空
      );

      const responseTime = Date.now() - startTime;
      
      console.log('📥 Received response:', response);
      console.log(`⏱️ Response time: ${responseTime}ms`);

      if (response && response.reply) {
        const botMessage = {
          id: `msg_${Date.now()}_bot`,
          sender: 'bot',
          text: response.reply,
          timestamp: new Date().toISOString(),
          type: 'normal',
          recommendations: response.recommendations || []
        };

        // 添加机器人回复到本地状态
        setMessages(prev => [...prev, botMessage]);
        
        // 🔧 重要：通知App组件机器人发送了回复
        if (onNewMessage) {
          onNewMessage({
            content: botMessage.text,
            sender: 'bot',
            timestamp: botMessage.timestamp,
            type: 'normal',
            recommendations: response.recommendations || [],
            customer_profile: response.customer_profile || {},
            extracted_info: response.extracted_info || {}
          });
        }

        // 🔧 重要：如果有推荐，通知App组件更新推荐
        if (response.recommendations && response.recommendations.length > 0 && onRecommendationUpdate) {
          console.log('📋 Updating recommendations:', response.recommendations);
          onRecommendationUpdate(response.recommendations);
        }

        // 更新调试信息
        setDebugInfo(prev => ({
          ...prev,
          lastApiCall: Date.now(),
          responseTime
        }));

      } else {
        throw new Error('Invalid response format');
      }

    } catch (error) {
      console.error('❌ Send message error:', error);
      
      const errorMessage = {
        id: `msg_${Date.now()}_error`,
        sender: 'bot',
        text: "I'm having trouble connecting to our AI service. Please try again in a moment.",
        timestamp: new Date().toISOString(),
        type: 'error'
      };

      setMessages(prev => [...prev, errorMessage]);
      
      // 🔧 通知App组件发生错误
      if (onError) {
        onError(error);
      }
      
      // 如果连接出错，尝试重新建立连接
      if (error.message?.includes('network') || error.message?.includes('fetch')) {
        setConnectionState(prev => ({ ...prev, isConnected: false }));
        scheduleRetry();
      }
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, connectionState.isConnected, sessionId, customerInfo, conversationHistory, onNewMessage, onRecommendationUpdate, onError, scheduleRetry]);

  // 消息渲染
  const renderMessage = useCallback((message) => {
    const isBot = message.sender === 'bot';
    const isError = message.type === 'error';
    
    return (
      <div key={message.id} className={`flex ${isBot ? 'justify-start' : 'justify-end'}`}>
        <div className={`max-w-3xl px-5 py-3 rounded-2xl shadow-lg ${
          isError 
            ? 'bg-red-50 border border-red-200 text-red-800'
            : isBot 
              ? 'bg-white border text-gray-800' 
              : 'bg-blue-600 text-white'
        }`}>
          <div className="whitespace-pre-wrap leading-relaxed">{message.text}</div>
          
          {/* 🔧 推荐信息显示 */}
          {message.recommendations && message.recommendations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <div className="text-sm text-gray-600 mb-2">
                💡 {message.recommendations.length} recommendation{message.recommendations.length > 1 ? 's' : ''} found
              </div>
              {message.recommendations.slice(0, 2).map((rec, index) => (
                <div key={index} className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-2 last:mb-0">
                  <div className="font-semibold text-blue-900">
                    {rec.lender_name} - {rec.product_name}
                  </div>
                  <div className="text-sm text-blue-700 mt-1">
                    Rate: {rec.base_rate}% | Max: {rec.max_loan_amount}
                  </div>
                </div>
              ))}
              {message.recommendations.length > 2 && (
                <div className="text-sm text-gray-500 italic">
                  +{message.recommendations.length - 2} more options available
                </div>
              )}
            </div>
          )}
          
          <div className={`text-xs mt-2 ${isBot ? 'text-gray-400' : 'text-blue-200'}`}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  }, []);

  // 连接状态指示器
  const ConnectionIndicator = useMemo(() => {
    if (connectionState.isChecking) {
      return (
        <div className="flex items-center space-x-2 text-yellow-600">
          <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
          <span className="text-sm">Connecting...</span>
        </div>
      );
    }
    
    if (!connectionState.isConnected) {
      return (
        <div className="flex items-center space-x-2 text-red-600">
          <div className="w-2 h-2 bg-red-500 rounded-full"></div>
          <span className="text-sm">Disconnected</span>
          <button 
            onClick={initializeConnection}
            className="text-xs bg-red-100 hover:bg-red-200 px-2 py-1 rounded transition-colors"
          >
            Retry
          </button>
        </div>
      );
    }
    
    return (
      <div className="flex items-center space-x-2 text-green-600">
        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
        <span className="text-sm">Connected</span>
      </div>
    );
  }, [connectionState, initializeConnection]);

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: '#fef7e8' }}>
      {/* 顶部状态栏 */}
      <div className="flex-shrink-0 px-6 py-3 border-b shadow-sm" style={{ backgroundColor: '#fef7e8' }}>
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <h2 className="text-lg font-semibold text-gray-800">Agent X</h2>
            {ConnectionIndicator}
          </div>
          
          {/* 🔧 调试信息（仅开发模式） */}
          {process.env.NODE_ENV === 'development' && (
            <div className="text-xs text-gray-500 space-y-1">
              <div>Session: {sessionId.slice(-8)}</div>
              <div>Sync: {debugInfo.lastSync ? 
                new Date(debugInfo.lastSync).toLocaleTimeString() : 'None'}</div>
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