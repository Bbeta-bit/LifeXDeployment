import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicCustomerForm from './components/DynamicCustomerForm'; // Updated to use enhanced version
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
    console.log('Customer info updated:', updatedInfo);
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
    <div className="h-screen w-screen flex bg-gray-100">
      {/* Left sidebar - fixed width */}
      <FunctionBar activePanel={activePanel} setActivePanel={setActivePanel} />
      
      {/* Main content area */}
      <div className="flex-1 flex">
        {/* Function panel - shows when activePanel exists, takes half width */}
        {activePanel && (
          <div className="flex-1 bg-white border-r shadow-lg overflow-hidden">
            {renderActivePanel()}
          </div>
        )}
        
        {/* Chatbot - takes remaining space (half or full) */}
        <div className={activePanel ? "flex-1" : "flex-1"}>
          <Chatbot 
            onNewMessage={handleNewMessage}
            conversationHistory={conversationHistory}
            customerInfo={customerInfo}
          />
        </div>
      </div>
      
      {/* 调试信息 - 只在开发环境显示 */}
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 left-20 bg-black bg-opacity-75 text-white text-xs p-2 rounded max-w-xs">
          <div>Messages: {conversationHistory.length}</div>
          <div>Extracted Fields: {customerInfo.extracted_fields?.length || 0}</div>
          <div>Active Panel: {activePanel || 'None'}</div>
        </div>
      )}
    </div>
  );
}

export default App;