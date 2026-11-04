# 消息发送

用户明确要求发送或推送，并给出站内消息、邮件或其他渠道时进入本场景。若同时要求定时执行，由主技能确认当前包含定时任务模块后组合调度与发送；未包含时说明不支持定时发送。没有收件对象、必要的渠道配置或实际发送授权时，先补齐缺项，不猜收件人或群地址。

## 最短执行链

1. 已知渠道 ID 且本任务已核实可用时直接复用；否则调用 `push.listPushChannels`，从 `result.channels` 核对 `channelId`、`available` 和能力。渠道列表因部署而异，不能把渠道显示名或旧版 `channelType` 枚举直接当作 `channelId`。
2. 按 `push.sendMessage` 的当前契约构造 `sendMessageRequest`：`channelId`、`message`、`config` 必填；`recipients` 按渠道和问句提供。`message` 中的 `content`、`contentType` 必填，`subject` 可选。接收人使用当前环境核实的 `{type, targetId}`；用户 ID、显示名和推送目标标识不能随意互换。
3. 将**内部请求对象**写入临时 UTF-8 JSON 文件，使用 `-F sendMessageRequest=@<文件>` 提交 multipart 表单。`-d @<文件>` 提交的是普通 JSON，不符合本接口契约。文件内容不要再套一层 `sendMessageRequest`。
4. 同时检查 CLI `ok`、业务 `success`、`result.status` 及 `channelResult.sent/notSent/failed`。只有实际目标送达才报告发送成功；`success=true`、HTTP 200 或仅有 `platformTaskId` 都不足以证明送达。若状态尚未完成，用返回的 `platformTaskId` 调用 `push.getSendProgress`；失败时报告渠道返回的原因，不盲目重发。

## 站内消息示例

先核实 `push.listPushChannels` 返回 `channelId: "message"` 且 `available: true`，并从当前环境确认接收人标识。以下文件**仅示意单个已确认的接收人**：

```json
{
  "channelId": "message",
  "message": {
    "subject": "业务通知",
    "content": "本次统计已完成。",
    "contentType": "PLAIN"
  },
  "recipients": [{"type": "USER", "targetId": "<当前环境确认的目标标识>"}],
  "config": {}
}
```

```bash
smartbi call push.sendMessage --profile <PROFILE> -F sendMessageRequest=@<绝对路径>.json --agent
```

`contentType` 由当前契约支持 `PLAIN`、`HTML`、`MARKDOWN`；渠道是否实际支持相应格式还要看 `listPushChannels` 的能力。邮件、飞书等渠道只在当前部署列为可用，且收件人与配置已核实时使用；企微、钉钉或其他渠道不能因为旧示例出现过就认定当前环境可用。

进度查询使用同一 SDK 中的 `push.getSendProgress`，当前路径为 `/api/v1/push/push/get-send-progress`：

```json
{"platformTaskId": "<sendMessage 返回的 ID>"}
```

## 定时任务中的推送

Rhino 脚本若直接通过 HTTP 调用推送接口，仍须遵循当前接口的 multipart 请求、消息对象和送达判定；不要沿用旧的 `channelType/content` 普通 JSON 模板。调用前核实脚本运行环境具备表单构造和凭证能力；不具备时不要创建一个必然无法推送的定时任务。

## 补充加载条件

渠道或接收对象缺失时只补齐当前发送所需信息；已知 `push.listPushChannels`、`push.sendMessage`、`push.getSendProgress` 不重新发现同类接口。请求结构不明时核对相应操作契约，附件需要读取时才加载文件处理规则；仅定时发送才由主入口组合定时模块。已准备好的内容不重新启动模型取数或白泽分析。
