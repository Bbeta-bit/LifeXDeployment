import { useState } from 'react';

const LoanCalculator = () => {
  const [loanAmount, setLoanAmount] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [loanTerm, setLoanTerm] = useState('');
  const [loanType, setLoanType] = useState('secured'); // 'secured' 或 'unsecured'
  const [balloonPayment, setBalloonPayment] = useState(''); // 尾款金额
  const [results, setResults] = useState(null);

  const calculateRepayment = () => {
    const principal = parseFloat(loanAmount);
    const annualRate = parseFloat(interestRate);
    const months = parseInt(loanTerm); // 直接使用月数
    const balloon = parseFloat(balloonPayment) || 0;

    if (!principal || !annualRate || !months) {
      setResults(null);
      return;
    }

    const monthlyRate = annualRate / 12 / 100;
    const numberOfPayments = months; // 直接使用月数
    
    // 根据贷款类型调整利率
    let adjustedRate = annualRate;
    if (loanType === 'unsecured') {
      adjustedRate += 2; // 无抵押贷款通常利率更高
    }
    const adjustedMonthlyRate = adjustedRate / 12 / 100;

    // 计算月供（考虑尾款）
    let monthlyPayment;
    if (balloon > 0) {
      // 有尾款的情况
      const presentValueOfBalloon = balloon / Math.pow(1 + adjustedMonthlyRate, numberOfPayments);
      const loanAmountMinusBalloon = principal - presentValueOfBalloon;
      monthlyPayment = (loanAmountMinusBalloon * adjustedMonthlyRate) / 
                      (1 - Math.pow(1 + adjustedMonthlyRate, -numberOfPayments));
    } else {
      // 无尾款的传统贷款
      monthlyPayment = (principal * adjustedMonthlyRate) / 
                      (1 - Math.pow(1 + adjustedMonthlyRate, -numberOfPayments));
    }

    // 计算总还款额
    const totalPayments = monthlyPayment * numberOfPayments + balloon;
    const totalInterest = totalPayments - principal;

    setResults({
      monthlyPayment: monthlyPayment.toFixed(2),
      balloonPayment: balloon.toFixed(2),
      totalPayments: totalPayments.toFixed(2),
      totalInterest: totalInterest.toFixed(2),
      adjustedRate: adjustedRate.toFixed(2)
    });
  };

  const resetCalculator = () => {
    setLoanAmount('');
    setInterestRate('');
    setLoanTerm('');
    setBalloonPayment('');
    setResults(null);
  };

  return (
    <div className="p-6 space-y-6 bg-white h-full overflow-y-auto">
      <div className="border-b pb-4">
        <h2 className="text-xl font-bold text-gray-800">Loan Calculator</h2>
        <p className="text-sm text-gray-600 mt-1">Calculate your monthly payment and balloon payment</p>
      </div>

      <div className="space-y-4">
        {/* 贷款类型选择 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Loan Type
          </label>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                value="secured"
                checked={loanType === 'secured'}
                onChange={(e) => setLoanType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm">Secured Loan</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="unsecured"
                checked={loanType === 'unsecured'}
                onChange={(e) => setLoanType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm">Unsecured Loan</span>
            </label>
          </div>
          {loanType === 'unsecured' && (
            <p className="text-xs text-orange-600 mt-1">
              Unsecured loans typically have 2% higher interest rates
            </p>
          )}
        </div>

        {/* 贷款金额 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Loan Amount (AUD)
          </label>
          <input
            type="number"
            value={loanAmount}
            onChange={(e) => setLoanAmount(e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 300000"
          />
        </div>

        {/* 年利率 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Annual Interest Rate (%)
          </label>
          <input
            type="number"
            step="0.01"
            value={interestRate}
            onChange={(e) => setInterestRate(e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 4.5"
          />
        </div>

        {/* 贷款期限 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Loan Term (Months)
          </label>
          <select
            value={loanTerm}
            onChange={(e) => setLoanTerm(e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select term</option>
            <option value="12">12 months</option>
            <option value="24">24 months</option>
            <option value="36">36 months</option>
            <option value="48">48 months</option>
            <option value="60">60 months</option>
            <option value="72">72 months</option>
            <option value="84">84 months</option>
            <option value="96">96 months</option>
            <option value="120">120 months</option>
            <option value="180">180 months</option>
            <option value="240">240 months</option>
            <option value="300">300 months</option>
            <option value="360">360 months</option>
          </select>
        </div>

        {/* 尾款（可选） */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Balloon Payment (AUD) - Optional
          </label>
          <input
            type="number"
            value={balloonPayment}
            onChange={(e) => setBalloonPayment(e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 50000 (leave empty if no balloon payment)"
          />
          <p className="text-xs text-gray-500 mt-1">
            Balloon payment is a lump sum due at the end of the loan term
          </p>
        </div>

        {/* 按钮组 */}
        <div className="flex space-x-3 pt-2">
          <button
            onClick={calculateRepayment}
            className="flex-1 bg-blue-600 text-white px-4 py-3 rounded-md hover:bg-blue-700 transition-colors font-medium"
          >
            Calculate
          </button>
          <button
            onClick={resetCalculator}
            className="px-4 py-3 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
        </div>

        {/* 计算结果 */}
        {results && (
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
            <h3 className="text-lg font-semibold text-green-800 mb-3">Calculation Results</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Effective Annual Rate:</span>
                <span className="font-medium">{results.adjustedRate}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Monthly Payment:</span>
                <span className="font-medium text-lg text-green-700">
                  ${results.monthlyPayment}
                </span>
              </div>
              {parseFloat(results.balloonPayment) > 0 && (
                <div className="flex justify-between">
                  <span className="text-gray-600">Balloon Payment:</span>
                  <span className="font-medium text-orange-600">
                    ${results.balloonPayment}
                  </span>
                </div>
              )}
              <div className="flex justify-between border-t pt-2">
                <span className="text-gray-600">Total Payments:</span>
                <span className="font-medium">${results.totalPayments}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Total Interest:</span>
                <span className="font-medium text-red-600">${results.totalInterest}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default LoanCalculator;

