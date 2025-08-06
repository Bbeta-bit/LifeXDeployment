// services/api.js
const API_BASE_URL = 'http://localhost:8000';

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

// 增强的消息发送API - 使用你的unified intelligent service
export const sendEnhancedMessage = async (message, sessionId = null, chatHistory = []) => {
  try {
    const payload = {
      message: message,
      session_id: sessionId || `session_${Date.now()}`,
      history: chatHistory
    };

    console.log('Sending enhanced message:', payload);

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();
    console.log('Enhanced API response:', data);

    return {
      reply: data.reply,
      session_id: data.session_id,
      stage: data.stage,
      customer_profile: data.customer_profile,
      recommendations: data.recommendations || [],
      next_questions: data.next_questions || [],
      round_count: data.round_count,
      status: data.status || 'success'
    };
  } catch (error) {
    console.error('Enhanced API call failed:', error);
    throw error;
  }
};

// 重置对话
export const resetConversation = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/reset-conversation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Reset conversation failed:', error);
    throw error;
  }
};

// 获取对话状态
export const getConversationStatus = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/conversation-status/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Get conversation status failed:', error);
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
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Health check failed:', error);
    throw error;
  }
};

// 测试服务
export const testService = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/test-service`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Service test failed:', error);
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
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Customer info extraction failed:', error);
    throw error;
  }
};

// 导出默认配置
export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3
};

// 通用的fetch包装器，带重试逻辑
export const fetchWithRetry = async (url, options = {}, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const response = await fetch(url, {
        timeout: API_CONFIG.TIMEOUT,
        ...options
      });
      
      if (response.ok) {
        return response;
      }
      
      // 如果是最后一次尝试，抛出错误
      if (i === retries - 1) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 等待后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
      
    } catch (error) {
      if (i === retries - 1) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
};