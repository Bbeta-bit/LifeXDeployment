import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';
import PromotionsShowcase from './components/PromotionsShowcase';
import ProductComparison from './components/ProductComparison';

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 客户信息状态 - 优化管理，支持双向同步
  const [customerInfo, setCustomerInfo] = useState({});
  
  // 推荐状态管理 - 支持多推荐管理
  const [recommendations, setRecommendations] = useState([]);

  // 处理新消息 - 从Chatbot传来
  const handleNewMessage = (message) => {
    setConversationHistory(prev => [...prev, message]);
  };

  // 处理表单更新 - 优化双向同步逻辑
  const handleFormUpdate = (updatedInfo) => {
    try {
      // 深度比较，只有真正变化时才更新
      const hasChanges = Object.keys(updatedInfo || {}).some(key => {
        const oldValue = customerInfo[key];
        const newValue = updatedInfo[key];
        return oldValue !== newValue;
      });

      if (hasChanges) {
        setCustomerInfo(prev => ({ ...prev, ...updatedInfo }));
      }
    } catch (error) {
      console.error('Error in handleFormUpdate:', error);
    }
  };
  
  // 处理推荐更新 - 支持多推荐管理和自动面板切换
  const handleRecommendationUpdate = (newRecommendations) => {
    try {
      if (newRecommendations && Array.isArray(newRecommendations) && newRecommendations.length > 0) {
        // 更新推荐状态
        setRecommendations(newRecommendations);
        
        // 自动打开Product Comparison面板（如果没有面板激活）
        if (!activePanel) {
          setActivePanel('Current Product Info');
        }
      }
    } catch (error) {
      console.error('Error in handleRecommendationUpdate:', error);
    }
  };

  // 面板渲染函数
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
          return <ProductComparison recommendations={recommendations} customerInfo={customerInfo} />;
        case 'Promotions':
          return <PromotionsShowcase />;
        default:
          return null;
      }
    } catch (error) {
      console.error('Error rendering panel:', error);
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

  // 错误边界状态
  const [hasError, setHasError] = React.useState(false);

  React.useEffect(() => {
    // 重置错误状态
    setHasError(false);
  }, [activePanel]);

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
            onError={(error) => {
              console.error('Chatbot error:', error);
              setHasError(true);
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default App;