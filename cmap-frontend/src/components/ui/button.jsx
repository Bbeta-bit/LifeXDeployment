// src/components/ui/button.jsx
import React from 'react';
import clsx from 'clsx'; // 你可以先用这个方式组合 className，没有的话也能正常用

export const Button = ({
  children,
  className,
  variant = 'default',
  ...props
}) => {
  const baseStyle =
    'rounded-md px-3 py-2 text-sm font-medium transition-all';

  const variants = {
    default: 'bg-blue-600 text-white hover:bg-blue-700',
    ghost: 'bg-transparent text-gray-700 hover:bg-gray-100'
  };

  return (
    <button
      className={clsx(baseStyle, variants[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
};
