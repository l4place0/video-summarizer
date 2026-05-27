## Why

Bilibili cookies 是访问受限视频的必要凭证，但当前系统无法检测 cookies 是否过期，也无法方便地更新 cookies。用户必须手动编辑文件。

## What Changes

- **Cookies 自检** — 启动时和 status 命令时检测 cookies 有效性
- **WebUI 管理** — 添加 Settings 页面，支持粘贴更新 cookies
- **Skill 管理** — 添加 `update-cookies.sh` 脚本
- **过期提醒** — 在 status 和 WebUI 中显示 cookies 状态

## Capabilities

### New Capabilities

- `cookies-health-check`: Cookies 有效性检测和状态报告
- `cookies-management`: Cookies 更新接口（WebUI + Skill）

### Modified Capabilities

（无）

## Impact

- `core/platforms/bilibili.py` — 添加 cookies 验证方法
- `core/api/routes.py` — cookies 状态端点 + 更新端点
- `core/web/index.html` — Settings 页面
- `core/web/app.js` — cookies 管理逻辑
- `core/web/style.css` — Settings 样式
- `skill/scripts/status.sh` — 显示 cookies 状态
- `skill/scripts/update-cookies.sh` — 新增
