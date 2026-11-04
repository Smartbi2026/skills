# 多环境（Profile）规范

本文件为 **SmartBI CLI Skill** 的附属参考；流程要求以 `SKILL.md` 为准。

**用途**：环境（profile）的确定、配置与错误处理。普通业务用户只感知连接的 SmartBI 地址或业务名称；`dev`、`--profile`、默认 profile 等是内部细节，不进入用户视野。

## 核心原则

1. **隐藏内部配置**：任务开始时确定连接，普通业务对话不单独展示 profile 名
2. **连接所需信息**：复用已有配置；缺少时仅补地址和有效令牌，内部名称自动确定
3. **执行环境一致**：所有 `smartbi` 命令一律带 `--profile <name>`
4. **不动默认环境**：新增环境不带 `--set-default`；用户明确要求切换默认时用 `smartbi profile set-default <name>`
5. **向后兼容**：用户未指定环境时走默认环境，行为与单环境时代一致

## 环境确定

任务开始时，按以下顺序确定环境：

1. 扫描对话识别环境/客户关键词（环境名、`prod`/`qa`/`dev` 等后缀、客户名），与 config.yaml 的 `profiles` 键匹配
2. 唯一匹配 → 使用该环境
3. 多个匹配 → 用服务器地址或用户熟悉的业务名称让用户选择，不要求识别 profile 名
4. 无匹配且用户提供了新连接的地址/令牌 → 按[连接指南的新增环境流程](setup-and-connection.md#新增环境已有配置文件时)新建
5. 未指定任何环境信息 → 默认环境（config.yaml 的 `profile:` 字段）

确定后直接继续原业务请求；仅在连接切换会影响结果或排错时，说明所用服务器地址或业务名称。用户中途明确“切到 Y”时按上述流程重新确定，不展示内部 profile 名。

## 执行规则

- 环境确定后，所有 `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**

## 连接写入与命名

安装、地址和令牌的提问、存储方式、首次初始化、新增与修复统一见[连接指南](setup-and-connection.md)，不重复询问已有有效信息。

- 首次无配置时使用 `smartbi init`；省略内部名称时由 CLI 使用默认名。
- 已有配置时新增连接使用 `smartbi profile add`，不改变默认环境。用户明确要求切换默认时，使用 `smartbi profile set-default <name>`；不重复索要已经授权的确认。
- 新连接优先从用户已给业务名称生成合法且不冲突的内部名；没有名称时按 `connection-2`、`connection-3` 等取首个未占用名。不得覆盖已有连接，也不为内部名称打断用户。

## 错误处理

| 错误 | 处理 |
|------|------|
| `PROFILE_NOT_FOUND` | `smartbi profile list` 读取现有连接；按地址或业务名称让用户选择，或按[新增环境流程](setup-and-connection.md#新增环境已有配置文件时)新建，不要求用户识别内部 profile 名 |
| `AUTH_FAILED` | 核对所选地址、serverType、凭证来源及有效性；必要时执行 `smartbi profile show <name>`，只在内部检查并避免输出凭证。不能仅凭错误认定令牌过期；仅缺失或失效时请用户补充 |
| 其他 | 按 SKILL.md 第四阶段 通用诊断，报告本次调用所用环境 |

用户明确要求浏览器登录或登出时，按[连接指南](setup-and-connection.md#浏览器授权登录与登出仅用户明确要求时)执行，默认仍用令牌；不主动推荐登录，不因失败重试或覆盖原连接。CLI 2.2.0 的 profile list 包含超时信息，profile show 可用于内部核对凭证来源。

## 版本约束

- **版本要求**：CLI ≥ **2.2.0**（本技能依赖的 CLI 2.2.0 能力基线）。安装后验证：`smartbi --version` ≥ 2.2.0，或 `smartbi profile list --help` 可用；低于 2.2.0 时按 `references/common-core/setup-and-connection.md`「标准安装」升级
- **命名规则**：profile 名仅允许 `[A-Za-z0-9_-]`；"环境 × 客户"维度通过命名约定 `<客户>-<环境>` 承载（如 `customerA-test`），不强制
