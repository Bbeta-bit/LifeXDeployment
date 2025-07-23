import { useState } from 'react';

const LoanCalculator = () => {
  const [loanAmount, setLoanAmount] = useState('');
  const [interestRate, setInterestRate] = useState('');
  const [loanTerm, setLoanTerm] = useState('');
  const [monthlyRepayment, setMonthlyRepayment] = useState(null);

  const calculateRepayment = () => {
    const principal = parseFloat(loanAmount);
    const annualRate = parseFloat(interestRate);
    const years = parseInt(loanTerm);

    if (!principal || !annualRate || !years) {
      setMonthlyRepayment(null);
      return;
    }

    const monthlyRate = annualRate / 12 / 100;
    const numberOfPayments = years * 12;
    const monthly =
      (principal * monthlyRate) /
      (1 - Math.pow(1 + monthlyRate, -numberOfPayments));

    setMonthlyRepayment(monthly.toFixed(2));
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium">Loan Amount ($)</label>
        <input
          type="number"
          value={loanAmount}
          onChange={(e) => setLoanAmount(e.target.value)}
          className="border p-2 rounded w-full"
          placeholder="Enter loan amount"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Annual Interest Rate (%)</label>
        <input
          type="number"
          value={interestRate}
          onChange={(e) => setInterestRate(e.target.value)}
          className="border p-2 rounded w-full"
          placeholder="Enter interest rate"
        />
      </div>

      <div>
        <label className="block text-sm font-medium">Loan Term (Years)</label>
        <input
          type="number"
          value={loanTerm}
          onChange={(e) => setLoanTerm(e.target.value)}
          className="border p-2 rounded w-full"
          placeholder="Enter loan term"
        />
      </div>

      <button
        onClick={calculateRepayment}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        Calculate
      </button>

      {monthlyRepayment && (
        <div className="mt-4 text-green-600 text-lg font-semibold">
          Monthly Repayment: ${monthlyRepayment}
        </div>
      )}
    </div>
  );
};

export default LoanCalculator;

