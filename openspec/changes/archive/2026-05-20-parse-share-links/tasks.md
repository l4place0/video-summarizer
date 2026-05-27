## 1. 前端解析

- [x] 1.1 在 `app.js` 中添加 `extractUrl(text)` 函数，从文本中提取第一个 HTTP/HTTPS URL
- [x] 1.2 修改 `handleSubmit` 中的行处理逻辑，先 `extractUrl` 再 `isValidVideoUrl`
- [x] 1.3 处理提取结果为空的情况（跳过该行）

## 2. 测试

- [x] 2.1 验证 Bilibili 分享格式 `【标题】 URL` 正确提取
- [x] 2.2 验证纯 URL 行为不变
- [x] 2.3 验证无 URL 文本被跳过
- [x] 2.4 验证批量模式每行带标题正确处理
