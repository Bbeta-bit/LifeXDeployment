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

  // 🔧 固定使用生产环境 URL
  const API_BASE_URL = 'https://lifex-backend.onrender.com';
  
  // 添加调试信息显示
  const addDebugInfo = (info) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugInfo(prev => `${prev}\n[${timestamp}] ${info}`);
    console.log(`[DEBUG ${timestamp}] ${info}`);
  };

  // 🆕 简化的健康检查 - 去掉可能有问题的配置
  const healthCheck = async () => {
    try {
      addDebugInfo(`🔍 健康检查: ${API_BASE_URL}/health`);
      
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
        // 移除可能有问题的 mode, credentials 等配置
      });
      
      addDebugInfo(`📡 状态: ${response.status} ${response.statusText}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        addDebugInfo(`❌ HTTP错误: ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      addDebugInfo(`✅ 健康检查成功`);
      addDebugInfo(`🔧 服务版本: ${data.version}`);
      addDebugInfo(`🤖 统一服务: ${data.unified_service}`);
      return data;
    } catch (error) {
      addDebugInfo(`❌ 健康检查错误: ${error.message}`);
      throw error;
    }
  };

  // 🆕 简化的基础消息发送
  const sendMessageToChatAPI = async (message) => {
    try {
      addDebugInfo(`📤 发送基础消息`);
      
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message })
      });
      
      addDebugInfo(`📨 响应: ${response.status}`);

      if (!response.ok) {
        const errorText = await response.text();
        addDebugInfo(`❌ 聊天API错误: ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      addDebugInfo(`✅ 基础API成功`);
      return data.reply || 'Sorry, I could not process your request.';
    } catch (error) {
      addDebugInfo(`❌ 基础API失败: ${error.message}`);
      throw error;
    }
  };

  // 🆕 简化的增强消息发送
  const sendEnhancedMessage = async (message, sessionId = null, chatHistory = []) => {
    try {
      addDebugInfo(`🚀 发送增强消息`);
      const payload = {
        message: message,
        session_id: sessionId || `session_${Date.now()}`,
        history: chatHistory
      };

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        addDebugInfo(`❌ 增强API错误: ${errorText}`);
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      addDebugInfo(`✅ 增强API成功`);

      return {
        reply: data.reply,
        session_id: data.session_id,
        stage: data.stage,
        customer_profile: data.customer_profile,
        recommendations: data.recommendations || [],
        next_questions: data.next_questions || [],
        round_count: data.round_count,
        status: data.status || 'success'
      };
    } catch (error) {
      addDebugInfo(`❌ 增强API失败: ${error.message}`);
      throw error;
    }
  };

  // 生成会话ID
  useEffect(() => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    addDebugInfo(`🆔 会话开始: ${newSessionId}`);
    addDebugInfo(`🔗 API地址: ${API_BASE_URL}`);
    
    // 延迟检查，给服务器时间
    setTimeout(() => {
      checkAPIHealth();
    }, 2000);
  }, []);

  // 检查API健康状态
  const checkAPIHealth = async () => {
    try {
      addDebugInfo(`🔄 开始健康检查...`);
      const health = await healthCheck();
      
      setApiStatus({
        healthy: health.status === 'healthy',
        enhanced: health.unified_service === 'available'
      });
      
      if (health.unified_service !== 'available') {
        setUseEnhancedAPI(false);
        addDebugInfo(`⚠️ 基础模式 - 增强功能不可用`);
      } else {
        setUseEnhancedAPI(true);
        addDebugInfo(`✅ 完整功能可用`);
      }
      
      addDebugInfo(`🎯 最终状态: 健康=${health.status === 'healthy'} 增强=${health.unified_service === 'available'}`);
      
    } catch (error) {
      addDebugInfo(`💥 健康检查失败: ${error.message}`);
      setApiStatus({ healthy: false, enhanced: false });
      setUseEnhancedAPI(false);
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
        text: "Hello! I'm here to help you find the perfect loan product. I can assist with vehicle loans, equipment finance, and business loans.\n\nTell me about what you're looking to finance and I'll find the best options for you.",
        timestamp: new Date().toISOString()
      };
      setMessages([welcomeMessage]);
    }
  }, []);

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
    addDebugInfo(`💬 用户消息: "${currentInput.slice(0, 30)}..."`);

    try {
      let replyText = '';
      let apiResponse = null;

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
            
            if (apiResponse.stage) {
              setConversationStage(apiResponse.stage);
              addDebugInfo(`🎯 对话阶段更新: ${apiResponse.stage}`);
            }
            if (apiResponse.round_count) {
              setRoundCount(apiResponse.round_count);
              addDebugInfo(`🔢 对话轮数: ${apiResponse.round_count}`);
            }
          } else {
            throw new Error('Enhanced API returned error status');
          }
        } catch (enhancedError) {
          addDebugInfo(`⚠️ 回退到基础模式: ${enhancedError.message}`);
          setUseEnhancedAPI(false);
          replyText = await sendMessageToChatAPI(currentInput);
        }
      } else {
        try {
          replyText = await sendMessageToChatAPI(currentInput);
        } catch (basicError) {
          addDebugInfo(`💥 基础API也失败: ${basicError.message}`);
          throw basicError;
        }
      }
      
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
      
      let errorMessage = "I'm experiencing technical difficulties. Please try again in a moment.";
      
      if (!apiStatus.healthy) {
        errorMessage = "Unable to connect to our services. Please wait 30-60 seconds and try again, or refresh the page.";
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

      {/* 简化的连接状态显示 */}
      {!apiStatus.healthy && (
        <div className="border-b border-red-200 px-6 py-3" style={{ backgroundColor: '#fef7e8' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="text-red-700 text-sm">
              ⚠️ 连接后端服务中...
            </div>
            <div className="flex space-x-2">
              <button
                onClick={checkAPIHealth}
                className="text-xs px-3 py-1 bg-blue-100 hover:bg-blue-200 rounded text-blue-700 transition-colors"
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
          
          <div className="text-xs text-gray-600 mb-2">
            后端URL: <code className="bg-gray-100 px-1 rounded">{API_BASE_URL}</code>
          </div>
          
          {/* 调试信息面板 */}
          <details className="mt-2">
            <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-800">
              📊 调试信息 (点击查看详细日志)
            </summary>
            <div className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto max-h-40 text-gray-700">
              <pre>{debugInfo || '等待调试信息...'}</pre>
            </div>
          </details>
          
          <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
            <strong>💡 提示:</strong>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>后端服务运行正常，正在建立连接...</li>
              <li>如果持续失败，请刷新页面重试</li>
              <li>首次访问可能需要等待30秒让服务启动</li>
            </ul>
          </div>
        </div>
      )}

      {/* 推荐状态提示 */}
      {useEnhancedAPI && apiStatus.enhanced && conversationStage === 'recommendation' && (
        <div className="px-6 py-2 bg-green-50 border-b border-green-200" style={{ backgroundColor: '#f0f9ff' }}>
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
                : "Connecting to service..."
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
        
        {/* 状态栏 */}
        <div className="mt-3 flex justify-between items-center text-sm">
          <div className="flex items-center space-x-4">
            <span className={`flex items-center ${apiStatus.healthy ? 'text-green-600' : 'text-orange-600'}`}>
              <div className={`w-2 h-2 rounded-full mr-1 ${apiStatus.healthy ? 'bg-green-500' : 'bg-orange-500 animate-pulse'}`}></div>
              {apiStatus.healthy ? 'Connected' : 'Connecting...'}
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