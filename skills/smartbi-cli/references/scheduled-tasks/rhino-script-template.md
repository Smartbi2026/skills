# MQL 取数 — Rhino 1.7R2 脚本模板

本文件是 `scenarios/scheduled-tasks.md` 共享的 Rhino JS 代码模板，只在定时任务已选定 MQL 路径时使用；不是外部即时模型查询入口。

`<...>` 占位符由 agent 根据用户问句和已核实契约填入。本模板只在任务实际需要服务端脚本时使用，普通外部取数走数据查询路径，不创建计划或任务。

## 完整模板

```js
// === <任务名称> ===
// 运行时自动注入: logger, context, connector

var print = (typeof logger !== "undefined")
    ? function(m) { logger.info(String(m)); }
    : function(m) { java.lang.System.out.println(String(m)); };

// BASE_URL：优先从环境变量 SMARTBI_SDK_BASE_URL 获取，不存在时使用占位值
var BASE_URL = java.lang.System.getenv("SMARTBI_SDK_BASE_URL") || "<SDK_API_BASE_URL>";
if (!/^https?:\/\//.test(String(BASE_URL)) || String(BASE_URL).indexOf("<") >= 0) {
    throw new Error("任务缺少有效 SDK 地址");
}
var newline = String.fromCharCode(10);

// ===== Token 获取 =====
// 按任务已确认的凭证来源填 ENV 或 TEMP_TOKEN，不在一种来源失败后自动切换。
var TOKEN_SOURCE = "<TOKEN_SOURCE>";
var TOKEN;
if (TOKEN_SOURCE === "ENV") {
    TOKEN = java.lang.System.getenv("<TOKEN_ENV_NAME>");
} else if (TOKEN_SOURCE === "TEMP_TOKEN") {
    // 仅在当前运行环境支持且已授权时选择此方式。
    var expireTime = java.lang.System.currentTimeMillis() + 30 * 60 * 1000;
    var tokenResult = connector.remoteInvoke("UserService", "generateTempToken", [expireTime]);
    if (!tokenResult || !tokenResult.getResult()) throw new Error("无法取得任务使用的临时令牌");
    TOKEN = tokenResult.getResult().toString();
} else {
    throw new Error("任务凭证来源必须明确为 ENV 或 TEMP_TOKEN");
}
if (!TOKEN || String(TOKEN).indexOf("<") >= 0) throw new Error("任务缺少有效凭证");
var MODEL_ID = "<MODEL_ID>";

// ===== HTTP POST (Java 桥接) =====
function httpPostJson(url, token, body) {
    var c = new java.net.URL(url).openConnection();
    c.setRequestMethod("POST");
    c.setDoOutput(true); c.setDoInput(true);
    c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
    c.setRequestProperty("Authorization", "Bearer " + token);
    c.setConnectTimeout(30000); c.setReadTimeout(120000);
    var w = new java.io.OutputStreamWriter(c.getOutputStream(), "UTF-8");
    w.write(body); w.flush(); w.close();
    var status = c.getResponseCode();
    var s = status == 200 ? c.getInputStream() : c.getErrorStream();
    if (!s) { c.disconnect(); return { code: status, body: "" }; }
    var r = new java.io.BufferedReader(new java.io.InputStreamReader(s, "UTF-8"));
    var sb = new java.lang.StringBuilder(); var l;
    while ((l = r.readLine()) != null) sb.append(l);
    r.close(); c.disconnect();
    return { code: status, body: sb.toString() };
}

// ===== MQL 查询 =====
// 仅用于已确认 dataTable 可覆盖每批结果的接口；预览/文件接口需按契约生成独立下载流程。
// scope=all 时批量取齐，scope=topn 时 limit 是用户明确的结果上限。
function arrayLength(a) {
    if (typeof a.length === "number") return a.length;
    if (typeof a.length === "function") return a.length();
    if (typeof a.size === "function") return a.size();
    throw new Error("无法读取查询结果数组长度");
}
function arrayItem(a, i) {
    return typeof a.get === "function" ? a.get(i) : a[i];
}
function queryData(dims, metrics, opt) {
    opt = opt || {};
    if (opt.inlineCompleteVerified !== true) {
        throw new Error("尚未确认 dataTable 批次完整性，不能据此交付或推送");
    }
    var limit = Number(opt.limit);
    var maxPages = Number(opt.maxPages);
    if (!(limit > 0) || Math.floor(limit) !== limit ||
        !(maxPages > 0) || Math.floor(maxPages) !== maxPages) {
        throw new Error("limit 和 maxPages 必须是正整数");
    }
    if (opt.scope !== "all" && opt.scope !== "topn") {
        throw new Error("必须明确 all 或用户指定的 topn 范围");
    }
    if (!opt.sort || !opt.sort.length) {
        throw new Error("需要按模型粒度确认的稳定排序；TopN 按目标指标排序");
    }
    var offset = opt.offset == null ? 0 : Number(opt.offset);
    if (offset !== 0) throw new Error("本完整交付模板从 offset=0 开始");
    var allRows = [], headers = null, headerSignature = null, seenPages = {};
    for (var page = 0; page < maxPages; page++) {
        var mql = { dims: dims, metrics: metrics, sort: opt.sort,
            limit: new java.lang.Integer(limit), offset: new java.lang.Integer(page * limit) };
        if (opt.from) mql.from = opt.from;
        if (opt.dimFilter) mql.dimFilter = opt.dimFilter;
        if (opt.metricFilter) mql.metricFilter = opt.metricFilter;
        var payload = { req: { modelId: MODEL_ID, modelType: "<MODEL_TYPE>",
            showDataTable: true, mql: mql, params: opt.params || [] } };
        var body = Packages.smartbi.net.sf.json.JSONObject.fromObject(payload).toString();
        var resp = httpPostJson(BASE_URL + "/api/v1/datamodel/datamodel/query-data-by-mql", TOKEN, body);
        if (resp.code !== 200) throw new Error("MQL HTTP " + resp.code);
        var obj = Packages.smartbi.net.sf.json.JSONObject.fromObject(resp.body);
        if (!obj.optBoolean("success", false)) {
            throw new Error("MQL 业务失败，停止当前任务；核对权限、字段或服务端日志，不自动切换文件查询");
        }
        var result = obj.optJSONObject("result");
        var dt = result && result.optJSONObject("dataTable");
        var rows = dt && dt.optJSONArray("data");
        var cols = dt && dt.optJSONArray("headers");
        if (!rows || !cols || arrayLength(rows) > limit) {
            throw new Error("批次数据缺失或超出请求行数，禁止交付部分结果");
        }
        var currentHeaders = [];
        for (var h = 0; h < arrayLength(cols); h++) currentHeaders.push(String(arrayItem(cols, h)));
        if (headerSignature !== null && headerSignature !== JSON.stringify(cols)) {
            throw new Error("分页字段发生变化，禁止拼接");
        }
        headers = currentHeaders;
        headerSignature = JSON.stringify(cols);
        var signature = JSON.stringify(rows);
        if (arrayLength(rows) && seenPages[signature]) throw new Error("检测到重复页，无法证明完整性");
        seenPages[signature] = true;
        for (var i = 0; i < arrayLength(rows); i++) {
            var row = arrayItem(rows, i), values = [];
            if (arrayLength(row) !== headers.length) throw new Error("行列宽度不一致");
            for (var j = 0; j < arrayLength(row); j++) values.push(arrayItem(row, j));
            allRows.push(values);
        }
        if (opt.scope === "topn" || arrayLength(rows) < limit) {
            return Packages.smartbi.net.sf.json.JSONObject.fromObject({
                rowCount: allRows.length, s3Url: "", dataTable: { headers: headers, data: allRows }
            });
        }
    }
    throw new Error("达到本任务执行批数预算但未取齐，已取 " + allRows.length + " 行；禁止作为成功结果推送");
}

// ===== dataTable → HTML 表格 =====
function escapeHtml(value) {
    return String(value == null ? "" : value)
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function buildTableHtml(dt) {
    var html = "<table border='1' cellpadding='4' cellspacing='0'>";
    html += "<tr style='background-color:#f0f0f0'>";
    var headers = dt.optJSONArray("headers");
    if (headers) {
        for (var i = 0; i < arrayLength(headers); i++) {
            html += "<th>" + escapeHtml(arrayItem(headers, i)) + "</th>";
        }
    }
    html += "</tr>";
    var rows = dt.optJSONArray("data");
    if (rows) {
        for (var r = 0; r < arrayLength(rows); r++) {
            html += "<tr>";
            var row = arrayItem(rows, r);
            for (var c = 0; c < arrayLength(row); c++) {
                html += "<td>" + escapeHtml(arrayItem(row, c)) + "</td>";
            }
            html += "</tr>";
        }
    }
    html += "</table>";
    return html;
}

// ===== 推送（仅在用户要求且已核实渠道和接收人后启用） =====
// push.sendMessage 使用 multipart/form-data，不能复用上面的 httpPostJson。
// 下例为站内消息请求；其他渠道按当前环境契约构造。
function pushMessage(channelId, subject, content, contentType, recipients, config) {
    var request = {
        channelId: channelId,
        message: { subject: subject, content: content, contentType: contentType },
        recipients: recipients,
        config: config || {}
    };
    var json = Packages.smartbi.net.sf.json.JSONObject.fromObject(request).toString();
    var boundary = "----smartbi" + String(java.util.UUID.randomUUID()).replace(/-/g, "");
    var body = "--" + boundary + "\r\n" +
        "Content-Disposition: form-data; name=\"sendMessageRequest\"\r\n" +
        "Content-Type: application/json\r\n\r\n" + json + "\r\n" +
        "--" + boundary + "--\r\n";
    var c = new java.net.URL(BASE_URL + "/api/v1/push/push/send-message").openConnection();
    c.setRequestMethod("POST"); c.setDoOutput(true); c.setDoInput(true);
    c.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
    c.setRequestProperty("Authorization", "Bearer " + TOKEN);
    c.setConnectTimeout(30000); c.setReadTimeout(60000);
    var w = new java.io.OutputStreamWriter(c.getOutputStream(), "UTF-8");
    w.write(body); w.flush(); w.close();
    var code = c.getResponseCode();
    var stream = code == 200 ? c.getInputStream() : c.getErrorStream();
    var r = new java.io.BufferedReader(new java.io.InputStreamReader(stream, "UTF-8"));
    var b = new java.lang.StringBuilder(), line;
    while ((line = r.readLine()) != null) b.append(line);
    r.close(); c.disconnect();
    if (code != 200) throw new Error("推送 HTTP " + code);
    var response = Packages.smartbi.net.sf.json.JSONObject.fromObject(String(b));
    var result = response.optJSONObject("result");
    if (!response.optBoolean("success", false) || !result || result.optString("status") != "SUCCESS") {
        throw new Error("推送未送达: " + (result ? result.optString("status") : "无状态"));
    }
    var channelResult = result.optJSONObject("channelResult");
    var sent = channelResult && channelResult.optJSONArray("sent");
    var failed = channelResult && channelResult.optJSONArray("failed");
    function countItems(a) {
        return !a ? 0 : typeof a.length === "number" ? a.length :
            typeof a.length === "function" ? a.length() : a.size();
    }
    if (countItems(sent) < 1 || countItems(failed) > 0) {
        throw new Error("推送未确认目标送达");
    }
    return result.optString("platformTaskId", "");
}

// ===== 主流程 =====
try {
    print("开始: <任务名称>");

    var result = queryData(
        [<DIMS>],        // 示例: "业务机构名称", "年月"
        [<METRICS>],     // 示例: "贷款余额", "不良率"
        {
            // dimFilter: "<SQL过滤>",   // 示例: "贷款余额 > 200000"
            sort: [["<SORT_FIELD>", "DESC"]],
            limit: <QUERY_LIMIT>,
            maxPages: <MAX_PAGES>,
            scope: "<QUERY_SCOPE>",
            inlineCompleteVerified: <INLINE_COMPLETE_VERIFIED>
        }
    );

    if (result) {
        var rowCount = result.optInt("rowCount", 0);
        var dt = result.optJSONObject("dataTable");
        var html = "<h3><任务名称></h3>" + newline + buildTableHtml(dt);
        // 此处 rowCount 是本模板已拼接的交付行数；接口原始 rowCount 不保证等于本页行数。
        var markdown = "### <任务名称>\n\n" + "- 已校验结果行数: " + rowCount;
        context.put("resultTitle", "<任务名称>");
        context.put("resultContent", html);
        context.put("resultIsHtml", true);
        print("完成, deliveredRows=" + rowCount);

        // ===== 推送（可选） =====
        // 已核实 channelId 为 message、接收人是当前 SmartBI 用户时，可启用：
        // pushMessage("message", "<任务名称>", markdown, "PLAIN",
        //     [{type: "USER", targetId: "<已核实的用户ID>"}], {});
        // 其他渠道先调用 push.listPushChannels，并核实当前渠道配置和接收人格式。
    }
} catch (e) { logger.error("异常: " + (e.message || e)); throw e; }
```

## 占位符说明

| 占位符 | 来源 | 说明 |
|--------|------|------|
| `<任务名称>` | 自动生成 | 如 "每日贷款质量分析" |
| `<SDK_API_BASE_URL>` | 已核实的连接 | SDK API 根地址：直连 SmartBI 为配置 baseUrl 加 `/sdk`；sdk-server 使用其根地址。以当前契约核对，环境变量必须指向同一根地址 |
| `<TOKEN_SOURCE>` | 已确认的凭证方式 | `ENV` 使用环境变量；`TEMP_TOKEN` 仅用于已核实支持并授权的运行环境；失败时停止，不自动换来源 |
| `<TOKEN_ENV_NAME>` | 环境变量名称 | 选择 `ENV` 时必须指向实际可用的令牌变量，不填变量内容 |
| `<MODEL_TYPE>` | 当前模型元数据 | 不固定为某一种模型类型 |
| `<MODEL_ID>` | 数据模型 ID | 通过问句检索或用户提供 |
| `<DIMS>` | 从已核实的模型元数据提取维度标识，必要时补字段树确认层级路径 | 如 `"年"`, `"产品类别"`；需要来源限定时使用完整层级标识，不猜字段名 |
| `<METRICS>` | 从已核实的模型元数据提取度量标识 | 如 `"销售额"`, `"订单量"`；不把普通数值字段自行提升为度量 |
| `<QUERY_LIMIT>` | 问句与规模 | all 模式批量大小；topn 模式为用户明确的 N，不固定100行作为全量 |
| `<MAX_PAGES>` | 任务运行预算 | 正整数；达到预算仍未取齐时任务失败，不交付部分结果 |
| `<QUERY_SCOPE>` | 用户范围 | all 或 topn；不能为避免分页擅自改成topn |
| `<INLINE_COMPLETE_VERIFIED>` | 当前接口契约及验证 | 仅确认dataTable覆盖批次结果后填true；预览或仅文件模式另生成已验证下载流程，不盲设true |
| `<SORT_FIELD>` | 问句与模型粒度 | TopN 按目标指标；分页需唯一稳定排序，必要时扩展sort为多个已核实字段，不默认只按金额排序 |
| `dimFilter` | 问句中的过滤条件 | 如 `"贷款余额 > 200000"`（SQL 语法，字符串用单引号，内部单引号双写 `'it''s'`） |

### 推送参数

`channelId` 来自当前环境 `push.listPushChannels`；站内消息示例为 `message`。`recipients` 使用当前渠道核实的 `{type, targetId}` 对象，不把用户显示名当成 ID。推送成功以 `result.status` 和送达数量为准；未完成时通过当前 `push.getSendProgress` 契约按返回的 `platformTaskId` 查询进度；发送任务须同时保留消息发送模块。

## 脚本注入方式

模板代码写入 `.js` 文件后，**使用 `scripts/scheduled-tasks/inject-script.mjs` 工具**自动完成 JSON 转义并注入请求体。
详见 `scenarios/scheduled-tasks.md`「script 字段处理」章节。

**必须 使用 inject-script 工具**，禁止手动 JSON.stringify 或手写转义。工具会自动处理换行、引号、反斜杠等转义字符。

### 如需在脚本中使用特殊字符

HTML 输出中的换行由模板的 `newline` 变量表示；完整脚本通过注入工具进行 JSON 编码。

## 注意事项

- **查询与交付**：模板仅用于已验证可完整分页的内联结果。业务失败直接使任务失败，不自动改成文件请求；文件模式须单独按当前契约实现下载、识别、完整性校验后才交付，不把 s3Url 当作已交付文件。
- **分页边界**：all 模式固定页长与唯一稳定排序，满批继续、短批结束；TopN按用户明确N停止。重复页、字段或行数异常、超过任务批数预算均抛错，禁止执行后续成功推送。无法维持稳定数据快照时仍须披露完整性限制。
- **参数来源**：任务脚本所用的渠道、接收人、凭证和模型字段都需按目标环境核实。其他渠道不能照搬站内消息的接收人格式。
- sdk-server 路径为 `/api/v1/datamodel/datamodel/query-data-by-mql`（双 datamodel）
- 模型元数据遵循已由主入口组合的模型取数场景的统一规则，按定义与 MQL 契约核对字段层级和来源标识。不得把内部 `name`、物理列名直接当作查询标识，字段树不能代替参数定义。
- 跨来源维度与指标能否组合，以当前模型关联和口径为准；异常重复或汇总放大时停止交付该结论
- **push API 路径**：
  - 以目标环境 `describe push.sendMessage` 为准，核对 SDK 路径与请求契约。
  - SmartBI 的 SDK 根地址是配置 baseUrl 加 `/sdk`，sdk-server 则使用配置根地址；不因 serverType 改写 operation 的路径段。
- `dimFilter` SQL 字符串值用单引号括起，内部单引号双写转义
