# WorldArena + ABot-PhysWorld Workspace

本仓库用于管理 **ABot-PhysWorld 在 WorldArena / RoboTwin2.0 上的实验流程**。仓库本身是实验工作区，主要放配置、脚本、实验入口和记录；ABot 源码、数据集、模型权重和大体积输出都放在 `/root/autodl-tmp` 下，通过软链接接入。

## 当前只看这里

当前主线是 **Track 2 Data Engine smoke**。有效产物只有这一份：

```text
/root/autodl-tmp/track2_data_engine_abot/smoke/image_action_dataset_track2_aligned
```

在当前 workspace 里也可以通过软链接进入：

```text
outputs/current_track2_aligned_dataset
```

这个目录是严格基于 Track 2 数据生成和对齐的 smoke 数据，包含：

```text
adjust_bottle/episode0
adjust_bottle/episode1
dataset_manifest.json
```

旧的占位数据和半成品已经放到：

```text
/root/autodl-tmp/track2_data_engine_abot/smoke/archive
```

## codex的使用

### vscode需要加入配置Preferences: Open Remote Settings (JSON)
```json
{
  "http.proxy": "http://127.0.0.1:17890",
  "http.proxySupport": "override",
  "http.systemCertificates": true,
  "http.proxyStrictSSL": true
}
```

### 本地需要开反向ssh
ssh -N -R 17890:127.0.0.1:7897 autodl-worldarena

## 当前目标

### Track 1: Video Quality Evaluation

当前优先任务是先跑通 **本地可复现、且不依赖 GT 视频/reference video 的 Track 1 指标**：

```text
WorldArena first frame + prompt
-> ABot-PhysWorld I2V
-> generated video
-> local no-GT Track 1 metrics
```

官方完整提交仍然需要三套视频，每套 1000 条，共 3000 条；但这一步先不作为当前主目标：

| 输入 | 输出目录 | 作用 |
|---|---|---|
| `instructions/` | `{model_name}_test` | 主 prompt |
| `instructions_1/` | `{model_name}_test_1` | Action Following 变体 1 |
| `instructions_2/` | `{model_name}_test_2` | Action Following 变体 2 |

当前 JSONL 字段为：

```json
{
  "video": "/root/autodl-tmp/WorldArena_Robotwin2.0/test_dataset/first_frame/fixed_scene_task/episode1.png",
  "prompt": "In a fixed robotic workspace, generate ...",
  "episode_id": "episode1"
}
```

这批数据暂时只走 `first frame + prompt -> video`，没有启用 A2V/action 条件生成。官方要求视频建议为 `640x480` 或更高、`121 frames`、`24 fps`。

#### Track 1 本地评测现状

公开 `test_dataset` 是 leaderboard 输入数据，不包含真实 GT 视频/帧。完整 16 指标里有部分指标依赖官方私有 GT/reference，因此本地不能完全复现官方 Track 1 分数。当前策略改为：

1. 只跑不依赖 GT/reference video 的本地指标。
2. 先用小样本检查生成、预处理、评测输出能否串起来。
3. 依赖 GT/reference 的指标先不处理，不强行伪造 `gt_path`。
4. 官方提交作为后续可选项，不是当前主线。

16 个官方指标及本地 GT 依赖关系：

| 维度 | 指标 | 本地是否需要 GT/reference |
|---|---|---|
| Visual Quality | Image Quality | 不需要 |
| Visual Quality | Aesthetic Quality | 不需要 |
| Visual Quality | JEPA Similarity | 需要 GT/real video |
| Motion Quality | Dynamic Degree | 不需要 |
| Motion Quality | Flow Score | 不需要 |
| Motion Quality | Motion Smoothness | 不需要 |
| Content Consistency | Subject Consistency | 不需要 |
| Content Consistency | Background Consistency | 不需要 |
| Content Consistency | Photometric Consistency | 不需要真实 GT |
| Physics Adherence | Interaction Quality | 不需要 |
| Physics Adherence | Trajectory Accuracy | 需要 GT traj/reference |
| 3D Accuracy | Depth Accuracy | 需要 GT video/frames |
| 3D Accuracy | Perspectivity | 不需要 |
| Controllability | Instruction Following | 不需要 GT video，只需要 prompt |
| Controllability | Semantic Alignment | 需要 GT video caption/reference |
| Controllability | Action Following | 不需要真实 GT video，但需要三组生成视频 |

当前优先尝试的本地 no-GT 指标：

```text
image_quality
aesthetic_quality
dynamic_degree
flow_score
motion_smoothness
subject_consistency
background_consistency
photometric_smoothness / photometric_consistency
interaction_quality
perspectivity
instruction_following
```

暂不处理的 GT/reference 依赖指标：

```text
JEPA Similarity
Trajectory Accuracy
Depth Accuracy
Semantic Alignment
PSNR / SSIM / PSNR_SSIM
```

官方提交说明要点，后续如果要提交再使用：

- 使用 `test_dataset` 作为最终 leaderboard 数据。
- 打包目录名建议为 `{Your_Model_Name}_eval`。
- 包内包含三套 test 视频目录和 `model_README.md` 或 `model_README.txt`。
- `model_README` 中 `Affiliation / Organization` 必填。
- 邮件发送到 `WorldArena1@outlook.com`。
- 邮件主题：`{Your_Model_Name}_evaluation`。
- 附件：`{Your_Model_Name}_eval.zip`。
- 官方没有明确写每日提交次数限制；高峰期按 FIFO 排队，短时间重复提交同一模型会被延迟或降低优先级。

### Track 2: Data Engine

Track 2 先做 Data Engine，把数据生成和对齐流程打通；暂时不做 Policy Evaluator：

```text
WorldArena 原始数据
-> ABot-PhysWorld 生成 synthetic frames
-> 对齐原始 actions / states / instruction
-> 构造 image-action 数据
-> 后续用于 policy fine-tuning 和 RoboTwin 2.0 评估
```

Policy Evaluator 涉及 policy server、closed-loop rollout、action bridge 和状态更新，暂时放到后续阶段。

## 环境

当前 conda 中有两个相关环境，**当前适配并优先使用的是 `abot`**：

```bash
conda activate abot
```

另一个环境可作为备用或历史环境，后续脚本默认按 `abot` 环境维护。

运行前建议检查 GPU：

```bash
conda activate abot

python - <<'PY'
import torch
print("torch:", torch.__version__)
print("cuda:", torch.cuda.is_available())
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
PY
```

## 关键路径

| 路径 | 作用 |
|---|---|
| `/root/autodl-tmp/worldarena-abot-workspace` | 当前实验管理仓库 |
| `/root/autodl-tmp/ABot-PhysWorld` | ABot-PhysWorld 源码 |
| `/root/autodl-tmp/ABot-PhysWorld/inference` | ABot I2V/A2V 推理入口 |
| `/root/autodl-tmp/WorldArena_Robotwin2.0` | WorldArena / RoboTwin2.0 数据 |
| `/root/autodl-tmp/worldarena_jsonl` | Track 1 JSONL |
| `/root/autodl-tmp/model` | Wan2.1-I2V 和 ABot 权重 |
| `/root/autodl-tmp/abot_worldarena_raw` | ABot 原始生成视频 |
| `/root/autodl-tmp/worldarena_track1_eval` | Track 1 评测整理目录 |
| `/root/autodl-tmp/track2_data_engine_abot` | Track 2 Data Engine 输出目录 |
| `outputs/abot_worldarena_raw` | 指向 Track 1/旧 ABot 输出 |
| `outputs/track2_data_engine_abot` | 指向 Track 2 Data Engine 输出根目录 |
| `outputs/current_track2_aligned_dataset` | 指向当前有效 Track 2 aligned smoke 数据 |

统一路径配置在：

```bash
configs/paths.yaml
```

## 当前数据状态

Track 1 JSONL：

```text
/root/autodl-tmp/worldarena_jsonl/worldarena_test.jsonl      1000 lines
/root/autodl-tmp/worldarena_jsonl/worldarena_test_1.jsonl    1000 lines
/root/autodl-tmp/worldarena_jsonl/worldarena_test_2.jsonl    1000 lines
```

已有 smoke 输出：

```text
/root/autodl-tmp/abot_worldarena_raw/test_smoke/fixed_scene_task_episode1_generated.mp4
/root/autodl-tmp/abot_worldarena_raw/test_smoke/fixed_scene_task_episode2_generated.mp4
```

Track 2 原始包：

```text
/root/autodl-tmp/WorldArena_Robotwin2.0/track2_data_engine_validation.tar.gz
/root/autodl-tmp/WorldArena_Robotwin2.0/track2_data_engine_test.tar.gz
```

Track 2 当前有效 smoke 产物：

```text
/root/autodl-tmp/track2_data_engine_abot/smoke/
├── abot_track2_smoke.jsonl
├── manifest.json
├── source/
├── abot_outputs_track2/
├── abot_outputs_track2_fast_retry/
├── image_action_dataset_track2_aligned/
└── archive/
```

其中：

```text
image_action_dataset_track2_aligned/   # 当前有效数据
archive/                               # 历史占位/半成品，可忽略
```

## 仓库结构

```text
worldarena-abot-workspace/
├── README.md
├── configs/       # 路径和实验配置
├── scripts/       # 数据处理、推理、整理、检查脚本
├── experiments/   # 具体实验入口
├── adapters/      # WorldArena 和 ABot 之间的适配代码
├── docs/          # 实验记录和流程说明
├── env/           # 环境检查和依赖说明
├── external/      # 外部源码软链接
├── data/          # 数据软链接
├── model/         # 模型软链接
└── outputs/       # 输出软链接或小型实验输出
```

本仓库只提交脚本、配置和文档，不提交模型权重、原始数据、生成视频、日志、大型中间结果。

## 常用命令

检查工作区状态：

```bash
cd /root/autodl-tmp/worldarena-abot-workspace
python scripts/check_workspace.py
```

查看 ABot I2V 参数：

```bash
conda activate abot
cd /root/autodl-tmp/ABot-PhysWorld/inference

bash run_inference.sh --help
python inference.py --help
```

运行 ABot I2V JSONL 推理示例：

```bash
conda activate abot
cd /root/autodl-tmp/ABot-PhysWorld/inference

python inference.py \
  --jsonl_path /root/autodl-tmp/worldarena_jsonl/worldarena_test.jsonl \
  --output_dir /root/autodl-tmp/abot_worldarena_raw/track1_smoke \
  --checkpoint_path /root/autodl-tmp/model/abotpw_i2v_480p.safetensors \
  --num_samples 2
```

检查生成视频：

```bash
find /root/autodl-tmp/abot_worldarena_raw -name "*.mp4" | sort | head
find /root/autodl-tmp/abot_worldarena_raw -name "*.mp4" | wc -l
```

查看视频信息：

```bash
ffprobe -v error \
  -show_entries stream=width,height,nb_frames,r_frame_rate,duration \
  -of default=noprint_wrappers=1 \
  /path/to/generated_video.mp4
```

查看 Track 2 压缩包结构：

```bash
tar -tf /root/autodl-tmp/WorldArena_Robotwin2.0/track2_data_engine_validation.tar.gz | head -n 80
```

准备 Track 2 Data Engine smoke 输入，不会重新生成视频：

```bash
cd /root/autodl-tmp/worldarena-abot-workspace
conda activate abot

python scripts/prepare_track2_data_engine_smoke.py --max-samples 2
```

输出：

```text
/root/autodl-tmp/track2_data_engine_abot/smoke/abot_track2_smoke.jsonl
/root/autodl-tmp/track2_data_engine_abot/smoke/manifest.json
/root/autodl-tmp/track2_data_engine_abot/smoke/source/
```

后续如果要用 ABot 生成 Track 2 synthetic videos：

```bash
cd /root/autodl-tmp/ABot-PhysWorld/inference
conda activate abot

python inference.py \
  --jsonl_path /root/autodl-tmp/track2_data_engine_abot/smoke/abot_track2_smoke.jsonl \
  --output_dir /root/autodl-tmp/track2_data_engine_abot/smoke/abot_outputs_track2 \
  --checkpoint_path /root/autodl-tmp/model/abotpw_i2v_480p.safetensors \
  --num_samples 2
```

ABot 生成完成后，构造最小 image-action 数据目录：

```bash
cd /root/autodl-tmp/worldarena-abot-workspace
conda activate abot

python scripts/build_track2_image_action_dataset.py \
  --manifest /root/autodl-tmp/track2_data_engine_abot/smoke/manifest.json \
  --abot-results /root/autodl-tmp/track2_data_engine_abot/smoke/abot_outputs_track2/results.json \
  --output-dir /root/autodl-tmp/track2_data_engine_abot/smoke/image_action_dataset_track2
```

如果中途 OOM 后用轻量参数重跑了部分样本，可以把多个 `results.json` 合并：

```bash
python scripts/build_track2_image_action_dataset.py \
  --manifest /root/autodl-tmp/track2_data_engine_abot/smoke/manifest.json \
  --abot-results \
    /root/autodl-tmp/track2_data_engine_abot/smoke/abot_outputs_track2/results.json \
    /root/autodl-tmp/track2_data_engine_abot/smoke/abot_outputs_track2_fast_retry/results.json \
  --output-dir /root/autodl-tmp/track2_data_engine_abot/smoke/image_action_dataset_track2_aligned
```

## 推荐执行顺序

1. 用 `abot` 环境复现 2 条 smoke test。
2. 用少量样本整理成 WorldArena 本地评测输入目录。
3. 跑通 no-GT Track 1 指标的最小集合，先确认预处理、模型权重、输出 JSON/CSV 正常。
4. 扩大到 30 条或 150 条 subset，得到 ABot Base 在 no-GT 指标上的本地结果。
5. 暂不追求完整 3000 条官方提交包。
6. 启动 Track 2 Data Engine 最小实验：解包、抽样、生成 synthetic frames、对齐 action/state/instruction。
7. Track 2 打通后，再决定是否补官方 Track 1 提交或扩大全量实验。

## 给 Codex 的上下文

后续任务默认从本仓库开始：

```bash
/root/autodl-tmp/worldarena-abot-workspace
```

优先阅读：

```text
README.md
configs/paths.yaml
scripts/check_workspace.py
docs/experiment_log.md
```

默认环境：

```bash
conda activate abot
```

不要移动或覆盖原始数据、模型权重和已有输出。
