# WorldArena + ABot-PhysWorld Workspace

本仓库用于管理 **ABot-PhysWorld 在 WorldArena / RoboTwin2.0 上的实验流程**。仓库本身是实验工作区，主要放配置、脚本、实验入口和记录；ABot 源码、数据集、模型权重和大体积输出都放在 `/root/autodl-tmp` 下，通过软链接接入。

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

当前优先任务是按 WorldArena Track 1 官方格式生成视频提交包，用官方服务端评测：

```text
WorldArena first frame + prompt
-> ABot-PhysWorld I2V
-> generated video
-> package as official Track 1 submission
-> send to WorldArena official evaluator
```

Track 1 完整提交需要三套视频，每套 1000 条，共 3000 条：

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

公开 `test_dataset` 是 leaderboard 输入数据，不包含真实 GT 视频/帧。完整 16 指标里有部分指标依赖官方私有 GT/reference，因此本地不能完全复现官方 Track 1 分数。当前策略是：

1. 本地只做小样本生成、视频规格检查、目录/命名检查。
2. 不在本机配置完整 `gt_path` 和所有评测模型权重。
3. 正式结果以官方邮件提交后的评测为准。

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

官方提交说明要点：

- 使用 `test_dataset` 作为最终 leaderboard 数据。
- 打包目录名建议为 `{Your_Model_Name}_eval`。
- 包内包含三套 test 视频目录和 `model_README.md` 或 `model_README.txt`。
- `model_README` 中 `Affiliation / Organization` 必填。
- 邮件发送到 `WorldArena1@outlook.com`。
- 邮件主题：`{Your_Model_Name}_evaluation`。
- 附件：`{Your_Model_Name}_eval.zip`。
- 官方没有明确写每日提交次数限制；高峰期按 FIFO 排队，短时间重复提交同一模型会被延迟或降低优先级。

### Track 2: Data Engine

Track 2 后续先做 Data Engine，而不是 Policy Evaluator：

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

## 推荐执行顺序

1. 用 `abot` 环境复现 2 条 smoke test。
2. 从三套 JSONL 各抽 2 条，生成 6 条小样本视频。
3. 检查视频规格：分辨率、帧数、fps、是否能正常解码。
4. 整理成官方 Track 1 目录命名：`{model}_test`、`{model}_test_1`、`{model}_test_2`。
5. 做 30 条或 150 条 subset，估算全量时间和显存稳定性。
6. 全量生成 3000 条视频。
7. 准备 `model_README.md`，打包 `{model}_eval.zip` 并邮件提交官方评测。
8. Track 1 提交后，再启动 Track 2 Data Engine 最小实验。

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
