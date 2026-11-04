#!/usr/bin/env python3
"""管理 SmartBI 智能体工作流和工具 Provider。

内部接口仅在标准 SDK 缺少所需能力且当前契约已核实时使用。
认证头从环境变量读取；修改默认预览，提交须校验哈希、备份并回读。
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {"authorization", "cookie", "password", "secret", "token", "credential"}
AGENT_EDITABLE_FIELDS = ("name", "alias", "desc", "define", "setting")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[已隐藏]" if key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def headers_from_environment(items: list[str]) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    for item in items:
        if "=" not in item:
            raise ValueError("--header-env 必须为 HTTP_HEADER=ENV_VAR")
        header, environment_name = item.split("=", 1)
        if not header or not environment_name or any(c in header for c in "\r\n"):
            raise ValueError("请求头或环境变量名无效")
        value = os.environ.get(environment_name)
        if value is None:
            raise ValueError(f"环境变量 {environment_name!r} 未设置")
        if any(c in value for c in "\r\n"):
            raise ValueError(f"环境变量 {environment_name!r} 含换行符")
        headers[header] = value
    return headers


class Client:
    def __init__(self, base_url: str, header_env: list[str], timeout: float):
        base = base_url.rstrip("/")
        parsed = urllib.parse.urlsplit(base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("请提供不含凭证、查询参数和片段的 SmartBI 根地址")
        if not parsed.path or parsed.path == "/":
            base += "/smartbi"
        self.prefix = base + "/smartbix/api/dataagent"
        self.headers = headers_from_environment(header_env)
        self.timeout = timeout

    def request(self, method: str, path: str, body: Any = None, *, content_type: str = "application/json") -> Any:
        headers = dict(self.headers)
        data = None
        if body is not None:
            headers["Content-Type"] = content_type
            if content_type.startswith("application/json"):
                data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                data = body.encode("utf-8")
            else:
                data = bytes(body)
        request = urllib.request.Request(self.prefix + path, data=data, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            content = response.read()
            encoding = (getattr(response, "headers", {}) or {}).get("Content-Encoding", "").lower()
            if encoding == "gzip":
                content = gzip.decompress(content)
            raw = content.decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                # 部分部署的创建接口返回未加 JSON 引号的资源 ID。
                value = raw.strip()
                if (path.startswith("/graph/create/") or path == "/tools/create") and re.fullmatch(r"I[0-9a-fA-F]{16,}", value):
                    return value
                raise RuntimeError("内部接口未返回 JSON，需核实地址、认证与当前契约") from exc
        if isinstance(payload, dict):
            if payload.get("success") is False or payload.get("ok") is False:
                raise RuntimeError("内部接口返回业务失败；保留服务端诊断信息，不按 HTTP 成功判断完成")
            if "result" in payload and "code" in payload and str(payload["code"]) != "0":
                raise RuntimeError("内部接口返回非成功业务码，请核实当前契约和服务端错误")
        if isinstance(payload, dict) and str(payload.get("code")) == "0" and "result" in payload:
            return payload["result"]
        return payload


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_agent(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("智能体响应必须是对象")
    if not raw.get("id") and not raw.get("name") and "define" not in raw:
        raise ValueError("响应不含有效智能体定义")
    if isinstance(raw.get("define"), (dict, list)):
        raw = dict(raw)
        raw["define"] = json.dumps(raw["define"], ensure_ascii=False, separators=(",", ":"))
    if "define" in raw:
        try:
            graph = json.loads(raw["define"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("智能体 define 必须是有效 JSON 对象") from exc
        if not isinstance(graph, dict):
            raise ValueError("智能体 define 必须是 JSON 对象")
    return raw


def agent_digest(agent: dict[str, Any]) -> str:
    return canonical_hash({key: agent.get(key) for key in ("id",) + AGENT_EDITABLE_FIELDS})


def graph_summary(agent: dict[str, Any]) -> dict[str, Any]:
    define = agent.get("define")
    graph: dict[str, Any] = {}
    if isinstance(define, str):
        try:
            parsed = json.loads(define)
            if isinstance(parsed, dict):
                graph = parsed
        except json.JSONDecodeError:
            pass
    return {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "alias": agent.get("alias"),
        "sha256": agent_digest(agent),
        "node_count": len(graph.get("nodes") or []),
        "link_count": len(graph.get("links") or graph.get("edges") or []),
    }


def get_agent(client: Client, agent_id: str) -> dict[str, Any]:
    quoted = urllib.parse.quote(agent_id, safe="")
    return normalize_agent(client.request("GET", f"/graph/{quoted}"))


def command_agent_get(args: argparse.Namespace, client: Client) -> int:
    agent = get_agent(client, args.agent_id)
    write_json(args.output, redact(agent))
    print(json.dumps({"ok": True, "output": str(args.output), **graph_summary(agent)}, ensure_ascii=False, indent=2))
    return 0


def command_agent_update(args: argparse.Namespace, client: Client) -> int:
    live = get_agent(client, args.agent_id)
    current_hash = agent_digest(live)
    patch = load_json(args.file)
    if not isinstance(patch, dict):
        raise ValueError("更新补丁必须是对象")
    if "define" in patch:
        patch = normalize_agent(patch)
    if patch.get("id") not in (None, args.agent_id):
        raise ValueError("请求id与--agent-id不一致")

    candidate = dict(live)
    changed_fields: list[str] = []
    for key in AGENT_EDITABLE_FIELDS:
        if key in patch and patch[key] != live.get(key):
            candidate[key] = patch[key]
            changed_fields.append(key)
    candidate["id"] = args.agent_id
    candidate = normalize_agent(candidate)

    result = {
        "ok": True,
        "mode": "apply" if args.apply else "dry-run",
        "agent_id": args.agent_id,
        "current_sha256": current_hash,
        "candidate_sha256": agent_digest(candidate),
        "changed_fields": changed_fields,
        "current": graph_summary(live),
        "candidate": graph_summary(candidate),
    }
    if not args.apply:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if not args.expect_sha256:
        raise ValueError("--apply 需要此前预览返回的 --expect-sha256")
    if args.expect_sha256 != current_hash:
        raise ValueError("智能体在预览后已变化，请重新读取，不能覆盖")
    if not changed_fields:
        raise ValueError("没有可提交的字段变更")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    safe_id = urllib.parse.quote(args.agent_id, safe="")
    backup = args.backup_dir / f"agent-{safe_id}-before-{stamp}.json"
    write_json(backup, redact(live))
    update_result = client.request("POST", "/graph/update", candidate)
    if update_result is not True:
        raise RuntimeError("智能体更新返回异常，未确认更新成功")
    verified = get_agent(client, args.agent_id)
    for key in AGENT_EDITABLE_FIELDS:
        if verified.get(key) != candidate.get(key):
            raise RuntimeError(f"回读字段不一致 {key!r}")
    result.update({"backup": str(backup), "verified": graph_summary(verified)})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_agent_create(args: argparse.Namespace, client: Client) -> int:
    payload = normalize_agent(load_json(args.file))
    missing = [key for key in ("name", "alias", "define") if not payload.get(key)]
    if missing:
        raise ValueError(f"智能体请求缺少必填字段: {', '.join(missing)}")
    preview = {"mode": "apply" if args.apply else "dry-run", "parent_id": args.parent_id, **graph_summary(payload)}
    if not args.apply:
        print(json.dumps({"ok": True, **preview}, ensure_ascii=False, indent=2))
        return 0
    parent = urllib.parse.quote(args.parent_id, safe="")
    created_id = client.request("POST", f"/graph/create/{parent}", payload)
    if not isinstance(created_id, str) or not created_id:
        raise RuntimeError("智能体创建未返回有效资源 ID")
    verified = get_agent(client, created_id)
    for key in AGENT_EDITABLE_FIELDS:
        if key in payload and verified.get(key) != payload[key]:
            raise RuntimeError(f"创建后的回读字段不一致：{key}")
    print(json.dumps({"ok": True, **preview, "created_id": created_id, "verified": graph_summary(verified)}, ensure_ascii=False, indent=2))
    return 0


def command_provider_list(args: argparse.Namespace, client: Client) -> int:
    payload = client.request("POST", "/tools/list", {})
    safe = redact(payload)
    if args.output:
        write_json(args.output, safe)
    count = len(payload) if isinstance(payload, list) else None
    print(json.dumps({"ok": True, "provider_count": count, "output": str(args.output) if args.output else None}, ensure_ascii=False, indent=2))
    return 0


def command_provider_get(args: argparse.Namespace, client: Client) -> int:
    query = urllib.parse.urlencode({"name": args.name})
    payload = client.request("GET", "/tools/getByName?" + query)
    if args.output:
        write_json(args.output, redact(payload))
    summary = {
        "ok": True,
        "id": payload.get("id") if isinstance(payload, dict) else None,
        "name": payload.get("name") if isinstance(payload, dict) else None,
        "type": payload.get("type") if isinstance(payload, dict) else None,
        "tool_count": len(payload.get("tools") or []) if isinstance(payload, dict) else None,
        "output": str(args.output) if args.output else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def command_provider_parse(args: argparse.Namespace, client: Client) -> int:
    definition = args.openapi_file.read_text(encoding="utf-8")
    query = urllib.parse.urlencode({"type": "OPENAPI"})
    payload = client.request("POST", "/tools/parse?" + query, definition, content_type="text/plain; charset=utf-8")
    if args.output:
        write_json(args.output, redact(payload))
    print(json.dumps({"ok": True, "name": payload.get("name") if isinstance(payload, dict) else None, "tool_count": len(payload.get("tools") or []) if isinstance(payload, dict) else None, "output": str(args.output) if args.output else None}, ensure_ascii=False, indent=2))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="已确认的 SmartBI 根地址，例如 https://smartbi.example/smartbi")
    parser.add_argument("--header-env", action="append", default=[], metavar="HTTP_HEADER=ENV_VAR")
    parser.add_argument("--timeout", type=float, default=30.0)
    subparsers = parser.add_subparsers(dest="action", required=True)

    agent_get = subparsers.add_parser("agent-get")
    agent_get.add_argument("--agent-id", required=True)
    agent_get.add_argument("--output", required=True, type=Path)
    agent_get.set_defaults(func=command_agent_get)

    agent_update = subparsers.add_parser("agent-update")
    agent_update.add_argument("--agent-id", required=True)
    agent_update.add_argument("--file", required=True, type=Path)
    agent_update.add_argument("--backup-dir", required=True, type=Path)
    agent_update.add_argument("--expect-sha256")
    agent_update.add_argument("--apply", action="store_true")
    agent_update.set_defaults(func=command_agent_update)

    agent_create = subparsers.add_parser("agent-create")
    agent_create.add_argument("--parent-id", required=True)
    agent_create.add_argument("--file", required=True, type=Path)
    agent_create.add_argument("--apply", action="store_true")
    agent_create.set_defaults(func=command_agent_create)

    provider_list = subparsers.add_parser("provider-list")
    provider_list.add_argument("--output", type=Path)
    provider_list.set_defaults(func=command_provider_list)

    provider_get = subparsers.add_parser("provider-get")
    provider_get.add_argument("--name", required=True)
    provider_get.add_argument("--output", type=Path)
    provider_get.set_defaults(func=command_provider_get)

    provider_parse = subparsers.add_parser("provider-parse")
    provider_parse.add_argument("--openapi-file", required=True, type=Path)
    provider_parse.add_argument("--output", type=Path)
    provider_parse.set_defaults(func=command_provider_parse)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        client = Client(args.base_url, args.header_env, args.timeout)
        return int(args.func(args, client))
    except urllib.error.HTTPError as exc:
        print(json.dumps({"ok": False, "error": "内部接口 HTTP 调用失败", "status": exc.code}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
