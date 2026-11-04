# 智能体工作流管理

仅在用户明确要求管理工作流时读取。优先使用目标部署已注册的 SDK 管理能力；不足时才核实下列内部契约。内部原始 ID 与会话 `customagent_<ID>` 不同，只移除已确认的该前缀，不随意改写 ID。

## 能力与内部契约

| 操作 | 方法与路径（相对 SmartBI 根地址） | 随包脚本 |
|---|---|---|
| 读取并导出 JSON 定义 | GET `/smartbix/api/dataagent/graph/{id}` | `agent-get` |
| 创建 | POST `/smartbix/api/dataagent/graph/create/{parentId}` | `agent-create` |
| 更新 | POST `/smartbix/api/dataagent/graph/update` | `agent-update` |
| 搜索工作流 | POST `/smartbix/api/dataagent/graphs` | 无专用命令，须核实当前契约 |
| 下载定义 | GET `/smartbix/api/dataagent/define/download/{id}` | 无专用命令，须核实当前契约 |
| 上传定义 | POST `/smartbix/api/dataagent/define/upload` | 无专用命令，须核实当前契约 |

这些路径保留原版的管理范围，不证明任意部署可用。认证和操作权限按当前部署核实，包括相应 `AI_AGENT` 与编辑权限；辅助脚本只覆盖表中三个命令，不自动执行定义上传、发布、删除或回滚。

## 调用形式

`<PYTHON>` 为 Python 3，`<SCRIPT>` 为 Skill 下 `scripts/agent-management/smartbi_internal.py` 的绝对路径；所有文件路径用实际工作目录绝对路径。认证值通过已设置的环境变量传入，示例只包含变量名，不在命令、输出或请求文件中写入凭证值。

```bash
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE agent-get --agent-id <RAW_AGENT_ID> --output <AGENT_JSON>
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE agent-update --agent-id <RAW_AGENT_ID> --file <PATCH_JSON> --backup-dir <BACKUP_DIR>
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE agent-update --agent-id <RAW_AGENT_ID> --file <PATCH_JSON> --backup-dir <BACKUP_DIR> --expect-sha256 <PREVIEW_HASH> --apply
<PYTHON> <SCRIPT> --base-url <SMARTBI_BASE_URL> --header-env Cookie=SMARTBI_SESSION_COOKIE agent-create --parent-id <CONFIRMED_PARENT_ID> --file <AGENT_JSON>
```

创建默认只预览，提交时追加 `--apply`。裸主机地址使用默认 `/smartbi` 上下文；部署使用其他上下文时，提供完整根地址，如 `https://host.example/bi`，不携带 index.jsp、查询参数或片段。认证方式并非固定 Cookie，也可按已确认契约用 `--header-env Authorization=<ENV_VAR>`，脚本不会自动拼接 Bearer 或跨连接复用凭证。

脚本按 HTTP 响应声明解压 gzip 后解析 JSON；创建接口可返回 JSON 字符串或符合资源 ID 格式的裸 ID。该文本兼容仅限创建接口，HTML 登录页、其他非 JSON 响应及业务失败仍不能当作有效定义。

## 修改与验收

读取现有定义并保留所有未知字段。脚本仅变更补丁中声明的 `name`、`alias`、`desc`、`define`、`setting`，不以精简示例覆盖整个资源。`define` 必须为 JSON 对象；修改图结构时还需按当前图契约核对节点、连线和端口引用，保持不变节点的 ID，不猜测节点格式。

预览返回当前和候选 SHA-256、变更字段及节点/连线数量。提交使用此次预览哈希，当前对象变化则停止，不能覆盖。提交前写入备份，更新一次，再回读所有可编辑字段；创建同样回读核对请求字段。备份沿用原版脱敏方式，恢复前须核对隐藏字段是否需要重新配置，不能将脱敏文件直接视为无损回滚包。

回读不一致或 HTTP/业务失败时报告实际影响，不自动重试。配置回读成功后，仅在用户要求运行验收时检查相关 Provider/Tool 绑定、当前 SDK 的可见性接口，并由主入口组合白泽新会话验证成功及失败分支。创建不自动等于发布或出现在 `getAgentItems` 中。回滚是用户明确要求后对已审阅备份执行更新，脚本无自动回滚命令。
