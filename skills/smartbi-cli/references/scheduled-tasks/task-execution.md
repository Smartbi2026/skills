# 定时任务请求与实现

仅在对应任务或计划需要创建、修改或回读时查阅相应小节。当前操作的结构以 describe 契约为准；业务步骤与启用范围由[定时任务场景](../../scenarios/scheduled-tasks.md)决定。

## 修改已有任务

当用户通过多轮对话修改已有任务时（如"增加某列""改展示格式"）：

```
步骤 A：获取已有任务——用户提供 taskId，或调用 listTasks 搜索
        将 {"id": "<taskId>"} 写入 task_verify.json 后执行：
        smartbi call scheduletask.getTaskById --profile <PROFILE> -d @task_verify.json --agent
        取出 script 字段内容
   ↓
步骤 B：将 script 内容写入 .js 文件（还原为可读多行代码）
        按用户意图修改 .js 文件内容
   ↓
步骤 C：修改元数据模板并重新注入
        node scripts/scheduled-tasks/inject-script.mjs updated_task.js task_meta.json task.json
   ↓
步骤 D：更新任务
        smartbi call scheduletask.updateSelfDefineTask --profile <PROFILE> -d @task.json --agent
```

> `updateSelfDefineTask` 的请求体与 `createSelfDefineTask` 相同，额外需要 `id` 字段。

## API 请求体

### 创建任务

```
POST /api/v1/scheduletask/task/create-self-define-task
```

```text
{
  "selfDefineTaskUpsertRequest": {
    "name": "<英文名>",
    "alias": "<中文名>",
    "desc": "<描述>",
    "parentFolderId": "<已核实的目录 ID>",
    "type": "SELFDEFINE",
    "script": "<Rhino JS 脚本>",
    "scriptVersion": "2.0"
  }
}
```

必填：`name`, `alias`, `script`, **`parentFolderId`**。SmartBI 资源为树状结构，新建任务必须指定存放目录。

### parentFolderId 选取（任务专属）

**任务（TASK）的父节点必须位于 `TASKS` 根节点下**。目录类型和可写权限以目标环境当前契约为准；下方示例筛选 `DEFAULT_TREENODE`，不能把 `SELF_TREENODE` 或其他类型硬编码为跨版本规则。

用户未指定子目录时，`parentFolderId` 直接使用 `"TASKS"`。用户明确指定子目录时，按名称或路径从 `TASKS` 下查询，并核实节点类型与写权限；计划目录同理，根节点为 `SCHEDULES`。

查询指定子目录时，将以下内容写入 `task_folder.json`：

```json
{
  "listDescendantCatalogsReq": {
    "pids": ["TASKS"],
    "types": ["DEFAULT_TREENODE"],
    "purviewType": "WRITE",
    "limit": -1
  }
}
```

```bash
smartbi call catalogtree.listDescendantCatalogs --profile <PROFILE> -d @task_folder.json --agent
```

- `limit=-1` 按当前契约返回全部匹配节点；按用户指定的名称和完整路径消歧，不能静默取第一项。
- 无匹配或无写权限时说明原因，不改存到其他目录。

> `parentFolderId` 已在 YAML `required` 数组中。调用时缺 `parentFolderId` 服务端会报错。

### script 字段处理（必须 使用 inject-script 工具）

**禁止手工 JSON 转义脚本**。必须 使用 `scripts/scheduled-tasks/inject-script.mjs` 工具完成转义和注入。

**工作流程**：

1. 将 Rhino JS 脚本写入 `.js` 文件（如 `task.js`），内容为原始多行 JS，无需转义
2. 将元数据模板写入 `.json` 文件（如 `task_meta.json`），`script` 字段留空字符串：

```json
{
  "selfDefineTaskUpsertRequest": {
    "name": "daily_report",
    "alias": "每日报表",
    "desc": "每天9:00发送报表",
    "parentFolderId": "<已核实的目录 ID>",
    "type": "SELFDEFINE",
    "script": "",
    "scriptVersion": "2.0"
  }
}
```

3. 调用工具合并：

```bash
node scripts/scheduled-tasks/inject-script.mjs task.js task_meta.json task.json
```

4. 使用合并后的 `task.json` 调用 API：

```bash
smartbi call scheduletask.createSelfDefineTask --profile <PROFILE> -d @task.json --agent
```

> **禁止占位符**：`script` 字段必须包含实际的 Rhino JS 代码字符串，禁止使用 `"..."` 等占位符。
> 服务端会对脚本做非空校验，空内容或 `"..."` 将直接报错。

#### 工具路径

`scripts/scheduled-tasks/inject-script.mjs` 位于本 skill 目录下。使用时需从 skill 根目录解析绝对路径：
- 若当前工作目录不在 skill 目录内，使用绝对路径调用
- 示例：`node /path/to/skills/smartbi-cli/scripts/scheduled-tasks/inject-script.mjs task.js task_meta.json task.json`

### 创建计划

```
POST /api/v1/scheduletask/schedule/create-time-schedule
```

```text
{
  "scheduleUpsertRequest": {
    "name": "<英文名>",
    "alias": "<中文名>",
    "desc": "<描述>",
    "taskIds": "<任务创建返回的 taskId>",
    "timeType": "DAY",
    "startHour": "9",
    "startMinute": "0",
    "cron": "0 0 9 * * ?",
    "creatUsername": "<当前用户名，必填>",
    "creatUserAuth": true,
    "actived": false,
    "retryCount": 0,
    "retryIntervalMinute": 0,
    "enableRange": false,
    "parentFolderId": "SCHEDULES"
  }
}
```

> **`cron` 必须 主动传入有效 Quartz 6 字段表达式**，不要传 `null`/省略。

> **`actived` 创建时设置为 `false`**：先创建并核对计划，再按用户授权单独激活。
> 用户要求启用时才单独调用 `changeScheduleActiveStatus`；要求先保存或保持停用时不激活。操作后回读目标状态。

**全部必填字段**（13 个，按 schema `required` 数组）：`name`, `alias`, `taskIds`, `actived`, `retryCount`, `retryIntervalMinute`, `startHour`, `startMinute`, `timeType`, `creatUserAuth`, `creatUsername`, `enableRange`, `parentFolderId`。

**调度参数约束**：

| 约束 | 说明 |
|------|------|
| `startHour`/`startMinute` **始终必传** | 按当前接口契约填写；值为字符串 `"0"`–`"23"` / `"0"`–`"59"` |
| `cron` **必须 主动传入** | 传入与用户日期、时间要求一致的有效 Quartz 表达式，格式示例见下表 |
| `parentFolderId` **必填** | SmartBI 资源为树状结构，必须指定计划存放的目录。计划根节点 ID 为 `SCHEDULES`，可直接使用 `"SCHEDULES"`；用户明确要求子目录时再调用 `catalogtree.listDescendantCatalogs`，按名称/路径匹配并核实写权限，不能静默取任意第一项；目录类型以目标环境契约为准 |
| `creatUsername` **必须用当前用户真实名称** | 不能硬编码 `"admin"`。通过当前环境已注册的当前用户接口核实；服务端脚本中可使用 `context.get("userName")` |

**`timeType` 与 `cron` 格式示例**（周一和每月 1 日仅为示例，执行日取自用户需求，不是默认值）：

| timeType | startHour/Minute | cron 推荐格式 |
|----------|:---:|:---|
| `DAY` | 必传 | `0 {minute} {hour} * * ?` |
| `WEEK` | 必传 | `0 {minute} {hour} ? * MON` |
| `MONTH` | 必传 | `0 {minute} {hour} 1 * ?` |
| `BYHAND` | 必传 | 任意有效 Quartz 6 字段 |

> 调度日及时间只使用当前接口支持的字段表达，不自行增加 `weekDay`、`monthDay` 等未声明字段；回读核实实际调度时间。

### 启用计划

```
POST /api/v1/scheduletask/schedule/change-schedule-active-status
```

```json
{
  "scheduleActiveStatusRequest": {
    "scheduleId": "<计划创建返回的 scheduleId>",
    "actived": true
  }
}
```

## 创建后验证（必须）

任务创建成功后，**必须**立即调用 `scheduletask.getTaskById` 验证：

```bash
smartbi call scheduletask.getTaskById --profile <PROFILE> -d @task_verify.json --agent
```

其中 `task_verify.json` 内容为 `{"id": "<taskId>"}`。

检查项：
- `script` 字段**非空**且不是 `"..."` 等占位符——若为空则说明脚本未正确注入，需终止流程
- 使用当前目录接口按同一任务 ID 核实 `pid` 及所属路径，确认位于 TASKS 或用户指定的可写子目录；不把请求中的目录值当作执行后的目录证据。
- `type` 为 `SELFDEFINE`

若验证失败，不创建或激活后续计划，报告错误原因。

### 计划激活验证

计划激活验证使用 `scheduletask.getScheduleDtoById`（而非 `getScheduleById`），返回更完整的字段映射：

```bash
smartbi call scheduletask.getScheduleDtoById --profile <PROFILE> -d @schedule_verify.json --agent
```

检查 `actived`、绑定任务及调度时间是否与用户要求一致；不一致时报告原始状态和受影响范围，重试遵循公共幂等规则，不设置额外的激活重试循环。

## 推送（可选）

用户明确要求通知时，先通过 `push.listPushChannels` 核实目标环境的 `channelId` 与可用性，再按 已保留的消息发送模块 核实接收人标识和当前 `push.sendMessage` 契约。只说“通知我”而渠道或接收人仍有歧义时，应先澄清。多渠道逐个确认，不推断企微、钉钉、邮件或飞书一定已配置。

`push.sendMessage` 接收 `multipart/form-data`：表单项 `sendMessageRequest` 内含 `channelId`、`message`、`config`，按渠道填写 `recipients`。不能在 Rhino 中直接用 `httpPostJson` 发送旧版 `channelType/content/title` JSON。`references/scheduled-tasks/rhino-script-template.md` 给出站内消息请求示例；其他渠道须按本环境 `describe`、渠道能力和真实收件人重新核对。

任务脚本须同时检查 HTTP、外层 `success` 和 `result.status`，失败就使任务失败；仅收到任务 ID 不代表送达。执行后用 `scheduletask.getTaskExecutionLogs` 核对任务状态，推送未完成时再用 `push.getSendProgress` 查询。不要把失败任务报告为发送成功。

## 非 MQL 任务

报表导出、JSON/SQL 取数及 ETL 任务使用已选业务场景的 SDK 接口和当前契约构造脚本，不套用 MQL 模板，也不预置未核实的 `execute` 或 RMI 方法签名。缺少所需接口或脚本运行能力时说明限制，不创建不能完成业务的计划。
