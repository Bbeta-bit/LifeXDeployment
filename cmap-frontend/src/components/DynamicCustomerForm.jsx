// DynamicCustomerForm.jsx
import React, { useState, useEffect, useCallback } from 'react';

const DynamicCustomerForm = ({ conversationHistory, onFormUpdate, initialData }) => {
  const [customerInfo, setCustomerInfo] = useState({
    loan_type: 'consumer',
    personal_info: {
      name: '',
      age: '',
      income: '',
      employment_status: '',
      employment_type: '',
      work_experience: '',
      phone: '',
      email: '',
      address: '',
      abn: '',
      gst_registered: '',
      credit_score: '',
      marital_status: '',
      dependents: '',
      assets: '',
      liabilities: '',
      bank_statements: '',
      id_verification: ''
    },
    business_info: {
      business_name: '',
      business_type: '',
      business_age: '',
      annual_revenue: '',
      monthly_revenue: '',
      business_address: '',
      industry: '',
      employees: '',
      gst_number: '',
      business_registration: ''
    },
    asset_info: {
      vehicle_make: '',
      vehicle_model: '',
      vehicle_year: '',
      vehicle_value: '',
      vehicle_condition: '',
      vehicle_rego: '',
      existing_loan_amount: '',
      desired_loan_amount: '',
      loan_purpose: '',
      collateral_type: '',
      collateral_value: '',
      insurance_status: ''
    },
    financial_info: {
      monthly_expenses: '',
      rent_mortgage: '',
      other_loans: '',
      credit_cards: '',
      savings: '',
      investments: '',
      financial_commitments: '',
      bankruptcy_history: '',
      payment_defaults: ''
    },
    extracted_fields: [],
    confidence_score: 0
  });

  const [loading, setLoading] = useState(false);
  const [extractionStatus, setExtractionStatus] = useState(null);
  const [lastProcessedLength, setLastProcessedLength] = useState(0);
  const [autoExtractEnabled, setAutoExtractEnabled] = useState(true);

  // Extract information from conversation
  const extractInfoFromConversation = useCallback(async (forceExtract = false) => {
    if (!conversationHistory || conversationHistory.length === 0) return;
    
    // Skip if no new messages and not forced
    if (!forceExtract && conversationHistory.length === lastProcessedLength) return;

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/extract-customer-info', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_history: conversationHistory,
          existing_info: customerInfo
        }),
      });

      if (!response.ok) {
        throw new Error('Information extraction failed');
      }

      const data = await response.json();
      
      if (data.status === 'success') {
        setCustomerInfo(data.customer_info);
        setExtractionStatus({
          missing_fields: data.missing_fields,
          completeness: data.extraction_completeness,
          suggestions: data.suggestions
        });
        
        // Update last processed length
        setLastProcessedLength(conversationHistory.length);
        
        // Notify parent component that form has been updated
        if (onFormUpdate) {
          onFormUpdate(data.customer_info);
        }
      }
    } catch (error) {
      console.error('Error extracting customer information:', error);
      setExtractionStatus({ error: error.message });
    } finally {
      setLoading(false);
    }
  }, [conversationHistory, customerInfo, lastProcessedLength, onFormUpdate]);

  // Auto-extract when conversation updates
  useEffect(() => {
    if (autoExtractEnabled && conversationHistory && conversationHistory.length > lastProcessedLength) {
      // Debounce extraction to avoid too frequent calls
      const timeoutId = setTimeout(() => {
        extractInfoFromConversation();
      }, 2000); // Wait 2 seconds after last message

      return () => clearTimeout(timeoutId);
    }
  }, [conversationHistory, autoExtractEnabled, extractInfoFromConversation, lastProcessedLength]);

  // Load initial data
  useEffect(() => {
    if (initialData) {
      setCustomerInfo(prev => ({ ...prev, ...initialData }));
    }
  }, [initialData]);

  // Handle form field changes
  const handleFieldChange = (section, field, value) => {
    setCustomerInfo(prev => {
      const updated = {
        ...prev,
        [section]: {
          ...prev[section],
          [field]: value
        }
      };

      // Real-time notification to parent component
      if (onFormUpdate) {
        onFormUpdate(updated);
      }

      return updated;
    });
  };

  // Handle loan type changes
  const handleLoanTypeChange = (value) => {
    setCustomerInfo(prev => {
      const updated = { ...prev, loan_type: value };
      if (onFormUpdate) {
        onFormUpdate(updated);
      }
      return updated;
    });
  };

  const getFieldDisplayName = (field) => {
    const fieldNames = {
      // Personal Info
      name: 'Full Name',
      age: 'Age',
      income: 'Monthly Income',
      employment_status: 'Employment Status',
      employment_type: 'Job Type',
      work_experience: 'Work Experience',
      phone: 'Phone Number',
      email: 'Email Address',
      address: 'Residential Address',
      abn: 'ABN Number',
      gst_registered: 'GST Registered',
      credit_score: 'Credit Score',
      marital_status: 'Marital Status',
      dependents: 'Number of Dependents',
      assets: 'Total Assets',
      liabilities: 'Total Liabilities',
      bank_statements: 'Bank Statements Available',
      id_verification: 'ID Verification Status',
      
      // Business Info
      business_name: 'Business Name',
      business_type: 'Business Type',
      business_age: 'Business Age (Years)',
      annual_revenue: 'Annual Revenue',
      monthly_revenue: 'Monthly Revenue',
      business_address: 'Business Address',
      industry: 'Industry Type',
      employees: 'Number of Employees',
      gst_number: 'GST Number',
      business_registration: 'Business Registration',
      
      // Asset Info
      vehicle_make: 'Vehicle Brand',
      vehicle_model: 'Vehicle Model',
      vehicle_year: 'Vehicle Year',
      vehicle_value: 'Vehicle Value',
      vehicle_condition: 'Vehicle Condition',
      vehicle_rego: 'Vehicle Registration',
      existing_loan_amount: 'Existing Loan Amount',
      desired_loan_amount: 'Desired Loan Amount',
      loan_purpose: 'Loan Purpose',
      collateral_type: 'Collateral Type',
      collateral_value: 'Collateral Value',
      insurance_status: 'Insurance Status',
      
      // Financial Info
      monthly_expenses: 'Monthly Expenses',
      rent_mortgage: 'Rent/Mortgage Payment',
      other_loans: 'Other Loan Payments',
      credit_cards: 'Credit Card Debt',
      savings: 'Savings Amount',
      investments: 'Investment Portfolio',
      financial_commitments: 'Other Financial Commitments',
      bankruptcy_history: 'Bankruptcy History',
      payment_defaults: 'Payment Defaults History'
    };
    return fieldNames[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const isFieldExtracted = (field) => {
    return customerInfo.extracted_fields.includes(field);
  };

  const hasNewMessages = conversationHistory && conversationHistory.length > lastProcessedLength;

  const renderFormSection = (title, sectionKey, fields) => (
    <div className="mb-8">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 sticky top-0 bg-white py-2 border-b">{title}</h3>
      <div className="space-y-3">
        {Object.entries(fields).map(([field, value]) => (
          <div key={field} className="flex flex-col">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {getFieldDisplayName(field)}
              {isFieldExtracted(field) && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 ml-2">
                  Auto-filled
                </span>
              )}
            </label>
            {field === 'gst_registered' || field === 'bank_statements' || field === 'id_verification' ? (
              <select
                value={value || ''}
                onChange={(e) => handleFieldChange(sectionKey, field, e.target.value)}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isFieldExtracted(field) ? 'bg-green-50 border-green-300' : 'border-gray-300'
                }`}
              >
                <option value="">Select...</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
            ) : field === 'marital_status' ? (
              <select
                value={value || ''}
                onChange={(e) => handleFieldChange(sectionKey, field, e.target.value)}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isFieldExtracted(field) ? 'bg-green-50 border-green-300' : 'border-gray-300'
                }`}
              >
                <option value="">Select...</option>
                <option value="single">Single</option>
                <option value="married">Married</option>
                <option value="divorced">Divorced</option>
                <option value="widowed">Widowed</option>
                <option value="defacto">De facto</option>
              </select>
            ) : field === 'employment_status' ? (
              <select
                value={value || ''}
                onChange={(e) => handleFieldChange(sectionKey, field, e.target.value)}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isFieldExtracted(field) ? 'bg-green-50 border-green-300' : 'border-gray-300'
                }`}
              >
                <option value="">Select...</option>
                <option value="employed">Employed</option>
                <option value="self-employed">Self-employed</option>
                <option value="unemployed">Unemployed</option>
                <option value="retired">Retired</option>
                <option value="student">Student</option>
              </select>
            ) : (
              <input
                type={
                  ['age', 'income', 'work_experience', 'credit_score', 'dependents', 'assets', 'liabilities', 
                   'business_age', 'annual_revenue', 'monthly_revenue', 'employees', 'vehicle_year', 
                   'vehicle_value', 'existing_loan_amount', 'desired_loan_amount', 'collateral_value',
                   'monthly_expenses', 'rent_mortgage', 'other_loans', 'credit_cards', 'savings'].includes(field) 
                  ? 'number' : field === 'email' ? 'email' : 'text'
                }
                value={value || ''}
                onChange={(e) => handleFieldChange(sectionKey, field, e.target.value)}
                className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isFieldExtracted(field) ? 'bg-green-50 border-green-300' : 'border-gray-300'
                }`}
                placeholder={`Enter ${getFieldDisplayName(field)}`}
                min={field === 'vehicle_year' ? '1980' : field.includes('amount') || field.includes('value') || field.includes('income') || field.includes('revenue') ? '0' : undefined}
                max={field === 'vehicle_year' ? '2030' : undefined}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Fixed Header */}
      <div className="flex-shrink-0 p-6 border-b bg-white">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Customer Information</h2>
        
        {/* Auto-extract toggle */}
        <div className="mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={autoExtractEnabled}
              onChange={(e) => setAutoExtractEnabled(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Auto-extract from conversation</span>
          </label>
        </div>

        {/* New messages indicator */}
        {hasNewMessages && autoExtractEnabled && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
            <div className="flex items-center">
              <div className="h-2 w-2 bg-blue-600 rounded-full mr-2"></div>
              <span className="text-blue-700">New messages detected - extracting information...</span>
            </div>
          </div>
        )}
        
        {loading && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-blue-700">Extracting information from conversation...</span>
            </div>
          </div>
        )}

        {extractionStatus && !loading && (
          <div className="bg-green-50 border border-green-200 rounded-md p-4 mb-4">
            <h3 className="text-sm font-medium text-green-800 mb-2">Extraction Status</h3>
            <div className="text-sm text-green-700">
              <p>Completeness: {Math.round(extractionStatus.completeness * 100)}%</p>
              <p>Extracted: {customerInfo.extracted_fields.length} fields</p>
              {conversationHistory && (
                <p>Processed: {lastProcessedLength}/{conversationHistory.length} messages</p>
              )}
            </div>
          </div>
        )}

        {/* Loan Type Selection */}
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Loan Type</h3>
          <div className="flex space-x-4">
            <label className="flex items-center">
              <input
                type="radio"
                name="loan_type"
                value="consumer"
                checked={customerInfo.loan_type === 'consumer'}
                onChange={(e) => handleLoanTypeChange(e.target.value)}
                className="mr-2"
              />
              <span>Consumer Loan</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="loan_type"
                value="commercial"
                checked={customerInfo.loan_type === 'commercial'}
                onChange={(e) => handleLoanTypeChange(e.target.value)}
                className="mr-2"
              />
              <span>Commercial Loan</span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between items-center">
          <button
            type="button"
            onClick={() => extractInfoFromConversation(true)}
            disabled={loading || !conversationHistory || conversationHistory.length === 0}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Extracting...
              </>
            ) : (
              'Re-extract Information'
            )}
          </button>

          <div className="flex space-x-3">
            <button
              type="button"
              onClick={() => {
                setCustomerInfo({
                  loan_type: 'consumer',
                  personal_info: {},
                  business_info: {},
                  asset_info: {},
                  financial_info: {},
                  extracted_fields: [],
                  confidence_score: 0
                });
                setLastProcessedLength(0);
                setExtractionStatus(null);
              }}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Reset
            </button>
            <button
              type="submit"
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
              Save
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Personal Information */}
        {renderFormSection('Personal Information', 'personal_info', customerInfo.personal_info)}

        {/* Business Information - only show for commercial loans */}
        {customerInfo.loan_type === 'commercial' && 
          renderFormSection('Business Information', 'business_info', customerInfo.business_info)
        }

        {/* Asset Information */}
        {renderFormSection('Asset Information', 'asset_info', customerInfo.asset_info)}

        {/* Financial Information */}
        {renderFormSection('Financial Information', 'financial_info', customerInfo.financial_info)}

        {/* Extraction Suggestions */}
        {extractionStatus && extractionStatus.suggestions && (
          <div className="mt-6 bg-yellow-50 border border-yellow-200 rounded-md p-4">
            <h4 className="text-sm font-medium text-yellow-800 mb-2">Suggested follow-up questions:</h4>
            <ul className="text-sm text-yellow-700 space-y-1">
              {extractionStatus.suggestions.next_questions?.map((question, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 bg-yellow-400 rounded-full mt-2 mr-2 flex-shrink-0"></span>
                  {question}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default DynamicCustomerForm;