#!/usr/bin/env python3
"""通过 SmartBI CLI 执行和检查白泽会话。

请求体使用临时 JSON 文件，命令结束后清理；不读取或打印 SmartBI 凭证。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

SMARTBI_CMD = "smartbi.cmd" if os.name == "nt" else "smartbi"

def _artifact_helpers():
    helper_dir = Path(__file__).resolve().parents[1] / "common-core"
    if not (helper_dir / "artifact_io.py").is_file():
        raise RuntimeError("文件下载需要保留 scripts/common-core/artifact_io.py；不下载文件时可省略该辅助模块")
    sys.path.insert(0, str(helper_dir))
    from artifact_io import download_artifacts, find_artifacts
    return download_artifacts, find_artifacts


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _run(command: list[str], *, stdout_path: Path | None = None, config: Path | None = None) -> subprocess.CompletedProcess[str]:
    if config is not None:
        command = [*command, "--config", str(config)]
    if stdout_path is None:
        return subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)
    with stdout_path.open("w", encoding="utf-8") as output:
        return subprocess.run(command, text=True, encoding="utf-8", errors="replace", stdout=output, stderr=subprocess.PIPE, check=False)


def _call_json(profile: str, operation: str, body_path: Path, *, config: Path | None = None) -> dict[str, Any]:
    result = _run(
        [
            SMARTBI_CMD,
            "call",
            operation,
            "--profile",
            profile,
            "-d",
            f"@{body_path}",
            "--json",
        ],
        config=config,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{operation} 执行失败，退出码 {result.returncode}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{operation} 返回内容不是 JSON") from exc
    if payload.get("ok") is not True or int(payload.get("status") or 0) >= 400:
        raise RuntimeError(f"{operation} 调用失败：status={payload.get('status')}")
    business = payload.get("data")
    if isinstance(business, dict) and business.get("success") is False:
        raise RuntimeError(f"{operation} 返回业务失败；请根据响应排查，不将 HTTP 200 当作成功")
    return payload


def _round_summary(payload: dict[str, Any]) -> dict[str, Any]:
    rounds = (((payload.get("data") or {}).get("result")) or [])
    return {
        "round_count": len(rounds),
        "rounds": [
            {
                "id": item.get("id"),
                "status": item.get("status"),
                "errorType": item.get("errorType"),
                "duration": item.get("duration"),
                "question": item.get("question"),
                "queryType": item.get("queryType"),
            }
            for item in rounds
            if isinstance(item, dict)
        ],
    }


def _logs_summary(payload: dict[str, Any], query_id: str | None = None) -> dict[str, Any]:
    logs = (((payload.get("data") or {}).get("result")) or [])
    if query_id:
        logs = [item for item in logs if isinstance(item, dict) and item.get("queryId") == query_id]
    return {
        "log_count": len(logs),
        "query_ids": sorted(
            {str(item.get("queryId")) for item in logs if isinstance(item, dict) and item.get("queryId")}
        ),
    }


def _conversation_payload(args: argparse.Namespace, conv_id: str, rpc_id: str, message_id: str) -> dict[str, Any]:
    params: list[dict[str, Any]] = [
        {"singleRound": False},
        {"use_personal_knowledge": args.use_personal_knowledge},
        {"webSearch": args.web_search},
        {"crossDatasetQuery": False},
        {"need_inquiry": args.need_inquiry},
        {"is_recommend_dataset": False},
        {"needConfirmPlan": False},
        {"needUpdatePlan": True},
    ]
    if args.llm_config_id:
        params.append({"LLMConfigId": args.llm_config_id})
    if args.skill:
        params.append({"skills": args.skill})

    resource = {"id": args.dataset_id, "name": args.dataset_name, "type": args.dataset_type}
    knowledge = []
    if args.knowledge_file:
        knowledge = json.loads(args.knowledge_file.read_text(encoding="utf-8"))

    return {
        "jsonRpcStreamReq": {
            "jsonrpc": "2.0",
            "method": "message/stream",
            "id": rpc_id,
            "params": {
                "message": {
                    "messageId": message_id,
                    "kind": "message",
                    "role": "user",
                    "metadata": {
                        "agentId": args.agent_id,
                        "convId": conv_id,
                        "selectedResources": [resource],
                        "datasets": [resource],
                        "queryGridData": True,
                        "params": params,
                    },
                    "parts": [
                        {"kind": "text", "text": args.question},
                        {"kind": "knowledge", "knowledge": json.dumps(knowledge, ensure_ascii=False)},
                    ],
                }
            },
        }
    }


def command_run(args: argparse.Namespace) -> int:
    if args.download_artifacts:
        download_artifacts, find_artifacts = _artifact_helpers()
    conv_id = args.conv_id or str(uuid.uuid4())
    rpc_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())
    output_dir = args.out_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "profile": args.profile,
        "convId": conv_id,
        "rpcId": rpc_id,
        "messageId": message_id,
        "agentId": args.agent_id,
        "dataset": {"id": args.dataset_id, "name": args.dataset_name, "type": args.dataset_type},
        "question": args.question,
    }
    _write_json(output_dir / "manifest.json", manifest)

    stream_path = output_dir / "stream.ndjson"
    stderr_path = output_dir / "stream.stderr.txt"
    rounds_path = output_dir / "rounds.json"
    logs_path = output_dir / "chat-logs.json"

    with tempfile.TemporaryDirectory(prefix="smartbi-baize-") as temp_name:
        temp_dir = Path(temp_name)
        create_path = temp_dir / "create.json"
        query_path = temp_dir / "query.json"
        rounds_request_path = temp_dir / "rounds.json"
        logs_request_path = temp_dir / "logs.json"
        _write_json(create_path, {"convId": conv_id})
        _write_json(query_path, _conversation_payload(args, conv_id, rpc_id, message_id))
        _write_json(rounds_request_path, {"convId": conv_id})
        _write_json(logs_request_path, {"query": {"skip": 0, "limit": args.log_limit, "convId": conv_id}})

        if not args.conv_id:
            created = _call_json(args.profile, "aichat.createConversation", create_path, config=args.config)
            if ((created.get("data") or {}).get("success")) is not True:
                raise RuntimeError("createConversation 返回的 data.success 不是 true")

        stream_result = _run(
            [
                SMARTBI_CMD,
                "call",
                "aichat.queryRpc",
                "--profile",
                args.profile,
                "-d",
                f"@{query_path}",
                "--stream",
                "--max-events",
                str(args.max_events),
                "--timeout",
                str(args.timeout_ms),
                "--agent",
            ],
            stdout_path=stream_path,
            config=args.config,
        )
        stderr_path.write_text(stream_result.stderr or "", encoding="utf-8")

        artifact_results: list[dict[str, Any]] = []
        if args.download_artifacts and stream_result.returncode == 0:
            artifacts = find_artifacts(stream_path)
            artifact_dir = args.artifact_dir or (output_dir / "artifacts")
            downloaded = download_artifacts(
                args.profile,
                artifacts,
                artifact_dir,
                operation=args.artifact_operation,
                request_field=args.artifact_request_field,
                overwrite=args.artifact_overwrite,
                config=args.config,
            )
            artifact_results = [
                {
                    "name": artifact.name,
                    "path": str(path),
                    "bytes": path.stat().st_size,
                }
                for artifact, path in zip(artifacts, downloaded)
            ]

        rounds = _call_json(args.profile, "aichat.getConversationRounds", rounds_request_path, config=args.config)
        logs = {"data": {"result": []}}
        if args.collect_logs:
            logs = _call_json(args.profile, "aichat.queryChatLogs", logs_request_path, config=args.config)
        _write_json(rounds_path, rounds)
        if args.collect_logs:
            _write_json(logs_path, logs)

    round_items = ((rounds.get("data") or {}).get("result")) or []
    current_rounds = [
        item for item in round_items if isinstance(item, dict)
        and message_id in {item.get("id"), item.get("queryId"), item.get("messageId")}
    ]
    if not args.conv_id and not current_rounds and len(round_items) == 1 and isinstance(round_items[0], dict):
        current_rounds = round_items
    current_states = [str(item.get("status") or "").upper() for item in current_rounds]
    execution_failed = any(state in {"ERROR", "FAILED", "INTERRUPTED"} for state in current_states)
    execution_complete = bool(current_states) and all(state == "NORMAL" for state in current_states)
    summary = {
        "ok": stream_result.returncode == 0 and execution_complete,
        "ok_scope": "transport_and_current_round_status_only",
        "transport_ok": stream_result.returncode == 0,
        "current_round_states": current_states,
        "business_result": "failed" if execution_failed else (
            "requires_answer_and_tool_result_review" if execution_complete else "pending_or_unknown"
        ),
        "logs_collected": args.collect_logs,
        "convId": conv_id,
        "rpcId": rpc_id,
        "messageId": message_id,
        "stream_exit": stream_result.returncode,
        "output_dir": str(output_dir),
        "artifacts": artifact_results,
        **_round_summary(rounds),
        **_logs_summary(logs),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if stream_result.returncode != 0 or execution_failed:
        return 1
    return 0 if execution_complete else 2


def command_rounds(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="smartbi-baize-") as temp_name:
        request_path = Path(temp_name) / "rounds.json"
        _write_json(request_path, {"convId": args.conv_id})
        payload = _call_json(args.profile, "aichat.getConversationRounds", request_path, config=args.config)
    if args.output:
        _write_json(args.output, payload)
    print(json.dumps(_round_summary(payload), ensure_ascii=False, indent=2))
    return 0


def command_logs(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="smartbi-baize-") as temp_name:
        request_path = Path(temp_name) / "logs.json"
        _write_json(request_path, {"query": {"skip": 0, "limit": args.limit, "convId": args.conv_id}})
        payload = _call_json(args.profile, "aichat.queryChatLogs", request_path, config=args.config)
    if args.query_id:
        result = (((payload.get("data") or {}).get("result")) or [])
        payload["data"]["result"] = [
            item for item in result if isinstance(item, dict) and item.get("queryId") == args.query_id
        ]
    if args.output:
        _write_json(args.output, payload)
    print(json.dumps(_logs_summary(payload), ensure_ascii=False, indent=2))
    return 0


def command_resume(args: argparse.Namespace) -> int:
    with tempfile.TemporaryDirectory(prefix="smartbi-baize-") as temp_name:
        request_path = Path(temp_name) / "resume.json"
        _write_json(request_path, {"req": {"convId": args.conv_id}})
        result = _run(
            [
                SMARTBI_CMD,
                "call",
                "aichat.queryRpcResume",
                "--profile",
                args.profile,
                "-d",
                f"@{request_path}",
                "--stream",
                "--max-events",
                str(args.max_events),
                "--timeout",
                str(args.timeout_ms),
                "--agent",
            ],
            stdout_path=args.output,
            config=args.config,
        )
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    run = subparsers.add_parser("run", help="创建会话、执行一次问数并收集结果证据")
    run.add_argument("--profile", required=True)
    run.add_argument(
        "--agent-id",
        default="customagent_AGENT_DATA_INSIGHT_ASSISTANT",
        help="智能体 ID（默认使用白泽数据洞察智能体）",
    )
    run.add_argument("--dataset-id", required=True)
    run.add_argument("--dataset-name", required=True)
    run.add_argument("--dataset-type", required=True, help="按目标元数据和 queryRpc 契约核实的真实资源类型")
    run.add_argument("--question", required=True)
    run.add_argument("--conv-id")
    run.add_argument("--llm-config-id")
    run.add_argument("--skill", action="append", default=[])
    run.add_argument("--knowledge-file", type=Path)
    run.add_argument("--use-personal-knowledge", action="store_true")
    run.add_argument("--web-search", action="store_true")
    run.add_argument("--need-inquiry", action="store_true")
    run.add_argument("--timeout-ms", type=int, default=900000)
    run.add_argument("--max-events", type=int, default=2000)
    run.add_argument("--log-limit", type=int, default=500)
    run.add_argument("--collect-logs", action="store_true", help="按需保存会话日志；默认仅回读轮次")
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument(
        "--download-artifacts",
        action="store_true",
        help="下载已完成 SSE 流中的文件交付物",
    )
    run.add_argument(
        "--artifact-dir",
        type=Path,
        help="文件下载目录（默认 <out-dir>/artifacts）",
    )
    run.add_argument(
        "--artifact-operation",
        default="aichat.downloadQueryResult",
        help="二进制下载操作（默认 aichat.downloadQueryResult）",
    )
    run.add_argument(
        "--artifact-request-field",
        default="filePath",
        help="下载请求字段（S3 CGI 操作使用 s3Uri）",
    )
    run.add_argument(
        "--artifact-overwrite",
        action="store_true",
        help="允许覆盖已有交付文件",
    )
    run.set_defaults(func=command_run)

    rounds = subparsers.add_parser("rounds", help="检查会话轮次")
    rounds.add_argument("--profile", required=True)
    rounds.add_argument("--conv-id", required=True)
    rounds.add_argument("--output", type=Path)
    rounds.set_defaults(func=command_rounds)

    logs = subparsers.add_parser("logs", help="检查会话聊天日志")
    logs.add_argument("--profile", required=True)
    logs.add_argument("--conv-id", required=True)
    logs.add_argument("--query-id")
    logs.add_argument("--limit", type=int, default=500)
    logs.add_argument("--output", type=Path)
    logs.set_defaults(func=command_logs)

    resume = subparsers.add_parser("resume", help="继续已中断的 SSE 会话")
    resume.add_argument("--profile", required=True)
    resume.add_argument("--conv-id", required=True)
    resume.add_argument("--timeout-ms", type=int, default=900000)
    resume.add_argument("--max-events", type=int, default=2000)
    resume.add_argument("--output", type=Path, required=True)
    resume.set_defaults(func=command_resume)
    for action in (run, rounds, logs, resume):
        action.add_argument("--config", type=Path, help="已指定的 SmartBI CLI 配置文件路径")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
