## ADDED Requirements

### Requirement: Extract URL from share text
系统 SHALL 从分享文本中自动提取视频 URL。

#### Scenario: Bilibili share link with title
- **WHEN** 用户粘贴 `【【中文字幕】C 中的递归宏】 https://www.bilibili.com/video/BV1fWdPBmEMc/?share_source=copy_web`
- **THEN** 系统提取 `https://www.bilibili.com/video/BV1fWdPBmEMc/?share_source=copy_web` 作为 URL

#### Scenario: Pure URL (backward compatible)
- **WHEN** 用户粘贴 `https://www.bilibili.com/video/BV1fWdPBmEMc/`
- **THEN** 行为与之前完全一致

#### Scenario: YouTube share link
- **WHEN** 用户粘贴 `Some Title https://youtube.com/watch?v=abc123`
- **THEN** 系统提取 `https://youtube.com/watch?v=abc123` 作为 URL

#### Scenario: Batch with mixed formats
- **WHEN** 用户在 textarea 中粘贴多行，每行格式为 `【标题】 URL`
- **THEN** 每行都正确提取 URL 并提交

#### Scenario: No URL in text
- **WHEN** 用户粘贴 `这是一段没有URL的文字`
- **THEN** 该行被跳过，不提交
