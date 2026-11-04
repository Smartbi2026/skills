#!/usr/bin/env python3
"""解析、下载并读取 SmartBI 会话交付文件。

可独立处理已保存的 ``stream.ndjson``；SSE 中的 ``file.uri`` 只有下载并校验后才视为本地文件。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


class ArtifactError(RuntimeError):
    """交付文件无法解析、下载或读取时抛出。"""


@dataclass(frozen=True)
class ArtifactFile:
    """由 ``artifact-update`` SSE 事件声明的文件。"""

    uri: str
    name: str | None = None
    artifact_id: str | None = None
    task_id: str | None = None

    @property
    def source_path(self) -> str:
        """返回下载操作使用的服务端路径。"""

        return self.uri


def _json_event(value: str) -> dict[str, Any] | None:
    """解析一个 SSE 数据段，忽略心跳和非 JSON 内容。"""

    value = value.strip()
    if not value or value == "[DONE]":
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def iter_sse_events(source: Iterable[str]) -> Iterator[dict[str, Any]]:
    """从 SSE 或 CLI ``--stream`` 输出中逐个解析 JSON 事件。

    兼容 CLI 的逐行 ``data:...`` 格式和通用 SSE 客户端的多行事件块；
    注释行与非数据字段会被忽略。
    """

    data_lines: list[str] = []

    def flush() -> Iterator[dict[str, Any]]:
        if not data_lines:
            return
        payload = _json_event("\n".join(data_lines))
        data_lines.clear()
        if payload is not None:
            yield payload

    def decoded_lines() -> Iterator[str]:
        # CLI 外层可能只包含传输分块，未必是完整事件。
        pending = ""
        for raw in source:
            wrapper = _json_event(raw) if raw.lstrip().startswith("{") else None
            chunk = wrapper.get("event") if wrapper else None
            if isinstance(chunk, str):
                pending += chunk
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    yield line + "\n"
            elif wrapper is None:
                yield raw
        if pending:
            yield pending

    for raw_line in decoded_lines():
        line = raw_line.rstrip("\r\n")
        # ``smartbi call --stream`` 将 SSE 分块包在 JSON 外层中：
        # {"schemaVersion":"smartbi.cli.call.stream.v1", "event":"data:..."}.
        # 先拆开 CLI 外层，再将内部事件交给 SSE 解析器。
        if line and not line.startswith((":", "data:")):
            wrapper = _json_event(line)
            wrapped_event = wrapper.get("event") if wrapper else None
            if isinstance(wrapped_event, str):
                yield from iter_sse_events(wrapped_event.splitlines(keepends=True))
            continue
        if line == "":
            yield from flush()
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())

    yield from flush()


def iter_stream_events(stream_path: str | os.PathLike[str]) -> Iterator[dict[str, Any]]:
    """读取已保存的 UTF-8 SSE/NDJSON 流并逐个返回事件。"""

    path = Path(stream_path)
    if not path.is_file():
        raise ArtifactError(f"事件流文件不存在：{path}")
    with path.open("r", encoding="utf-8") as stream:
        yield from iter_sse_events(stream)


def iter_artifacts(events: Iterable[dict[str, Any]]) -> Iterator[ArtifactFile]:
    """从 ``artifact-update`` 事件提取去重后的文件。"""

    seen: set[tuple[str, str | None]] = set()
    for event in events:
        result = event.get("result")
        if not isinstance(result, dict) or result.get("kind") != "artifact-update":
            continue
        artifact = result.get("artifact")
        if not isinstance(artifact, dict):
            continue
        artifact_id = artifact.get("artifactId")
        task_id = result.get("taskId")
        parts = artifact.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict) or part.get("kind") != "file":
                continue
            file_info = part.get("file")
            if not isinstance(file_info, dict):
                continue
            uri = file_info.get("uri")
            if not isinstance(uri, str) or not uri.strip():
                continue
            name = file_info.get("name")
            name = name if isinstance(name, str) and name else None
            key = (uri, name)
            if key in seen:
                continue
            seen.add(key)
            yield ArtifactFile(uri=uri, name=name, artifact_id=artifact_id, task_id=task_id)


def find_artifacts(stream_path: str | os.PathLike[str]) -> list[ArtifactFile]:
    """返回已保存事件流中的全部去重文件。"""

    return list(iter_artifacts(iter_stream_events(stream_path)))


def _safe_output_path(output_dir: Path, artifact: ArtifactFile, index: int) -> Path:
    """根据服务端文件名构造不越过目标目录的保存路径。"""

    candidate = Path(artifact.name or Path(artifact.uri).name or f"artifact-{index}").name
    if candidate in {"", ".", ".."}:
        candidate = f"artifact-{index}"
    return output_dir / candidate


def download_artifact(
    profile: str,
    artifact: ArtifactFile,
    output_path: str | os.PathLike[str],
    *,
    operation: str = "aichat.downloadQueryResult",
    request_field: str = "filePath",
    smartbi_command: str = "smartbi.cmd" if os.name == "nt" else "smartbi",
    overwrite: bool = False,
    config: str | os.PathLike[str] | None = None,
) -> Path:
    """通过 SmartBI CLI 下载一个服务端文件。

    ``operation`` 默认使用会话结果下载接口；不同部署可指定其他二进制下载操作，
    无需更改文件事件解析逻辑。
    """

    destination = Path(output_path)
    if destination.exists() and not overwrite:
        raise ArtifactError(f"目标文件已存在，拒绝覆盖：{destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    # 使用临时 @file 请求体，避免 shell 转义问题及命令历史暴露文件 URI。
    with tempfile.TemporaryDirectory(prefix="smartbi-artifact-") as temp_name:
        request_path = Path(temp_name) / "download.json"
        request_path.write_text(
            json.dumps({request_field: artifact.source_path}, ensure_ascii=False),
            encoding="utf-8",
        )
        command = [
            smartbi_command,
            "call",
            operation,
            "--profile",
            profile,
            "-d",
            f"@{request_path}",
            "-o",
            str(destination),
            "--agent",
        ]
        if config is not None:
            command.extend(["--config", str(config)])
        result = subprocess.run(command, text=True, encoding="utf-8", errors="replace", capture_output=True, check=False)

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ArtifactError(f"文件下载失败 {artifact.uri}：{detail}")
    if not destination.is_file():
        raise ArtifactError(f"下载返回成功，但目标文件不存在：{destination}")
    if destination.stat().st_size <= 0:
        raise ArtifactError(f"下载文件为空：{destination}")
    return destination


def download_artifacts(
    profile: str,
    artifacts: Iterable[ArtifactFile],
    output_dir: str | os.PathLike[str],
    *,
    operation: str = "aichat.downloadQueryResult",
    request_field: str = "filePath",
    smartbi_command: str = "smartbi.cmd" if os.name == "nt" else "smartbi",
    overwrite: bool = False,
    config: str | os.PathLike[str] | None = None,
) -> list[Path]:
    """下载全部文件到 ``output_dir`` 并返回本地路径。"""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for index, artifact in enumerate(artifacts, start=1):
        destination = _safe_output_path(directory, artifact, index)
        if destination.exists() and not overwrite:
            suffix = destination.suffix
            destination = destination.with_name(f"{destination.stem}-{index}{suffix}")
        downloaded.append(
            download_artifact(
                profile,
                artifact,
                destination,
                operation=operation,
                request_field=request_field,
                smartbi_command=smartbi_command,
                overwrite=overwrite,
                config=config,
            )
        )
    return downloaded


def detect_artifact_format(path: str | os.PathLike[str]) -> str:
    """先识别真实文件格式，再参考文件名后缀。"""
    file_path = Path(path)
    if not file_path.is_file():
        raise ArtifactError(f"交付文件不存在：{file_path}")
    with file_path.open("rb") as stream:
        head = stream.read(8)
        if head[:4] == b"PAR1" and file_path.stat().st_size >= 8:
            stream.seek(-4, os.SEEK_END)
            if stream.read(4) == b"PAR1":
                return "parquet"
    if head[:2] == b"PK":
        try:
            with zipfile.ZipFile(file_path) as archive:
                if "xl/workbook.xml" in archive.namelist():
                    return "xlsx"
        except zipfile.BadZipFile as exc:
            raise ArtifactError(f"ZIP 文件无效：{file_path}") from exc
        raise ArtifactError(f"ZIP 文件不是 Excel 工作簿：{file_path}")
    if head == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    # CSV 没有固定文件头；仅在明确为 .csv 且无空字节时交给解析器校验。
    if file_path.suffix.lower() == ".csv" and b"\x00" not in head:
        return "csv"
    raise ArtifactError(f"无法识别交付文件格式：{file_path}")


def read_artifact(path: str | os.PathLike[str], *, sheet_name: str | int | None = 0) -> Any:
    """用 pandas 读取已下载的表格文件。

    Excel 默认读取第一个工作表；显式传入 ``sheet_name=None`` 时读取全部工作表。
    CSV 无类型模式，保留文本值；Excel 保留单元格类型，Parquet 保留文件模式。
    字面值 NA/NULL 不自动当作缺失值；度量类型应结合模型元数据确认。
    延迟导入 pandas，单纯解析 SSE 流不依赖它。
    """

    file_path = Path(path)
    if not file_path.is_file():
        raise ArtifactError(f"交付文件不存在：{file_path}")
    detected_format = detect_artifact_format(file_path)
    try:
        import pandas as pd
    except ImportError as exc:
        raise ArtifactError("读取已下载的表格文件需要 pandas") from exc

    try:
        if detected_format in {"xlsx", "xls"}:
            # 默认读单个工作表；传入 None 时按 pandas 约定读取全部工作表。
            return pd.read_excel(file_path, sheet_name=sheet_name, dtype=object, keep_default_na=False)
        if detected_format == "csv":
            return pd.read_csv(file_path, dtype=str, keep_default_na=False)
        if detected_format == "parquet":
            return pd.read_parquet(file_path)
    except Exception as exc:
        raise ArtifactError(f"读取文件失败 {file_path}：{exc}") from exc
    raise ArtifactError(f"不支持的交付文件格式：{file_path.suffix or '<无后缀>'}")


def artifact_summary(path: str | os.PathLike[str], *, sheet_name: str | int | None = 0) -> dict[str, Any]:
    """返回可序列化的元数据及少量表格预览。"""

    data = read_artifact(path, sheet_name=sheet_name)
    if isinstance(data, dict):
        sheets = {
            str(name): {"rows": int(frame.shape[0]), "columns": [str(c) for c in frame.columns]}
            for name, frame in data.items()
        }
        return {"path": str(Path(path)), "format": detect_artifact_format(path), "sheets": sheets}
    return {
        "path": str(Path(path)),
        "format": detect_artifact_format(path),
        "rows": int(data.shape[0]),
        "columns": [str(column) for column in data.columns],
        "preview": data.head(5).where(data.notna(), None).to_dict(orient="records"),
    }


def _command_inspect(args: argparse.Namespace) -> int:
    artifacts = find_artifacts(args.stream)
    print(json.dumps([asdict(item) for item in artifacts], ensure_ascii=False, indent=2))
    return 0


def _command_download(args: argparse.Namespace) -> int:
    artifacts = find_artifacts(args.stream)
    if args.index < 1 or args.index > len(artifacts):
        raise ArtifactError(f"交付文件序号 {args.index} 超出范围 1..{len(artifacts)}")
    path = download_artifact(
        args.profile,
        artifacts[args.index - 1],
        args.output,
        operation=args.operation,
        request_field=args.request_field,
        smartbi_command=args.smartbi,
        overwrite=args.overwrite,
        config=args.config,
    )
    print(json.dumps({"path": str(path), "bytes": path.stat().st_size}, ensure_ascii=False, indent=2))
    return 0


def _command_read(args: argparse.Namespace) -> int:
    sheet = None if args.all_sheets else (args.sheet if args.sheet is not None else 0)
    print(json.dumps(artifact_summary(args.file, sheet_name=sheet), ensure_ascii=False, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect = subparsers.add_parser("inspect", help="列出 SSE/NDJSON 流中的文件交付物")
    inspect.add_argument("stream", type=Path)
    inspect.set_defaults(func=_command_inspect)

    download = subparsers.add_parser("download", help="下载流中的一个文件交付物")
    download.add_argument("stream", type=Path)
    download.add_argument("--profile", required=True)
    download.add_argument("--config", type=Path, help="已指定的 SmartBI CLI 配置文件路径")
    download.add_argument("--index", type=int, default=1, help="从 1 开始的交付文件序号")
    download.add_argument("--output", type=Path, required=True)
    download.add_argument("--operation", default="aichat.downloadQueryResult")
    download.add_argument(
        "--request-field",
        default="filePath",
        help="下载请求字段（S3 CGI 接口使用 s3Uri）",
    )
    download.add_argument("--smartbi", default=("smartbi.cmd" if os.name == "nt" else "smartbi"))
    download.add_argument("--overwrite", action="store_true")
    download.set_defaults(func=_command_download)

    read = subparsers.add_parser("read", help="读取已下载的 CSV/Excel/Parquet 文件")
    read.add_argument("file", type=Path)
    read.add_argument("--sheet", help="Excel 工作表名称或从 0 开始的序号")
    read.add_argument("--all-sheets", action="store_true", help="读取全部 Excel 工作表")
    read.set_defaults(func=_command_read)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        if getattr(args, "command", None) == "read" and args.sheet is not None:
            try:
                args.sheet = int(args.sheet)
            except ValueError:
                pass
        return int(args.func(args))
    except (ArtifactError, OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
