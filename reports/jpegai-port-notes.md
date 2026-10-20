# JPEG AI 参考软件 M2 移植实录（2026-10-20）

> 源：[gitlab.com/wg1/jpeg-ai/jpeg-ai-reference-software](https://gitlab.com/wg1/jpeg-ai/jpeg-ai-reference-software)（ISO/IEC 6048-3 对应参考实现，BSD 协议）
> 目标机：M2 Mac 24G，无 CUDA。结果：**编解码全链路跑通**（kodim23 0.057 bpp 往返，编码 5.7s / 解码 9.7s，CPU）。

## 移植补丁清单（6 处，全部最小侵入）

| # | 问题 | 修法 |
|---|---|---|
| 1 | requirements.txt 钉死 numpy 1.19/pandas 1.3 等 2022 年依赖 | 不用它，直接现代依赖逐个补（addict/einops/opencv-headless/prettytable/ptflops/pynvml/commentjson/GPUtil 等） |
| 2 | `ptflops` 新版删了 `conv_flops_counter_hook` | **钉 ptflops==0.6.5**（repo 自己的 requirements 本来就钉了这个版本） |
| 3 | `pynvml.smi` 在新版不存在（且 Mac 无 NVIDIA） | `gpu_memory_usage.py` 改 try/except 退化，profiler 变 no-op |
| 4 | me-tANS / direct 两个 C++ 熵编码扩展无 Mac 构建路径 | 手动 clang++ 构建：`-undefined dynamic_lookup`（macOS 扩展标准做法）+ brew libomp 替代 gcc OpenMP + 注意 zsh 不做单词分割（`${=INC}`） |
| 5 | torch 2.6+ `weights_only=True` 默认拒载熵编码缓存 | `ec_lib_mans.py` 的 `torch.load` 加 `weights_only=False`（官方可信文件） |
| 6 | numpy 2.x 标量转换破坏 Exp-Golomb 解码 | **钉 numpy==1.26.4** |

## 首个实测数据点（kodim23，768×512，默认工作点）

| codec | bpp | PSNR | LPIPS |
|---|---|---|---|
| **JPEG AI**（参考编码器默认档） | 0.057 | 28.49 | 0.246 |
| cheng2020-q1 | 0.060 | **31.88** | **0.226** |
| AVIF-q20 | 0.114 | 31.71 | 0.190 |

**⚠️ 解读纪律**：JPEG AI 参考编码器是为**标准一致性**设计的，默认工作点不做 RD 优化；官方 28-30% 码率节省的口径是优化配置 + 主观质量（非 PSNR）。单图单点不能下「JPEG AI 不如 2020 年学术模型」的结论——但这个对照值得扩图集复测，若为真，本身就是有话题度的实测发现。

## 复现命令

```bash
cd codec-lab/jpeg-ai-rs
PYTHONPATH=. ../.venv/bin/python -m src.reco.coders.encoder <img.png> <out.jai>
PYTHONPATH=. ../.venv/bin/python -m src.reco.coders.decoder <in.jai> <out.png>
# 目标 bpp: 编码加 --set_target_bpp <bpp×100，如 0.25bpp→25>
```

## 多工作点复测（kodim23/kodim08，2026-10-20）

| codec | bpp | PSNR | LPIPS |
|---|---|---|---|
| JPEGAI default | 0.057 | 28.49 | 0.246 |
| JPEGAI t12 | 0.128 | 32.07 | 0.169 |
| JPEGAI t25 | 0.231 | 34.90 | 0.128 |
| cheng-q3 | 0.116 | **34.68** | 0.171 |
| AVIF-q45 | 0.284 | 35.69 | **0.106** |
| kodim08: JPEGAI t25 | 0.229 | 24.20 | 0.253 |
| kodim08: cheng-q1 | 0.253 | **25.70** | **0.225** |

**结论收窄**：2 图 × 3 工作点方向一致——**JPEG AI 参考编码器开箱 RD 性能落后于 2020 学术模型和 AVIF**。
正确解读：ISO 参考编码器是为码流一致性而非 RD 最优设计的（标准钉的是解码器和语法，编码器可无限优化），
所以这不是「JPEG AI 标准不行」，而是「开箱即用的官方实现留出了明显的编码器优化空间」——
这恰好坐实了方向②工具包的价值主张：RD 优化编码器 + 消费硬件推理是真实空位。
