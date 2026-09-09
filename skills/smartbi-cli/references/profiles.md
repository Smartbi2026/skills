# 多环境（Profile）规范

本文件为 **Smartbi CLI Skill** 的附属参考；流程性 MUST 以上级 `SKILL.md` 为准。

**用途**：环境（profile）的确定、告知、配置与错误处理。用户视角只感知"一个环境"；`--profile`、默认环境等是内部细节，不进入用户视野。

## 核心原则

1. **用户只感知一个环境**：任务开始时确定并告知一次，之后全程静默
2. **配置 = 三要素**：地址、令牌、名字；首次与新增共用同一套提问
3. **执行零分支**：所有 `smartbi` 命令一律带 `--profile <name>`
4. **不动默认环境**：新增环境不带 `--set-default`；用户明确要求切换默认时用 `smartbi profile set-default <name>`
5. **向后兼容**：用户未指定环境时走默认环境，行为与单环境时代一致

## 环境确定

任务开始时，按以下顺序确定环境：

1. 扫描对话识别环境/客户关键词（环境名、`prod`/`qa`/`dev` 等后缀、客户名），与 config.yaml 的 `profiles` 键匹配
2. 唯一匹配 → 使用该环境
3. 多个匹配 → 问用户，不猜
4. 无匹配且用户提供了新环境的地址/令牌 → 走「配置三要素」新建
5. 未指定任何环境信息 → 默认环境（config.yaml 的 `profile:` 字段）

确定后 MUST 告知用户一次：

> 本次操作环境：`<name>`

用户中途明确"切到 Y"→ 按上述流程重新确定，并再次告知一次。

## 执行规则

- 环境确定后，所有 `smartbi` 命令（`list`/`search`/`describe`/`call`/`doc`）**一律带 `--profile <name>`**

## 配置三要素流程（首次与新增统一）

触发：首次使用（无配置文件）、用户要求配置新环境、指定的环境不存在。

按顺序提问（一次一个）：

1. **名字**：用户已提供环境线索（如"客户A的测试环境"）→ 确认名字；未提供 → 先跳过
2. **地址**：提供 Smartbi 地址 → `serverType: smartbi`；无法提供 → 问 SDK Server 地址 → `serverType: sdk-server`；均无法提供 → 暂停
3. **令牌**：问令牌时一并说明存储方式（仅一句）："请提供 Smartbi 个人令牌（可登录 Smartbi，在个人中心申请）。令牌默认直接存进配置；如对安全有更高要求，也可以改用「环境变量」或「系统钥匙串」存储。"
4. **名字（兜底）**：仍未确定时问："这个环境叫什么名字？（不填则默认 dev）"

写入方式：

| 场景 | 命令 | `profile:` 默认环境 |
|------|------|-------------------|
| 首次（无配置文件） | `smartbi init --server-type <sdk-server\|smartbi> --base-url <地址> --token <令牌> [--profile <环境名>]`（不指定 `--profile` 时默认 `dev`） | CLI 自动设为该环境 |
| 新增 | `smartbi profile add <name> --server-type <sdk-server\|smartbi> --base-url <地址> --token <令牌>`（创建时即预期为新默认，直接加 `--set-default`） | 不动（需要成为默认时，经用户确认后执行 `smartbi profile set-default <name>`，无需重建） |

完成后告知："环境 `<name>` 已配置 ✓"，并按「环境确定」告知本次操作环境。存储方式的说明已含于第 3 步令牌问询话术内，写入后不要重复询问。

## 错误处理

| 错误 | 处理 |
|------|------|
| `PROFILE_NOT_FOUND` | `smartbi profile list` 列出现有环境 → 用户选择，或走「配置三要素」新建 |
| `AUTH_FAILED` | 提示"`<name>` 环境的 token 无效或已过期"；执行 `smartbi profile show <name>` 查看凭证来源（env/keyring/字面量）与可用性，请用户确认该环境凭证 |
| 其他 | 按 SKILL.md Phase 4 通用诊断，报告本次调用所用环境 |

## 版本约束

- **版本要求**：CLI ≥ **2.0.0**（profile 命令族与 init/profile add 写盘的最低版本）。安装后验证：`smartbi --version` ≥ 2.0.0，或 `smartbi profile list --help` 可用；低于 2.0.0 时按 `references/init.md`「标准安装」升级
- **命名规则**：profile 名仅允许 `[A-Za-z0-9_-]`；"环境 × 客户"维度通过命名约定 `<客户>-<环境>` 承载（如 `customerA-test`），不强制
