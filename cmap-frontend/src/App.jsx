import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';

// Import other components if they exist
let CurrentProduct, ProductShowcase;
try {
  CurrentProduct = require('./components/CurrentProduct').default;
} catch {
  CurrentProduct = () => <div className="p-4"><h2 className="text-lg font-bold">Current Product Information</h2><p>Product information content goes here</p></div>;
}

try {
  ProductShowcase = require('./components/ProductShowcase').default;
} catch {
  ProductShowcase = () => <div className="p-4"><h2 className="text-lg font-bold">Product Showcase</h2><p>Product showcase content goes here</p></div>;
}

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 客户信息状态 - 从dynamic form同步
  const [customerInfo, setCustomerInfo] = useState({});

  // 处理新消息 - 从Chatbot传来
  const handleNewMessage = (message) => {
    setConversationHistory(prev => [...prev, message]);
  };

  // 处理表单更新 - 从Dynamic Form传来
  const handleFormUpdate = (updatedInfo) => {
    setCustomerInfo(updatedInfo);
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
      case 'Current Product Info':
        return <CurrentProduct customerInfo={customerInfo} />;
      case 'Product Showcase':
        return <ProductShowcase customerInfo={customerInfo} />;
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
          />
        </div>
      </div>
    </div>
  );
}

export default App;