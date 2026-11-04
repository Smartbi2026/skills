# OpenAPI 工具 Provider 管理

仅用于工具配置维护。优先使用当前 SDK 的 Provider 读取、解析和维护接口；例如 `getToolProviders` 仅在当前注册且契约适用时使用。SDK 不足时核实以下内部契约，不通过普通问数失败自动修改工具。

| 操作 | 方法与路径（相对 SmartBI 根地址） | 辅助命令 |
|---|---|---|
| 列举 | POST `/smartbix/api/dataagent/tools/list` | `provider-list` |
| 按名称读取 | GET `/smartbix/api/dataagent/tools/getByName?name=...` | `provider-get` |
| 仅解析不保存 | POST `/smartbix/api/dataagent/tools/parse?type=OPENAPI`，正文为 OpenAPI 文本 | `provider-parse` |
| 执行工具 | POST `/smartbix/api/dataagent/tools/execute` | 无自动化命令 |
| 创建、更新 | POST `/smartbix/api/dataagent/tools/create`、`/update` | 无自动化命令 |
| 删除 | POST `/smartbix/api/dataagent/tools/delete?id=...` | 无自动化命令 |

后三项保留原版说明范围，须按当前接口契约和明确操作授权执行，不意味着随包脚本已实现。工具执行是否产生写入或发送取决于实际操作，不能当作解析验证。浏览器/HAR 仅可帮助确认缺失契约，不复制其中凭证重放。

## 读取与解析

```bash
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE provider-list --output <PROVIDERS_JSON>
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE provider-get --name <PROVIDER_NAME> --output <PROVIDER_JSON>
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE provider-parse --openapi-file <OPENAPI_FILE> --output <PARSED_JSON>
```

`<SCRIPT>` 为 `scripts/agent-management/smartbi_internal.py` 的绝对路径。认证和地址规则与[工作流管理](agent-workflows.md#调用形式)一致。输出包含摘要，完整结果仅按需写文件；解析不保存也不执行远端工具，解析成功不证明实际调用成功。

## 定义与维护

按当前解析器能力准备 OpenAPI。原版兼容子集保留为保守起点：OpenAPI 3、单个 servers、明确 operationId 和 200 响应，优先单一内容类型、简单对象和清晰命名参数；GET/POST/PUT/DELETE 按解析器支持使用。不能把这组起点当作所有版本的完整支持范围；复杂引用和参数结构须以实际解析与回读核实。

用户授权修改时，先保存现有定义、解析候选，再按已核实的当前写接口提交一次并回读。更新可能重新生成 Tool ID，应核对绑定该工具的工作流，不能仅凭 Provider 名称未变认为绑定仍有效。旧版文档提到的参数 ID 不稳定、布尔值序列化差异等，仅在当前返回中出现时定位，不预设修复或修改节点来绕过。

需要重绑定时，另行核实受影响节点与用户授权范围；需要运行验收时由主入口组合白泽模块，用新会话检查参数传递及结果，不复用旧运行状态。远端工具若要求只读或不执行，需由服务端真实执行约束保证，不能只依赖提示词或 OpenAPI 默认值。
