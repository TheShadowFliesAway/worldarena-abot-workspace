#!/usr/bin/env python3
"""从生成视频构造最小 Track 2 image-action 数据目录。

这个脚本负责 Track 2 Data Engine 的“后处理”阶段：

1. 读取 `prepare_track2_data_engine_smoke.py` 生成的 manifest。
2. 找到每条样本对应的 ABot 生成视频。
3. 把生成视频抽成逐帧图片。
4. 把原始 action hdf5、instruction json 复制到同一个样本目录。
5. 写出 metadata，形成一个最小的 image-action 数据样例。

输入可以有两种：
  - 严格对齐模式：使用 ABot 推理产生的一个或多个 results.json。
  - 占位烟测模式：手动传入已有 mp4，仅验证抽帧和打包流程。

输出结构：
  output_dir/<task>/<episode>/
    frames/frame_000000.png
    action.hdf5
    instruction.json
    metadata.json

注意：这只是验证 Data Engine 流程的 smoke-format 数据，不是最终 policy
训练格式。占位烟测模式会在 metadata 中写入 `placeholder_video: true`，
避免以后误认为它是语义严格对齐的 Track 2 样本。
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_ROOT = Path("/root/autodl-tmp/track2_data_engine_abot")


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "smoke" / "manifest.json",
        help="Manifest produced by prepare_track2_data_engine_smoke.py.",
    )
    parser.add_argument(
        "--abot-results",
        type=Path,
        nargs="*",
        default=None,
        help="One or more ABot inference results.json files.",
    )
    parser.add_argument(
        "--generated-videos",
        type=Path,
        nargs="*",
        default=None,
        help="Optional generated videos to pair with manifest entries by order.",
    )
    parser.add_argument(
        "--allow-placeholder-videos",
        action="store_true",
        help="Allow generated videos that are not produced from the manifest first frames.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "smoke" / "image_action_dataset",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="Optional maximum frames to extract per video. 0 means all frames.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    """读取 JSON 文件。"""
    return json.loads(path.read_text(encoding="utf-8"))


def result_map(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """把 ABot results.json 映射成 `输入 first_frame -> 推理结果`。

    ABot batch 推理的 results.json 中会记录：
      - video: 原始输入图像/视频路径
      - output_video: 生成视频路径

    严格对齐模式下，我们要求 manifest 里的 first_frame 路径和 results.json
    里的 video 路径一致。
    """
    mapped = {}
    for item in results:
        if item.get("status") != "success":
            continue
        video = item.get("video")
        output_video = item.get("output_video")
        if video and output_video:
            mapped[str(Path(video))] = item
    return mapped


def ordered_placeholder_map(
    manifest: list[dict[str, Any]],
    generated_videos: list[Path],
    allow_placeholder: bool,
) -> dict[str, dict[str, Any]]:
    """按顺序把已有视频配给 manifest 样本，用于流程烟测。

    这个模式只验证 Data Engine 后处理是否能跑通，不保证生成视频和 Track 2
    的 first_frame / instruction / action 是语义对齐的。因此必须显式传入
    `--allow-placeholder-videos`，并且输出 metadata 会标记 placeholder。
    """
    if not generated_videos:
        return {}
    if len(generated_videos) < len(manifest):
        raise ValueError(
            f"Need at least {len(manifest)} generated videos, got {len(generated_videos)}"
        )
    if not allow_placeholder:
        raise ValueError(
            "--generated-videos pairs videos by order and may be semantically unaligned; "
            "pass --allow-placeholder-videos to use it for smoke testing."
        )

    mapped = {}
    for entry, video_path in zip(manifest, generated_videos):
        video_path = Path(video_path)
        mapped[str(Path(entry["video"]))] = {
            "video": entry["video"],
            "prompt": entry["prompt"],
            "output_video": str(video_path),
            "status": "success",
            "placeholder_video": True,
        }
    return mapped


def extract_video_frames(video_path: Path, frames_dir: Path, max_frames: int = 0) -> int:
    """把 mp4 抽成 PNG 帧，返回抽出的帧数。"""
    import imageio

    frames_dir.mkdir(parents=True, exist_ok=True)
    reader = imageio.get_reader(str(video_path))
    count = 0
    try:
        for frame in reader:
            if max_frames and count >= max_frames:
                break
            out = frames_dir / f"frame_{count:06d}.png"
            imageio.imwrite(out, frame)
            count += 1
    finally:
        reader.close()
    return count


def main() -> None:
    args = parse_args()
    manifest = load_json(args.manifest)

    # 优先使用严格对齐模式：ABot results.json 里记录了每条视频来自哪个 first_frame。
    # 如果没有传 results.json，则允许使用手动传入的占位 mp4 做后处理烟测。
    if args.abot_results:
        # 支持多个 ABot results.json，便于把 OOM 后重跑的样本合并到一个数据集。
        all_results = []
        for results_path in args.abot_results:
            all_results.extend(load_json(results_path))
        generated_by_input = result_map(all_results)
    else:
        generated_by_input = ordered_placeholder_map(
            manifest,
            args.generated_videos or [],
            args.allow_placeholder_videos,
        )
    if not generated_by_input:
        raise ValueError("Provide --abot-results or --generated-videos with --allow-placeholder-videos")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_manifest = []
    missing = []

    for entry in manifest:
        # manifest 中的 video 是 Track 2 first_frame。严格模式下用它去匹配
        # ABot results.json；占位模式下则由 ordered_placeholder_map 伪造映射。
        source_video = str(Path(entry["video"]))
        result = generated_by_input.get(source_video)
        if result is None:
            missing.append(source_video)
            continue

        generated_video = Path(result["output_video"])
        if not generated_video.exists():
            missing.append(str(generated_video))
            continue

        task = entry["task"]
        episode_id = entry["episode_id"]
        sample_dir = args.output_dir / task / episode_id
        frames_dir = sample_dir / "frames"
        sample_dir.mkdir(parents=True, exist_ok=True)

        # 核心产物 1：synthetic frames。
        frame_count = extract_video_frames(generated_video, frames_dir, args.max_frames)

        # 核心产物 2：复制原始 action 和 instruction，先保持官方原始格式。
        # 后续如果要转成 policy 训练格式，再在这里之后追加转换逻辑。
        action_dst = sample_dir / "action.hdf5"
        instruction_dst = sample_dir / "instruction.json"
        shutil.copy2(entry["hdf5_path"], action_dst)
        shutil.copy2(entry["instruction_path"], instruction_dst)

        # 每个样本保留完整溯源信息，尤其是 placeholder_video 标记。
        metadata = {
            "task": task,
            "scene": entry["scene"],
            "episode_id": episode_id,
            "placeholder_video": bool(result.get("placeholder_video", False)),
            "prompt": entry["prompt"],
            "first_frame": entry["video"],
            "generated_video": str(generated_video),
            "frame_count": frame_count,
            "action_hdf5": str(action_dst),
            "instruction_json": str(instruction_dst),
            "source_hdf5": entry["hdf5_path"],
            "source_instruction": entry["instruction_path"],
        }
        metadata_path = sample_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        dataset_manifest.append(metadata)

    dataset_manifest_path = args.output_dir / "dataset_manifest.json"
    dataset_manifest_path.write_text(
        json.dumps(dataset_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote image-action dataset: {args.output_dir}")
    print(f"Wrote dataset manifest: {dataset_manifest_path}")
    print(f"Built samples: {len(dataset_manifest)}")
    if missing:
        print("Missing generated outputs:")
        for item in missing:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
