## ADDED Requirements

### Requirement: Multi-URL input
前端 SHALL 支持通过 textarea 输入多个 URL，每行一个。

#### Scenario: Enter multiple URLs
- **WHEN** 用户在 textarea 中输入多个 URL（每行一个）
- **AND** 点击 Submit 按钮
- **THEN** 系统按行分割，过滤空行，验证每个 URL

#### Scenario: Paste from clipboard
- **WHEN** 用户粘贴包含多个 URL 的文本
- **THEN** 系统正确解析每行作为独立 URL

#### Scenario: Single URL still works
- **WHEN** 用户只输入一个 URL
- **THEN** 行为与之前完全一致

### Requirement: Batch API endpoint
系统 SHALL 提供 `POST /api/summarize/batch` 端点接受 URL 列表。

#### Scenario: Submit multiple valid URLs
- **WHEN** POST /api/summarize/batch 包含 3 个有效 URL
- **THEN** 返回 3 个 task_id，每个 status 为 "pending"
- **AND** 每个 URL 启动独立的 pipeline 后台线程

#### Scenario: Mixed valid and invalid URLs
- **WHEN** 请求包含 2 个有效 URL 和 1 个无效 URL
- **THEN** 返回 2 个 task_id
- **AND** `skipped` 数组包含 1 个无效 URL

#### Scenario: All invalid URLs
- **WHEN** 所有 URL 都无法匹配已知平台
- **THEN** 返回空 tasks 数组和完整的 skipped 列表

### Requirement: Batch progress display
前端 SHALL 显示批量提交的整体进度。

#### Scenario: Show batch counter
- **WHEN** 批量提交了 5 个 URL
- **THEN** 显示 "Batch: 0/5 done" 或类似的进度计数器

#### Scenario: Update on completion
- **WHEN** 其中一个 task 完成
- **THEN** 计数器更新为 "1/5 done"

#### Scenario: All complete
- **WHEN** 所有 task 都完成或失败
- **THEN** 显示最终结果 "Batch: 5/5 done"（含失败数）

### Requirement: URL validation
前端 SHALL 在提交前验证 URL 格式。

#### Scenario: Skip invalid URLs
- **WHEN** textarea 中包含 "not a url" 和 "https://www.bilibili.com/video/BV123"
- **THEN** 仅提交有效的 Bilibili URL
- **AND** 显示跳过的无效 URL 数量

#### Scenario: All invalid
- **WHEN** 所有输入都不是有效 URL
- **THEN** 显示错误提示，不提交
