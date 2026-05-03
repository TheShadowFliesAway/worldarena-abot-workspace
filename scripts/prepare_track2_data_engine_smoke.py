#!/usr/bin/env python3
"""准备一个很小的 Track 2 Data Engine smoke 子集。

这个脚本负责 Track 2 Data Engine 的“输入准备”阶段：

1. 从官方 Track 2 tar.gz 中抽取少量 episode。
2. 保留每个 episode 的 first_frame、instruction、hdf5 action/state。
3. 生成 ABot I2V 可直接读取的 JSONL：

       {"video": first_frame.png, "prompt": "...", ...}

4. 生成 manifest.json，记录样本路径、任务名、episode id 和 hdf5 摘要。

这个脚本不会运行 ABot 推理，也不会修改官方原始 tar 包。
"""

from __future__ import annotations

import argparse
import json
import re
import tarfile
from pathlib import Path
from typing import Any


DEFAULT_DATA_ROOT = Path("/root/autodl-tmp/WorldArena_Robotwin2.0")
DEFAULT_OUTPUT_ROOT = Path("/root/autodl-tmp/track2_data_engine_abot")


EPISODE_RE = re.compile(r"episode(\d+)\.json$")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tar-path",
        type=Path,
        default=DEFAULT_DATA_ROOT / "track2_data_engine_validation.tar.gz",
        help="Track 2 tarball to sample from.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output root for the smoke subset.",
    )
    parser.add_argument("--max-samples", type=int, default=2)
    parser.add_argument(
        "--task",
        default=None,
        help="Optional task name filter, e.g. adjust_bottle.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Optional text prefix prepended to each instruction.",
    )
    return parser.parse_args()


def safe_extract_member(tar: tarfile.TarFile, member_name: str, dst_root: Path) -> Path:
    """安全解压单个 tar 成员，避免 tar 内部路径逃逸到输出目录外。"""
    member = tar.getmember(member_name)
    target = dst_root / member.name
    resolved_root = dst_root.resolve()
    resolved_target = target.resolve()
    if resolved_root not in resolved_target.parents and resolved_target != resolved_root:
        raise ValueError(f"Refusing unsafe tar member path: {member.name}")
    tar.extract(member, dst_root)
    return target


def load_instruction(path: Path) -> str:
    """从 WorldArena instruction json 中取出文本 prompt。

    Track 2 validation 中常见格式是 {"seen": ["..."]}，Track 1/test
    中更常见的是 {"instruction": "..."}。这里兼容几种字段，方便后续扩展。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("instruction", "seen", "unseen"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list) and value:
            return str(value[0])
    return json.dumps(data, ensure_ascii=False)


def summarize_hdf5(path: Path) -> dict[str, Any]:
    """读取 hdf5 中各 dataset 的 shape/dtype，用于快速确认 action/state 结构。"""
    try:
        import h5py
    except Exception:
        return {"error": "h5py is not available"}

    summary: dict[str, Any] = {}
    with h5py.File(path, "r") as h5:
        def visit(name: str, obj: Any) -> None:
            # h5py 的 Dataset 有 shape/dtype；Group 没有 shape，这里只记录 Dataset。
            if hasattr(obj, "shape"):
                summary[name] = {
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                }

        h5.visititems(visit)
    return summary


def collect_instruction_members(tar: tarfile.TarFile, task_filter: str | None) -> list[str]:
    """从 tar 包中收集可用的 instruction episode，并按 task/episode 排序。"""
    members = []
    for name in tar.getnames():
        if "/instructions/" not in name or not name.endswith(".json"):
            continue
        parts = Path(name).parts
        # track2_data_engine_validation/adjust_bottle/fixed_scene_task/instructions/episode0.json
        if len(parts) < 5:
            continue
        task = parts[1]
        if task_filter and task != task_filter:
            continue
        if not EPISODE_RE.search(parts[-1]):
            continue
        members.append(name)

    def sort_key(name: str) -> tuple[str, int]:
        parts = Path(name).parts
        match = EPISODE_RE.search(parts[-1])
        episode_num = int(match.group(1)) if match else -1
        return ("/".join(parts[1:3]), episode_num)

    return sorted(members, key=sort_key)


def main() -> None:
    args = parse_args()
    if not args.tar_path.exists():
        raise FileNotFoundError(args.tar_path)

    smoke_root = args.output_root / "smoke"
    source_root = smoke_root / "source"
    source_root.mkdir(parents=True, exist_ok=True)

    manifest = []
    jsonl_rows = []

    with tarfile.open(args.tar_path, "r:gz") as tar:
        # 先只从 instructions 目录选 episode，再推导对应 first_frame/hdf5/scene_info。
        # 这样可以保证输出样本以“有任务指令”为中心组织。
        instruction_members = collect_instruction_members(tar, args.task)
        selected = instruction_members[: args.max_samples]
        if not selected:
            raise RuntimeError(f"No instruction episodes found in {args.tar_path}")

        for instruction_member in selected:
            parts = Path(instruction_member).parts
            dataset_root, task, scene = parts[0], parts[1], parts[2]
            episode_name = Path(parts[-1]).stem

            # Track 2 包的固定结构：
            # track2_data_engine_validation/<task>/<scene>/{instructions,first_frame,data}
            base = f"{dataset_root}/{task}/{scene}"
            paths = {
                "instruction": f"{base}/instructions/{episode_name}.json",
                "first_frame": f"{base}/first_frame/{episode_name}.png",
                "hdf5": f"{base}/data/{episode_name}.hdf5",
                "scene_info": f"{base}/scene_info.json",
            }

            extracted = {
                key: safe_extract_member(tar, member_name, source_root)
                for key, member_name in paths.items()
            }

            # ABot I2V 当前只需要 video(first frame) 和 prompt；额外字段保留给后处理。
            instruction = load_instruction(extracted["instruction"])
            prompt = f"{args.prefix}{instruction}" if args.prefix else instruction

            row = {
                "video": str(extracted["first_frame"]),
                "prompt": prompt,
                "episode_id": episode_name,
                "track": "track2_data_engine",
                "task": task,
                "scene": scene,
                "hdf5_path": str(extracted["hdf5"]),
                "instruction_path": str(extracted["instruction"]),
            }
            jsonl_rows.append(row)

            # manifest 是 Data Engine 后处理的桥：它把 ABot 输入、原始 action、
            # instruction 和 hdf5 结构摘要连在一起。
            manifest.append({
                **row,
                "source_tar": str(args.tar_path),
                "scene_info_path": str(extracted["scene_info"]),
                "hdf5_summary": summarize_hdf5(extracted["hdf5"]),
            })

    jsonl_path = smoke_root / "abot_track2_smoke.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in jsonl_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest_path = smoke_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote JSONL: {jsonl_path}")
    print(f"Wrote manifest: {manifest_path}")
    print(f"Extracted source subset: {source_root}")


if __name__ == "__main__":
    main()
