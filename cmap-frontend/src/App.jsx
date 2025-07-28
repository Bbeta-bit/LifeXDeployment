import React, { useState } from 'react';
import Chatbot from './components/Chatbot';
import FunctionBar from './components/FunctionBar';
import DynamicForm from './components/DynamicCustomerForm';
import LoanCalculator from './components/LoanCalculator';

function App() {
  const [activePanel, setActivePanel] = useState(null);

  // Mock form data and state
  const [formData, setFormData] = useState({});
  const mockSchema = {
    fields: [
      { name: 'loanAmount', label: 'Loan Amount', type: 'text', required: true },
      { name: 'interestRate', label: 'Interest Rate', type: 'text', required: true },
      { name: 'loanTerm', label: 'Loan Term', type: 'select', required: true, options: [
        { value: '12', label: '12 Months' },
        { value: '24', label: '24 Months' },
        { value: '36', label: '36 Months' }
      ]},
      { name: 'income', label: 'Monthly Income', type: 'text', required: true }
    ]
  };

  // Render different components based on activePanel
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
        return <div className="p-4 h-full overflow-y-auto"><h2 className="text-lg font-bold">Current Product Information</h2><p>Product information content goes here</p></div>;
      case 'Product Showcase':
        return <div className="p-4 h-full overflow-y-auto"><h2 className="text-lg font-bold">Product Showcase</h2><p>Product showcase content goes here</p></div>;
      default:
        return null;
    }
  };

  return (
    <div className="h-screen w-screen flex">
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
          <Chatbot />
        </div>
      </div>
    </div>
  );
}

export default App;