import React from 'react';
import { Button } from './ui/button';
import { Home, Calculator, Info, LayoutGrid } from 'lucide-react';

const FunctionBar = ({ activePanel, setActivePanel }) => {
  const buttons = [
    { label: 'Dynamic Form', icon: Home },
    { label: 'Loan Calculator', icon: Calculator },
    { label: 'Current Product Info', icon: Info },
    { label: 'Product Showcase', icon: LayoutGrid }
  ];

  return (
    <div className="w-16 bg-white border-r shadow flex flex-col items-center py-4 space-y-4">
      {buttons.map(({ label, icon: Icon }) => (
        <div key={label} className="relative group">
          <Button
            variant={activePanel === label ? 'default' : 'ghost'}
            className="w-12 h-12 p-0 flex items-center justify-center"
            onClick={() => setActivePanel(activePanel === label ? null : label)}
          >
            <Icon className="w-5 h-5" />
          </Button>
          {/* 悬停提示文字 */}
          <span className="absolute left-14 top-1/2 -translate-y-1/2 whitespace-nowrap bg-gray-700 text-white text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {label}
          </span>
        </div>
      ))}
    </div>
  );
};

export default FunctionBar;



