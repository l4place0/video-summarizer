## 1. Cookies 自检

- [x] 1.1 在 `bilibili.py` 中添加 `check_cookies()` 方法，用 yt-dlp 请求测试视频检测 403
- [x] 1.2 在 `routes.py` 中添加 `GET /api/settings/cookies` 端点返回 cookies 状态
- [x] 1.3 在 `status.sh` 中添加 cookies 状态显示

## 2. Cookies 更新 API

- [x] 2.1 在 `routes.py` 中添加 `PUT /api/settings/cookies` 端点更新 cookies 文件
- [x] 2.2 验证写入的 cookies 格式（Netscape 格式检查）

## 3. WebUI 管理

- [x] 3.1 在 `index.html` 中添加 Settings 页面（cookies 状态 + 文本框 + 保存按钮）
- [x] 3.2 在 `app.js` 中实现 cookies 加载和保存逻辑
- [x] 3.3 在 `style.css` 中添加 Settings 页面样式（复用现有 prompt 样式）

## 4. Skill 脚本

- [x] 4.1 创建 `skill/scripts/update-cookies.sh` 支持 stdin 或文件参数输入

## 5. 测试

- [x] 5.1 验证 cookies 状态检测逻辑
- [x] 5.2 验证 cookies 更新 API
