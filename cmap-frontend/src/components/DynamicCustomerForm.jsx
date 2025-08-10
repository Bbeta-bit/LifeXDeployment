import React, { useState, useEffect, useCallback } from 'react';

const DynamicCustomerForm = ({ conversationHistory, onFormUpdate, initialData, recommendations = [] }) => {
  const [customerInfo, setCustomerInfo] = useState({
    loan_type: '',
    asset_type: '',
    property_status: '',
    ABN_years: '',
    GST_years: '',
    credit_score: '',
    desired_loan_amount: '',
    vehicle_type: '',
    vehicle_condition: '',
    vehicle_make: '',
    vehicle_model: '',
    vehicle_year: '',
    business_structure: '',
    interest_rate_ceiling: '',
    monthly_budget: '',
    loan_term_preference: '',
    extracted_fields: [],
    last_updated: null
  });

  const [extractionStatus, setExtractionStatus] = useState({
    isExtracting: false,
    lastExtracted: 0,
    confidence: 0,
    newFieldsCount: 0
  });

  const [autoExtractEnabled, setAutoExtractEnabled] = useState(true);

  // Field configuration
  const fieldConfig = {
    loan_type: {
      label: 'Loan Type',
      type: 'select',
      options: [
        { value: 'consumer', label: 'Consumer Loan' },
        { value: 'commercial', label: 'Commercial Loan' }
      ],
      section: 'core'
    },
    asset_type: {
      label: 'Asset Type',
      type: 'select',
      options: [
        { value: 'motor_vehicle', label: 'Motor Vehicle' },
        { value: 'primary', label: 'Primary Equipment' },
        { value: 'secondary', label: 'Secondary Equipment' },
        { value: 'tertiary', label: 'Tertiary Equipment' }
      ],
      section: 'core'
    },
    property_status: {
      label: 'Property Ownership',
      type: 'select',
      options: [
        { value: 'property_owner', label: 'Property Owner' },
        { value: 'non_property_owner', label: 'Non-Property Owner' }
      ],
      section: 'core'
    },
    ABN_years: {
      label: 'ABN Years',
      type: 'number',
      min: 0,
      max: 50,
      section: 'business'
    },
    GST_years: {
      label: 'GST Years',
      type: 'number',
      min: 0,
      max: 50,
      section: 'business'
    },
    credit_score: {
      label: 'Credit Score',
      type: 'number',
      min: 300,
      max: 900,
      section: 'financial'
    },
    desired_loan_amount: {
      label: 'Desired Loan Amount ($)',
      type: 'number',
      min: 1000,
      section: 'financial'
    },
    vehicle_type: {
      label: 'Vehicle Type',
      type: 'select',
      options: [
        { value: 'passenger_car', label: 'Passenger Car' },
        { value: 'light_truck', label: 'Light Truck' },
        { value: 'van_ute', label: 'Van/Ute' },
        { value: 'motorcycle', label: 'Motorcycle' },
        { value: 'heavy_truck', label: 'Heavy Truck' }
      ],
      section: 'vehicle',
      conditional: (info) => info.asset_type === 'motor_vehicle'
    },
    vehicle_condition: {
      label: 'Vehicle Condition',
      type: 'select',
      options: [
        { value: 'new', label: 'New' },
        { value: 'demonstrator', label: 'Demonstrator' },
        { value: 'used', label: 'Used' }
      ],
      section: 'vehicle',
      conditional: (info) => info.asset_type === 'motor_vehicle'
    },
    vehicle_make: {
      label: 'Vehicle Make',
      type: 'text',
      section: 'vehicle',
      conditional: (info) => info.asset_type === 'motor_vehicle'
    },
    vehicle_model: {
      label: 'Vehicle Model',
      type: 'text',
      section: 'vehicle',
      conditional: (info) => info.asset_type === 'motor_vehicle'
    },
    vehicle_year: {
      label: 'Vehicle Year',
      type: 'number',
      min: 1980,
      max: new Date().getFullYear() + 2,
      section: 'vehicle',
      conditional: (info) => info.asset_type === 'motor_vehicle'
    },
    interest_rate_ceiling: {
      label: 'Maximum Interest Rate (%)',
      type: 'number',
      min: 0,
      max: 30,
      step: 0.1,
      section: 'preferences'
    },
    monthly_budget: {
      label: 'Monthly Budget ($)',
      type: 'number',
      min: 0,
      section: 'preferences'
    },
    loan_term_preference: {
      label: 'Preferred Loan Term (months)',
      type: 'select',
      options: [
        { value: '12', label: '12 months' },
        { value: '24', label: '24 months' },
        { value: '36', label: '36 months' },
        { value: '48', label: '48 months' },
        { value: '60', label: '60 months' },
        { value: '72', label: '72 months' },
        { value: '84', label: '84 months' }
      ],
      section: 'preferences'
    },
    business_structure: {
      label: 'Business Structure',
      type: 'select',
      options: [
        { value: 'sole_trader', label: 'Sole Trader' },
        { value: 'company', label: 'Company' },
        { value: 'trust', label: 'Trust' },
        { value: 'partnership', label: 'Partnership' }
      ],
      section: 'business',
      conditional: (info) => info.loan_type === 'commercial'
    }
  };

  // 🔧 增强的规则提取方法，修复property_status识别
  const extractUsingRules = (text) => {
    const lowercaseText = text.toLowerCase();
    const extracted = {};

    // 🔧 修复房产状态识别 - 更精确的关键词匹配
    const propertyOwnerPatterns = [
      /\bown\s+property\b/,
      /\bproperty\s+owner\b/,
      /\bhave\s+property\b/,
      /\bown\s+a\s+house\b/,
      /\bown\s+a\s+home\b/,
      /\bproperty_owner\b/,
      /\bhomeowner\b/
    ];
    
    const nonPropertyOwnerPatterns = [
      /\bno\s+property\b/,
      /\bdon'?t\s+own\b/,
      /\brent\b/,
      /\brenting\b/,
      /\bnon.property\b/,
      /\bwithout\s+property\b/,
      /\bnon_property_owner\b/,
      /\btenant\b/
    ];

    // 检查房产拥有状态
    const isPropertyOwner = propertyOwnerPatterns.some(pattern => pattern.test(lowercaseText));
    const isNonPropertyOwner = nonPropertyOwnerPatterns.some(pattern => pattern.test(lowercaseText));

    // 🔧 优先级：明确的property_owner关键词 > 否定词汇
    if (isPropertyOwner && !isNonPropertyOwner) {
      extracted.property_status = 'property_owner';
    } else if (isNonPropertyOwner && !isPropertyOwner) {
      extracted.property_status = 'non_property_owner';
    } else if (lowercaseText.includes('property_owner')) {
      // 直接包含property_owner的情况
      extracted.property_status = 'property_owner';
    }

    // 🔧 增强否定语句处理
    const negative_abn_patterns = [
      /no\s+abn/i,
      /don't\s+have\s+abn/i,
      /without\s+abn/i,
      /no\s+abn\s+and\s+gst/i,
      /no\s+abn.*gst/i
    ];
    
    const negative_gst_patterns = [
      /no\s+gst/i,
      /don't\s+have\s+gst/i,
      /not\s+registered\s+for\s+gst/i,
      /no\s+abn\s+and\s+gst/i,
      /no.*gst.*years/i
    ];
    
    for (const pattern of negative_abn_patterns) {
      if (new RegExp(pattern, 'i').test(lowercaseText)) {
        extracted.ABN_years = 0;
        break;
      }
    }
        
    for (const pattern of negative_gst_patterns) {
      if (new RegExp(pattern, 'i').test(lowercaseText)) {
        extracted.GST_years = 0;
        break;
      }
    }

    // 贷款类型
    if (lowercaseText.includes('business') || lowercaseText.includes('commercial') || lowercaseText.includes('company')) {
      extracted.loan_type = 'commercial';
    } else if (lowercaseText.includes('personal') || lowercaseText.includes('consumer')) {
      extracted.loan_type = 'consumer';
    }

    // 资产类型
    if (lowercaseText.includes('car') || lowercaseText.includes('vehicle') || lowercaseText.includes('truck') || lowercaseText.includes('van')) {
      extracted.asset_type = 'motor_vehicle';
    } else if (lowercaseText.includes('equipment') || lowercaseText.includes('machinery')) {
      extracted.asset_type = 'primary';
    }

    // 数值提取
    const abnMatch = text.match(/(\d+)\s*years?\s*(?:abn|ABN)|(?:abn|ABN).*?(\d+)\s*years?/i);
    if (abnMatch && extracted.ABN_years === undefined) {
      const years = parseInt(abnMatch[1] || abnMatch[2]);
      if (years >= 0 && years <= 50) extracted.ABN_years = years;
    }

    const gstMatch = text.match(/(\d+)\s*years?\s*(?:gst|GST)|(?:gst|GST).*?(\d+)\s*years?/i);
    if (gstMatch && extracted.GST_years === undefined) {
      const years = parseInt(gstMatch[1] || gstMatch[2]);
      if (years >= 0 && years <= 50) extracted.GST_years = years;
    }

    const creditMatch = text.match(/credit.*?(\d{3,4})|score.*?(\d{3,4})|(\d{3,4}).*?credit/i);
    if (creditMatch) {
      const score = parseInt(creditMatch[1] || creditMatch[2] || creditMatch[3]);
      if (score >= 300 && score <= 900) extracted.credit_score = score;
    }

    // 车辆品牌识别
    const carBrands = ['toyota', 'holden', 'ford', 'mazda', 'honda', 'subaru', 'mitsubishi', 'nissan', 'hyundai', 'kia', 'volkswagen', 'bmw', 'mercedes', 'audi', 'tesla'];
    for (const brand of carBrands) {
      if (lowercaseText.includes(brand)) {
        extracted.vehicle_make = brand.charAt(0).toUpperCase() + brand.slice(1);
        break;
      }
    }

    // 车辆型号 - 特殊处理Tesla Model Y
    if (lowercaseText.includes('model y') || lowercaseText.includes('tesla model y')) {
      extracted.vehicle_make = 'Tesla';
      extracted.vehicle_model = 'Model Y';
      extracted.vehicle_type = 'passenger_car';
      extracted.asset_type = 'motor_vehicle';
    }

    if (lowercaseText.includes('new car') || lowercaseText.includes('new vehicle')) {
      extracted.vehicle_condition = 'new';
    } else if (lowercaseText.includes('used car') || lowercaseText.includes('used vehicle')) {
      extracted.vehicle_condition = 'used';
    }

    // 贷款金额
    const amountMatch = text.match(/[\$]?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)|(\d+)k|(\d+)\s*thousand/i);
    if (amountMatch) {
      let amount;
      if (amountMatch[2]) { // k format
        amount = parseInt(amountMatch[2]) * 1000;
      } else if (amountMatch[3]) { // thousand format
        amount = parseInt(amountMatch[3]) * 1000;
      } else if (amountMatch[1]) {
        amount = parseFloat(amountMatch[1].replace(/,/g, ''));
      }
      
      if (amount && amount >= 1000 && amount <= 10000000) {
        extracted.desired_loan_amount = amount;
      }
    }

    console.log('🔍 Enhanced extraction result:', extracted);
    return extracted;
  };

  // Extract info from conversation
  const extractInfoFromConversation = useCallback(async () => {
    if (!conversationHistory || conversationHistory.length === 0) return;
    if (!autoExtractEnabled) return;
    if (conversationHistory.length === extractionStatus.lastExtracted) return;

    setExtractionStatus(prev => ({ ...prev, isExtracting: true }));

    try {
      const conversationText = conversationHistory
        .slice(-10) // Only take last 10 messages
        .map(msg => `${msg.role}: ${msg.content}`)
        .join('\n');

      const extracted = extractUsingRules(conversationText);
      
      let newFieldsCount = 0;
      const updatedInfo = { ...customerInfo };

      Object.entries(extracted).forEach(([key, value]) => {
        if (value && !customerInfo[key] && fieldConfig[key]) {
          updatedInfo[key] = value;
          if (!updatedInfo.extracted_fields.includes(key)) {
            updatedInfo.extracted_fields.push(key);
            newFieldsCount++;
          }
        }
      });

      if (newFieldsCount > 0) {
        updatedInfo.last_updated = new Date().toISOString();
        setCustomerInfo(updatedInfo);
        
        if (onFormUpdate) {
          onFormUpdate(updatedInfo);
        }
      }

      setExtractionStatus(prev => ({
        ...prev,
        isExtracting: false,
        lastExtracted: conversationHistory.length,
        newFieldsCount,
        confidence: Math.min(updatedInfo.extracted_fields.length / 10, 1)
      }));

    } catch (error) {
      console.error('Error extracting information:', error);
      setExtractionStatus(prev => ({ ...prev, isExtracting: false }));
    }
  }, [conversationHistory, customerInfo, autoExtractEnabled, onFormUpdate]);

  // Auto-extract when conversation updates
  useEffect(() => {
    if (autoExtractEnabled && conversationHistory) {
      const timeoutId = setTimeout(() => {
        extractInfoFromConversation();
      }, 1500); // Delay 1.5 seconds

      return () => clearTimeout(timeoutId);
    }
  }, [conversationHistory, extractInfoFromConversation, autoExtractEnabled]);

  // 🔧 PDF下载功能
  const downloadInformation = () => {
    // 检查是否有信息可下载
    const hasCustomerInfo = Object.values(customerInfo).some(value => 
      value !== '' && value !== null && value !== undefined && !Array.isArray(value)
    );
    const hasRecommendations = recommendations && recommendations.length > 0;
    
    if (!hasCustomerInfo && !hasRecommendations) {
      alert('No information available to download. Please fill out the form or get product recommendations first.');
      return;
    }

    // 🔧 使用现代浏览器的打印功能生成PDF
    const printWindow = window.open('', '_blank');
    
    // 创建PDF内容
    let content = `
    <!DOCTYPE html>
    <html>
    <head>
        <title>LIFEX Loan Information Summary</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
                line-height: 1.6;
                color: #333;
            }
            .header { 
                text-align: center; 
                border-bottom: 2px solid #333; 
                padding-bottom: 20px; 
                margin-bottom: 30px; 
            }
            .section { 
                margin-bottom: 25px; 
                border: 1px solid #ddd; 
                padding: 15px; 
                border-radius: 5px;
            }
            .section h3 { 
                color: #2563eb; 
                border-bottom: 1px solid #e5e7eb; 
                padding-bottom: 8px; 
                margin-top: 0;
            }
            .info-grid { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 10px; 
                margin-top: 10px;
            }
            .info-item { 
                display: flex; 
                justify-content: space-between; 
                padding: 5px 0; 
                border-bottom: 1px dotted #ccc;
            }
            .label { 
                font-weight: bold; 
                color: #555;
            }
            .recommendation { 
                border: 2px solid #10b981; 
                background-color: #f0fdf4; 
                margin-bottom: 20px;
            }
            .disclaimer { 
                background-color: #fef3c7; 
                border: 1px solid #f59e0b; 
                padding: 15px; 
                border-radius: 5px; 
                font-size: 12px; 
                margin-top: 30px;
            }
            @media print {
                body { margin: 0; padding: 15px; }
                .no-print { display: none; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>LIFEX LOAN INFORMATION SUMMARY</h1>
            <p>Generated: ${new Date().toLocaleString()}</p>
        </div>
    `;

    // 客户信息部分
    if (hasCustomerInfo) {
      content += `<div class="section">
        <h3>Customer Information</h3>`;
      
      const sections = {
        'Basic Details': ['loan_type', 'asset_type', 'property_status'],
        'Financial Information': ['credit_score', 'desired_loan_amount'],
        'Business Information': ['ABN_years', 'GST_years', 'business_structure'],
        'Vehicle Information': ['vehicle_type', 'vehicle_condition', 'vehicle_make', 'vehicle_model', 'vehicle_year'],
        'Preferences': ['interest_rate_ceiling', 'monthly_budget', 'loan_term_preference']
      };

      Object.entries(sections).forEach(([sectionName, fields]) => {
        const sectionData = fields.filter(field => {
          const config = fieldConfig[field];
          const hasValue = customerInfo[field];
          const isVisible = !config?.conditional || config.conditional(customerInfo);
          return hasValue && isVisible;
        });

        if (sectionData.length > 0) {
          content += `<h4>${sectionName}</h4><div class="info-grid">`;
          sectionData.forEach(field => {
            const config = fieldConfig[field];
            const value = customerInfo[field];
            const displayValue = config?.type === 'select' 
              ? config.options?.find(opt => opt.value === value)?.label || value
              : value;
            content += `
              <div class="info-item">
                <span class="label">${config?.label || field}:</span>
                <span>${displayValue}</span>
              </div>`;
          });
          content += `</div>`;
        }
      });

      // 自动提取的字段
      if (customerInfo.extracted_fields.length > 0) {
        content += `
          <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd;">
            <strong>Auto-extracted Fields:</strong> ${customerInfo.extracted_fields.length}<br>
            <strong>Last Updated:</strong> ${customerInfo.last_updated ? new Date(customerInfo.last_updated).toLocaleString() : 'N/A'}
          </div>`;
      }
      
      content += `</div>`;
    }

    // 推荐产品部分
    if (hasRecommendations) {
      content += `<div class="section">
        <h3>Product Recommendations</h3>`;
      
      recommendations.forEach((rec, index) => {
        content += `
          <div class="recommendation">
            <h4>${index + 1}. ${rec.lender_name} - ${rec.product_name}</h4>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Interest Rate:</span>
                <span>${rec.base_rate}% p.a.</span>
              </div>`;
              
        if (rec.comparison_rate) {
          content += `
              <div class="info-item">
                <span class="label">Comparison Rate:</span>
                <span>${rec.comparison_rate}% p.a.</span>
              </div>`;
        }
        
        if (rec.monthly_payment) {
          content += `
              <div class="info-item">
                <span class="label">Monthly Payment:</span>
                <span>${rec.monthly_payment}</span>
              </div>`;
        }
        
        content += `
              <div class="info-item">
                <span class="label">Max Loan Amount:</span>
                <span>${rec.max_loan_amount}</span>
              </div>
              <div class="info-item">
                <span class="label">Loan Terms:</span>
                <span>${rec.loan_term_options}</span>
              </div>
              <div class="info-item">
                <span class="label">Documentation:</span>
                <span>${rec.documentation_type}</span>
              </div>
              <div class="info-item">
                <span class="label">Requirements Met:</span>
                <span>${rec.requirements_met ? 'Yes' : 'Review Required'}</span>
              </div>
            </div>`;

        // 详细要求
        if (rec.detailed_requirements) {
          content += `<h5>Eligibility Requirements:</h5><div class="info-grid">`;
          Object.entries(rec.detailed_requirements).forEach(([key, value]) => {
            content += `
              <div class="info-item">
                <span class="label">${key.replace(/_/g, ' ')}:</span>
                <span>${value}</span>
              </div>`;
          });
          content += `</div>`;
        }

        // 费用
        if (rec.fees_breakdown) {
          content += `<h5>Fees:</h5><div class="info-grid">`;
          Object.entries(rec.fees_breakdown).forEach(([key, value]) => {
            content += `
              <div class="info-item">
                <span class="label">${key.replace(/_/g, ' ')}:</span>
                <span>${value}</span>
              </div>`;
          });
          content += `</div>`;
        }

        content += `</div>`;
      });
      
      content += `</div>`;
    }

    // 免责声明
    content += `
        <div class="disclaimer">
            <h4>DISCLAIMER:</h4>
            <p>This summary is for informational purposes only. Interest rates, terms, and conditions are subject to change and final approval by the lender. All calculations are estimates and actual payments may vary. Please consult with a financial advisor for personalized advice.</p>
            <p><strong>Generated by LIFEX Loan Agent System</strong></p>
        </div>
        
        <div class="no-print" style="text-align: center; margin-top: 30px;">
            <button onclick="window.print()" style="background: #2563eb; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">
                Generate PDF
            </button>
            <button onclick="window.close()" style="background: #6b7280; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-left: 10px;">
                Close
            </button>
        </div>
    </body>
    </html>`;

    printWindow.document.write(content);
    printWindow.document.close();

    // 🔧 自动触发打印对话框
    setTimeout(() => {
      printWindow.focus();
      printWindow.print();
    }, 500);
  };

  // Clear form
  const clearForm = () => {
    const clearedInfo = {
      loan_type: '',
      asset_type: '',
      property_status: '',
      ABN_years: '',
      GST_years: '',
      credit_score: '',
      desired_loan_amount: '',
      vehicle_type: '',
      vehicle_condition: '',
      vehicle_make: '',
      vehicle_model: '',
      vehicle_year: '',
      business_structure: '',
      interest_rate_ceiling: '',
      monthly_budget: '',
      loan_term_preference: '',
      extracted_fields: [],
      last_updated: null
    };
    
    setCustomerInfo(clearedInfo);
    setExtractionStatus({
      isExtracting: false,
      lastExtracted: 0,
      confidence: 0,
      newFieldsCount: 0
    });
    
    if (onFormUpdate) {
      onFormUpdate(clearedInfo);
    }
  };

  // Handle field changes
  const handleFieldChange = (fieldName, value) => {
    const updatedInfo = { ...customerInfo, [fieldName]: value };
    setCustomerInfo(updatedInfo);
    
    if (onFormUpdate) {
      onFormUpdate(updatedInfo);
    }
  };

  // Render field
  const renderField = (fieldName, config) => {
    // Check conditional rendering
    if (config.conditional && !config.conditional(customerInfo)) {
      return null;
    }

    const isExtracted = customerInfo.extracted_fields.includes(fieldName);
    const value = customerInfo[fieldName] || '';

    return (
      <div key={fieldName} className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {config.label}
          {isExtracted && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 ml-2">
              Auto-filled
            </span>
          )}
        </label>
        
        {config.type === 'select' ? (
          <select
            value={value}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isExtracted ? 'bg-green-50 border-green-300' : 'border-gray-300'
            }`}
          >
            <option value="">Select...</option>
            {config.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            type={config.type}
            value={value}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            min={config.min}
            max={config.max}
            step={config.step}
            className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              isExtracted ? 'bg-green-50 border-green-300' : 'border-gray-300'
            }`}
            placeholder={`Enter ${config.label}`}
          />
        )}
      </div>
    );
  };

  // Group fields by section
  const fieldsBySection = {
    core: ['loan_type', 'asset_type', 'property_status'],
    financial: ['credit_score', 'desired_loan_amount'],
    business: ['ABN_years', 'GST_years', 'business_structure'],
    vehicle: ['vehicle_type', 'vehicle_condition', 'vehicle_make', 'vehicle_model', 'vehicle_year'],
    preferences: ['interest_rate_ceiling', 'monthly_budget', 'loan_term_preference']
  };

  const sectionTitles = {
    core: 'Core Information',
    financial: 'Financial Information',
    business: 'Business Information',
    vehicle: 'Vehicle Information',
    preferences: 'Preferences'
  };

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b" style={{ backgroundColor: '#fef7e8' }}>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Customer Information</h2>
        
        {/* Controls */}
        <div className="flex items-center justify-between mb-4">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={autoExtractEnabled}
              onChange={(e) => setAutoExtractEnabled(e.target.checked)}
              className="mr-2"
            />
            <span className="text-sm text-gray-700">Auto-extract from conversation</span>
          </label>
          
          <div className="flex space-x-2">
            <button
              onClick={() => extractInfoFromConversation()}
              disabled={extractionStatus.isExtracting || !conversationHistory?.length}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {extractionStatus.isExtracting ? 'Extracting...' : 'Re-extract'}
            </button>
            <button
              onClick={clearForm}
              className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
            >
              Clear
            </button>
            <button
              onClick={downloadInformation}
              disabled={!Object.values(customerInfo).some(value => 
                value !== '' && value !== null && value !== undefined && !Array.isArray(value)
              ) && (!recommendations || recommendations.length === 0)}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              title={
                (!Object.values(customerInfo).some(value => 
                  value !== '' && value !== null && value !== undefined && !Array.isArray(value)
                ) && (!recommendations || recommendations.length === 0))
                ? 'No information available to download'
                : 'Download PDF Summary'
              }
            >
              Download PDF
            </button>
          </div>
        </div>

        {/* Status */}
        {extractionStatus.isExtracting && (
          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-blue-700 text-sm">Extracting information from conversation...</span>
            </div>
          </div>
        )}

        {extractionStatus.newFieldsCount > 0 && !extractionStatus.isExtracting && (
          <div className="bg-green-50 border border-green-200 rounded p-3 mb-4">
            <div className="text-green-700 text-sm">
              ✅ Extracted {extractionStatus.newFieldsCount} new fields! 
              Total: {customerInfo.extracted_fields.length} fields auto-filled
            </div>
          </div>
        )}

        {/* Progress */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm text-gray-600">Form Completion</span>
            <span className="text-sm text-gray-600">
              {Math.round(extractionStatus.confidence * 100)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${extractionStatus.confidence * 100}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {Object.entries(fieldsBySection).map(([sectionKey, fields]) => {
          const visibleFields = fields.filter(fieldName => {
            const config = fieldConfig[fieldName];
            return !config.conditional || config.conditional(customerInfo);
          });

          if (visibleFields.length === 0) return null;

          return (
            <div key={sectionKey} className="mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 pb-2 border-b">
                {sectionTitles[sectionKey]}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleFields.map(fieldName => 
                  renderField(fieldName, fieldConfig[fieldName])
                )}
              </div>
            </div>
          );
        })}

        {/* Summary */}
        {customerInfo.extracted_fields.length > 0 && (
          <div className="mt-8 p-4 bg-gray-50 rounded">
            <h4 className="font-medium text-gray-900 mb-2">Auto-extracted Fields:</h4>
            <div className="flex flex-wrap gap-2">
              {customerInfo.extracted_fields.map(field => (
                <span 
                  key={field}
                  className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded"
                >
                  {fieldConfig[field]?.label || field}
                </span>
              ))}
            </div>
            {customerInfo.last_updated && (
              <p className="text-xs text-gray-500 mt-2">
                Last updated: {new Date(customerInfo.last_updated).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DynamicCustomerForm;