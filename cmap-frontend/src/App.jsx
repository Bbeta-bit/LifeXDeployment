import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicForm from './components/DynamicForm';
import LoanCalculator from './components/LoanCalculator';

function App() {
  const [activePanel, setActivePanel] = useState(null);

  // 模拟的表单数据和状态
  const [formData, setFormData] = useState({});
  const mockSchema = {
    fields: [
      { name: 'loanAmount', label: '贷款金额', type: 'text', required: true },
      { name: 'interestRate', label: '利率', type: 'text', required: true },
      { name: 'loanTerm', label: '贷款期限', type: 'select', required: true, options: [
        { value: '12', label: '12个月' },
        { value: '24', label: '24个月' },
        { value: '36', label: '36个月' }
      ]},
      { name: 'income', label: '月收入', type: 'text', required: true }
    ]
  };

  // 根据activePanel渲染不同的组件
  const renderActivePanel = () => {
    switch (activePanel) {
      case 'Dynamic Form':
        return (
          <DynamicForm 
            schema={mockSchema} 
            formData={formData} 
            onChange={setFormData} 
          />
        );
      case 'Loan Calculator':
        return <LoanCalculator />;
      case 'Current Product Info':
        return <div className="p-4"><h2 className="text-lg font-bold">当前产品信息</h2><p>这里是产品信息的内容</p></div>;
      case 'Product Showcase':
        return <div className="p-4"><h2 className="text-lg font-bold">产品展示</h2><p>这里是产品展示的内容</p></div>;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen w-screen flex">
      {/* 左侧功能栏 - 固定宽度 */}
      <FunctionBar activePanel={activePanel} setActivePanel={setActivePanel} />
      
      {/* 主体内容区域 */}
      <div className="flex-1 flex">
        {/* 功能面板 - 当有activePanel时显示 */}
        {activePanel && (
          <div className="w-80 bg-white border-r shadow-lg">
            {renderActivePanel()}
          </div>
        )}
        
        {/* 聊天机器人 - 占据剩余空间 */}
        <div className="flex-1">
          <Chatbot />
        </div>
      </div>
    </div>
  );
}

export default App;