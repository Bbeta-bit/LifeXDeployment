import React, { useState, useRef, useEffect } from 'react';

const Chatbot = ({ onNewMessage, conversationHistory, customerInfo }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState({ healthy: false, enhanced: false });
  
  // 会话状态
  const [sessionId, setSessionId] = useState('');
  const [conversationStage, setConversationStage] = useState('greeting');
  const [roundCount, setRoundCount] = useState(0);
  const [useEnhancedAPI, setUseEnhancedAPI] = useState(true);
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // API functions - 直接在组件内定义
  const API_BASE_URL = 'http://localhost:8000';

  const sendMessageToChatAPI = async (message) => {
    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data.reply || 'Sorry, I could not process your request.';
    } catch (error) {
      console.error('API call failed:', error);
      throw error;
    }
  };

  const sendEnhancedMessage = async (message, sessionId = null, chatHistory = []) => {
    try {
      const payload = {
        message: message,
        session_id: sessionId || `session_${Date.now()}`,
        history: chatHistory
      };

      console.log('Sending enhanced message:', payload);

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();
      console.log('Enhanced API response:', data);

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
      console.error('Enhanced API call failed:', error);
      throw error;
    }
  };

  const healthCheck = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Health check failed:', error);
      throw error;
    }
  };

  const resetConversation = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/reset-conversation`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Reset conversation failed:', error);
      throw error;
    }
  };

  // 生成会话ID
  useEffect(() => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
    
    // 检查API健康状态
    checkAPIHealth();
  }, []);

  // 检查API健康状态
  const checkAPIHealth = async () => {
    try {
      console.log('Checking API health...');
      const health = await healthCheck();
      console.log('Health check result:', health);
      
      setApiStatus({
        healthy: health.status === 'healthy',
        enhanced: health.unified_service === 'available'
      });
      
      if (health.unified_service !== 'available') {
        setUseEnhancedAPI(false);
        console.warn('Enhanced API not available, falling back to basic API');
      } else {
        console.log('Enhanced API available');
        setUseEnhancedAPI(true);
      }
    } catch (error) {
      console.error('Health check failed:', error);
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

    const userMessage = { 
      sender: 'user', 
      text: input,
      timestamp: new Date().toISOString()
    };
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
      let replyText = '';
      let apiResponse = null;

      if (useEnhancedAPI && apiStatus.enhanced) {
        try {
          // 使用增强API - 传递完整的对话历史
          const chatHistory = messages.map(msg => ({
            role: msg.sender === 'user' ? 'user' : 'assistant',
            content: msg.text
          }));

          apiResponse = await sendEnhancedMessage(currentInput, sessionId, chatHistory);
          
          if (apiResponse && apiResponse.status === 'success') {
            replyText = apiResponse.reply;
            
            // 更新对话状态
            if (apiResponse.stage) {
              setConversationStage(apiResponse.stage);
            }
            if (apiResponse.round_count) {
              setRoundCount(apiResponse.round_count);
            }
            
            console.log('Enhanced API response:', {
              stage: apiResponse.stage,
              round: apiResponse.round_count,
              customer_profile: apiResponse.customer_profile
            });
          } else {
            throw new Error('Enhanced API returned error status');
          }
        } catch (enhancedError) {
          console.warn('Enhanced API failed, falling back to basic API:', enhancedError);
          setUseEnhancedAPI(false);
          replyText = await sendMessageToChatAPI(currentInput);
        }
      } else {
        // 使用基础API
        try {
          replyText = await sendMessageToChatAPI(currentInput);
        } catch (basicError) {
          console.error('Basic API also failed:', basicError);
          throw basicError;
        }
      }
      
      // 添加AI回复
      const botMessage = { 
        sender: 'bot', 
        text: replyText,
        timestamp: new Date().toISOString(),
        stage: conversationStage,
        round: roundCount
      };
      setMessages((prev) => [...prev, botMessage]);
      
      // 通知父组件有新的AI回复
      if (onNewMessage) {
        onNewMessage({
          role: 'assistant',
          content: replyText,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Error calling API:', error);
      
      // 显示友好的错误信息
      let errorMessage = "I'm experiencing technical difficulties. Please try again in a moment.";
      
      if (!apiStatus.healthy) {
        errorMessage = "The service is currently unavailable. Please check that the backend server is running on http://localhost:8000";
      }
      
      const botErrorMessage = { 
        sender: 'bot', 
        text: errorMessage,
        timestamp: new Date().toISOString(),
        isError: true
      };
      
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

  // 重置对话
  const handleResetConversation = async () => {
    try {
      if (useEnhancedAPI && apiStatus.enhanced) {
        await resetConversation(sessionId);
      }

      // 重置本地状态
      setMessages([]);
      setConversationStage('greeting');
      setRoundCount(0);
      
      // 重新显示欢迎消息
      setTimeout(() => {
        const welcomeMessage = {
          sender: 'bot',
          text: "Conversation reset. How can I help you with your loan requirements?",
          timestamp: new Date().toISOString()
        };
        setMessages([welcomeMessage]);
      }, 100);
      
    } catch (error) {
      console.error('Error resetting conversation:', error);
      setMessages([]);
    }
  };

  // 重新检查API健康状态的按钮
  const retryConnection = async () => {
    console.log('Retrying connection...');
    await checkAPIHealth();
  };

  // 获取阶段显示名称
  const getStageDisplayName = (stage) => {
    const stageNames = {
      'greeting': 'Getting Started',
      'mvp_collection': 'Collecting Information',
      'preference_collection': 'Understanding Preferences',
      'product_matching': 'Finding Products',
      'recommendation': 'Recommendation Ready',
      'refinement': 'Refining Options'
    };
    return stageNames[stage] || 'In Progress';
  };

  // 生成建议的快速回复
  const getQuickReplies = () => {
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
  const showProgressInfo = useEnhancedAPI && apiStatus.enhanced && conversationStage !== 'greeting';

  return (
    <div className="flex flex-col h-full relative">
      {/* Header */}
      <div className="relative px-4 py-3 border-b bg-white shadow-sm">
        {/* Logo */}
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
        
        {/* Title and Status */}
        <div className="flex justify-center items-center pt-6">
          <div className="text-center">
            <h1 className="text-lg font-semibold text-gray-800">Agent X</h1>
            {showProgressInfo && (
              <div className="text-xs text-gray-500 mt-1">
                {getStageDisplayName(conversationStage)}
                <span className="ml-2">Round {roundCount}/4</span>
              </div>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="absolute right-4 top-2 flex items-center space-x-2">
          {/* API Status Indicator with Retry */}
          <div className="flex items-center space-x-1">
            <button
              onClick={retryConnection}
              className={`w-2 h-2 rounded-full cursor-pointer ${apiStatus.healthy ? 'bg-green-500' : 'bg-red-500'}`}
              title="Click to retry connection"
            ></button>
            <span className="text-xs text-gray-500">
              {useEnhancedAPI && apiStatus.enhanced ? 'Enhanced' : 'Basic'}
            </span>
          </div>
          
          {/* Reset Button */}
          {messages.length > 1 && (
            <button
              onClick={handleResetConversation}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-600 transition-colors"
            >
              Reset
            </button>
          )}
        </div>

        {/* Customer Info Summary */}
        {customerInfo && Object.keys(customerInfo).length > 0 && customerInfo.extracted_fields?.length > 0 && (
          <div className="mt-2 text-xs text-center text-blue-600 bg-blue-50 py-1 rounded">
            📋 {customerInfo.extracted_fields.length} fields auto-filled from conversation
          </div>
        )}
      </div>

      {/* Connection Status Banner */}
      {!apiStatus.healthy && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="text-red-700 text-sm">
              ⚠️ Cannot connect to backend service. Please ensure the server is running on http://localhost:8000
            </div>
            <button
              onClick={retryConnection}
              className="text-xs px-2 py-1 bg-red-100 hover:bg-red-200 rounded text-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-4 py-4 bg-gray-50 space-y-3"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-4 py-2 rounded-lg max-w-[70%] whitespace-pre-wrap text-sm ${
                m.sender === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : m.isError
                  ? 'bg-red-50 border border-red-200 text-red-700'
                  : 'bg-white border shadow-sm'
              }`}
            >
              {m.text}
              {/* Message metadata for development */}
              {process.env.NODE_ENV === 'development' && m.stage && (
                <div className="text-xs opacity-60 mt-1">
                  {m.stage} • R{m.round}
                </div>
              )}
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-lg bg-white border text-sm text-gray-500 shadow-sm">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Quick Replies */}
      {quickReplies.length > 0 && !isLoading && apiStatus.healthy && (
        <div className="px-4 py-2 bg-white border-t">
          <div className="flex flex-wrap gap-2">
            {quickReplies.map((reply, index) => (
              <button
                key={index}
                onClick={() => {
                  setInput(reply);
                  setTimeout(() => handleSend(), 100);
                }}
                className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700 transition-colors"
              >
                {reply}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Bar */}
      <div className="px-4 py-3 bg-white border-t shadow-sm">
        {/* Stage-specific hints */}
        {showProgressInfo && conversationStage === 'mvp_collection' && (
          <div className="mb-2 text-xs text-amber-600 bg-amber-50 p-2 rounded">
            💡 I need to collect some basic information to find the best loan options for you
          </div>
        )}

        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder={
              apiStatus.healthy 
                ? (conversationStage === 'greeting' 
                    ? "Tell me about your loan requirements..." 
                    : "Continue the conversation...")
                : "Backend service unavailable - please check server status"
            }
            className="w-full resize-none overflow-hidden rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm"
            disabled={isLoading || !apiStatus.healthy}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim() || !apiStatus.healthy}
            className={`absolute right-2 bottom-2 text-sm font-semibold ${
              isLoading || !input.trim() || !apiStatus.healthy
                ? 'text-gray-400 cursor-not-allowed' 
                : 'text-blue-600 hover:underline'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
        
        {!apiStatus.healthy && (
          <div className="mt-2 text-xs text-red-600 text-center">
            Service unavailable - please check your connection
            <button 
              onClick={retryConnection}
              className="ml-2 underline hover:no-underline"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Chatbot;