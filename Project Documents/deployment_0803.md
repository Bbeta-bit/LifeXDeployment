# Enhanced Memory Service Deployment Guide

## 部署步骤

### 1. 添加新文件
将 `enhanced_memory_conversation_service.py` 文件放在你的项目根目录下（与 `main.py` 同级）。

### 2. 更新 main.py
用提供的新版本 `main.py` 替换现有文件。

### 3. 无需额外依赖
增强记忆服务使用标准Python库，无需安装新的依赖包。

## 功能特性

### 🧠 增强记忆功能
- **字段追踪**: 自动识别并记录客户提供的信息
- **防重复询问**: 智能避免询问已提供的信息
- **上下文感知**: 基于对话历史智能推进对话

### 🔄 反重复机制
- 追踪已询问的字段 (`asked_fields`)
- 记录已确认的信息 (`confirmed_fields`) 
- 监控最近的问题 (`last_questions`)
- 智能判断是否应该询问某个字段

### 📊 信息提取
支持自动提取以下信息：
- `credit_score`: 信用评分
- `desired_loan_amount`: 期望贷款金额
- `ABN_years`: ABN注册年数
- `GST_years`: GST注册年数
- `property_status`: 房产状态

## 新增API端点

### `/get-memory-status`
```json
POST /get-memory-status
{
  "session_id": "user_session_123"
}
```
返回会话的记忆状态和防重复信息。

### `/reset-memory` 
```json
POST /reset-memory
{
  "session_id": "user_session_123"
}
```
清除指定会话的记忆。

### `/update-customer-info`
```json
POST /update-customer-info
{
  "session_id": "user_session_123",
  "updates": {
    "credit_score": 750,
    "desired_loan_amount": 50000
  }
}
```
强制更新客户信息（用于纠错）。

### `/memory-analytics`
```json
GET /memory-analytics
```
获取记忆系统的分析数据。

## 测试方法

### 1. 启动服务
```bash
python main.py
```

### 2. 测试防重复功能
1. 发送消息: "My credit score is 750"
2. 再发送: "I need a loan"
3. 观察AI是否避免重复询问信用评分

### 3. 检查记忆状态
```bash
curl -X POST http://localhost:8000/get-memory-status \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_session"}'
```

## 配置选项

### 调整重复询问阈值
在 `EnhancedMemoryService.should_ask_field()` 中修改：
```python
if asked_count >= 2:  # 修改这个数字调整最大询问次数
    return False
```

### 调整记忆的问题数量
在 `ConversationMemory.add_question()` 中修改：
```python
if len(self.last_questions) > 5:  # 修改这个数字调整记忆的问题数量
    self.last_questions.pop(0)
```

### 添加新的字段提取模式
在 `EnhancedMemoryService._init_field_patterns()` 中添加：
```python
"new_field": [
    r"pattern1.*?(\d+)",
    r"pattern2.*?(\w+)"
]
```

## 监控和调试

### 查看服务状态
```bash
curl http://localhost:8000/health
```

### 查看详细服务状态
```bash
curl http://localhost:8000/service-status
```

### 查看记忆分析
```bash
curl http://localhost:8000/memory-analytics
```

## 故障排除

### 问题1: 记忆服务未加载
**症状**: 日志显示 "Enhanced memory service not available"
**解决**: 确保 `enhanced_memory_conversation_service.py` 在正确位置

### 问题2: 仍然出现重复询问
**原因**: 可能是字段提取模式不匹配
**解决**: 检查 `_init_field_patterns()` 中的正则表达式

### 问题3: 信息提取不准确
**解决**: 在 `extract_information_from_message()` 中添加调试日志：
```python
print(f"Extracted: {extracted}")
```

## 性能考虑

### 内存使用
- 每个会话存储的信息有限
- 自动清理旧会话（可扩展实现）

### 响应时间
- 正则表达式匹配开销很小
- 建议监控 `/memory-analytics` 端点

## 扩展建议

### 1. 持久化存储
考虑将会话数据存储到Redis或数据库：
```python
# 示例: 使用Redis
import redis
redis_client = redis.Redis()

def save_session(self, session_id: str):
    session_data = json.dumps(self.sessions[session_id], default=str)
    redis_client.set(f"session:{session_id}", session_data, ex=3600)
```

### 2. 更智能的字段提取
集成现有的 `MVPPreferenceExtractor` 进行更准确的信息提取。

### 3. 会话超时
添加自动清理旧会话的功能：
```python
def cleanup_old_sessions(self, max_age_hours: int = 24):
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    to_remove = [sid for sid, mem in self.sessions.items() 
                 if mem.last_updated < cutoff]
    for sid in to_remove:
        del self.sessions[sid]
```

## 日志配置
添加详细日志便于调试：
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在关键位置添加日志
logger.info(f"Extracted info: {extracted_info}")
logger.warning(f"Repeated question detected for field: {field_name}")
```
