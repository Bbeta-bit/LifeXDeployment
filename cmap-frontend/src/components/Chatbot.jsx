import React, { useState, useRef, useEffect } from 'react';
import { sendMessageToChatAPI, sendEnhancedMessage, resetConversation } from '../services/api.js';

const Chatbot = ({ onNewMessage, conversationHistory }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // 新增状态用于跟踪对话流程（可选功能）
  const [sessionId, setSessionId] = useState('');
  const [conversationStage, setConversationStage] = useState('greeting');
  const [mvpProgress, setMvpProgress] = useState({
    completed_fields: [],
    missing_fields: ['loan_type', 'asset_type', 'property_status', 'ABN_years', 'GST_years'],
    is_complete: false
  });
  const [preferencesCollected, setPreferencesCollected] = useState({});
  const [useEnhancedAPI, setUseEnhancedAPI] = useState(true); // 可以控制是否使用新API
  
  const chatRef = useRef(null);
  const textareaRef = useRef(null);

  // 生成会话ID
  useEffect(() => {
    const newSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newSessionId);
  }, []);

  // 自动滚动到底部
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: 'user', text: input };
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

      if (useEnhancedAPI) {
        try {
          // 尝试使用新的增强API
          const chatHistory = messages.map(msg => ({
            role: msg.sender === 'user' ? 'user' : 'assistant',
            content: msg.text
          }));

          apiResponse = await sendEnhancedMessage(currentInput, sessionId, chatHistory);
          
          if (apiResponse && apiResponse.status === 'success') {
            replyText = apiResponse.reply;
            
            // 更新对话状态信息（如果返回了的话）
            if (apiResponse.conversation_stage) {
              setConversationStage(apiResponse.conversation_stage);
            }
            
            if (apiResponse.mvp_progress) {
              setMvpProgress(apiResponse.mvp_progress);
            }
            
            if (apiResponse.preferences_collected) {
              setPreferencesCollected(apiResponse.preferences_collected);
            }
          } else {
            throw new Error('Enhanced API returned error status');
          }
        } catch (enhancedError) {
          console.warn('Enhanced API failed, falling back to original API:', enhancedError);
          // 回退到原来的API
          replyText = await sendMessageToChatAPI(currentInput);
          setUseEnhancedAPI(false); // 标记增强API不可用
        }
      } else {
        // 直接使用原来的API
        replyText = await sendMessageToChatAPI(currentInput);
      }
      
      // 添加AI回复
      const botMessage = { sender: 'bot', text: replyText };
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
      
      // 显示错误信息
      const errorMessage = 'Sorry, we encountered a technical issue. Please try again later. If the problem persists, please contact customer service.';
      const botErrorMessage = { sender: 'bot', text: errorMessage };
      
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

  // 重置对话的函数
  const handleResetConversation = async () => {
    try {
      if (useEnhancedAPI) {
        await resetConversation(sessionId);
      }

      // 重置本地状态
      setMessages([]);
      setConversationStage('greeting');
      setMvpProgress({
        completed_fields: [],
        missing_fields: ['loan_type', 'asset_type', 'property_status', 'ABN_years', 'GST_years'],
        is_complete: false
      });
      setPreferencesCollected({});
    } catch (error) {
      console.error('Error resetting conversation:', error);
      // 即使重置API失败，也清除本地状态
      setMessages([]);
    }
  };

  // 获取阶段显示名称
  const getStageDisplayName = (stage) => {
    const stageNames = {
      'greeting': 'Getting Started',
      'mvp_collection': 'Collecting Info',
      'preference_collection': 'Understanding Preferences',
      'product_matching': 'Finding Products',
      'gap_analysis': 'Reviewing Requirements',
      'refinement': 'Refining Options',
      'final_recommendation': 'Final Recommendation',
      'handoff': 'Specialist Referral'
    };
    return stageNames[stage] || 'In Progress';
  };

  // 确定是否显示进度信息（只在使用增强API时显示）
  const showProgressInfo = useEnhancedAPI && conversationStage !== 'greeting';

  return (
    <div className="flex flex-col h-full relative">
      {/* Header with Logo and Title */}
      <div className="relative px-4 py-3 border-b bg-white shadow-sm">
        {/* Logo - 固定在左上角 */}
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
        
        {/* Centered Title with Progress Info */}
        <div className="flex justify-center items-center pt-6">
          <div className="text-center">
            <h1 className="text-lg font-semibold text-gray-800">Agent X</h1>
            {/* 进度指示器（仅在使用增强API时显示） */}
            {showProgressInfo && (
              <div className="text-xs text-gray-500 mt-1">
                {getStageDisplayName(conversationStage)}
                {conversationStage === 'mvp_collection' && mvpProgress.completed_fields.length > 0 && (
                  <span className="ml-2">({mvpProgress.completed_fields.length}/5)</span>
                )}
                {conversationStage === 'preference_collection' && Object.keys(preferencesCollected).length > 0 && (
                  <span className="ml-2">({Object.keys(preferencesCollected).length} prefs)</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 重置按钮（仅在有消息时显示） */}
        {messages.length > 0 && (
          <button
            onClick={handleResetConversation}
            className="absolute right-4 top-4 text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded text-gray-600 transition-colors"
          >
            Reset
          </button>
        )}

        {/* API状态指示器（开发调试用，可选） */}
        {process.env.NODE_ENV === 'development' && (
          <div className="absolute right-4 bottom-1 text-xs text-gray-400">
            {useEnhancedAPI ? 'Enhanced' : 'Legacy'} API
          </div>
        )}
      </div>

      {/* Chat Messages */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto px-4 py-4 bg-gray-100 space-y-3"
      >
        {messages.length === 0 && (
          <div className="flex justify-center items-center h-full">
            <div className="text-center text-gray-500">
              <p className="text-lg mb-2">Hello, how can I help you today?</p>
              <p className="text-sm">Start by telling us about your loan preferences</p>
            </div>
          </div>
        )}
        
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`px-4 py-2 rounded-lg max-w-[70%] whitespace-pre-wrap text-sm ${
                m.sender === 'user' ? 'bg-green-200' : 'bg-white border'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-lg bg-white border text-sm text-gray-500">
              <div className="flex items-center space-x-1">
                <div className="animate-bounce">●</div>
                <div className="animate-bounce delay-100">●</div>
                <div className="animate-bounce delay-200">●</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar with Stage Hints */}
      <div className="px-4 py-3 bg-white border-t shadow-sm">
        {/* 阶段特定提示（仅在使用增强API时显示） */}
        {useEnhancedAPI && conversationStage === 'preference_collection' && Object.keys(preferencesCollected).length === 0 && (
          <div className="mb-2 text-xs text-blue-600 bg-blue-50 p-2 rounded">
            💡 Now I'll ask about your preferences (interest rate, monthly budget, etc.)
          </div>
        )}
        
        {useEnhancedAPI && conversationStage === 'mvp_collection' && mvpProgress.missing_fields.length > 0 && (
          <div className="mb-2 text-xs text-amber-600 bg-amber-50 p-2 rounded">
            ℹ️ Still need: {mvpProgress.missing_fields.slice(0, 2).join(', ')}
            {mvpProgress.missing_fields.length > 2 && '...'}
          </div>
        )}

        <div className="relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            rows={1}
            placeholder="Tell us your loan preferences, like interest rate or repayment term"
            className="w-full resize-none overflow-hidden rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className={`absolute right-2 bottom-2 text-sm font-semibold ${
              isLoading || !input.trim() 
                ? 'text-gray-400 cursor-not-allowed' 
                : 'text-blue-600 hover:underline'
            }`}
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;