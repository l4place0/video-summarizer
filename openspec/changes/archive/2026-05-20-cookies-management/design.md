## Context

Bilibili cookies 存储在 `data/cookies.txt`（Netscape 格式），由 bilibili.py 传递给 yt-dlp。cookies 过期后会导致 403 错误，元数据提取失败。

## Goals / Non-Goals

**Goals:**
- 自动检测 cookies 是否有效
- WebUI 和 Skill 都能更新 cookies
- 过期时主动提醒用户

**Non-Goals:**
- 不做自动刷新 cookies（需要用户登录）
- 不做多账号管理

## Decisions

### 1. Cookies 验证方式

用 yt-dlp 请求一个已知公开视频（如 BV1GJ411x7h7）的 metadata，检查是否返回 403。

**替代方案：** 解析 cookies 文件检查过期时间（不可靠，很多 cookies 无明确过期时间）

### 2. WebUI Settings 页面

在 navbar 添加 "Settings" tab，包含：
- Cookies 状态显示（有效/过期/未配置）
- Cookies 文本框（支持粘贴更新）
- 保存按钮

### 3. API 端点

- `GET /api/settings/cookies` — 返回 cookies 状态
- `PUT /api/settings/cookies` — 更新 cookies 文件内容

### 4. Skill 脚本

`update-cookies.sh` — 接受 cookies 内容作为参数或 stdin，写入文件。

## Risks / Trade-offs

- [验证视频选择] 需要一个稳定的公开视频 → 使用经典测试视频
- [并发更新] 多人同时更新 cookies → 文件写入加锁
