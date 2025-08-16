// 🔧 整合版 DynamicCustomerForm.jsx - 结合您的提取修复 + 我的新功能
import React, { useState, useEffect, useCallback } from 'react';
import { Download, Upload, RefreshCw, AlertCircle, CheckCircle, Info } from 'lucide-react';

const DynamicCustomerForm = ({ conversationHistory, onFormUpdate, initialData, recommendations = [], onCustomerInfoChange }) => {
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
    business_structure: '', // 🔧 新增：业务结构字段
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
  const [validationErrors, setValidationErrors] = useState({});
  const [previousAmount, setPreviousAmount] = useState(null);

  // 🔧 新增：增强的字段配置，包含business_structure优先级
  const fieldConfig = {
    loan_type: {
      label: 'Loan Type',
      type: 'select',
      required: true,
      priority: 1,
      options: [
        { value: '', label: 'Please select...' },
        { value: 'business', label: 'Business Loan' },
        { value: 'consumer', label: 'Consumer Loan' }
      ],
      section: 'core',
      validation: (value) => {
        if (!value || value === '') return 'Please select a loan type';
        return null;
      }
    },
    asset_type: {
      label: 'Asset Type',
      type: 'select',
      required: true,
      priority: 2,
      options: [
        { value: '', label: 'Please select...' },
        { value: 'motor_vehicle', label: 'Motor Vehicle' },
        { value: 'primary', label: 'Primary Equipment' },
        { value: 'secondary', label: 'Secondary Equipment' },
        { value: 'tertiary', label: 'Tertiary Equipment' }
      ],
      section: 'core',
      validation: (value) => {
        if (!value || value === '') return 'Please select an asset type';
        return null;
      }
    },
    // 🔧 新增：business_structure作为高优先级字段
    business_structure: {
      label: 'Business Structure',
      type: 'select',
      required: true,
      priority: 3, // 高优先级，早期收集
      options: [
        { value: '', label: 'Please select...' },
        { value: 'sole_trader', label: 'Sole Trader' },
        { value: 'company', label: 'Company (Pty Ltd)' },
        { value: 'partnership', label: 'Partnership' },
        { value: 'trust', label: 'Trust' }
      ],
      section: 'core',
      conditional: (profile) => {
        // 对于商业贷款或车辆融资，总是显示
        return profile.loan_type === 'business' || profile.asset_type === 'motor_vehicle';
      },
      validation: (value) => {
        if (!value || value === '') {
          return 'Please select your business structure';
        }
        return null;
      },
      helpText: 'Your business legal structure affects loan eligibility and requirements'
    },
    property_status: {
      label: 'Property Ownership',
      type: 'select',
      required: true,
      priority: 4,
      options: [
        { value: '', label: 'Please select...' },
        { value: 'property_owner', label: 'Property Owner' },
        { value: 'non_property_owner', label: 'Non-Property Owner' }
      ],
      section: 'core',
      validation: (value) => {
        if (!value || value === '') return 'Please select your property status';
        return null;
      }
    },
    ABN_years: {
      label: 'ABN Registration Years',
      type: 'number',
      required: true,
      priority: 5,
      min: 0,
      max: 50,
      section: 'business',
      placeholder: 'e.g., 5',
      validation: (value) => {
        if (value === null || value === undefined || value === '') return 'Please enter ABN registration years';
        if (value < 0 || value > 50) return 'ABN years must be between 0 and 50';
        return null;
      }
    },
    GST_years: {
      label: 'GST Registration Years',
      type: 'number',
      required: true,
      priority: 6,
      min: 0,
      max: 50,
      section: 'business',
      placeholder: 'e.g., 3',
      validation: (value) => {
        if (value === null || value === undefined || value === '') return 'Please enter GST registration years';
        if (value < 0 || value > 50) return 'GST years must be between 0 and 50';
        return null;
      }
    },
    credit_score: {
      label: 'Credit Score',
      type: 'number',
      required: false,
      priority: 7,
      min: 300,
      max: 900,
      section: 'financial',
      placeholder: 'e.g., 750',
      validation: (value) => {
        if (value !== null && value !== undefined && value !== '') {
          if (value < 300 || value > 900) return 'Credit score must be between 300 and 900';
        }
        return null;
      }
    },
    // 🔧 新增：增强的贷款金额字段，支持实时更新
    desired_loan_amount: {
      label: 'Desired Loan Amount',
      type: 'currency',
      required: false,
      priority: 8,
      min: 1000,
      section: 'financial',
      placeholder: 'e.g., 100,000',
      validation: (value, profile) => {
        if (value !== null && value !== undefined && value !== '') {
          if (value <= 0) return 'Please enter a valid loan amount';
          
          // 动态验证基于资产类型
          if (profile?.asset_type === 'motor_vehicle' && value > 1000000) {
            return 'Vehicle loans typically have lower maximums. Consider contacting us for amounts over $1M';
          }
        }
        return null;
      },
      onChange: (value, onUpdate) => {
        // 🔧 新增：当金额变化显著时触发重新匹配
        if (previousAmount && Math.abs(value - previousAmount) > 50000) {
          console.log(`💰 Significant loan amount change: ${previousAmount} → ${value}`);
          if (onUpdate) onUpdate('loan_amount_changed', value);
        }
        setPreviousAmount(value);
      },
      formatDisplay: (value) => {
        return value ? `$${value.toLocaleString()}` : '';
      }
    },
    // Vehicle-specific fields
    vehicle_type: {
      label: 'Vehicle Type',
      type: 'select',
      required: false,
      priority: 9,
      options: [
        { value: '', label: 'Please select...' },
        { value: 'passenger_car', label: 'Passenger Car' },
        { value: 'light_truck', label: 'Light Truck' },
        { value: 'van_ute', label: 'Van/Ute' },
        { value: 'motorcycle', label: 'Motorcycle' },
        { value: 'heavy_vehicle', label: 'Heavy Vehicle' }
      ],
      section: 'vehicle',
      conditional: (profile) => profile.asset_type === 'motor_vehicle'
    },
    vehicle_condition: {
      label: 'Vehicle Condition',
      type: 'select',
      required: false,
      priority: 10,
      options: [
        { value: '', label: 'Please select...' },
        { value: 'new', label: 'New' },
        { value: 'demonstrator', label: 'Demonstrator' },
        { value: 'used', label: 'Used' }
      ],
      section: 'vehicle',
      conditional: (profile) => profile.asset_type === 'motor_vehicle'
    },
    vehicle_make: {
      label: 'Vehicle Make',
      type: 'text',
      required: false,
      priority: 11,
      placeholder: 'e.g., Toyota',
      section: 'vehicle',
      conditional: (profile) => profile.asset_type === 'motor_vehicle'
    },
    vehicle_model: {
      label: 'Vehicle Model',
      type: 'text',
      required: false,
      priority: 12,
      placeholder: 'e.g., Camry',
      section: 'vehicle',
      conditional: (profile) => profile.asset_type === 'motor_vehicle'
    },
    vehicle_year: {
      label: 'Vehicle Year',
      type: 'number',
      required: false,
      priority: 13,
      placeholder: 'e.g., 2023',
      min: 1990,
      max: new Date().getFullYear() + 2,
      section: 'vehicle',
      conditional: (profile) => profile.asset_type === 'motor_vehicle'
    },
    // Preference fields
    interest_rate_ceiling: {
      label: 'Maximum Acceptable Interest Rate (%)',
      type: 'number',
      required: false,
      priority: 14,
      placeholder: 'e.g., 8.5',
      min: 0,
      max: 30,
      step: 0.1,
      section: 'preferences'
    },
    monthly_budget: {
      label: 'Maximum Monthly Payment',
      type: 'currency',
      required: false,
      priority: 15,
      placeholder: 'e.g., 2,000',
      section: 'preferences'
    },
    loan_term_preference: {
      label: 'Preferred Loan Term (months)',
      type: 'number',
      required: false,
      priority: 16,
      placeholder: 'e.g., 60',
      min: 12,
      max: 84,
      section: 'preferences'
    }
  };

  // 🔧 修复 + 新增：增强的数据提取方法，包含business_structure
  const extractUsingRulesFixed = (text) => {
    console.log('🔍 Starting enhanced extraction with text:', text.substring(0, 200) + '...');
    
    const lowercaseText = text.toLowerCase();
    const originalText = text;
    const extracted = {};

    // 🔧 新增：业务结构提取模式
    const extractBusinessStructure = (text) => {
      const businessStructurePatterns = {
        sole_trader: [
          /\bsole\s*trader\b/gi,
          /\bindividual\s*trader\b/gi,
          /\bself\s*employed\b/gi,
          /\boperating\s*as\s*an\s*individual\b/gi,
          /\btrading\s*individually\b/gi,
          /\bpersonal\s*trading\b/gi
        ],
        company: [
          /\bcompany\b/gi,
          /\bpty\s*ltd\b/gi,
          /\bcorporation\b/gi,
          /\bincorporated\b/gi,
          /\bltd\b/gi,
          /\bcorporate\s*entity\b/gi,
          /\blimited\s*company\b/gi
        ],
        partnership: [
          /\bpartnership\b/gi,
          /\bpartners\b/gi,
          /\bjoint\s*venture\b/gi,
          /\bbusiness\s*partnership\b/gi,
          /\btrading\s*partnership\b/gi
        ],
        trust: [
          /\btrust\b/gi,
          /\bfamily\s*trust\b/gi,
          /\bdiscretionary\s*trust\b/gi,
          /\bunit\s*trust\b/gi,
          /\btrustee\b/gi,
          /\btrading\s*trust\b/gi
        ]
      };

      for (const [structure, patterns] of Object.entries(businessStructurePatterns)) {
        for (const pattern of patterns) {
          if (pattern.test(text)) {
            console.log('🏢 Business structure detected:', structure, 'from pattern:', pattern.source);
            return structure;
          }
        }
      }
      return null;
    };

    // 🔧 保留您的修复：房产状态识别 - 优先级处理
    const extractPropertyStatus = (text) => {
      const lowerText = text.toLowerCase();
      
      // 优先检查明确的ownership关键词
      const strongOwnerPatterns = [
        /\bproperty_owner\b/,
        /\bown\s+property\b/,
        /\bproperty\s+owner\b/,
        /\bhave\s+property\b/,
        /\bown\s+a\s+house\b/,
        /\bown\s+a\s+home\b/,
        /\bhomeowner\b/,
        /\bown\s+real\s+estate\b/
      ];
      
      // 然后检查否定关键词
      const strongNonOwnerPatterns = [
        /\bnon.?property.?owner\b/,
        /\bno\s+property\b/,
        /\bdon'?t\s+own\b/,
        /\brenting\b/,
        /\btenant\b/,
        /\bwithout\s+property\b/
      ];
      
      // 检查强确认模式
      for (const pattern of strongOwnerPatterns) {
        if (pattern.test(lowerText)) {
          console.log('🏠 Property owner pattern matched:', pattern.source);
          return 'property_owner';
        }
      }
      
      for (const pattern of strongNonOwnerPatterns) {
        if (pattern.test(lowerText)) {
          console.log('🏠 Non-property owner pattern matched:', pattern.source);
          return 'non_property_owner';
        }
      }
      
      return null;
    };

    // 🔧 保留您的修复：Credit Score提取 - 多模式匹配
    const extractCreditScore = (text) => {
      const patterns = [
        // 标准格式："credit score 750", "score 750", "750 credit score"
        /\bcredit\s*score\s*(?:is\s*)?(?:of\s*)?(\d{3,4})\b/i,
        /\bscore\s*(?:is\s*)?(?:of\s*)?(\d{3,4})\b/i,
        /\b(\d{3,4})\s*credit\s*score\b/i,
        
        // 简化格式："my score is 750", "I have 750"
        /\bmy\s*(?:credit\s*)?score\s*(?:is\s*)?(\d{3,4})\b/i,
        /\bi\s*have\s*(?:a\s*)?(?:credit\s*)?score\s*(?:of\s*)?(\d{3,4})\b/i,
        
        // 数字在前："750 is my score", "750 credit"
        /\b(\d{3,4})\s*(?:is\s*)?(?:my\s*)?(?:credit\s*)?score\b/i,
        /\b(\d{3,4})\s*credit\b/i,
        
        // 特殊格式："credit: 750", "score: 750"
        /\bcredit\s*:?\s*(\d{3,4})\b/i,
        /\bscore\s*:?\s*(\d{3,4})\b/i,
        
        // 范围格式："score around 750", "approximately 750"
        /\bscore\s*(?:is\s*)?(?:around|approximately|about)\s*(\d{3,4})\b/i,
        /\b(?:around|approximately|about)\s*(\d{3,4})\s*(?:credit\s*)?score\b/i
      ];
      
      for (const pattern of patterns) {
        const match = text.match(pattern);
        if (match) {
          const score = parseInt(match[1]);
          if (score >= 300 && score <= 900) {
            console.log('💳 Credit score extracted:', score, 'using pattern:', pattern.source);
            return score;
          }
        }
      }
      
      return null;
    };

    // 🔧 保留您的修复：Desired Loan Amount提取 - 增强金额识别
    const extractLoanAmount = (text) => {
      const patterns = [
        // 标准货币格式："$50,000", "$50000", "50,000 dollars"
        /\$\s*([\d,]+(?:\.\d{2})?)\b/g,
        
        // K格式："50k", "50K", "50 k"
        /\b(\d+)\s*k\b/gi,
        
        // 千格式："50 thousand", "fifty thousand"
        /\b(\d+)\s*thousand\b/gi,
        
        // 万格式（澳洲常用）
        /\b(\d+(?:\.\d+)?)\s*(?:million|mil)\b/gi,
        
        // 贷款上下文："loan amount 50000", "need 50000", "looking for 50000"
        /\b(?:loan\s*amount|need|looking\s*for|want|require)\s*(?:is\s*)?(?:of\s*)?(?:\$\s*)?([\d,]+)\b/gi,
        /\b(?:\$\s*)?([\d,]+)\s*(?:loan|dollars?|bucks)\b/gi,
        
        // 数字后跟"for loan"、"to borrow"
        /\b([\d,]+)\s*(?:for\s*(?:the\s*)?loan|to\s*borrow)\b/gi,
        
        // 范围格式："around 50000", "about 50k"
        /\b(?:around|about|approximately)\s*(?:\$\s*)?([\d,]+|(\d+)\s*k)\b/gi
      ];
      
      let amounts = [];
      
      for (const pattern of patterns) {
        let match;
        while ((match = pattern.exec(text)) !== null) {
          let amount = 0;
          
          if (match[0].toLowerCase().includes('k')) {
            // K格式处理
            amount = parseInt(match[1] || match[2]) * 1000;
          } else if (match[0].toLowerCase().includes('million') || match[0].toLowerCase().includes('mil')) {
            // 百万格式处理
            amount = parseFloat(match[1]) * 1000000;
          } else {
            // 标准数字格式
            const numStr = match[1] || match[2];
            if (numStr) {
              amount = parseFloat(numStr.replace(/,/g, ''));
            }
          }
          
          // 验证金额范围（$1K - $10M）
          if (amount >= 1000 && amount <= 10000000) {
            amounts.push({
              amount: amount,
              pattern: pattern.source,
              match: match[0]
            });
            console.log('💰 Loan amount candidate:', amount, 'from:', match[0]);
          }
        }
        // 重置regex
        pattern.lastIndex = 0;
      }
      
      // 如果找到多个金额，选择最可能的一个
      if (amounts.length > 0) {
        // 优先选择有明确贷款上下文的金额
        const contextualAmounts = amounts.filter(a => 
          a.pattern.includes('loan|need|looking|want|require') || 
          a.match.toLowerCase().includes('loan') ||
          a.match.toLowerCase().includes('borrow')
        );
        
        if (contextualAmounts.length > 0) {
          const selected = contextualAmounts[0];
          console.log('💰 Selected contextual loan amount:', selected.amount);
          return selected.amount;
        }
        
        // 否则选择第一个合理的金额
        const selected = amounts[0];
        console.log('💰 Selected loan amount:', selected.amount);
        return selected.amount;
      }
      
      return null;
    };

    // 🔧 保留您的修复：ABN/GST年数提取 - 改进数字识别
    const extractABNGSTYears = (text) => {
      const result = { ABN_years: null, GST_years: null };
      
      // 否定语句检查
      const negativePatterns = {
        ABN: [
          /\bno\s+abn\b/i,
          /\bdon'?t\s+have\s+(?:an\s+)?abn\b/i,
          /\bwithout\s+(?:an\s+)?abn\b/i,
          /\bnot\s+registered\s+for\s+abn\b/i
        ],
        GST: [
          /\bno\s+gst\b/i,
          /\bdon'?t\s+have\s+gst\b/i,
          /\bnot\s+registered\s+for\s+gst\b/i,
          /\bwithout\s+gst\b/i
        ]
      };
      
      // 检查否定语句
      for (const pattern of negativePatterns.ABN) {
        if (pattern.test(text)) {
          result.ABN_years = 0;
          console.log('📋 ABN negative pattern matched: 0 years');
          break;
        }
      }
      
      for (const pattern of negativePatterns.GST) {
        if (pattern.test(text)) {
          result.GST_years = 0;
          console.log('📋 GST negative pattern matched: 0 years');
          break;
        }
      }
      
      // 数字提取模式（如果没有否定语句）
      if (result.ABN_years === null) {
        const abnPatterns = [
          /\b(\d+)\s*years?\s*(?:of\s*)?abn\b/i,
          /\babn\s*(?:for\s*)?(\d+)\s*years?\b/i,
          /\bhave\s*(?:had\s*)?(?:an\s*)?abn\s*(?:for\s*)?(\d+)\s*years?\b/i,
          /\b(\d+)\s*year\s*abn\b/i
        ];
        
        for (const pattern of abnPatterns) {
          const match = text.match(pattern);
          if (match) {
            const years = parseInt(match[1]);
            if (years >= 0 && years <= 50) {
              result.ABN_years = years;
              console.log('📋 ABN years extracted:', years);
              break;
            }
          }
        }
      }
      
      if (result.GST_years === null) {
        const gstPatterns = [
          /\b(\d+)\s*years?\s*(?:of\s*)?gst\b/i,
          /\bgst\s*(?:for\s*)?(\d+)\s*years?\b/i,
          /\bhave\s*(?:had\s*)?gst\s*(?:for\s*)?(\d+)\s*years?\b/i,
          /\b(\d+)\s*year\s*gst\b/i
        ];
        
        for (const pattern of gstPatterns) {
          const match = text.match(pattern);
          if (match) {
            const years = parseInt(match[1]);
            if (years >= 0 && years <= 50) {
              result.GST_years = years;
              console.log('📋 GST years extracted:', years);
              break;
            }
          }
        }
      }
      
      return result;
    };

    // 执行所有提取
    
    // 🔧 新增：业务结构提取
    const businessStructure = extractBusinessStructure(originalText);
    if (businessStructure) {
      extracted.business_structure = businessStructure;
    }

    const propertyStatus = extractPropertyStatus(originalText);
    if (propertyStatus) {
      extracted.property_status = propertyStatus;
    }

    const creditScore = extractCreditScore(originalText);
    if (creditScore) {
      extracted.credit_score = creditScore;
    }

    const loanAmount = extractLoanAmount(originalText);
    if (loanAmount) {
      extracted.desired_loan_amount = loanAmount;
    }

    const abnGstYears = extractABNGSTYears(originalText);
    if (abnGstYears.ABN_years !== null) {
      extracted.ABN_years = abnGstYears.ABN_years;
    }
    if (abnGstYears.GST_years !== null) {
      extracted.GST_years = abnGstYears.GST_years;
    }

    // 贷款类型检测
    if (lowercaseText.includes('business') || lowercaseText.includes('commercial') || lowercaseText.includes('company')) {
      extracted.loan_type = 'business';
    } else if (lowercaseText.includes('personal') || lowercaseText.includes('consumer')) {
      extracted.loan_type = 'consumer';
    }

    // 资产类型检测
    if (lowercaseText.includes('car') || lowercaseText.includes('vehicle') || lowercaseText.includes('truck') || lowercaseText.includes('van')) {
      extracted.asset_type = 'motor_vehicle';
    } else if (lowercaseText.includes('equipment') || lowercaseText.includes('machinery')) {
      extracted.asset_type = 'primary';
    }

    // 车辆相关信息提取
    const carBrands = ['toyota', 'holden', 'ford', 'mazda', 'honda', 'subaru', 'mitsubishi', 'nissan', 'hyundai', 'kia', 'volkswagen', 'bmw', 'mercedes', 'audi', 'tesla'];
    for (const brand of carBrands) {
      if (lowercaseText.includes(brand)) {
        extracted.vehicle_make = brand.charAt(0).toUpperCase() + brand.slice(1);
        break;
      }
    }

    // 特殊处理Tesla Model Y
    if (lowercaseText.includes('model y') || lowercaseText.includes('tesla model y')) {
      extracted.vehicle_make = 'Tesla';
      extracted.vehicle_model = 'Model Y';
      extracted.vehicle_type = 'passenger_car';
      extracted.asset_type = 'motor_vehicle';
    }

    // 车辆状态
    if (lowercaseText.includes('new car') || lowercaseText.includes('new vehicle')) {
      extracted.vehicle_condition = 'new';
    } else if (lowercaseText.includes('used car') || lowercaseText.includes('used vehicle')) {
      extracted.vehicle_condition = 'used';
    }

    console.log('🔍 Enhanced extraction completed:', extracted);
    return extracted;
  };

  // 🔧 新增：会话重置检测
  const detectSessionReset = useCallback((newMessage) => {
    const resetPatterns = [
      /new\s*(loan|application)/i,
      /different\s*(loan|finance)/i,
      /start\s*over/i,
      /fresh\s*start/i,
      /another\s*(loan|quote)/i,
      /completely\s*different/i
    ];
    
    return resetPatterns.some(pattern => pattern.test(newMessage));
  }, []);

  // 🔧 新增：验证函数
  const validateField = useCallback((fieldName, value, currentProfile) => {
    const config = fieldConfig[fieldName];
    if (!config) return null;
    
    if (config.validation) {
      return config.validation(value, currentProfile);
    }
    
    if (config.required && (!value || value === '')) {
      return `${config.label} is required`;
    }
    
    return null;
  }, []);

  // Extract info from conversation - 修复版本
  const extractInfoFromConversation = useCallback(async () => {
    if (!conversationHistory || conversationHistory.length === 0) return;
    if (!autoExtractEnabled) return;
    if (conversationHistory.length === extractionStatus.lastExtracted) return;

    setExtractionStatus(prev => ({ ...prev, isExtracting: true }));

    try {
      const conversationText = conversationHistory
        .slice(-10) // 只取最近10条消息
        .map(msg => {
          if (typeof msg === 'string') return msg;
          return msg.content || msg.text || '';
        })
        .filter(text => text.trim().length > 0)
        .join(' ');

      console.log('🔍 Extracting from conversation text:', conversationText.substring(0, 300) + '...');

      if (conversationText.trim().length === 0) {
        console.log('⚠️ No valid conversation text found');
        return;
      }

      // 🔧 新增：检测会话重置
      const latestMessage = conversationHistory[conversationHistory.length - 1];
      if (latestMessage && detectSessionReset(latestMessage.content || latestMessage)) {
        console.log('🔄 Session reset detected - clearing form');
        setCustomerInfo({
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
          last_updated: new Date().toISOString()
        });
        return;
      }

      // 使用修复后的提取方法
      const extractedData = extractUsingRulesFixed(conversationText);
      
      if (Object.keys(extractedData).length === 0) {
        console.log('ℹ️ No data extracted from conversation');
        setExtractionStatus(prev => ({ 
          ...prev, 
          isExtracting: false,
          lastExtracted: conversationHistory.length 
        }));
        return;
      }

      console.log('✅ Extracted data:', extractedData);

      // 更新状态
      setCustomerInfo(prev => {
        const updated = { ...prev };
        let hasChanges = false;
        const newFields = [];

        Object.entries(extractedData).forEach(([key, value]) => {
          if (value !== null && value !== undefined && value !== '') {
            const currentValue = prev[key];
            
            // 只更新空字段或有明显改变的字段
            if (!currentValue || currentValue === '' || currentValue !== value) {
              updated[key] = value;
              hasChanges = true;
              newFields.push(key);
              console.log(`🔄 Updated ${key}: ${currentValue} → ${value}`);
            }
          }
        });

        if (hasChanges) {
          updated.extracted_fields = [...(prev.extracted_fields || []), ...newFields];
          updated.last_updated = new Date().toISOString();
          
          // 通知父组件
          if (onFormUpdate) {
            onFormUpdate(updated);
          }
          if (onCustomerInfoChange) {
            onCustomerInfoChange(updated);
          }
        }

        return updated;
      });

      setExtractionStatus(prev => ({
        ...prev,
        isExtracting: false,
        lastExtracted: conversationHistory.length,
        newFieldsCount: Object.keys(extractedData).length,
        confidence: 0.8 // 固定置信度，可以后续改进
      }));

    } catch (error) {
      console.error('❌ Extraction error:', error);
      setExtractionStatus(prev => ({
        ...prev,
        isExtracting: false,
        lastExtracted: conversationHistory.length
      }));
    }
  }, [conversationHistory, onFormUpdate, onCustomerInfoChange, autoExtractEnabled, extractionStatus.lastExtracted, detectSessionReset]);

  // Watch for conversation changes
  useEffect(() => {
    if (conversationHistory && conversationHistory.length > 0) {
      const timeoutId = setTimeout(() => {
        extractInfoFromConversation();
      }, 1000); // 1秒延迟防抖

      return () => clearTimeout(timeoutId);
    }
  }, [conversationHistory, extractInfoFromConversation]);

  // Load initial data
  useEffect(() => {
    if (initialData && Object.keys(initialData).length > 0) {
      console.log('📥 Loading initial data:', initialData);
      setCustomerInfo(prev => ({
        ...prev,
        ...initialData
      }));
    }
  }, [initialData]);

  // Handle manual field updates
  const handleFieldChange = useCallback((fieldName, value) => {
    console.log(`🔄 Manual field update: ${fieldName} = ${value}`);
    
    const config = fieldConfig[fieldName];
    
    // 类型转换
    let processedValue = value;
    if (config.type === 'number' && value !== '' && value !== null) {
      processedValue = parseFloat(value) || null;
    } else if (config.type === 'currency' && value !== '' && value !== null) {
      processedValue = parseFloat(value.toString().replace(/[,$]/g, '')) || null;
    }
    
    // 验证
    const error = validateField(fieldName, processedValue, customerInfo);
    setValidationErrors(prev => ({
      ...prev,
      [fieldName]: error
    }));
    
    setCustomerInfo(prev => {
      const updated = {
        ...prev,
        [fieldName]: processedValue,
        last_updated: new Date().toISOString()
      };
      
      // 通知父组件
      if (onFormUpdate) {
        onFormUpdate(updated);
      }
      if (onCustomerInfoChange) {
        onCustomerInfoChange(updated);
      }
      
      return updated;
    });
    
    // 🔧 新增：处理特殊字段的onChange回调
    if (config.onChange) {
      config.onChange(processedValue, (eventType, data) => {
        if (eventType === 'loan_amount_changed') {
          console.log(`📊 Loan amount change detected: ${data}`);
          // 这里可以触发重新匹配逻辑
        }
      });
    }
  }, [customerInfo, onFormUpdate, onCustomerInfoChange, validateField]);

  // 🔧 新增：获取可见字段
  const getVisibleFields = useCallback(() => {
    return Object.keys(fieldConfig)
      .filter(fieldName => {
        const config = fieldConfig[fieldName];
        if (config.conditional) {
          return config.conditional(customerInfo);
        }
        return true;
      })
      .sort((a, b) => {
        const priorityA = fieldConfig[a].priority || 99;
        const priorityB = fieldConfig[b].priority || 99;
        return priorityA - priorityB;
      });
  }, [customerInfo]);

  // 🔧 新增：导出PDF功能
  const exportToPDF = useCallback(() => {
    const visibleFields = getVisibleFields();
    const hasCustomerInfo = visibleFields.some(field => customerInfo[field]);
    
    if (!hasCustomerInfo && (!recommendations || recommendations.length === 0)) {
      alert("No information available to export");
      return;
    }

    // 生成HTML内容
    let content = `
      <!DOCTYPE html>
      <html>
      <head>
          <title>LIFEX Loan Information Summary</title>
          <style>
              body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; }
              .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; }
              .header h1 { color: #3b82f6; margin: 0; font-size: 24px; }
              .section { margin-bottom: 25px; }
              .section h3 { color: #1f2937; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin-bottom: 15px; }
              .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
              .info-item { display: flex; justify-content: space-between; padding: 8px 12px; background: #f9fafb; border-radius: 6px; }
              .label { font-weight: 600; color: #374151; }
              .value { color: #1f2937; }
              .recommendation { background: #f0f9ff; border: 1px solid #bae6fd; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
              .recommendation h4 { margin: 0 0 10px 0; color: #0369a1; }
              .rate-info { font-size: 18px; font-weight: bold; color: #059669; }
              @media print {
                  body { margin: 0; }
                  .no-print { display: none !important; }
                  .page-break { page-break-before: always; }
              }
          </style>
      </head>
      <body>
          <div class="header">
              <h1>🏦 LIFEX LOAN INFORMATION SUMMARY</h1>
              <p><strong>Generated:</strong> ${new Date().toLocaleDateString('en-AU', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}</p>
          </div>
    `;

    // 客户信息部分
    if (hasCustomerInfo) {
      content += `<div class="section">
        <h3>📋 Customer Information</h3>`;
      
      const sections = {
        'Basic Details': ['loan_type', 'asset_type', 'business_structure', 'property_status'],
        'Financial Information': ['credit_score', 'desired_loan_amount'],
        'Business Information': ['ABN_years', 'GST_years'],
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
              : typeof value === 'number' ? value.toLocaleString() : value;
            content += `
              <div class="info-item">
                <span class="label">${config?.label || field}:</span>
                <span class="value">${displayValue}</span>
              </div>`;
          });
          content += `</div>`;
        }
      });

      // 自动提取的字段
      if (customerInfo.extracted_fields && customerInfo.extracted_fields.length > 0) {
        content += `
          <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 10px;">
            <strong>📊 Auto-extracted Fields:</strong> ${customerInfo.extracted_fields.length}<br>
            <strong>📅 Last Updated:</strong> ${customerInfo.last_updated ? new Date(customerInfo.last_updated).toLocaleString() : 'N/A'}
          </div>`;
      }

      content += `</div>`;
    }

    // 推荐产品部分
    if (recommendations && recommendations.length > 0) {
      content += `<div class="section">
        <h3>💰 Loan Recommendations</h3>`;
      
      recommendations.forEach((rec, index) => {
        const status = rec.recommendation_status === 'current' ? '⭐ Current Recommendation' : '📋 Previous Option';
        content += `
          <div class="recommendation">
            <h4>${status}: ${rec.lender_name} - ${rec.product_name}</h4>
            <div class="rate-info">Interest Rate: ${rec.base_rate}% p.a.</div>
            <div class="info-grid" style="margin-top: 10px;">
              <div class="info-item">
                <span class="label">Comparison Rate:</span>
                <span class="value">${rec.comparison_rate}% p.a.</span>
              </div>
              <div class="info-item">
                <span class="label">Max Loan Amount:</span>
                <span class="value">${rec.max_loan_amount?.toLocaleString() || 'N/A'}</span>
              </div>
              <div class="info-item">
                <span class="label">Est. Monthly Payment:</span>
                <span class="value">${rec.monthly_payment?.toLocaleString() || 'N/A'}</span>
              </div>
              <div class="info-item">
                <span class="label">Eligibility:</span>
                <span class="value">${rec.eligibility_status || 'Under Review'}</span>
              </div>
            </div>
          </div>`;
      });
      
      content += `</div>`;
    }

    content += `
          <div class="section" style="font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 15px;">
              <p><strong>Disclaimer:</strong> This information is for reference purposes only. Final loan terms and approval are subject to lender assessment and verification of all provided information.</p>
              <p><strong>Generated by:</strong> LIFEX AI Loan Assistant | <strong>Date:</strong> ${new Date().toISOString()}</p>
          </div>
      </body>
      </html>
    `;

    // 打开新窗口并打印
    const printWindow = window.open('', '_blank');
    printWindow.document.write(content);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  }, [customerInfo, recommendations, getVisibleFields]);

  // 🔧 新增：清除表单
  const clearForm = useCallback(() => {
    if (window.confirm("Are you sure you want to clear all information? This action cannot be undone.")) {
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
        last_updated: new Date().toISOString()
      };
      
      setCustomerInfo(clearedInfo);
      setValidationErrors({});
      setExtractionStatus({
        isExtracting: false,
        lastExtracted: 0,
        confidence: 0,
        newFieldsCount: 0
      });
      
      if (onFormUpdate) {
        onFormUpdate(clearedInfo);
      }
      if (onCustomerInfoChange) {
        onCustomerInfoChange(clearedInfo);
      }
    }
  }, [onFormUpdate, onCustomerInfoChange]);

  // 🔧 新增：重新提取
  const reExtract = useCallback(() => {
    if (conversationHistory && conversationHistory.length > 0) {
      setExtractionStatus(prev => ({ ...prev, lastExtracted: 0 }));
      extractInfoFromConversation();
    }
  }, [conversationHistory, extractInfoFromConversation]);

  // 🔧 新增：渲染字段
  const renderField = useCallback((fieldName) => {
    const config = fieldConfig[fieldName];
    const value = customerInfo[fieldName] || '';
    const error = validationErrors[fieldName];
    const isRequired = config.required;
    const isAutoExtracted = customerInfo.extracted_fields?.includes(fieldName);

    const baseClasses = `w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors ${
      error ? 'border-red-500 bg-red-50' : 'border-gray-300'
    } ${isAutoExtracted ? 'bg-green-50 border-green-300' : ''}`;

    let inputElement;

    switch (config.type) {
      case 'select':
        inputElement = (
          <select
            value={value}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            className={baseClasses}
          >
            {config.options.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        );
        break;

      case 'number':
        inputElement = (
          <input
            type="number"
            value={value || ''}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            placeholder={config.placeholder}
            min={config.min}
            max={config.max}
            step={config.step}
            className={baseClasses}
          />
        );
        break;

      case 'currency':
        inputElement = (
          <input
            type="text"
            value={value ? value.toLocaleString() : ''}
            onChange={(e) => {
              const numericValue = e.target.value.replace(/[,$]/g, '');
              handleFieldChange(fieldName, numericValue);
            }}
            placeholder={config.placeholder}
            className={baseClasses}
          />
        );
        break;

      default:
        inputElement = (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleFieldChange(fieldName, e.target.value)}
            placeholder={config.placeholder}
            className={baseClasses}
          />
        );
    }

    return (
      <div key={fieldName} className="space-y-2">
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
          {config.label}
          {isRequired && <span className="text-red-500">*</span>}
          {isAutoExtracted && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">
              <CheckCircle className="w-3 h-3 mr-1" />
              Auto-filled
            </span>
          )}
        </label>
        
        {inputElement}
        
        {error && (
          <div className="flex items-center gap-1 text-sm text-red-600">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
        
        {config.helpText && (
          <div className="flex items-center gap-1 text-xs text-gray-500">
            <Info className="w-3 h-3" />
            {config.helpText}
          </div>
        )}
      </div>
    );
  }, [customerInfo, validationErrors, handleFieldChange]);

  // Render form sections - 改进版本
  const renderFormSection = (sectionName, title) => {
    const sectionFields = Object.entries(fieldConfig).filter(([key, config]) => {
      if (config.section !== sectionName) return false;
      if (config.conditional && !config.conditional(customerInfo)) return false;
      return true;
    });

    if (sectionFields.length === 0) return null;

    return (
      <div key={sectionName} className="mb-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-3 border-b border-gray-200 pb-2">
          {title}
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sectionFields.map(([fieldName]) => renderField(fieldName))}
        </div>
      </div>
    );
  };

  const visibleFields = getVisibleFields();
  const hasAnyData = visibleFields.some(field => customerInfo[field]);
  const completionPercentage = visibleFields.length > 0 
    ? Math.round((visibleFields.filter(field => customerInfo[field]).length / visibleFields.length) * 100)
    : 0;

  return (
    <div className="h-full flex flex-col" style={{ backgroundColor: '#fef7e8' }}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold text-gray-800">Customer Information</h2>
            <div className="flex items-center gap-4 mt-1">
              <div className="text-sm text-gray-600">
                Form Completion: {completionPercentage}%
              </div>
              {extractionStatus.newFieldsCount > 0 && (
                <div className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="w-4 h-4" />
                  Extracted {extractionStatus.newFieldsCount} fields
                </div>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {/* Auto-extraction toggle */}
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={autoExtractEnabled}
                onChange={(e) => setAutoExtractEnabled(e.target.checked)}
                className="mr-2"
              />
              <span className="text-sm text-gray-600">Auto-extract</span>
            </label>

            {/* Extraction status */}
            {extractionStatus.isExtracting && (
              <div className="flex items-center text-sm text-blue-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                Extracting...
              </div>
            )}
            
            <button
              onClick={reExtract}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-md hover:bg-blue-100 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-1" />
              Re-extract
            </button>
            
            <button
              onClick={clearForm}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 bg-gray-50 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
            >
              Clear
            </button>
            
            <button
              onClick={exportToPDF}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-green-600 border border-green-600 rounded-md hover:bg-green-700 transition-colors"
            >
              <Download className="w-4 h-4 mr-1" />
              Download PDF
            </button>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>Progress</span>
            <span>{completionPercentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${completionPercentage}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Form Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {hasAnyData ? (
          <>
            {/* Core Information */}
            {renderFormSection('core', '📋 Core Information')}
            
            {/* Financial Information */}
            {renderFormSection('financial', '💰 Financial Information')}
            
            {/* Business Information */}
            {renderFormSection('business', '🏢 Business Information')}
            
            {/* Vehicle Information */}
            {renderFormSection('vehicle', '🚗 Vehicle Information')}
            
            {/* Additional Preferences */}
            {renderFormSection('preferences', '⚙️ Loan Preferences')}
          </>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Upload className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Information will be automatically extracted from your conversation</p>
            <p className="text-sm">or you can fill out the form manually</p>
          </div>
        )}

        {/* Debug Information (Development Mode) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-8 p-4 bg-gray-100 rounded-lg">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">🔍 Debug Information</h3>
            <div className="text-xs text-gray-600 space-y-1">
              <div>Last Updated: {customerInfo.last_updated ? new Date(customerInfo.last_updated).toLocaleString() : 'Never'}</div>
              <div>Extracted Fields: {customerInfo.extracted_fields?.length || 0}</div>
              <div>Auto-Extract: {autoExtractEnabled ? 'Enabled' : 'Disabled'}</div>
              <div>Confidence: {(extractionStatus.confidence * 100).toFixed(0)}%</div>
              <div>Visible Fields: {visibleFields.length}</div>
              <div>Business Structure: {customerInfo.business_structure || 'Not set'}</div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      {(extractionStatus.newFieldsCount > 0 || hasAnyData) && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          <div className="flex justify-between items-center">
            <span>
              {extractionStatus.newFieldsCount > 0 && `Auto-extracted: ${extractionStatus.newFieldsCount} fields`}
              {hasAnyData && extractionStatus.newFieldsCount === 0 && "Manually entered information"}
            </span>
            {customerInfo.last_updated && (
              <span>
                Last updated: {new Date(customerInfo.last_updated).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DynamicCustomerForm;