import React, { useState, useCallback, useEffect, useMemo } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import PromotionsShowcase from './components/PromotionsShowcase';
import ProductComparison from './components/ProductComparison';

function App() {
  // 🔧 修复：状态管理 - 确保所有数据正确流动
  const [activePanel, setActivePanel] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [customerInfo, setCustomerInfo] = useState({});
  const [recommendations, setRecommendations] = useState([]);
  const [debugInfo, setDebugInfo] = useState({
    lastFormUpdate: null,
    lastChatMessage: null,
    lastRecommendationUpdate: null
  });
  const [hasError, setHasError] = useState(false);

  // 错误边界状态重置
  useEffect(() => {
    setHasError(false);
  }, [activePanel]);

  // 🔧 修复：优化的消息处理 - 确保数据正确传递给所有组件
  const handleNewMessage = useCallback((message) => {
    if (!message || !message.content) {
      console.warn('⚠️ Invalid message received:', message);
      return;
    }

    console.log('📨 App received new message:', {
      sender: message.sender,
      content: message.content?.substring(0, 100) + '...',
      hasRecommendations: !!message.recommendations?.length,
      hasCustomerProfile: !!message.customer_profile,
      hasExtractedInfo: !!message.extracted_info
    });

    // 🔧 构建完整的消息对象
    const fullMessage = {
      id: message.id || `msg_${Date.now()}_${message.sender}`,
      content: message.content,
      sender: message.sender,
      timestamp: message.timestamp || new Date().toISOString(),
      type: message.type || 'normal',
      recommendations: message.recommendations || [],
      customer_profile: message.customer_profile || {},
      extracted_info: message.extracted_info || {}
    };

    // 更新对话历史
    setConversationHistory(prev => {
      const updated = [...prev, fullMessage];
      console.log(`📚 Conversation history updated: ${updated.length} messages`);
      return updated;
    });

    // 🔧 重要：如果消息包含客户信息提取，更新customerInfo
    if (message.customer_profile && Object.keys(message.customer_profile).length > 0) {
      setCustomerInfo(prevInfo => {
        const updatedInfo = { ...prevInfo, ...message.customer_profile };
        console.log('👤 Customer info updated from chat:', {
          previousFields: Object.keys(prevInfo).length,
          newFields: Object.keys(message.customer_profile).length,
          totalFields: Object.keys(updatedInfo).length
        });
        return updatedInfo;
      });
    }

    // 🔧 重要：如果消息包含提取信息，也更新customerInfo
    if (message.extracted_info && Object.keys(message.extracted_info).length > 0) {
      setCustomerInfo(prevInfo => {
        const updatedInfo = { ...prevInfo, ...message.extracted_info };
        console.log('🔍 Customer info updated from extraction:', {
          extractedFields: Object.keys(message.extracted_info),
          totalFields: Object.keys(updatedInfo).length
        });
        return updatedInfo;
      });
    }

    // 🔧 重要：如果消息包含推荐，更新推荐状态
    if (message.recommendations && message.recommendations.length > 0) {
      handleRecommendationUpdate(message.recommendations);
    }

    // 更新调试信息
    setDebugInfo(prev => ({
      ...prev,
      lastChatMessage: Date.now()
    }));

  }, []);

  // 🔧 修复：推荐更新处理 - 确保推荐数据正确传递给ProductComparison
  const handleRecommendationUpdate = useCallback((newRecommendations) => {
    console.log('📋 App updating recommendations:', {
      count: newRecommendations?.length || 0,
      recommendations: newRecommendations?.map(r => ({
        lender: r.lender_name,
        product: r.product_name,
        rate: r.base_rate
      })) || []
    });

    if (newRecommendations && Array.isArray(newRecommendations)) {
      setRecommendations(newRecommendations);
      
      // 更新调试信息
      setDebugInfo(prev => ({
        ...prev,
        lastRecommendationUpdate: Date.now()
      }));

      // 🔧 如果有推荐且没有激活面板，自动显示Product Comparison
      if (newRecommendations.length > 0 && !activePanel) {
        console.log('📋 Auto-opening Product Comparison panel');
        setActivePanel('Current Product Info');
      }
    }
  }, [activePanel]);

  // 🔧 修复：表单更新处理 - 确保表单数据正确同步
  const handleFormUpdate = useCallback((formData) => {
    console.log('📝 App received form update:', {
      fields: Object.keys(formData || {}),
      data: formData
    });

    if (formData && typeof formData === 'object') {
      setCustomerInfo(prevInfo => {
        const updatedInfo = { ...prevInfo, ...formData };
        console.log('📝 Customer info updated from form:', {
          previousFields: Object.keys(prevInfo).length,
          newFields: Object.keys(formData).length,
          totalFields: Object.keys(updatedInfo).length
        });
        return updatedInfo;
      });

      // 更新调试信息
      setDebugInfo(prev => ({
        ...prev,
        lastFormUpdate: Date.now()
      }));
    }
  }, []);

  // 🔧 修复：错误处理
  const handleError = useCallback((error) => {
    console.error('❌ App received error:', error);
    setHasError(true);
    
    // 可以在这里添加错误通知或其他错误处理逻辑
  }, []);

  // 🔧 修复：渲染激活的面板 - 确保所有数据正确传递
  const renderActivePanel = useMemo(() => {
    console.log(`🎛️ Rendering panel: ${activePanel}`, {
      customerInfoFields: Object.keys(customerInfo).length,
      recommendationsCount: recommendations.length
    });

    switch (activePanel) {
      case 'Dynamic Form':
        return (
          <DynamicCustomerForm 
            customerInfo={customerInfo}
            onUpdate={handleFormUpdate}
            conversationHistory={conversationHistory}
          />
        );
      
      case 'Loan Calculator':
        return (
          <LoanCalculator 
            customerInfo={customerInfo}
            recommendations={recommendations}
          />
        );
      
      case 'Current Product Info':
        return (
          <ProductComparison 
            recommendations={recommendations}
            customerInfo={customerInfo}
            conversationHistory={conversationHistory}
          />
        );
      
      case 'Promotions':
        return (
          <PromotionsShowcase 
            customerInfo={customerInfo}
            recommendations={recommendations}
          />
        );
      
      default:
        return null;
    }
  }, [activePanel, customerInfo, recommendations, conversationHistory, handleFormUpdate]);

  // 🔧 错误边界渲染
  if (hasError) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-red-50">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full mx-4">
          <h2 className="text-xl font-bold text-red-600 mb-4">Application Error</h2>
          <p className="text-gray-600 mb-6">
            Something went wrong with the application. 
            Please refresh to continue.
          </p>
          <div className="space-y-2">
            <button 
              onClick={() => window.location.reload()}
              className="w-full px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Refresh Page
            </button>
            <button 
              onClick={() => setHasError(false)}
              className="w-full px-6 py-3 bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex" style={{ backgroundColor: '#fef7e8' }}>
      {/* 🔧 调试面板（仅开发模式） */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed top-4 right-4 bg-white border border-gray-300 rounded p-3 text-xs z-50 shadow-lg max-w-xs">
          <div className="font-semibold mb-2 text-gray-800">Debug Info</div>
          <div className="space-y-1 text-gray-600">
            <div>History: {conversationHistory.length} messages</div>
            <div>Customer: {Object.keys(customerInfo).length} fields</div>
            <div>Recommendations: {recommendations.length}</div>
            <div>Active Panel: {activePanel || 'None'}</div>
            <div className="border-t pt-1 mt-2">
              <div>Form: {debugInfo.lastFormUpdate ? 
                new Date(debugInfo.lastFormUpdate).toLocaleTimeString() : 'None'}</div>
              <div>Chat: {debugInfo.lastChatMessage ? 
                new Date(debugInfo.lastChatMessage).toLocaleTimeString() : 'None'}</div>
              <div>Rec: {debugInfo.lastRecommendationUpdate ? 
                new Date(debugInfo.lastRecommendationUpdate).toLocaleTimeString() : 'None'}</div>
            </div>
          </div>
        </div>
      )}
      
      {/* 左侧功能栏 */}
      <FunctionBar 
        activePanel={activePanel} 
        setActivePanel={setActivePanel}
      />
      
      {/* 主内容区域 */}
      <div className="flex-1 flex min-w-0">
        {/* 🔧 功能面板 - 50% 宽度（当激活时） */}
        {activePanel && (
          <div 
            className="border-r shadow-lg overflow-hidden flex-shrink-0"
            style={{ width: '50%', backgroundColor: '#fef7e8' }}
          >
            <div className="h-full">
              {renderActivePanel}
            </div>
          </div>
        )}
        
        {/* 🔧 聊天机器人 - 动态宽度，确保传递所有必要的props */}
        <div 
          className="flex-1 min-w-0"
          style={{ backgroundColor: '#fef7e8' }}
        >
          <Chatbot 
            onNewMessage={handleNewMessage}
            conversationHistory={conversationHistory}
            customerInfo={customerInfo}
            onRecommendationUpdate={handleRecommendationUpdate}
            onError={handleError}
          />
        </div>
      </div>
    </div>
  );
}

export default App;