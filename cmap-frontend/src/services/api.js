const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

// 原有的发送消息函数（保持完全兼容）
export async function sendMessageToChatAPI(message) {
  const response = await fetch(`${backendUrl}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    // 这里抛出错误，前端调用时可以捕获并显示错误信息
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  return data.reply;
}

// 新增：增强的聊天API函数（支持会话管理和流程控制）
export async function sendEnhancedMessage(message, sessionId, history = []) {
  try {
    const response = await fetch(`${backendUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        session_id: sessionId,
        history: history
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in sendEnhancedMessage:', error);
    // 如果新API失败，回退到原有API
    try {
      const fallbackReply = await sendMessageToChatAPI(message);
      return {
        status: 'success',
        reply: fallbackReply,
        conversation_stage: 'unknown',
        mvp_progress: {
          completed_fields: [],
          missing_fields: [],
          is_complete: false
        },
        preferences_collected: {}
      };
    } catch (fallbackError) {
      throw fallbackError;
    }
  }
}

// 新增：获取对话状态
export async function getConversationState(sessionId) {
  try {
    const response = await fetch(`${backendUrl}/get-conversation-state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in getConversationState:', error);
    // 返回默认状态而不是抛出错误
    return {
      session_id: sessionId,
      stage: 'unknown',
      message: 'State unavailable'
    };
  }
}

// 新增：重置对话
export async function resetConversation(sessionId) {
  try {
    const response = await fetch(`${backendUrl}/reset-conversation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in resetConversation:', error);
    // 静默失败，返回成功状态
    return {
      status: 'success',
      message: 'Reset completed (fallback mode)'
    };
  }
}

// 新增：提取客户信息
export async function extractCustomerInfo(conversationHistory) {
  try {
    const response = await fetch(`${backendUrl}/extract-customer-info`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation_history: conversationHistory
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in extractCustomerInfo:', error);
    throw error;
  }
}

// 新增：健康检查
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${backendUrl}/health`, {
      method: 'GET',
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in checkBackendHealth:', error);
    return {
      status: 'error',
      message: 'Backend unavailable'
    };
  }
}

