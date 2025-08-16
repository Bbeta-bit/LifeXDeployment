// api.js - Render部署优化版本
const getApiBaseUrl = () => {
  // 优先使用环境变量
  if (import.meta.env.VITE_BACKEND_URL) {
    return import.meta.env.VITE_BACKEND_URL;
  }
  
  // 生产环境自动判断
  if (import.meta.env.PROD) {
    return 'https://lifex-backend.onrender.com';
  }
  
  // 开发环境默认值
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();
console.log('🔧 API Base URL configured:', API_BASE_URL);

// 增强的连接检查
export const checkConnection = async () => {
  try {
    console.log('🔍 Checking connection to:', API_BASE_URL);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15秒超时
    
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
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

// 增强的消息发送API
export const sendEnhancedMessage = async (message, sessionId = null, chatHistory = [], customerInfo = {}) => {
  try {
    const payload = {
      message: message,
      session_id: sessionId || `session_${Date.now()}`,
      history: chatHistory || []
    };

    // 包含客户信息
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

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();
    console.log('📨 Response received:', data);
    return data;
  } catch (error) {
    console.error('❌ Send enhanced message failed:', error);
    throw error;
  }
};

// 简化的消息发送（向后兼容）
export const sendMessageToChatAPI = async (message) => {
  try {
    const response = await sendEnhancedMessage(message);
    return response.reply || 'Sorry, I could not process your request.';
  } catch (error) {
    console.error('API call failed:', error);
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

// 会话管理
export const getSessionStatus = async (sessionId) => {
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
    console.error('❌ Get session status failed:', error);
    throw error;
  }
};

export const resetSession = async (sessionId) => {
  try {
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
    return data;
  } catch (error) {
    console.error('❌ Reset session failed:', error);
    throw error;
  }
};

// API配置
export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  ENDPOINTS: {
    CHAT: '/chat',
    HEALTH: '/health',
    SESSION_STATUS: '/session-status',
    RESET_SESSION: '/reset-session'
  }
};

// 通用的fetch包装器，带重试逻辑
export const fetchWithRetry = async (url, options = {}, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);
      
      const response = await fetch(url, {
        signal: controller.signal,
        ...options
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        return response;
      }
      
      // 如果是最后一次尝试，抛出错误
      if (i === retries - 1) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.warn(`Attempt ${i + 1} failed:`, error.message);
      
      // 如果是最后一次尝试，抛出错误
      if (i === retries - 1) {
        throw error;
      }
      
      // 等待后重试 (指数退避)
      await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000));
    }
  }
};