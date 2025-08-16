import React, { useState, useCallback, useEffect, useMemo } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import PromotionsShowcase from './components/PromotionsShowcase';
import ProductComparison from './components/ProductComparison';

// 应用状态管理器
class AppStateManager {
  constructor() {
    this.subscribers = new Set();
    this.state = {
      conversationHistory: [],
      customerInfo: {},
      recommendations: [],
      activePanel: null,
      debugInfo: {
        lastFormUpdate: null,
        lastChatMessage: null,
        lastRecommendationUpdate: null
      }
    };
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  updateState(updates) {
    this.state = { ...this.state, ...updates };
    this.notifySubscribers();
  }

  notifySubscribers() {
    this.subscribers.forEach(callback => callback(this.state));
  }

  getState() {
    return this.state;
  }
}

function App() {
  // 状态管理
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

  // 优化的消息处理
  const handleNewMessage = useCallback((message) => {
    if (!message || !message.content) {
      console.warn('⚠️ Invalid message received:', message);
      return;
    }

    console.log('📝 App received new message:', {
      role: message.role,
      content_length: message.content.length,
      timestamp: message.timestamp
    });
    
    setConversationHistory(prev => {
      // 防止重复消息
      const lastMessage = prev[prev.length - 1];
      if (lastMessage && 
          lastMessage.content === message.content && 
          lastMessage.role === message.role) {
        console.log('ℹ️ Duplicate message prevented');
        return prev;
      }

      const updated = [...prev, message];
      console.log('📚 Conversation history updated, length:', updated.length);
      return updated;
    });
    
    setDebugInfo(prev => ({
      ...prev,
      lastChatMessage: new Date().toISOString()
    }));
  }, []);

  // 优化的表单更新处理
  const handleFormUpdate = useCallback((updatedInfo) => {
    if (!updatedInfo || typeof updatedInfo !== 'object') {
      console.warn('⚠️ Invalid form update data:', updatedInfo);
      return;
    }

    console.log('📋 App received form update:', {
      fields: Object.keys(updatedInfo),
      values: Object.values(updatedInfo).filter(v => v !== null && v !== undefined && v !== '')
    });

    setCustomerInfo(prev => {
      // 深度比较，只更新真正变化的字段
      const changes = {};
      let hasChanges = false;

      for (const [key, value] of Object.entries(updatedInfo)) {
        if (prev[key] !== value) {
          changes[key] = value;
          hasChanges = true;
        }
      }

      if (!hasChanges) {
        console.log('ℹ️ No actual changes in form update');
        return prev;
      }

      const updated = { ...prev, ...changes };
      console.log('📊 Customer info updated:', {
        total_fields: Object.keys(updated).length,
        changed_fields: Object.keys(changes)
      });

      return updated;
    });

    setDebugInfo(prev => ({
      ...prev,
      lastFormUpdate: new Date().toISOString()
    }));
  }, []);

  // 优化的推荐更新处理
  const handleRecommendationUpdate = useCallback((newRecommendations) => {
    if (!Array.isArray(newRecommendations)) {
      console.warn('⚠️ Invalid recommendations data:', newRecommendations);
      return;
    }

    console.log('🎯 App received recommendation update:', {
      count: newRecommendations.length,
      lenders: newRecommendations.map(r => r.lender_name).filter(Boolean)
    });

    // 验证推荐数据质量
    const validRecommendations = newRecommendations.filter(rec => {
      const isValid = rec && 
        typeof rec === 'object' && 
        rec.lender_name && 
        rec.product_name && 
        rec.base_rate !== undefined;
      
      if (!isValid) {
        console.warn('⚠️ Invalid recommendation filtered out:', rec);
      }
      
      return isValid;
    });

    if (validRecommendations.length === 0) {
      console.warn('⚠️ No valid recommendations found');
      return;
    }

    setRecommendations(validRecommendations);

    // 智能面板管理 - 自动打开Product Comparison（如果合适）
    if (!activePanel && validRecommendations.length > 0) {
      console.log('🔄 Auto-opening Product Comparison panel');
      setActivePanel('productComparison');
    }

    setDebugInfo(prev => ({
      ...prev,
      lastRecommendationUpdate: new Date().toISOString()
    }));
  }, [activePanel]);

  // 全局错误处理
  const handleError = useCallback((error) => {
    console.error('🚨 App-level error:', error);
    
    // 根据错误类型决定处理策略
    if (error.message && error.message.includes('Critical')) {
      setHasError(true);
    }
    
    // 这里可以添加错误报告逻辑
    // 例如发送错误到分析服务
    
  }, []);

  // 面板渲染优化
  const renderActivePanel = useMemo(() => {
    const panelProps = {
      customerInfo,
      onCustomerInfoUpdate: handleFormUpdate,
      recommendations,
      conversationHistory
    };

    switch (activePanel) {
      case 'customerForm':
        return (
          <div className="h-full overflow-auto">
            <DynamicCustomerForm {...panelProps} />
          </div>
        );
      
      case 'loanCalculator':
        return (
          <div className="h-full overflow-auto">
            <LoanCalculator {...panelProps} />
          </div>
        );
      
      case 'promotions':
        return (
          <div className="h-full overflow-auto">
            <PromotionsShowcase {...panelProps} />
          </div>
        );
      
      case 'productComparison':
        return (
          <div className="h-full overflow-auto">
            <ProductComparison {...panelProps} />
          </div>
        );
      
      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg mb-2">Panel Error</p>
              <p className="text-sm">Unknown panel type: {activePanel}</p>
              <button 
                onClick={() => setActivePanel(null)}
                className="mt-4 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Close Panel
              </button>
            </div>
          </div>
        );
    }
  }, [activePanel, customerInfo, handleFormUpdate, recommendations, conversationHistory]);

  // 错误边界UI
  if (hasError) {
    return (
      <div className="h-screen w-screen flex items-center justify-center" style={{ backgroundColor: '#fef7e8' }}>
        <div className="text-center max-w-md p-6 bg-white rounded-lg shadow-lg">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Application Error</h1>
          <p className="text-gray-700 mb-4">
            Something went wrong with the application. Please refresh to continue.
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
      {/* 调试面板（仅开发模式） */}
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
        recommendations={recommendations}
        customerInfo={customerInfo}
      />
      
      {/* 主内容区域 */}
      <div className="flex-1 flex min-w-0">
        {/* 功能面板 - 50% 宽度（当激活时） */}
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
        
        {/* 聊天机器人 - 动态宽度 */}
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