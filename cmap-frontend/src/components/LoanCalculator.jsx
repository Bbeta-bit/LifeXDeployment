import { useState, useEffect } from 'react';

const EnhancedLoanCalculator = ({ customerInfo = {} }) => {
  const [calculatorMode, setCalculatorMode] = useState('monthly-first');
  const [inputs, setInputs] = useState({
    loanAmount: customerInfo.desired_loan_amount || '',
    monthlyPayment: '',
    interestRate: '',
    loanTermMonths: '60',
    balloonPayment: '',
    balloonPercent: ''
  });
  const [results, setResults] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // 根据客户信息预填表单
  useEffect(() => {
    if (customerInfo.desired_loan_amount) {
      setInputs(prev => ({
        ...prev,
        loanAmount: customerInfo.desired_loan_amount
      }));
    }
  }, [customerInfo]);

  // 主要计算函数
  const calculate = () => {
    const principal = parseFloat(inputs.loanAmount);
    const termMonths = parseInt(inputs.loanTermMonths);
    
    if (!principal || !termMonths) {
      setResults(null);
      return;
    }

    if (calculatorMode === 'monthly-first') {
      const monthlyPayment = parseFloat(inputs.monthlyPayment);
      if (!monthlyPayment) {
        setResults(null);
        return;
      }
      
      const balloonAmount = inputs.balloonPercent ? 
        (principal * parseFloat(inputs.balloonPercent) / 100) : 
        parseFloat(inputs.balloonPayment) || 0;
      
      const requiredRate = calculateRequiredRate(principal, monthlyPayment, termMonths, balloonAmount);
      
      const totalPayments = monthlyPayment * termMonths + balloonAmount;
      const totalInterest = totalPayments - principal;
      
      setResults({
        monthlyPayment: monthlyPayment.toFixed(2),
        requiredRate: requiredRate.toFixed(2),
        balloonPayment: balloonAmount.toFixed(2),
        totalPayments: totalPayments.toFixed(2),
        totalInterest: totalInterest.toFixed(2),
        mode: 'monthly-first'
      });
      
    } else {
      const annualRate = parseFloat(inputs.interestRate);
      if (!annualRate) {
        setResults(null);
        return;
      }
      
      const monthlyRate = annualRate / 12 / 100;
      const balloonAmount = inputs.balloonPercent ? 
        (principal * parseFloat(inputs.balloonPercent) / 100) : 
        parseFloat(inputs.balloonPayment) || 0;
      
      let monthlyPayment;
      if (balloonAmount > 0) {
        const presentValueOfBalloon = balloonAmount / Math.pow(1 + monthlyRate, termMonths);
        const loanAmountMinusBalloon = principal - presentValueOfBalloon;
        monthlyPayment = (loanAmountMinusBalloon * monthlyRate) / 
                        (1 - Math.pow(1 + monthlyRate, -termMonths));
      } else {
        monthlyPayment = (principal * monthlyRate) / 
                        (1 - Math.pow(1 + monthlyRate, -termMonths));
      }
      
      const totalPayments = monthlyPayment * termMonths + balloonAmount;
      const totalInterest = totalPayments - principal;
      
      setResults({
        monthlyPayment: monthlyPayment.toFixed(2),
        interestRate: annualRate.toFixed(2),
        balloonPayment: balloonAmount.toFixed(2),
        totalPayments: totalPayments.toFixed(2),
        totalInterest: totalInterest.toFixed(2),
        mode: 'rate-first'
      });
    }
  };

  // 数值方法计算所需利率
  const calculateRequiredRate = (principal, monthlyPayment, termMonths, balloonAmount) => {
    const targetPmt = monthlyPayment;
    let rate = 0.001;
    let maxRate = 0.5;
    let minRate = 0;
    
    for (let i = 0; i < 100; i++) {
      const monthlyRate = rate / 12;
      let calculatedPmt;
      
      if (balloonAmount > 0) {
        const presentValueOfBalloon = balloonAmount / Math.pow(1 + monthlyRate, termMonths);
        const loanAmountMinusBalloon = principal - presentValueOfBalloon;
        if (loanAmountMinusBalloon <= 0) {
          rate = minRate + (maxRate - minRate) / 2;
          continue;
        }
        calculatedPmt = (loanAmountMinusBalloon * monthlyRate) / 
                       (1 - Math.pow(1 + monthlyRate, -termMonths));
      } else {
        calculatedPmt = (principal * monthlyRate) / 
                       (1 - Math.pow(1 + monthlyRate, -termMonths));
      }
      
      if (Math.abs(calculatedPmt - targetPmt) < 0.01) {
        return rate * 100;
      }
      
      if (calculatedPmt > targetPmt) {
        maxRate = rate;
      } else {
        minRate = rate;
      }
      
      rate = minRate + (maxRate - minRate) / 2;
    }
    
    return rate * 100;
  };

  // 🔧 计算精确的替代方案
  const calculateAlternativeScenarios = () => {
    if (!results || !inputs.loanAmount) return null;
    
    const principal = parseFloat(inputs.loanAmount);
    const currentTerm = parseInt(inputs.loanTermMonths);
    const currentRate = calculatorMode === 'rate-first' ? 
      parseFloat(inputs.interestRate) : 
      parseFloat(results.requiredRate);
    
    const calculateMonthlyPayment = (amount, rate, term, balloon = 0) => {
      const monthlyRate = rate / 12 / 100;
      let payment;
      
      if (balloon > 0) {
        const presentValueOfBalloon = balloon / Math.pow(1 + monthlyRate, term);
        const loanAmountMinusBalloon = amount - presentValueOfBalloon;
        payment = (loanAmountMinusBalloon * monthlyRate) / 
                 (1 - Math.pow(1 + monthlyRate, -term));
      } else {
        payment = (amount * monthlyRate) / 
                 (1 - Math.pow(1 + monthlyRate, -term));
      }
      
      return payment;
    };
    
    const scenarios = [];
    
    // 较长期限选项
    if (currentTerm < 84) {
      const longerTerm = Math.min(84, currentTerm + 24);
      const longerPayment = calculateMonthlyPayment(principal, currentRate, longerTerm);
      scenarios.push({
        title: "Lower Monthly Payments",
        description: `Extend to ${longerTerm} months`,
        payment: longerPayment,
        savings: parseFloat(results.monthlyPayment) - longerPayment,
        type: "lower"
      });
    }
    
    // 较短期限选项
    if (currentTerm > 36) {
      const shorterTerm = Math.max(36, currentTerm - 24);
      const shorterPayment = calculateMonthlyPayment(principal, currentRate, shorterTerm);
      const interestSavings = (parseFloat(results.monthlyPayment) * currentTerm + parseFloat(results.balloonPayment)) - 
                             (shorterPayment * shorterTerm);
      scenarios.push({
        title: "Pay Off Faster",
        description: `Reduce to ${shorterTerm} months`,
        payment: shorterPayment,
        interestSavings: interestSavings,
        type: "shorter"
      });
    }
    
    // 30%尾款选项
    const balloonAmount = principal * 0.3;
    const balloonPayment = calculateMonthlyPayment(principal, currentRate, currentTerm, balloonAmount);
    scenarios.push({
      title: "Lower Payments with Balloon",
      description: "30% balloon payment",
      payment: balloonPayment,
      balloonDue: balloonAmount,
      savings: parseFloat(results.monthlyPayment) - balloonPayment,
      type: "balloon"
    });
    
    return scenarios;
  };

  const quickAmounts = [25000, 50000, 75000, 100000, 150000, 250000];
  
  const getQuickMonthlyAmounts = () => {
    const loanAmount = parseFloat(inputs.loanAmount);
    if (!loanAmount) return [];
    
    const lowRate = 6;
    const midRate = 10;
    const highRate = 15;
    const termMonths = parseInt(inputs.loanTermMonths);
    
    const calculateMonthly = (amount, rate, term) => {
      const monthlyRate = rate / 12 / 100;
      return (amount * monthlyRate) / (1 - Math.pow(1 + monthlyRate, -term));
    };
    
    return [
      Math.round(calculateMonthly(loanAmount, lowRate, termMonths)),
      Math.round(calculateMonthly(loanAmount, midRate, termMonths)),
      Math.round(calculateMonthly(loanAmount, highRate, termMonths))
    ].filter(amount => amount > 0);
  };

  const quickMonthlyAmounts = getQuickMonthlyAmounts();

  const handleInputChange = (field, value) => {
    setInputs(prev => ({ ...prev, [field]: value }));
    
    if (field === 'balloonPercent' && value) {
      setInputs(prev => ({ ...prev, balloonPayment: '' }));
    }
    if (field === 'balloonPayment' && value) {
      setInputs(prev => ({ ...prev, balloonPercent: '' }));
    }
  };

  const resetCalculator = () => {
    setInputs({
      loanAmount: customerInfo.desired_loan_amount || '',
      monthlyPayment: '',
      interestRate: '',
      loanTermMonths: '60',
      balloonPayment: '',
      balloonPercent: ''
    });
    setResults(null);
  };

  // 🔧 获取计算的替代方案
  const alternativeScenarios = calculateAlternativeScenarios();

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto" style={{ backgroundColor: '#fef7e8' }}>
      <div className="border-b pb-4">
        <h2 className="text-2xl font-bold text-gray-800">Smart Loan Calculator</h2>
        <p className="text-sm text-gray-600 mt-1">Calculate payments, rates, and explore loan scenarios</p>
      </div>

      {/* 计算模式切换 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-800 mb-3">What do you want to calculate?</h3>
        <div className="space-y-2">
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="monthly-first"
              checked={calculatorMode === 'monthly-first'}
              onChange={(e) => setCalculatorMode(e.target.value)}
              className="mr-3 text-blue-600"
            />
            <div>
              <span className="font-medium text-blue-800">I know my budget - what rate do I need?</span>
              <p className="text-sm text-blue-600">Enter your desired monthly payment to see what interest rate you'd need</p>
            </div>
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="radio"
              value="rate-first"
              checked={calculatorMode === 'rate-first'}
              onChange={(e) => setCalculatorMode(e.target.value)}
              className="mr-3 text-blue-600"
            />
            <div>
              <span className="font-medium text-blue-800">I have a rate quote - what's my payment?</span>
              <p className="text-sm text-blue-600">Got a product recommendation? Adjust the terms to find your ideal monthly payment</p>
            </div>
          </label>
        </div>
      </div>

      <div className="space-y-4">
        {/* 贷款金额 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Loan Amount (AUD)
          </label>
          <input
            type="number"
            value={inputs.loanAmount}
            onChange={(e) => handleInputChange('loanAmount', e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="e.g., 75000"
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {quickAmounts.map(amount => (
              <button
                key={amount}
                onClick={() => handleInputChange('loanAmount', amount)}
                className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              >
                ${amount.toLocaleString()}
              </button>
            ))}
          </div>
        </div>

        {/* 贷款期限 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Loan Term
          </label>
          <select
            value={inputs.loanTermMonths}
            onChange={(e) => handleInputChange('loanTermMonths', e.target.value)}
            className="w-full border border-gray-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="24">2 years (24 months)</option>
            <option value="36">3 years (36 months)</option>
            <option value="48">4 years (48 months)</option>
            <option value="60">5 years (60 months)</option>
            <option value="72">6 years (72 months)</option>
            <option value="84">7 years (84 months)</option>
          </select>
        </div>

        {/* 主要输入 */}
        {calculatorMode === 'monthly-first' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <span className="text-blue-600 font-semibold">Desired Monthly Payment (AUD)</span>
            </label>
            <input
              type="number"
              value={inputs.monthlyPayment}
              onChange={(e) => handleInputChange('monthlyPayment', e.target.value)}
              className="w-full border-2 border-blue-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-blue-50"
              placeholder="e.g., 1200"
            />
            {quickMonthlyAmounts.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                <span className="text-xs text-gray-600 self-center">Quick options:</span>
                {quickMonthlyAmounts.map(amount => (
                  <button
                    key={amount}
                    onClick={() => handleInputChange('monthlyPayment', amount)}
                    className="px-3 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-700 transition-colors"
                  >
                    ${amount}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              <span className="text-green-600 font-semibold">Interest Rate (% per annum)</span>
            </label>
            <input
              type="number"
              step="0.01"
              value={inputs.interestRate}
              onChange={(e) => handleInputChange('interestRate', e.target.value)}
              className="w-full border-2 border-green-300 p-3 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 bg-green-50"
              placeholder="e.g., 7.5"
            />
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-xs text-gray-600 self-center">Common rates:</span>
              {[6.5, 7.9, 9.5, 11.5, 15.0].map(rate => (
                <button
                  key={rate}
                  onClick={() => handleInputChange('interestRate', rate)}
                  className="px-3 py-1 text-xs bg-green-100 hover:bg-green-200 rounded text-green-700 transition-colors"
                >
                  {rate}%
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 高级选项 */}
        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {showAdvanced ? '▼ Hide' : '▶ Show'} Balloon Payment Options
          </button>
          
          {showAdvanced && (
            <div className="mt-3 p-4 bg-gray-50 rounded-md space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Balloon % of Loan
                  </label>
                  <select
                    value={inputs.balloonPercent}
                    onChange={(e) => handleInputChange('balloonPercent', e.target.value)}
                    className="w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">No balloon</option>
                    <option value="20">20%</option>
                    <option value="30">30%</option>
                    <option value="40">40%</option>
                    <option value="50">50%</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Or Balloon Amount ($)
                  </label>
                  <input
                    type="number"
                    value={inputs.balloonPayment}
                    onChange={(e) => handleInputChange('balloonPayment', e.target.value)}
                    className="w-full border border-gray-300 p-2 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., 25000"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-500">
                Balloon payment reduces monthly payments but creates a lump sum due at loan end
              </p>
            </div>
          )}
        </div>

        {/* 按钮组 */}
        <div className="flex space-x-3 pt-2">
          <button
            onClick={calculate}
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
          <div className="mt-6 p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-lg">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              📊 Calculation Results
              <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                {results.mode === 'monthly-first' ? 'Budget-based' : 'Rate-based'}
              </span>
            </h3>
            
            <div className="space-y-3">
              {results.mode === 'monthly-first' ? (
                <div className="bg-white p-3 rounded border">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">You need an interest rate of</p>
                    <p className="text-3xl font-bold text-green-600">
                      {results.requiredRate}% p.a.
                    </p>
                    <p className="text-sm text-gray-600">to achieve ${results.monthlyPayment}/month</p>
                  </div>
                </div>
              ) : (
                <div className="bg-white p-3 rounded border">
                  <div className="text-center">
                    <p className="text-sm text-gray-600">Your monthly payment will be</p>
                    <p className="text-3xl font-bold text-blue-600">
                      ${results.monthlyPayment}
                    </p>
                    <p className="text-sm text-gray-600">at {results.interestRate}% interest</p>
                  </div>
                </div>
              )}
              
              {/* 详细信息 */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-white p-3 rounded border">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Loan Amount:</span>
                    <span className="font-medium">${parseFloat(inputs.loanAmount).toLocaleString()}</span>
                  </div>
                </div>
                
                <div className="bg-white p-3 rounded border">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Loan Term:</span>
                    <span className="font-medium">{inputs.loanTermMonths} months</span>
                  </div>
                </div>
                
                {parseFloat(results.balloonPayment) > 0 && (
                  <div className="bg-white p-3 rounded border">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Balloon Payment:</span>
                      <span className="font-medium text-orange-600">
                        ${results.balloonPayment}
                      </span>
                    </div>
                  </div>
                )}
                
                <div className="bg-white p-3 rounded border">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Interest:</span>
                    <span className="font-medium text-red-600">${results.totalInterest}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-white p-3 rounded border">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Payments:</span>
                  <span className="font-bold text-lg">${results.totalPayments}</span>
                </div>
              </div>
            </div>

            {/* 市场比较提示 */}
            {results.mode === 'monthly-first' && (
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                <h4 className="font-medium text-yellow-800 mb-1">💡 Market Insight</h4>
                <p className="text-sm text-yellow-700">
                  {parseFloat(results.requiredRate) < 8 ? 
                    "This rate is very competitive! You should be able to find lenders offering this rate." :
                    parseFloat(results.requiredRate) < 12 ?
                    "This rate is reasonable for most borrowers with good credit." :
                    "This rate is quite high. Consider a longer term or larger deposit to reduce monthly payments."
                  }
                </p>
              </div>
            )}
          </div>
        )}

        {/* 🔧 改进的替代方案分析 */}
        {results && alternativeScenarios && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-800 mb-3">💼 Alternative Scenarios</h4>
            <p className="text-xs text-gray-600 mb-4">Compare different loan structures to find what works best for you:</p>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              {alternativeScenarios.map((scenario, index) => (
                <div key={index} className="bg-white p-3 rounded border">
                  <p className="font-medium text-gray-800 mb-1">{scenario.title}</p>
                  <p className="text-gray-600 mb-2">{scenario.description}</p>
                  
                  <div className="space-y-1">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Monthly payment:</span>
                      <span className="font-medium">${Math.round(scenario.payment)}</span>
                    </div>
                    
                    {scenario.savings && scenario.savings > 0 && (
                      <div className="flex justify-between text-green-600">
                        <span>Monthly savings:</span>
                        <span className="font-medium">${Math.round(scenario.savings)}</span>
                      </div>
                    )}
                    
                    {scenario.interestSavings && scenario.interestSavings > 0 && (
                      <div className="flex justify-between text-green-600">
                        <span>Total interest saved:</span>
                        <span className="font-medium">${Math.round(scenario.interestSavings)}</span>
                      </div>
                    )}
                    
                    {scenario.balloonDue && (
                      <div className="flex justify-between text-orange-600">
                        <span>Final balloon:</span>
                        <span className="font-medium">${Math.round(scenario.balloonDue)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {/* 免责声明 */}
            <div className="mt-4 pt-3 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                * Results are estimates only and do not include establishment fees, account keeping fees, or other charges. 
                Actual payments may vary based on lender terms and conditions.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedLoanCalculator;