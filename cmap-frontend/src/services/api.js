// services/api.js - 修复版本
// 🔧 修复：动态API URL配置，支持开发和生产环境
const getApiBaseUrl = () => {
  // 优先使用环境变量
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  
  // 根据当前环境自动判断
  if (import.meta.env.PROD) {
    return 'https://lifex-backend.onrender.com';
  }
  
  // 开发环境默认值
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

console.log('🔧 API Base URL configured:', API_BASE_URL);

// 🔧 修复：连接状态检查
export const checkConnection = async () => {
  try {
    console.log('🔍 Checking connection to:', API_BASE_URL);
    
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000), // 10秒超时
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('✅ Connection successful:', data);
    return { connected: true, data };
  } catch (error) {
    console.error('❌ Connection failed:', error);
    return { connected: false, error: error.message };
  }
};

// 原始的聊天API调用
export const sendMessageToChatAPI = async (message) => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.reply || 'Sorry, I could not process your request.';
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
};

// 🔧 修复：增强的消息发送API - 使用统一智能服务
export const sendEnhancedMessage = async (message, sessionId = null, chatHistory = [], customerInfo = {}) => {
  try {
    const payload = {
      message: message,
      session_id: sessionId || `session_${Date.now()}`,
      history: chatHistory
    };

    // 🔧 新增：包含客户信息
    if (customerInfo && Object.keys(customerInfo).length > 0) {
      // 清理空值
      const cleanedInfo = Object.fromEntries(
        Object.entries(customerInfo).filter(([key, value]) => 
          value !== null && value !== undefined && value !== '' && value !== 'undefined'
        )
      );
      
      if (Object.keys(cleanedInfo).length > 0) {
        payload.current_customer_info = cleanedInfo;
      }
    }

    console.log('📤 Sending enhanced message:', payload);

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(30000), // 30秒超时
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();
    console.log('📥 Enhanced API response:', data);

    return {
      reply: data.reply,
      session_id: data.session_id,
      stage: data.conversation_stage || data.stage,
      customer_profile: data.customer_profile,
      recommendations: data.recommendations || [],
      next_questions: data.next_questions || [],
      round_count: data.round_count,
      status: data.status || 'success',
      features: data.features || {}
    };
  } catch (error) {
    console.error('❌ Enhanced API call failed:', error);
    throw error;
  }
};

// 🔧 新增：更新贷款金额
export const updateLoanAmount = async (sessionId, newAmount) => {
  try {
    console.log(`💰 Updating loan amount: ${newAmount} for session: ${sessionId}`);
    
    const response = await fetch(`${API_BASE_URL}/update-loan-amount`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        new_amount: newAmount
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('✅ Loan amount updated:', data);
    return data;
  } catch (error) {
    console.error('❌ Update loan amount failed:', error);
    throw error;
  }
};

// 🔧 修复：重置对话
export const resetConversation = async (sessionId) => {
  try {
    console.log(`🔄 Resetting session: ${sessionId}`);
    
    const response = await fetch(`${API_BASE_URL}/reset-session`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: sessionId }),
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log('✅ Session reset:', data);
    return data;
  } catch (error) {
    console.error('❌ Reset conversation failed:', error);
    throw error;
  }
};

// 获取对话状态
export const getConversationStatus = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/session-status/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('❌ Get conversation status failed:', error);
    throw error;
  }
};

// 健康检查
export const healthCheck = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('❌ Health check failed:', error);
    throw error;
  }
};

// 🔧 新增：获取服务状态
export const getServiceStatus = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/service-status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: AbortSignal.timeout(10000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('❌ Service status check failed:', error);
    throw error;
  }
};

// 提取客户信息 - 备用API端点（如果需要单独的信息提取）
export const extractCustomerInfo = async (conversationHistory, existingInfo = {}) => {
  try {
    const response = await fetch(`${API_BASE_URL}/extract-customer-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        conversation_history: conversationHistory,
        existing_info: existingInfo
      }),
      signal: AbortSignal.timeout(20000),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('❌ Customer info extraction failed:', error);
    throw error;
  }
};

// 🔧 修复：导出增强的配置
export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  ENDPOINTS: {
    CHAT: '/chat',
    HEALTH: '/health',
    UPDATE_LOAN_AMOUNT: '/update-loan-amount',
    RESET_SESSION: '/reset-session',
    SERVICE_STATUS: '/service-status',
    SESSION_STATUS: '/session-status'
  }
};

// 🔧 修复：通用的fetch包装器，带重试逻辑
export const fetchWithRetry = async (url, options = {}, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        timeout: API_CONFIG.TIMEOUT,
        signal: AbortSignal.timeout(API_CONFIG.TIMEOUT),
        ...options
      });
      
      if (response.ok) {
        return response;
      }
      
      // 如果是最后一次尝试，抛出错误
      if (i === retries - 1) {
        throw new Error(`HTTP error! status: ${response.status} after ${retries} attempts`);
      }
      
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
      
    } catch (error) {
      if (i === retries - 1) {
        throw error;
      }
      
      console.warn(`⚠️ Attempt ${i + 1} failed:`, error.message);
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};

// 🔧 新增：导出便捷的API方法
export const api = {
  sendMessage: sendEnhancedMessage,
  updateLoanAmount,
  resetSession: resetConversation,
  getStatus: getConversationStatus,
  checkHealth: healthCheck,
  getServiceStatus,
  checkConnection
};

export default api;