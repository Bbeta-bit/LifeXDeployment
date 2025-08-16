// api.js - 完全优化版本
class APIManager {
  constructor() {
    this.baseUrl = this.getApiBaseUrl();
    this.requestQueue = new Map();
    this.retryDelays = [1000, 2000, 4000]; // 指数退避
    
    console.log('🔧 API Manager initialized:', this.baseUrl);
  }

  getApiBaseUrl() {
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
  }

  // 防抖请求（避免重复请求）
  debounceRequest(key, fn, delay = 300) {
    if (this.requestQueue.has(key)) {
      clearTimeout(this.requestQueue.get(key));
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(async () => {
        try {
          const result = await fn();
          this.requestQueue.delete(key);
          resolve(result);
        } catch (error) {
          this.requestQueue.delete(key);
          reject(error);
        }
      }, delay);

      this.requestQueue.set(key, timeoutId);
    });
  }

  // 智能超时处理（Render冷启动优化）
  createSmartTimeout(url) {
    // 健康检查用较短超时，聊天用较长超时
    if (url.includes('/health')) {
      return 15000; // 15秒
    } else if (url.includes('/chat')) {
      return 45000; // 45秒（适应AI处理时间）
    }
    return 30000; // 默认30秒
  }

  // 优化的fetch包装器
  async fetchWithRetry(url, options = {}, maxRetries = 3) {
    const fullUrl = url.startsWith('http') ? url : `${this.baseUrl}${url}`;
    const timeout = this.createSmartTimeout(fullUrl);
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      try {
        console.log(`🔄 API Request (attempt ${attempt + 1}/${maxRetries}): ${fullUrl}`);
        
        const response = await fetch(fullUrl, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        if (response.ok) {
          const data = await response.json();
          console.log(`✅ API Success: ${fullUrl}`);
          return { success: true, data, status: response.status };
        } else {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

      } catch (error) {
        clearTimeout(timeoutId);
        
        const isLastAttempt = attempt === maxRetries - 1;
        const isAbortError = error.name === 'AbortError';
        const isNetworkError = error.message.includes('Failed to fetch');
        
        console.warn(`⚠️ API Attempt ${attempt + 1} failed:`, error.message);

        if (isLastAttempt) {
          return {
            success: false,
            error: error.message,
            type: isAbortError ? 'timeout' : isNetworkError ? 'network' : 'http'
          };
        }

        // 智能重试延迟
        const delay = this.retryDelays[attempt] || 4000;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  // 连接检查（优化版）
  async checkConnection() {
    try {
      console.log('🔍 Checking connection to:', this.baseUrl);
      
      const result = await this.fetchWithRetry('/health', {}, 2); // 健康检查只重试2次
      
      if (result.success) {
        console.log('✅ Connection successful:', result.data);
        return { connected: true, data: result.data };
      } else {
        return { connected: false, error: result.error };
      }
    } catch (error) {
      console.error('❌ Connection check failed:', error);
      return { connected: false, error: error.message };
    }
  }

  // 优化的消息发送
  async sendMessage(message, sessionId = null, chatHistory = [], customerInfo = {}) {
    try {
      // 数据验证
      if (!message || typeof message !== 'string') {
        throw new Error('Valid message is required');
      }

      const payload = {
        message: message.trim(),
        session_id: sessionId || `session_${Date.now()}`,
        history: Array.isArray(chatHistory) ? chatHistory : []
      };

      // 清理客户信息
      if (customerInfo && typeof customerInfo === 'object') {
        const cleanedInfo = Object.fromEntries(
          Object.entries(customerInfo).filter(([key, value]) => 
            value !== null && 
            value !== undefined && 
            value !== '' && 
            value !== 'undefined' &&
            String(value).trim() !== ''
          )
        );
        
        if (Object.keys(cleanedInfo).length > 0) {
          payload.current_customer_info = cleanedInfo;
        }
      }

      console.log('📤 Sending message:', {
        message_length: payload.message.length,
        session_id: payload.session_id,
        has_history: payload.history.length > 0,
        customer_fields: Object.keys(payload.current_customer_info || {}).length
      });

      // 使用防抖（避免快速重复发送）
      const requestKey = `chat_${payload.session_id}_${Date.now()}`;
      
      return await this.debounceRequest(requestKey, async () => {
        const result = await this.fetchWithRetry('/chat', {
          method: 'POST',
          body: JSON.stringify(payload),
        });

        if (result.success) {
          console.log('📨 Message response received:', result.data);
          return result.data;
        } else {
          throw new Error(result.error || 'Failed to send message');
        }
      });

    } catch (error) {
      console.error('❌ Send message failed:', error);
      throw error;
    }
  }

  // 会话管理
  async getSessionStatus(sessionId) {
    try {
      const result = await this.fetchWithRetry(`/session-status/${sessionId}`, {}, 2);
      
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('❌ Get session status failed:', error);
      throw error;
    }
  }

  async resetSession(sessionId) {
    try {
      const result = await this.fetchWithRetry('/reset-session', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      console.error('❌ Reset session failed:', error);
      throw error;
    }
  }

  // 批量健康检查
  async performHealthChecks() {
    const checks = {
      api_health: null,
      response_time: null,
      features: null
    };

    try {
      const startTime = Date.now();
      const healthResult = await this.checkConnection();
      const endTime = Date.now();

      checks.api_health = healthResult.connected;
      checks.response_time = endTime - startTime;
      checks.features = healthResult.data?.features || null;

      return checks;
    } catch (error) {
      checks.api_health = false;
      checks.response_time = null;
      return checks;
    }
  }
}

// 创建全局API管理器实例
const apiManager = new APIManager();

// 导出的API函数（向后兼容）
export const checkConnection = () => apiManager.checkConnection();

export const sendEnhancedMessage = (message, sessionId, chatHistory, customerInfo) => 
  apiManager.sendMessage(message, sessionId, chatHistory, customerInfo);

export const sendMessageToChatAPI = async (message) => {
  try {
    const response = await apiManager.sendMessage(message);
    return response.reply || 'Sorry, I could not process your request.';
  } catch (error) {
    console.error('Legacy API call failed:', error);
    throw error;
  }
};

export const healthCheck = () => apiManager.checkConnection();

export const getSessionStatus = (sessionId) => apiManager.getSessionStatus(sessionId);

export const resetSession = (sessionId) => apiManager.resetSession(sessionId);

export const performHealthChecks = () => apiManager.performHealthChecks();

// API配置导出
export const API_CONFIG = {
  BASE_URL: apiManager.baseUrl,
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  ENDPOINTS: {
    CHAT: '/chat',
    HEALTH: '/health',
    SESSION_STATUS: '/session-status',
    RESET_SESSION: '/reset-session'
  }
};

// 导出API管理器（高级使用）
export default apiManager;