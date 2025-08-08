import React, { useState, useRef, useEffect } from 'react';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo, onRecommendationUpdate }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState({ healthy: false, enhanced: false });
  const [debugInfo, setDebugInfo] = useState('');
  
  // 会话状态
  const [sessionId, setSessionId] = useState('');
  const [conversationStage, setConversationStage] = useState('greeting');
  const [roundCount, setRoundCount] = useState(0);
  const [useEnhancedAPI, setUseEnhancedAPI] = useState(true);
  const [hasUserStarted, setHasUserStarted] = useState(false);
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // 🔧 智能后端URL检测
  const getBackendURL = () => {
    // 检查当前环境
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    
    // 生产环境 - 你的 Render 后端
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return 'https://lifex-backend.onrender.com';
    }
    
    // 本地开发环境
    return 'http://localhost:8000';
  };

  const API_BASE_URL = getBackendURL();
  
  // 添加调试信息显示
  const addDebugInfo = (info) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugInfo(prev => `${prev}\n[${timestamp}] ${info}`);
    console.log(`[DEBUG ${timestamp}] ${info}`);
  };

  // 🔧 改进的健康检查 - 添加重试逻辑
  const healthCheck = async (retries = 3) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        addDebugInfo(`🔍 健康检查 (尝试 ${attempt}/${retries}): ${API_BASE_URL}/health`);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 20000); // 增加到20秒
        
        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
          },
          signal: controller.signal,
          mode: 'cors',
        });
        
        clearTimeout(timeoutId);
        
        addDebugInfo(`📡 状态: ${response.status} ${response.statusText}`);
        
        if (!response.ok) {
          const errorText = await response.text();
          addDebugInfo(`❌ HTTP错误: ${errorText.slice(0, 200)}`);
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        addDebugInfo(`✅ 健康检查成功 (尝试 ${attempt})`);
        return data;
        
      } catch (error) {
        if (error.name === 'AbortError') {
          addDebugInfo(`⏰ 请求超时 (尝试 ${attempt}/${retries})`);
        } else if (error.message.includes('CORS')) {
          addDebugInfo(`🚫 CORS错误 (尝试 ${attempt}/${retries})`);
        } else if (error.message.includes('fetch') || error.message.includes('Failed to fetch')) {
          addDebugInfo(`🌐 网络错误 - 无法连接到服务器 (尝试 ${attempt}/${retries})`);
          addDebugInfo(`🔗 URL: ${API_BASE_URL}`);
        } else {
          addDebugInfo(`❌ 错误 (尝试 ${attempt}/${retries}): ${error.message}`);
        }

        // 如果不是最后一次尝试，等待后重试
        if (attempt < retries) {
          const waitTime = attempt * 2000; // 递增等待时间
          addDebugInfo(`⏳ 等待 ${waitTime/1000}秒 后重试...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        } else {
          throw error;
        }
      }
    }
  };

  // 🔧 改进的基础消息发送
  const sendMessageToChatAPI = async (message) => {
    try {
      addDebugInfo(`📤 发送基础消息: "${message.slice(0, 30)}..."`);
      
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000); // 增加超时时间
      
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify({ message }),
        signal: controller.signal,
        mode: 'cors',
      });
      
      clearTimeout(timeoutId);
      
      addDebugInfo(`📨 响应: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        addDebugInfo(`❌ 聊天API错误: ${errorText.slice(0, 200)}`);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      addDebugInfo(`✅ 基础API成功`);
      return data.reply || 'I apologize, but I encountered an issue processing your request.';
      
    } catch (error) {
      addDebugInfo(`❌ 基础API失败: ${error.message}`);
      throw error;
    }
  };

  // 🔧 改进的增强消息发送
  const sendEnhancedMessage = async (message, sessionId = null, chatHistory = []) => {
    try {
      addDebugInfo(`🚀 发送增强消息: "${message.slice(0, 30)}..."`);
      const payload = {
        message: message,
        session_id: sessionId || `session_${Date.now()}`,
        history: chatHistory.slice(-10) // 只发送最近10条历史记录
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
        mode: 'cors',
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        addDebugInfo(`❌ 增强API错误: ${errorText.slice(0, 200)}`);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      addDebugInfo(`✅ 增强API成功`);

      return {
        reply: data.reply || 'I apologize for the issue with processing your request.',
        session_id: data.session_id || sessionId,
        stage: data.stage || 'greeting',
        customer_profile: data.customer_profile || {},
        recommendations: data.recommendations || [],
        next_questions: data.next_questions || [],
        round_count: data.round_count || 1,
        status: data.status || 'success'
      };
    } catch (error) {
      addDebugInfo(`❌ 增强API失败: ${error.message}`);
      throw error;
    }
  };

  // 🔧 CORS 预检测试
  const testCORS = async () => {
    try {
      addDebugInfo(`🧪 测试CORS连接...`);
      const response = await fetch(`${API_BASE_URL}/cors-test`, {
        method: 'GET',
        mode: 'cors',
        headers: {
          'Accept': 'application/json',
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        addDebugInfo(`✅ CORS测试成功: ${data.message}`);
        return true;
      } else {
        addDebugInfo(`❌ CORS测试失败: ${response.status}`);
        return false;
      }
    } catch (error) {
      addDebugInfo(`❌ CORS测试错误: ${error.message}`);
      return false;
    }
  };

  // 生成会话ID
  useEffect(() => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    addDebugInfo(`🆔 会话开始: ${newSessionId}`);
    addDebugInfo(`🌐 检测到的后端URL: ${API_BASE_URL}`);
    
    // 延迟检查健康状态
    setTimeout(() => {
      checkAPIHealth();
    }, 1000);
  }, []);

  // 🔧 改进的API健康状态检查
  const checkAPIHealth = async () => {
    try {
      addDebugInfo(`🔄 开始完整健康检查...`);
      
      // 首先测试CORS
      const corsOk = await testCORS();
      
      // 然后测试健康检查
      const health = await healthCheck(3);
      
      const isHealthy = health.status === 'healthy';
      const hasEnhanced = health.unified_service === 'available';
      
      setApiStatus({
        healthy: isHealthy,
        enhanced: hasEnhanced
      });
      
      if (!hasEnhanced) {
        setUseEnhancedAPI(false);
        addDebugInfo(`⚠️ 基础模式 - 增强功能不可用`);
      } else {
        setUseEnhancedAPI(true);
        addDebugInfo(`✅ 完整功能可用`);
      }
      
      if (isHealthy) {
        addDebugInfo(`🎉 所有检查通过！`);
      }
      
    } catch (error) {
      addDebugInfo(`💥 健康检查失败: ${error.message}`);
      setApiStatus({ healthy: false, enhanced: false });
      setUseEnhancedAPI(false);
      
      // 提供具体的错误诊断
      if (error.message.includes('CORS')) {
        addDebugInfo(`🔧 CORS问题 - 请检查后端CORS配置`);
      } else if (error.message.includes('timeout') || error.name === 'AbortError') {
        addDebugInfo(`🔧 超时问题 - 后端可能正在冷启动`);
      } else if (error.message.includes('fetch')) {
        addDebugInfo(`🔧 网络问题 - 请检查URL和网络连接`);
      }
    }
  };

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
        text: "Hello! I'm Agent X, here to help you find the perfect loan product. I can assist with vehicle loans, equipment finance, and business loans.\n\nTell me about what you're looking to finance and I'll find the best options for you.",
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
    }
  }, []);

  // 🔧 改进的消息发送处理
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

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
    addDebugInfo(`💬 用户消息: "${currentInput.slice(0, 50)}..."`);

    try {
      let replyText = '';
      let apiResponse = null;
      let fallbackUsed = false;

      // 尝试增强模式
      if (useEnhancedAPI && apiStatus.enhanced) {
        try {
          const chatHistory = messages.map(msg => ({
            role: msg.sender === 'user' ? 'user' : 'assistant',
            content: msg.text
          }));

          apiResponse = await sendEnhancedMessage(currentInput, sessionId, chatHistory);
          
          if (apiResponse && apiResponse.status === 'success') {
            replyText = apiResponse.reply;
            
            // 处理推荐信息
            if (apiResponse.recommendations && apiResponse.recommendations.length > 0) {
              console.log('📊 收到推荐信息:', apiResponse.recommendations);
              addDebugInfo(`📊 收到 ${apiResponse.recommendations.length} 个产品推荐`);
              
              if (onRecommendationUpdate) {
                onRecommendationUpdate(apiResponse.recommendations);
                addDebugInfo(`✅ 推荐信息已传递给ProductComparison`);
              }
            }
            
            // 更新对话状态
            if (apiResponse.stage) {
              setConversationStage(apiResponse.stage);
              addDebugInfo(`🎯 对话阶段更新: ${apiResponse.stage}`);
            }
            if (apiResponse.round_count) {
              setRoundCount(apiResponse.round_count);
              addDebugInfo(`🔢 对话轮数: ${apiResponse.round_count}`);
            }
          } else {
            throw new Error('Enhanced API returned non-success status');
          }
        } catch (enhancedError) {
          addDebugInfo(`⚠️ 增强API失败，尝试基础模式: ${enhancedError.message}`);
          fallbackUsed = true;
          
          try {
            replyText = await sendMessageToChatAPI(currentInput);
          } catch (basicError) {
            throw basicError;
          }
        }
      } else {
        // 直接使用基础模式
        try {
          replyText = await sendMessageToChatAPI(currentInput);
          fallbackUsed = true;
        } catch (basicError) {
          throw basicError;
        }
      }
      
      // 添加回复消息
      const botMessage = { 
        sender: 'bot', 
        text: replyText,
        timestamp: new Date().toISOString(),
        fallback: fallbackUsed
      };
      setMessages((prev) => [...prev, botMessage]);
      
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: replyText,
          timestamp: new Date().toISOString()
        });
      }

      addDebugInfo(`✅ 对话完成${fallbackUsed ? ' (基础模式)' : ' (增强模式)'}`);
      
    } catch (error) {
      addDebugInfo(`💥 发送失败: ${error.message}`);
      
      let errorMessage = "I'm having trouble connecting right now. Please try again in a moment.";
      
      if (error.message.includes('timeout') || error.name === 'AbortError') {
        errorMessage = "The request timed out. The service might be starting up. Please wait 30-60 seconds and try again.";
      } else if (error.message.includes('CORS')) {
        errorMessage = "There's a connection issue. Please refresh the page and try again.";
      } else if (!apiStatus.healthy) {
        errorMessage = "The service is currently unavailable. Please wait a moment for it to start up and try again.";
      }
      
      const botErrorMessage = { 
        sender: 'bot', 
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
      setMessages((prev) => [...prev, botErrorMessage]);
      
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

  // 🔧 改进的快速回复逻辑
  const getQuickReplies = () => {
    if (!hasUserStarted || !apiStatus.healthy) {
      return [];
    }
    
    if (conversationStage === 'greeting' || conversationStage === 'mvp_collection') {
      return [
        "I need a car loan",
        "Business equipment finance",
        "Show me the lowest rates"
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

  // 🔧 改进的连接状态显示
  const getConnectionStatus = () => {
    if (apiStatus.healthy) {
      return {
        color: 'text-green-600',
        bg: 'bg-green-50',
        border: 'border-green-200',
        icon: '✅',
        text: 'Connected',
        detail: useEnhancedAPI ? 'Enhanced Mode' : 'Basic Mode'
      };
    } else {
      return {
        color: 'text-red-600',
        bg: 'bg-red-50',
        border: 'border-red-200', 
        icon: '❌',
        text: 'Disconnected',
        detail: 'Service Unavailable'
      };
    }
  };

  const connectionStatus = getConnectionStatus();

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

      {/* 改进的连接状态显示 */}
      {!apiStatus.healthy && (
        <div className={`border-b px-6 py-3 ${connectionStatus.bg} ${connectionStatus.border}`}>
          <div className="flex items-center justify-between mb-2">
            <div className={`${connectionStatus.color} text-sm font-medium`}>
              {connectionStatus.icon} {connectionStatus.text} - {connectionStatus.detail}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={checkAPIHealth}
                className={`text-xs px-3 py-1 rounded transition-colors ${connectionStatus.color} bg-white border hover:bg-gray-50`}
              >
                重试连接
              </button>
              <button
                onClick={() => setDebugInfo('')}
                className="text-xs px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              >
                清空日志
              </button>
            </div>
          </div>
          
          <div className="text-xs text-gray-600 mb-2 font-mono">
            后端: {API_BASE_URL}
          </div>
          
          {/* 调试信息面板 */}
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-800">
              🔍 诊断日志 (点击查看详情)
            </summary>
            <div className="mt-2 text-xs bg-white p-3 rounded border overflow-auto max-h-40 text-gray-700 font-mono">
              <pre>{debugInfo || '等待诊断信息...'}</pre>
            </div>
          </details>
          
          <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded text-xs">
            <div className="font-semibold text-blue-800 mb-2">🛠️ 诊断步骤:</div>
            <ol className="list-decimal list-inside space-y-1 text-blue-700">
              <li>检查后端URL是否正确: <code className="bg-white px-1 rounded text-blue-800">{API_BASE_URL}</code></li>
              <li>Render服务冷启动可能需要30-60秒</li>
              <li>检查浏览器网络和CORS设置</li>
              <li>如问题持续，请联系技术支持</li>
            </ol>
          </div>
        </div>
      )}

      {/* 产品推荐状态提示 */}
      {useEnhancedAPI && apiStatus.enhanced && conversationStage === 'recommendation' && (
        <div className="px-6 py-2 bg-green-50 border-b border-green-200">
          <div className="flex items-center text-sm text-green-700">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
            产品推荐已生成！请查看"Product Comparison"面板进行比较
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
              className={`px-5 py-3 rounded-2xl max-w-[75%] whitespace-pre-wrap text-base leading-relaxed relative ${
                m.sender === 'user' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : m.isError
                  ? 'bg-red-50 border border-red-200 text-red-700 shadow-sm'
                  : 'bg-white border shadow-lg'
              }`}
            >
              {m.text}
              {/* 显示回退模式标记 */}
              {m.fallback && (
                <div className="text-xs text-gray-500 mt-1 italic">基础模式响应</div>
              )}
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
      {quickReplies.length > 0 && !isLoading && (
        <div className="px-6 py-3 border-t" style={{ backgroundColor: '#fef7e8' }}>
          <div className="flex flex-wrap gap-2">
            {quickReplies.map((reply, index) => (
              <button
                key={index}
                onClick={() => {
                  setInput(reply);
                  setTimeout(() => handleSend(), 100);
                }}
                className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors shadow-sm disabled:opacity-50"
                disabled={!apiStatus.healthy}
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
            placeholder={apiStatus.healthy ? "Tell me about your loan requirements..." : "等待服务连接中..."}
            className="w-full resize-none overflow-hidden rounded-xl border border-gray-300 px-5 py-4 text-base focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm disabled:bg-gray-100 disabled:text-gray-500"
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
        
        {/* 连接状态和功能提示 */}
        <div className="mt-3 flex justify-between items-center text-sm">
          <div className="flex items-center space-x-4">
            <span className={`flex items-center ${connectionStatus.color}`}>
              <div className={`w-2 h-2 rounded-full mr-1 ${apiStatus.healthy ? 'bg-green-500' : 'bg-red-500'}`}></div>
              {connectionStatus.text}
            </span>
            {apiStatus.enhanced && apiStatus.healthy && (
              <span className="text-blue-600 flex items-center">
                <div className="w-2 h-2 bg-blue-500 rounded-full mr-1"></div>
                Enhanced Mode
              </span>
            )}
          </div>
          
          {conversationStage !== 'greeting' && apiStatus.healthy && (
            <div className="text-xs text-gray-500">
              💡 产品推荐会出现在比较面板中
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chatbot;