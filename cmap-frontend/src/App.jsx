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

// 🔧 改进的Product Comparison组件
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

  // 显示推荐产品
  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto">
      <div className="border-b pb-4">
        <h2 className="text-2xl font-bold text-gray-800">Product Recommendations</h2>
        <p className="text-sm text-gray-600 mt-1">
          {recommendations.length} recommendation{recommendations.length > 1 ? 's' : ''} found based on your requirements
        </p>
      </div>

      {recommendations.map((rec, index) => (
        <div key={index} className="bg-white border rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
          <div className="flex justify-between items-start mb-4">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-800">
                {rec.lender_name} - {rec.product_name}
              </h3>
              <div className="flex items-center space-x-4 mt-2">
                <span className="text-2xl font-bold text-blue-600">
                  {rec.base_rate}% p.a.
                </span>
                {rec.comparison_rate && (
                  <span className="text-sm text-gray-600">
                    Comparison: {rec.comparison_rate}% p.a.*
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              {rec.monthly_payment && (
                <>
                  <div className="text-xl font-semibold text-green-600">
                    ${rec.monthly_payment}/month
                  </div>
                  <div className="text-xs text-gray-500">estimated payment</div>
                </>
              )}
            </div>
          </div>

          {/* 贷款详情 */}
          <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Max Loan:</span>
              <span className="font-medium">{rec.max_loan_amount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Terms:</span>
              <span className="font-medium">{rec.loan_term_options}</span>
            </div>
          </div>

          {/* 可折叠的详细信息 */}
          <details className="mt-4">
            <summary className="cursor-pointer text-blue-600 hover:text-blue-800 font-medium">
              View detailed requirements and fees
            </summary>
            
            <div className="mt-3 space-y-4">
              {/* 要求详情 */}
              {rec.detailed_requirements && (
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">📋 Requirements:</h4>
                  <div className="grid grid-cols-1 gap-2 text-sm bg-gray-50 p-3 rounded">
                    {Object.entries(rec.detailed_requirements).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="font-medium">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 费用明细 */}
              {rec.fees_breakdown && (
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">💳 Fees:</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm bg-gray-50 p-3 rounded">
                    {Object.entries(rec.fees_breakdown).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                        <span className="font-medium">{value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 文档要求 */}
              {rec.documentation_requirements && rec.documentation_requirements.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-800 mb-2">📄 Documentation Required:</h4>
                  <ul className="text-sm space-y-1 bg-gray-50 p-3 rounded">
                    {rec.documentation_requirements.map((doc, i) => (
                      <li key={i} className="flex items-start">
                        <span className="text-blue-600 mr-2">•</span>
                        <span>{doc}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </details>

          {/* 状态指示 */}
          <div className="mt-4 pt-4 border-t flex justify-between items-center">
            <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm ${
              rec.requirements_met 
                ? 'bg-green-100 text-green-800' 
                : 'bg-yellow-100 text-yellow-800'
            }`}>
              {rec.requirements_met ? '✅ Eligible' : '⚠️ Review Requirements'}
            </div>
            
            <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm">
              Apply Now
            </button>
          </div>
        </div>
      ))}

      {/* 免责声明 */}
      <div className="mt-6 p-4 bg-gray-50 rounded text-xs text-gray-600">
        <p>* Comparison rates are estimates and include typical fees. Actual rates may vary based on individual circumstances and lender assessment.</p>
        <p className="mt-1">** Monthly payment estimates are indicative only. Final payments depend on approved loan amount, term, and individual pricing.</p>
      </div>
    </div>
  );
};

function App() {
  const [activePanel, setActivePanel] = useState(null);
  
  // 对话历史状态 - 统一管理
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // 客户信息状态 - 从dynamic form同步
  const [customerInfo, setCustomerInfo] = useState({});
  
  // 推荐状态管理
  const [recommendations, setRecommendations] = useState([]);

  // 处理新消息 - 从Chatbot传来
  const handleNewMessage = (message) => {
    setConversationHistory(prev => [...prev, message]);
  };

  // 处理表单更新 - 从Dynamic Form传来
  const handleFormUpdate = (updatedInfo) => {
    setCustomerInfo(updatedInfo);
  };
  
  // 🔧 处理推荐更新 - 从Chatbot传来
  const handleRecommendationUpdate = (newRecommendations) => {
    console.log('App received recommendations:', newRecommendations);
    setRecommendations(newRecommendations);
    
    // 如果收到推荐且没有打开面板，自动打开Loan Calculator面板来显示推荐
    if (newRecommendations && newRecommendations.length > 0 && !activePanel) {
      setActivePanel('Loan Calculator');
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
          />
        );
      case 'Loan Calculator':
        // 如果有推荐数据，显示Product Comparison；否则显示Calculator
        if (recommendations && recommendations.length > 0) {
          return <ProductComparison recommendations={recommendations} customerInfo={customerInfo} />;
        } else {
          return <LoanCalculator customerInfo={customerInfo} />;
        }
      case 'Current Product Info':
        return <CurrentProduct customerInfo={customerInfo} />;
      case 'Promotions':
        return <PromotionsShowcase />; // 🔧 新的优惠活动组件
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

