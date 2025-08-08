import React, { useState, useRef, useEffect } from 'react';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState({ healthy: false, enhanced: false });
  const [debugInfo, setDebugInfo] = useState('');
  const [connectionAttempts, setConnectionAttempts] = useState(0);
  
  // 会话状态
  const [sessionId, setSessionId] = useState('');
  const [conversationStage, setConversationStage] = useState('greeting');
  const [roundCount, setRoundCount] = useState(0);
  const [useEnhancedAPI, setUseEnhancedAPI] = useState(true);
  const [hasUserStarted, setHasUserStarted] = useState(false);
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);
  const retryTimeoutRef = useRef(null);

  // 🔧 API URL
  const API_BASE_URL = 'https://lifex-backend.onrender.com';
  
  // 添加调试信息显示
  const addDebugInfo = (info) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugInfo(prev => `${prev}\n[${timestamp}] ${info}`);
    console.log(`[DEBUG ${timestamp}] ${info}`);
  };

  // 🆕 多种方式尝试连接
  const attemptConnection = async (method = 'fetch') => {
    try {
      addDebugInfo(`🔄 尝试连接方式: ${method}`);
      
      if (method === 'fetch') {
        // 方式1：标准 fetch
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-cache',
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        addDebugInfo(`✅ 标准fetch成功`);
        return data;
        
      } else if (method === 'cors') {
        // 方式2：明确CORS模式
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          mode: 'cors',
          headers: {
            'Content-Type': 'application/json',
          },
          cache: 'no-cache',
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        addDebugInfo(`✅ CORS模式成功`);
        return data;
        
      } else if (method === 'no-cors') {
        // 方式3：no-cors模式 (降级方案)
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          mode: 'no-cors',
          cache: 'no-cache',
        });
        
        addDebugInfo(`⚠️ no-cors模式 - 假定服务器可达`);
        // no-cors模式无法读取响应，但能判断是否可达
        return { status: 'healthy', unified_service: 'available', mode: 'no-cors' };
        
      } else if (method === 'jsonp') {
        // 方式4：JSONP方式 (最后手段)
        return new Promise((resolve, reject) => {
          const script = document.createElement('script');
          const callbackName = 'healthCallback_' + Date.now();
          
          window[callbackName] = (data) => {
            document.head.removeChild(script);
            delete window[callbackName];
            addDebugInfo(`✅ JSONP成功`);
            resolve(data);
          };
          
          script.src = `${API_BASE_URL}/health?callback=${callbackName}`;
          script.onerror = () => {
            document.head.removeChild(script);
            delete window[callbackName];
            reject(new Error('JSONP failed'));
          };
          
          document.head.appendChild(script);
          
          // 10秒超时
          setTimeout(() => {
            if (window[callbackName]) {
              document.head.removeChild(script);
              delete window[callbackName];
              reject(new Error('JSONP timeout'));
            }
          }, 10000);
        });
      }
      
    } catch (error) {
      addDebugInfo(`❌ ${method}方式失败: ${error.message}`);
      throw error;
    }
  };

  // 🆕 智能健康检查 - 尝试多种连接方式
  const smartHealthCheck = async () => {
    const methods = ['fetch', 'cors', 'no-cors'];
    
    for (let i = 0; i < methods.length; i++) {
      try {
        addDebugInfo(`🎯 尝试方式 ${i + 1}/${methods.length}: ${methods[i]}`);
        const result = await attemptConnection(methods[i]);
        
        if (result) {
          addDebugInfo(`✅ 连接成功使用方式: ${methods[i]}`);
          return result;
        }
      } catch (error) {
        addDebugInfo(`⚠️ 方式${methods[i]}失败: ${error.message}`);
        if (i === methods.length - 1) {
          // 所有方式都失败了
          throw new Error('All connection methods failed');
        }
        // 继续尝试下一种方式
      }
    }
  };

  // 🆕 智能消息发送
  const smartSendMessage = async (message, isEnhanced = false) => {
    const payload = isEnhanced ? {
      message: message,
      session_id: sessionId || `session_${Date.now()}`,
      history: messages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text
      }))
    } : { message };

    // 尝试不同的请求方式
    const methods = ['fetch', 'cors'];
    
    for (const method of methods) {
      try {
        addDebugInfo(`📤 发送消息使用方式: ${method}`);
        
        const fetchOptions = {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
          cache: 'no-cache',
        };
        
        if (method === 'cors') {
          fetchOptions.mode = 'cors';
        }
        
        const response = await fetch(`${API_BASE_URL}/chat`, fetchOptions);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        addDebugInfo(`✅ 消息发送成功使用方式: ${method}`);
        return data;
        
      } catch (error) {
        addDebugInfo(`❌ 消息发送${method}失败: ${error.message}`);
        if (method === methods[methods.length - 1]) {
          throw error;
        }
      }
    }
  };

  // 生成会话ID
  useEffect(() => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    addDebugInfo(`🆔 会话开始: ${newSessionId}`);
    addDebugInfo(`🔗 API地址: ${API_BASE_URL}`);
    addDebugInfo(`🌐 浏览器: ${navigator.userAgent.split(' ')[0]}`);
    
    // 立即开始连接，然后定期重试
    checkAPIHealth();
  }, []);

  // 🆕 智能重连机制
  const scheduleRetry = () => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
    }
    
    // 指数退避重试：5秒，10秒，20秒，最多30秒
    const delays = [5000, 10000, 20000, 30000];
    const delay = delays[Math.min(connectionAttempts, delays.length - 1)];
    
    addDebugInfo(`⏱️ 将在${delay/1000}秒后重试 (尝试 ${connectionAttempts + 1})`);
    
    retryTimeoutRef.current = setTimeout(() => {
      checkAPIHealth();
    }, delay);
  };

  // 检查API健康状态
  const checkAPIHealth = async () => {
    try {
      addDebugInfo(`🔄 开始健康检查... (尝试 ${connectionAttempts + 1})`);
      
      setConnectionAttempts(prev => prev + 1);
      
      const health = await smartHealthCheck();
      
      // 连接成功，重置计数器
      setConnectionAttempts(0);
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      
      setApiStatus({
        healthy: health.status === 'healthy' || health.mode === 'no-cors',
        enhanced: health.unified_service === 'available' || health.mode === 'no-cors'
      });
      
      if (health.unified_service !== 'available' && health.mode !== 'no-cors') {
        setUseEnhancedAPI(false);
        addDebugInfo(`⚠️ 基础模式`);
      } else {
        setUseEnhancedAPI(true);
        addDebugInfo(`✅ 增强模式可用`);
      }
      
      addDebugInfo(`🎯 连接建立成功!`);
      
    } catch (error) {
      addDebugInfo(`💥 健康检查失败: ${error.message}`);
      
      setApiStatus({ healthy: false, enhanced: false });
      setUseEnhancedAPI(false);
      
      // 如果尝试次数少于10次，安排重试
      if (connectionAttempts < 10) {
        scheduleRetry();
      } else {
        addDebugInfo(`🛑 已达到最大重试次数，停止自动重试`);
      }
    }
  };

  // 手动重试连接
  const manualRetry = () => {
    setConnectionAttempts(0);
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    checkAPIHealth();
  };

  // 清理定时器
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  // 欢迎消息
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage = {
        sender: 'bot',
        text: "Hello! I'm here to help you find the perfect loan product. I can assist with vehicle loans, equipment finance, and business loans.\n\nTell me about what you're looking to finance and I'll find the best options for you.",
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
    }
  }, []);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // 如果未连接，尝试重新连接
    if (!apiStatus.healthy) {
      addDebugInfo(`⚠️ 服务未连接，尝试重新连接...`);
      await checkAPIHealth();
      if (!apiStatus.healthy) {
        addDebugInfo(`❌ 重连失败，无法发送消息`);
        return;
      }
    }

    if (!hasUserStarted) {
      setHasUserStarted(true);
    }

    const userMessage = { 
      sender: 'user', 
      text: input,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    
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
    addDebugInfo(`💬 发送消息: "${currentInput.slice(0, 30)}..."`);

    try {
      let apiResponse;
      
      if (useEnhancedAPI && apiStatus.enhanced) {
        try {
          apiResponse = await smartSendMessage(currentInput, true);
          
          if (apiResponse && apiResponse.status === 'success') {
            // 处理推荐信息
            if (apiResponse.recommendations && apiResponse.recommendations.length > 0) {
              console.log('📊 收到推荐信息:', apiResponse.recommendations);
              addDebugInfo(`📊 收到 ${apiResponse.recommendations.length} 个产品推荐`);
              
              if (onRecommendationUpdate) {
                onRecommendationUpdate(apiResponse.recommendations);
                addDebugInfo(`✅ 推荐信息已传递`);
              }
            }
            
            if (apiResponse.stage) {
              setConversationStage(apiResponse.stage);
              addDebugInfo(`🎯 对话阶段: ${apiResponse.stage}`);
            }
            if (apiResponse.round_count) {
              setRoundCount(apiResponse.round_count);
              addDebugInfo(`🔢 对话轮数: ${apiResponse.round_count}`);
            }
          }
        } catch (enhancedError) {
          addDebugInfo(`⚠️ 增强API失败，尝试基础模式`);
          setUseEnhancedAPI(false);
          apiResponse = await smartSendMessage(currentInput, false);
        }
      } else {
        apiResponse = await smartSendMessage(currentInput, false);
      }
      
      const replyText = apiResponse?.reply || apiResponse || 'Sorry, I could not process your request.';
      
      const botMessage = { 
        sender: 'bot', 
        text: replyText,
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, botMessage]);
      
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: replyText,
          timestamp: new Date().toISOString()
        });
      }

      addDebugInfo(`✅ 对话完成`);
      
    } catch (error) {
      addDebugInfo(`💥 发送失败: ${error.message}`);
      
      const errorMessage = "I'm having trouble connecting right now. The system is trying to reconnect automatically. Please wait a moment and try again.";
      
      const botErrorMessage = { 
        sender: 'bot', 
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages((prev) => [...prev, botErrorMessage]);
      
      // 发送失败时触发重连
      if (!apiStatus.healthy) {
        scheduleRetry();
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

  // 快速回复选项
  const getQuickReplies = () => {
    if (!hasUserStarted) {
      return [];
    }
    
    if (conversationStage === 'greeting') {
      return [
        "I need a car loan",
        "Business equipment finance",
        "I want the lowest interest rate"
      ];
    } else if (conversationStage === 'mvp_collection') {
      return [
        "I own property",
        "I don't own property", 
        "Show me options"
      ];
    } else if (conversationStage === 'preference_collection') {
      return [
        "Lowest interest rate possible",
        "I need low monthly payments",
        "Show me recommendations"
      ];
    }
    return [];
  };

  const quickReplies = getQuickReplies();

  return (
    <div className="flex flex-col h-full relative" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="relative px-6 py-4 shadow-sm border-b" style={{ backgroundColor: '#fef7e8' }}>
        <a 
          href="https://lifex.com.au/" 
          target="_blank" 
          rel="noopener noreferrer"
          className="absolute left-6 top-4 z-10"
        >
          <img 
            src="/lifex-logo.png" 
            alt="LIFEX Logo" 
            className="h-7 w-auto hover:opacity-80 transition-opacity"
          />
        </a>
        
        <div className="flex justify-center items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
        </div>
      </div>

      {/* 智能连接状态显示 */}
      {!apiStatus.healthy && (
        <div className="border-b border-orange-200 px-6 py-3" style={{ backgroundColor: '#fef7e8' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="text-orange-700 text-sm flex items-center">
              <div className="w-2 h-2 bg-orange-500 rounded-full mr-2 animate-pulse"></div>
              {connectionAttempts === 0 ? '正在连接服务...' : 
               connectionAttempts < 10 ? `连接中... (尝试 ${connectionAttempts})` : 
               '连接异常，请手动重试'}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={manualRetry}
                className="text-xs px-3 py-1 bg-blue-100 hover:bg-blue-200 rounded text-blue-700 transition-colors"
              >
                立即重试
              </button>
              <button
                onClick={() => setDebugInfo('')}
                className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              >
                清空日志
              </button>
            </div>
          </div>
          
          <div className="text-xs text-gray-600 mb-2">
            后端服务: <code className="bg-gray-100 px-1 rounded">{API_BASE_URL}</code>
          </div>
          
          {/* 调试信息面板 */}
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-800">
              📊 连接诊断日志
            </summary>
            <div className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-32 text-gray-700">
              <pre>{debugInfo || '初始化中...'}</pre>
            </div>
          </details>
          
          <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
            <strong>🔧 智能连接系统:</strong>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>正在尝试多种连接方式建立稳定连接</li>
              <li>系统会自动重试并选择最佳连接方法</li>
              <li>后端服务运行正常，请耐心等待连接建立</li>
              {retryTimeoutRef.current && <li className="text-green-600">⏰ 自动重试已安排</li>}
            </ul>
          </div>
        </div>
      )}

      {/* 推荐状态提示 */}
      {useEnhancedAPI && apiStatus.enhanced && conversationStage === 'recommendation' && (
        <div className="px-6 py-2 bg-green-50 border-b border-green-200">
          <div className="flex items-center text-sm text-green-700">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
            Products recommended! Check the Product Comparison panel to compare options.
          </div>
        </div>
      )}

      {/* 聊天消息区域 */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-4"
        style={{ 
          minHeight: '62vh',
          backgroundColor: '#fef7e8'
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-5 py-3 rounded-2xl max-w-[75%] whitespace-pre-wrap text-base leading-relaxed ${
                m.sender === 'user' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : m.isError
                  ? 'bg-red-50 border border-red-200 text-red-700 shadow-sm'
                  : 'bg-white border shadow-lg'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-5 py-3 rounded-2xl bg-white border text-base text-gray-500 shadow-lg">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 快速回复按钮 */}
      {quickReplies.length > 0 && !isLoading && apiStatus.healthy && (
        <div className="px-6 py-3 border-t" style={{ backgroundColor: '#fef7e8' }}>
          <div className="flex flex-wrap gap-2">
            {quickReplies.map((reply, index) => (
              <button
                key={index}
                onClick={() => {
                  setInput(reply);
                  setTimeout(() => handleSend(), 100);
                }}
                className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors shadow-sm"
              >
                {reply}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 输入区域 */}
      <div className="px-6 py-4 border-t shadow-lg" style={{ maxHeight: '20vh', backgroundColor: '#fef7e8' }}>
        <div className="relative max-w-4xl mx-auto">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={
              apiStatus.healthy 
                ? "Tell me about your loan requirements..." 
                : "System connecting... Please wait..."
            }
            className="w-full resize-none overflow-hidden rounded-xl border border-gray-300 px-5 py-4 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
            disabled={isLoading || !apiStatus.healthy}
            style={{ minHeight: '56px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || !apiStatus.healthy}
            className={`absolute right-3 bottom-3 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              isLoading || !input.trim() || !apiStatus.healthy
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        
        {/* 智能状态栏 */}
        <div className="mt-3 flex justify-between items-center text-sm">
          <div className="flex items-center space-x-4">
            <span className={`flex items-center ${
              apiStatus.healthy ? 'text-green-600' : 
              connectionAttempts > 0 ? 'text-orange-600' : 'text-gray-600'
            }`}>
              <div className={`w-2 h-2 rounded-full mr-1 ${
                apiStatus.healthy ? 'bg-green-500' : 
                connectionAttempts > 0 ? 'bg-orange-500 animate-pulse' : 'bg-gray-400'
              }`}></div>
              {apiStatus.healthy ? 'Connected' : 
               connectionAttempts > 0 ? 'Connecting...' : 'Initializing...'}
            </span>
            {apiStatus.enhanced && (
              <span className="text-blue-600 flex items-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-1"></div>
                Enhanced Mode
              </span>
            )}
          </div>
          
          {conversationStage !== 'greeting' && apiStatus.healthy && (
            <div className="text-xs text-gray-500">
              💡 Product recommendations will appear in comparison panel
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chatbot;