import React from 'react';
import { Button } from './ui/button';
import { Home, Calculator, BarChart3, LayoutGrid } from 'lucide-react';

const FunctionBar = ({ activePanel, setActivePanel }) => {
  const buttons = [
    { 
      label: 'Dynamic Form', 
      icon: Home,
      description: 'Auto-extract customer information'
    },
    { 
      label: 'Loan Calculator', 
      icon: Calculator,
      description: 'Calculate payments and rates'
    },
    { 
      label: 'Product Comparison', 
      icon: BarChart3,
      description: 'Compare recommended products'
    },
    { 
      label: 'Product Showcase', 
      icon: LayoutGrid,
      description: 'Browse all available products'
    }
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
            className="w-12 h-12 p-0 flex items-center justify-center"
            onClick={() => setActivePanel(activePanel === label ? null : label)}
          >
            <Icon className="w-5 h-5" />
          </Button>
          {/* 悬停提示文字 */}
          <div className="absolute left-14 top-1/2 -translate-y-1/2 whitespace-nowrap bg-gray-700 text-white text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
            <div className="font-medium">{label}</div>
            <div className="text-gray-300 text-xs">{description}</div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default FunctionBar;



