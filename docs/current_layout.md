# 当前目录地图

这个文件只解释当前 workspace 和 `/root/autodl-tmp` 下几个相关目录的用途，避免后续混淆。

## Workspace

```text
/root/autodl-tmp/worldarena-abot-workspace
```

这里是轻量实验管理仓库，只放：

```text
README.md
configs/
scripts/
docs/
experiments/
data/       # 软链接入口
external/   # 软链接入口
model/      # 软链接入口
outputs/    # 软链接入口
```

不要把大视频、模型权重、原始数据直接放进 workspace。

## 当前有效产物

当前真正要看的 Track 2 Data Engine smoke 输出是：

```text
/root/autodl-tmp/track2_data_engine_abot/smoke/image_action_dataset_track2_aligned
```

workspace 里有一个等价入口：

```text
outputs/current_track2_aligned_dataset
```

这个目录包含 2 条严格 Track 2 对齐样本：

```text
adjust_bottle/episode0/
adjust_bottle/episode1/
dataset_manifest.json
```

每个 episode 目录包含：

```text
frames/            # ABot 生成视频抽出来的 synthetic frames
action.hdf5        # Track 2 原始 hdf5 action/state
instruction.json   # Track 2 原始 instruction
metadata.json      # 样本溯源信息
```

## Track 2 Smoke 根目录

```text
/root/autodl-tmp/track2_data_engine_abot/smoke
```

主线文件：

```text
abot_track2_smoke.jsonl          # 给 ABot I2V 的输入
manifest.json                    # Track 2 样本索引和 hdf5 摘要
source/                          # 从官方 tar 包抽出来的 first_frame/hdf5/instruction
abot_outputs_track2/             # 默认参数生成输出，episode1 成功
abot_outputs_track2_fast_retry/  # 轻量参数补跑输出，episode0 成功
image_action_dataset_track2_aligned/  # 当前有效 aligned 数据
```

归档文件：

```text
archive/
```

里面是历史占位数据和半成品，可以暂时忽略。没有删除，是为了保留实验痕迹。

## Track 1 旧 Smoke

```text
/root/autodl-tmp/abot_worldarena_raw/test_smoke
```

这里是之前 Track 1 的两条 smoke 视频。它们不再是当前主线，只作为旧生成结果保留。

workspace 入口：

```text
outputs/abot_worldarena_raw
```

## 原始数据和源码

```text
/root/autodl-tmp/WorldArena_Robotwin2.0
/root/autodl-tmp/ABot-PhysWorld
/root/autodl-tmp/model
```

workspace 中对应软链接：

```text
data/worldarena_dataset
external/ABot-PhysWorld
model/abot_model
```

