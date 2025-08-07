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
  const [hasUserStarted, setHasUserStarted] = useState(false); // 新增状态：用户是否已经开始对话
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // API functions - 直接在组件内定义
  // const API_BASE_URL = 'http://localhost:8000';
  const API_BASE_URL = 'https://your-backend-on-render.onrender.com';

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
      const health = await healthCheck();
      
      setApiStatus({
        healthy: health.status === 'healthy',
        enhanced: health.unified_service === 'available'
      });
      
      if (health.unified_service !== 'available') {
        setUseEnhancedAPI(false);
      } else {
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

    // 标记用户已经开始对话
    if (!hasUserStarted) {
      setHasUserStarted(true);
    }

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
          // 使用增强API
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
        timestamp: new Date().toISOString()
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
        errorMessage = "The service is currently unavailable. Please check that the backend server is running.";
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

  // 生成建议的快速回复 - 修改：初次对话时不显示
  const getQuickReplies = () => {
    // 如果用户还没开始对话，不显示快速回复
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
        {/* Logo */}
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
        
        {/* 居中标题 */}
        <div className="flex justify-center items-center">
          <h1 className="text-xl font-semibold text-gray-800">Agent X</h1>
        </div>
      </div>

      {/* 连接状态横幅（仅在连接失败时显示） */}
      {!apiStatus.healthy && (
        <div className="border-b border-red-200 px-6 py-3" style={{ backgroundColor: '#fef7e8' }}>
          <div className="flex items-center justify-between">
            <div className="text-red-700 text-sm">
              ⚠️ Cannot connect to backend service. Please ensure the server is running.
            </div>
            <button
              onClick={checkAPIHealth}
              className="text-xs px-3 py-1 bg-red-100 hover:bg-red-200 rounded text-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* 聊天消息区域 - 更柔和的背景色 */}
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
        
        {/* Loading indicator */}
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
            placeholder="Tell me about your loan requirements..."
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
        
        {!apiStatus.healthy && (
          <div className="mt-3 text-sm text-red-600 text-center">
            Service unavailable - please check your connection
          </div>
        )}
      </div>
    </div>
  );
};

export default Chatbot;