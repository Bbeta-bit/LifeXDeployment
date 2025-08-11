import React, { useState, useCallback, useEffect } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import PromotionsShowcase from './components/PromotionsShowcase';
import ProductComparison from './components/ProductComparison';

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 🔧 修复1：对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 🔧 修复2：客户信息状态 - 优化管理，支持双向同步
  const [customerInfo, setCustomerInfo] = useState({});
  
  // 🔧 修复3：推荐状态管理 - 支持多推荐管理
  const [recommendations, setRecommendations] = useState([]);

  // 🔧 修复4：调试状态（开发模式）
  const [debugInfo, setDebugInfo] = useState({
    lastFormUpdate: null,
    lastChatMessage: null,
    lastRecommendationUpdate: null
  });

  // 🔧 修复5：处理新消息 - 从Chatbot传来，添加调试信息
  const handleNewMessage = useCallback((message) => {
    console.log('📝 App received new message:', message);
    
    setConversationHistory(prev => {
      const updated = [...prev, message];
      console.log('📚 Updated conversation history length:', updated.length);
      return updated;
    });
    
    // 更新调试信息
    setDebugInfo(prev => ({
      ...prev,
      lastChatMessage: new Date().toISOString()
    }));
  }, []);

  // 🔧 修复6：处理表单更新 - 优化双向同步逻辑，添加调试
  const handleFormUpdate = useCallback((updatedInfo) => {
    try {
      console.log('📋 App received form update:', updatedInfo);
      
      if (!updatedInfo || typeof updatedInfo !== 'object') {
        console.warn('⚠️ Invalid form update data received');
        return;
      }

      // 深度比较，只有真正变化时才更新
      const hasChanges = Object.keys(updatedInfo).some(key => {
        const oldValue = customerInfo[key];
        const newValue = updatedInfo[key];
        return oldValue !== newValue;
      });

      if (hasChanges) {
        console.log('🔄 Customer info has changes, updating...');
        
        setCustomerInfo(prev => {
          const updated = { ...prev, ...updatedInfo };
          console.log('📊 Updated customer info:', updated);
          return updated;
        });

        // 更新调试信息
        setDebugInfo(prev => ({
          ...prev,
          lastFormUpdate: new Date().toISOString()
        }));
      } else {
        console.log('ℹ️ No changes detected in form update');
      }
    } catch (error) {
      console.error('❌ Error in handleFormUpdate:', error);
    }
  }, [customerInfo]);
  
  // 🔧 修复7：处理推荐更新 - 支持多推荐管理和自动面板切换，添加调试
  const handleRecommendationUpdate = useCallback((newRecommendations) => {
    try {
      console.log('🎯 App received recommendation update:', newRecommendations);
      
      if (newRecommendations && Array.isArray(newRecommendations) && newRecommendations.length > 0) {
        // 验证推荐数据结构
        const validRecommendations = newRecommendations.filter(rec => 
          rec && 
          typeof rec === 'object' && 
          rec.lender_name && 
          rec.product_name && 
          rec.base_rate
        );

        if (validRecommendations.length > 0) {
          console.log('✅ Valid recommendations found:', validRecommendations.length);
          
          // 更新推荐状态
          setRecommendations(validRecommendations);
          
          // 自动打开Product Comparison面板（如果没有面板激活）
          if (!activePanel) {
            console.log('🔄 Auto-opening Product Comparison panel');
            setActivePanel('Current Product Info');
          }

          // 更新调试信息
          setDebugInfo(prev => ({
            ...prev,
            lastRecommendationUpdate: new Date().toISOString()
          }));
        } else {
          console.warn('⚠️ No valid recommendations in update');
        }
      } else {
        console.log('ℹ️ Empty or invalid recommendation update received');
      }
    } catch (error) {
      console.error('❌ Error in handleRecommendationUpdate:', error);
    }
  }, [activePanel]);

  // 🔧 修复8：面板渲染函数 - 增强错误处理
  const renderActivePanel = () => {
    try {
      switch (activePanel) {
        case 'Dynamic Form':
          return (
            <DynamicCustomerForm 
              conversationHistory={conversationHistory}
              onFormUpdate={handleFormUpdate}
              initialData={customerInfo}
              recommendations={recommendations}
            />
          );
        case 'Loan Calculator':
          return <LoanCalculator customerInfo={customerInfo} />;
        case 'Current Product Info':
          return (
            <ProductComparison 
              recommendations={recommendations} 
              customerInfo={customerInfo}
              onRecommendationUpdate={handleRecommendationUpdate}
            />
          );
        case 'Promotions':
          return <PromotionsShowcase />;
        default:
          return null;
      }
    } catch (error) {
      console.error('❌ Error rendering panel:', error);
      return (
        <div className="p-6 text-center">
          <div className="text-red-600 mb-4">
            <h3 className="text-lg font-semibold">Panel Loading Error</h3>
            <p className="text-sm">There was an issue loading this panel. Please try refreshing the page.</p>
          </div>
          <button 
            onClick={() => setActivePanel(null)}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Close Panel
          </button>
        </div>
      );
    }
  };

  // 🔧 修复9：错误边界状态
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    // 重置错误状态
    setHasError(false);
  }, [activePanel]);

  // 🔧 修复10：错误处理函数
  const handleError = useCallback((error) => {
    console.error('🚨 App-level error:', error);
    
    // 可以根据错误类型决定是否显示错误界面
    if (error.message && error.message.includes('Critical')) {
      setHasError(true);
    }
    
    // 这里可以添加错误报告逻辑
  }, []);

  // 🔧 修复11：监控状态变化（开发模式）
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🔍 App state update:');
      console.log('  - Conversation history length:', conversationHistory.length);
      console.log('  - Customer info fields:', Object.keys(customerInfo).length);
      console.log('  - Recommendations count:', recommendations.length);
      console.log('  - Active panel:', activePanel);
    }
  }, [conversationHistory, customerInfo, recommendations, activePanel]);

  if (hasError) {
    return (
      <div className="h-screen w-screen flex items-center justify-center" style={{ backgroundColor: '#fef7e8' }}>
        <div className="text-center max-w-md">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Application Error</h1>
          <p className="text-gray-700 mb-4">Something went wrong. Please refresh the page to continue.</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-6 py-3 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex" style={{ backgroundColor: '#fef7e8' }}>
      {/* 🔧 调试面板（仅开发模式） */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed top-4 right-4 bg-white border border-gray-300 rounded p-2 text-xs z-50 shadow-lg">
          <div className="font-semibold mb-1">Debug Info:</div>
          <div>History: {conversationHistory.length}</div>
          <div>Customer: {Object.keys(customerInfo).length} fields</div>
          <div>Recommendations: {recommendations.length}</div>
          <div>Panel: {activePanel || 'None'}</div>
          <div className="mt-1 pt-1 border-t">
            <div>Form: {debugInfo.lastFormUpdate ? new Date(debugInfo.lastFormUpdate).toLocaleTimeString() : 'None'}</div>
            <div>Chat: {debugInfo.lastChatMessage ? new Date(debugInfo.lastChatMessage).toLocaleTimeString() : 'None'}</div>
            <div>Rec: {debugInfo.lastRecommendationUpdate ? new Date(debugInfo.lastRecommendationUpdate).toLocaleTimeString() : 'None'}</div>
          </div>
        </div>
      )}
      
      {/* Left sidebar - fixed width */}
      <FunctionBar activePanel={activePanel} setActivePanel={setActivePanel} />
      
      {/* Main content area - 50/50 split when panel is active */}
      <div className="flex-1 flex">
        {/* Function panel - 50% width when active */}
        {activePanel && (
          <div 
            className="border-r shadow-lg overflow-hidden"
            style={{ width: '50%', backgroundColor: '#fef7e8' }}
          >
            {renderActivePanel()}
          </div>
        )}
        
        {/* Chatbot - 50% when panel is active, 100% when no panel */}
        <div 
          style={{ 
            width: activePanel ? '50%' : '100%',
            backgroundColor: '#fef7e8'
          }}
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