import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import PromotionsShowcase from './components/PromotionsShowcase';

// Import other components if they exist
let CurrentProduct;
try {
  CurrentProduct = require('./components/CurrentProduct').default;
} catch {
  CurrentProduct = () => (
    <div className="p-6">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Current Product Information</h2>
      <div className="bg-white rounded-lg border p-6">
        <p className="text-gray-600">Product information and details will be displayed here based on user selections and recommendations.</p>
        <div className="mt-4 p-4 bg-blue-50 rounded border border-blue-200">
          <p className="text-blue-800 text-sm">This section will show detailed information about the currently selected loan product, including terms, conditions, and application requirements.</p>
        </div>
      </div>
    </div>
  );
}

// 🔧 修复后的Product Comparison组件引用
const ProductComparison = ({ recommendations, customerInfo }) => {
  console.log('ProductComparison received recommendations:', recommendations);
  
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="mb-4">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-gray-400 text-2xl">💡</span>
          </div>
          <h2 className="text-xl font-semibold text-gray-800 mb-2">No Recommendations Yet</h2>
          <p className="text-gray-600 mb-2">Product recommendations from your chat conversation will appear here for easy comparison.</p>
          <p className="text-sm text-gray-500">Ask the chatbot about loan options to get started!</p>
          
          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h3 className="font-medium text-blue-800 mb-2">How to get recommendations:</h3>
            <ul className="text-sm text-blue-700 text-left space-y-1">
              <li>• Tell the chatbot what you want to finance</li>
              <li>• Provide your basic information (credit score, property status, etc.)</li>
              <li>• Ask for "lowest interest rate" or "show me options"</li>
            </ul>
          </div>
        </div>
      </div>
    );
  }

  // 🔧 使用修复后的ProductComparison组件逻辑
  const ProductComparisonComponent = require('./components/ProductComparison').default;
  return <ProductComparisonComponent recommendations={recommendations} customerInfo={customerInfo} />;
};

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 🔧 客户信息状态 - 优化管理，支持双向同步
  const [customerInfo, setCustomerInfo] = useState({});
  
  // 🔧 推荐状态管理 - 支持多推荐管理
  const [recommendations, setRecommendations] = useState([]);

  // 处理新消息 - 从Chatbot传来
  const handleNewMessage = (message) => {
    setConversationHistory(prev => [...prev, message]);
  };

  // 🔧 处理表单更新 - 优化双向同步逻辑
  const handleFormUpdate = (updatedInfo) => {
    console.log('📝 App: Form updated with:', updatedInfo);
    
    // 🔧 深度比较，只有真正变化时才更新
    const hasChanges = Object.keys(updatedInfo).some(key => {
      const oldValue = customerInfo[key];
      const newValue = updatedInfo[key];
      return oldValue !== newValue;
    });

    if (hasChanges) {
      setCustomerInfo(prev => {
        const merged = { ...prev, ...updatedInfo };
        console.log('🔄 App: CustomerInfo updated:', merged);
        return merged;
      });
    }
  };
  
  // 🔧 处理推荐更新 - 支持多推荐管理和自动面板切换
  const handleRecommendationUpdate = (newRecommendations) => {
    console.log('📋 App received recommendations:', newRecommendations);
    
    if (newRecommendations && newRecommendations.length > 0) {
      // 🔧 更新推荐状态
      setRecommendations(newRecommendations);
      
      // 🔧 自动打开Product Comparison面板（如果没有面板激活）
      if (!activePanel) {
        setActivePanel('Current Product Info');
        console.log('🎯 Auto-opened Product Comparison panel');
      }
      
      // 🔧 如果已经在其他面板，给用户提示（可选）
      else if (activePanel !== 'Current Product Info') {
        console.log('💡 Recommendations available in Product Comparison panel');
      }
    }
  };

  // 🔧 更新的面板渲染函数
  const renderActivePanel = () => {
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
        // 🔧 贷款计算器传入最新的客户信息
        return <LoanCalculator customerInfo={customerInfo} />;
      case 'Current Product Info':
        // 🔧 产品信息显示推荐产品比较，传入完整的推荐和客户信息
        return <ProductComparison recommendations={recommendations} customerInfo={customerInfo} />;
      case 'Promotions':
        return <PromotionsShowcase />;
      default:
        return null;
    }
  };

  // 🔧 调试信息：监控关键状态变化
  React.useEffect(() => {
    console.log('🔍 App state update:', {
      customerInfoKeys: Object.keys(customerInfo),
      recommendationsCount: recommendations.length,
      activePanel,
      conversationLength: conversationHistory.length
    });
  }, [customerInfo, recommendations, activePanel, conversationHistory.length]);

  return (
    <div className="h-screen w-screen flex" style={{ backgroundColor: '#fef7e8' }}>
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
          {/* 🔧 修复后的Chatbot组件，传入最新的customerInfo */}
          <Chatbot 
            onNewMessage={handleNewMessage}
            conversationHistory={conversationHistory}
            customerInfo={customerInfo}  // 🔧 传入最新的客户信息
            onRecommendationUpdate={handleRecommendationUpdate}
          />
        </div>
      </div>

      {/* 🔧 添加调试面板（开发时可用，生产时可移除） */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-black bg-opacity-75 text-white p-2 rounded text-xs max-w-xs">
          <div>Panel: {activePanel || 'None'}</div>
          <div>Customer fields: {Object.keys(customerInfo).length}</div>
          <div>Recommendations: {recommendations.length}</div>
          <div>Conversation: {conversationHistory.length} messages</div>
        </div>
      )}
    </div>
  );
}

export default App;

