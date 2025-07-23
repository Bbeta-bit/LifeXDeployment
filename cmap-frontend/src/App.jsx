import { useState } from 'react';
import Chatbot from './components/Chatbot';
import DynamicForm from './components/DynamicForm';
import FunctionBar from './components/FunctionBar';
import LanguageSelector from './components/LanguageSelector';
import LoanCalculator from './components/LoanCalculator';
import CurrentProduct from './components/CurrentProduct';
import ProductShowcase from './components/ProductShowcase';

import { useTranslation } from 'react-i18next'; // 引入翻译 Hook
import './App.css';

function App() {
  const [activePanel, setActivePanel] = useState(null);
  const [formData, setFormData] = useState({});
  const { t } = useTranslation(); // 使用翻译函数

  const [formSchema, setFormSchema] = useState({
    fields: [
      { name: 'fullName', label: t('form.fullName'), type: 'text', required: true },
      { name: 'loanAmount', label: t('form.loanAmount'), type: 'text', required: true },
      { name: 'annualIncome', label: t('form.annualIncome'), type: 'text', required: true },
      { name: 'collateral', label: t('form.collateral'), type: 'text', required: false },
    ]
  });

  const renderPanel = () => {
    switch (activePanel) {
      case 'Dynamic Form':
        return (
          <div className="p-4 overflow-y-auto bg-white w-1/2 border-r">
            <DynamicForm
              schema={formSchema}
              formData={formData}
              onChange={setFormData}
              readOnly={true}
            />
          </div>
        );
      case 'Loan Calculator':
        return (
          <div className="p-4 overflow-y-auto bg-white w-1/2 border-r">
            <LoanCalculator />
          </div>
        );
      case 'Current Product Info':
        return (
          <div className="p-4 overflow-y-auto bg-white w-1/2 border-r">
            <CurrentProduct />
          </div>
        );
      case 'Product Showcase':
        return (
          <div className="p-4 overflow-y-auto bg-white w-1/2 border-r">
            <ProductShowcase />
          </div>
        );
      default:
        return null;
    }
  };

  const isPanelOpen = activePanel !== null;

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-50">
      {/* 顶部语言选择器 */}
      <div className="flex justify-end items-center px-4 py-2 bg-white shadow">
        <LanguageSelector />
      </div>

      {/* 页面主体 */}
      <div className="flex flex-1 overflow-hidden">
        <FunctionBar activePanel={activePanel} setActivePanel={setActivePanel} />

        {/* 中间 + Chatbot */}
        {isPanelOpen ? (
          <div className="flex flex-1">
            {renderPanel()}
            <div className="w-1/2 p-4 overflow-y-auto bg-white flex flex-col items-center">
              <h2 className="text-xl font-semibold mb-4 text-center">AgentX</h2>
              <div className="w-full">
                <Chatbot
                  formData={formData}
                  setFormData={setFormData}
                  setFormSchema={setFormSchema}
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="flex-1 p-4 overflow-y-auto bg-white flex flex-col items-center">
            <h2 className="text-xl font-semibold mb-4 text-center">AgentX</h2>
            <div className="w-full">
              <Chatbot
                formData={formData}
                setFormData={setFormData}
                setFormSchema={setFormSchema}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;












