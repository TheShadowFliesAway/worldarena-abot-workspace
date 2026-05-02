from pathlib import Path
import json

paths = {
    "ABot repo": "/root/autodl-tmp/ABot-PhysWorld",
    "ABot inference": "/root/autodl-tmp/ABot-PhysWorld/inference",
    "WorldArena data": "/root/autodl-tmp/WorldArena_Robotwin2.0",
    "WorldArena test_dataset": "/root/autodl-tmp/WorldArena_Robotwin2.0/test_dataset",
    "JSONL dir": "/root/autodl-tmp/worldarena_jsonl",
    "Model dir": "/root/autodl-tmp/model",
    "Raw output": "/root/autodl-tmp/abot_worldarena_raw",
}

print("===== Path check =====")
for name, p in paths.items():
    path = Path(p)
    print(f"{name:28s}: {'OK' if path.exists() else 'MISSING'}  {p}")

print("\n===== JSONL files =====")
jsonl_dir = Path("/root/autodl-tmp/worldarena_jsonl")
if jsonl_dir.exists():
    for f in sorted(jsonl_dir.glob("*.jsonl")):
        n = sum(1 for _ in f.open())
        print(f"{f.name:30s}: {n} lines")
        try:
            first = json.loads(f.open().readline())
            print("  keys:", list(first.keys()))
            print("  episode_id:", first.get("episode_id"))
            print("  video:", first.get("video"))
            print("  prompt_prefix:", first.get("prompt", "")[:120])
        except Exception as e:
            print("  failed to parse:", e)

print("\n===== Existing generated videos =====")
out = Path("/root/autodl-tmp/abot_worldarena_raw")
videos = list(out.rglob("*.mp4")) if out.exists() else []
print("mp4 count:", len(videos))
for v in videos[:20]:
    print(" ", v)
