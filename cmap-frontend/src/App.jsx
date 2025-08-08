import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import ProductComparison from './components/ProductComparison';

// Import ProductShowcase component if it exists
let ProductShowcase;
try {
  ProductShowcase = require('./components/ProductShowcase').default;
} catch {
  ProductShowcase = () => (
    <div className="p-6 h-full flex flex-col" style={{ backgroundColor: '#fef7e8' }}>
      <div className="border-b pb-4 mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Product Showcase</h2>
        <p className="text-gray-600 mt-1">Market overview and product highlights</p>
      </div>
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <div className="text-6xl mb-4">🏪</div>
          <p>Product showcase content will be implemented here</p>
          <p className="text-sm mt-2">Feature coming soon...</p>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 客户信息状态 - 从dynamic form同步
  const [customerInfo, setCustomerInfo] = useState({});
  
  // 推荐产品状态 - 从chatbot传递给ProductComparison
  const [recommendations, setRecommendations] = useState([]);

  // 处理新消息 - 从Chatbot传来
  const handleNewMessage = (message) => {
    setConversationHistory(prev => [...prev, message]);
  };

  // 处理表单更新 - 从Dynamic Form传来
  const handleFormUpdate = (updatedInfo) => {
    setCustomerInfo(updatedInfo);
  };

  // 处理推荐更新 - 从Chatbot传来
  const handleRecommendationUpdate = (newRecommendations) => {
    if (newRecommendations && newRecommendations.length > 0) {
      setRecommendations(prev => {
        // 合并新推荐和现有推荐
        const combined = [...newRecommendations, ...prev];
        // 去重，基于lender_name和product_name
        const unique = combined.filter((item, index, self) => 
          index === self.findIndex(t => 
            t.lender_name === item.lender_name && t.product_name === item.product_name
          )
        );
        // 只保留最新的3个
        return unique.slice(0, 3);
      });
    }
  };

  // 清空推荐 - 从ProductComparison传来
  const handleClearRecommendations = () => {
    setRecommendations([]);
  };

  // 渲染不同的面板组件
  const renderActivePanel = () => {
    switch (activePanel) {
      case 'Dynamic Form':
        return (
          <DynamicCustomerForm 
            conversationHistory={conversationHistory}
            onFormUpdate={handleFormUpdate}
            initialData={customerInfo}
          />
        );
      case 'Loan Calculator':
        return <LoanCalculator customerInfo={customerInfo} />;
      case 'Product Comparison':
        return (
          <ProductComparison 
            recommendations={recommendations}
            onRecommendationUpdate={handleClearRecommendations}
          />
        );
      case 'Product Showcase':
        return <ProductShowcase customerInfo={customerInfo} recommendations={recommendations} />;
      default:
        return null;
    }
  };

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
          <Chatbot 
            onNewMessage={handleNewMessage}
            conversationHistory={conversationHistory}
            customerInfo={customerInfo}
            onRecommendationUpdate={handleRecommendationUpdate}
          />
        </div>
      </div>
    </div>
  );
}

export default App;