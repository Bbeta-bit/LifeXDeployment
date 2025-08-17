import React from 'react';
import { Button } from './ui/button';
import { Home, Calculator, Info, Gift } from 'lucide-react';

const FunctionBar = ({ activePanel, setActivePanel }) => {
  const buttons = [
    { label: 'Dynamic Form', icon: Home, description: 'Customer Information' },
    { label: 'Loan Calculator', icon: Calculator, description: 'Payment Calculator' },
    { label: 'Current Product Info', icon: Info, description: 'Product Details' },
    { label: 'Promotions', icon: Gift, description: 'Marketing Materials' }
  ];

  return (
    <div 
      className="w-16 border-r shadow flex flex-col items-center py-4 space-y-4"
      style={{ backgroundColor: '#fef7e8' }}
    >
      {buttons.map(({ label, icon: Icon, description }) => (
        <div key={label} className="relative group">
          <Button
            variant={activePanel === label ? 'default' : 'ghost'}
            className={`w-12 h-12 p-0 flex items-center justify-center transition-all duration-200 ${
              activePanel === label 
                ? 'bg-blue-600 text-white shadow-md scale-105' 
                : 'hover:bg-gray-100 hover:shadow-sm hover:scale-105'
            }`}
            onClick={() => setActivePanel(activePanel === label ? null : label)}
          >
            <Icon className={`w-5 h-5 ${
              label === 'Promotions' ? 'text-orange-500' : 
              activePanel === label ? 'text-white' : 'text-gray-600'
            }`} />
          </Button>
          
          {/* 原始的悬停提示 */}
          <div className="absolute left-14 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none">
            <div className="bg-gray-900 text-white text-sm rounded-lg px-3 py-2 whitespace-nowrap shadow-lg">
              <div className="font-medium">{label}</div>
              <div className="text-xs text-gray-300 mt-1">{description}</div>
              
              {/* 箭头 */}
              <div className="absolute left-[-4px] top-1/2 -translate-y-1/2 w-0 h-0 border-t-[4px] border-b-[4px] border-r-[4px] border-transparent border-r-gray-900"></div>
            </div>
          </div>
        </div>
      ))}

      {/* 底部装饰 */}
      <div className="flex-1"></div>
      
      <div className="w-8 h-0.5 bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
    </div>
  );
};

export default FunctionBar;