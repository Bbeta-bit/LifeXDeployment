const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

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

