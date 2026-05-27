## ADDED Requirements

### Requirement: Check for skill updates
系统 SHALL 提供脚本检查是否有新版本可用。

#### Scenario: New version available
- **WHEN** 用户运行 `bash skill/scripts/check-update.sh`
- **AND** GitHub 上有更新版本
- **THEN** 显示当前版本和最新版本，并提示更新方式

#### Scenario: Already up to date
- **WHEN** 用户运行 `bash skill/scripts/check-update.sh`
- **AND** 当前已是最新版本
- **THEN** 显示"已是最新版本"

#### Scenario: Network error
- **WHEN** 用户运行 `bash skill/scripts/check-update.sh`
- **AND** 网络请求失败
- **THEN** 显示错误提示，不崩溃

### Requirement: Version tracking
系统 SHALL 维护当前版本号。

#### Scenario: Version file exists
- **WHEN** 脚本读取版本号
- **THEN** 从 `skill/scripts/version.sh` 中的 `CURRENT_VERSION` 变量获取
