# imgbench — 图片编解码一键 Benchmark（消费级硬件友好）

一条命令，对任意图片或目录跑 **学习型（CompressAI）/ JPEG AI（ISO 官方参考实现）/ AVIF / JPEG** 四族编解码器，输出统一的 bpp / PSNR / LPIPS / 编解码耗时对照表。

> **Why this exists**: 学术界的压缩代码全为训练设计，JPEG AI 参考软件只支持 CUDA+Ubuntu。
> 本工具在 **Apple Silicon Mac（M2，无独显）** 上打通了全链路，并附 JPEG AI 的移植补丁。
> 所有结论均来自真实机器实测，非论文转述。

## 实测发现（M2 Mac，2026-10）

| 发现 | 数据 |
|---|---|
| 2020 年的学术模型等 PSNR 下码率仅为 AVIF 的一半 | cheng2020-q1 @ 0.060bpp / 31.9dB vs AVIF-q20 @ 0.114bpp / 31.7dB |
| JPEG AI 参考编码器 RD 表现依内容/工作点大幅波动 | Kodak 默认档落后 2020 学术模型；ImageNet 30 张 t25 档与 cheng-q3 打平、优于 AVIF（详见 reports/imagenet-scale.md，单点结论勿外推） |
| **M2 上 CPU 编码比 MPS GPU 快 3 倍** | 1.03s vs 3.19s（cheng-q1，小模型 GPU 负优化） |
| **AI 生成图天生好压 2-3 倍** | AIGC 中位 0.097bpp vs 自然照片 0.208bpp（44 张实测，高频能量 r=0.794） |
| **<16px 文字在低码率档被学习型 codec 团灭** | OCR 0.00-0.06 vs AVIF 0.76+；阈值=codec 下采样因子 |
| **自然照片人眼无感阈值 ≈ 0.12bpp（q3 档）** | 用户实测：q3/q6 无感，q1 纹理软化可感知（体积 1/93） |

## 安装

```bash
pip install -r requirements.txt
```

## 用法

```bash
# 默认跑 cheng + JPEG + AVIF
python bench.py image.png

# 整个目录，含 JPEG AI（需先按 patches/README.md 完成移植）
python bench.py images/ --codecs cheng,avif,jpegai

# 结果存 JSON
python bench.py images/ --out results.json
```

JPEG AI 支持需要两个环境变量（可选）：
- `JPEGAI_RS`：jpeg-ai-reference-software 克隆路径
- `JPEGAI_PY`：运行参考软件用的 python 解释器（默认当前）

## 示例输出

```
== kodim15.png
  cheng-q1       0.062bpp  PSNR  29.69  LPIPS 0.3358  enc 1.0s  dec 3.6s
  AVIF-q20       0.121bpp  PSNR  30.06  LPIPS 0.2692
  jpegai-t12     0.127bpp  PSNR  29.28  LPIPS 0.2450  enc 5.9s  dec 9.8s
```

## JPEG AI on Apple Silicon

`patches/` 内含完整移植材料：2 个源码补丁（`git apply` 即可）+ C++ 熵编码扩展的 macOS 构建脚本 + 逐步文档。详见 [patches/README.md](patches/README.md)。

**免责声明**：JPEG AI 参考编码器为标准一致性设计，开箱配置不做率失真优化；本工具的 JPEG AI 数据反映的是「开箱默认表现」，不代表标准的 RD 上限。JPEG AI 标准为 BSD 代码协议但不涵盖可能的专利权，商用前请自行评估。

## 真实性与可复现

本仓库的每条结论都附带原始数据与复现脚本：

- `results/` —— 全部测量的原始 JSON（7 份，可直接复算每张表）
- `experiments/` —— 每个实验的完整脚本（文字 OCR 审计 / 字号梯度 / AIGC 矩阵 / 频谱分析）
- `reports/` —— 带局限标注的详细报告（含我们推翻自己结论的记录）

测试图：自然图为公开 Kodak 测试集（[下载](https://r0k.us/graphics/kodak/)），AIGC 图为作者自有内容管线产物。实验脚本默认读 `testimg/` 目录，放入图片即可复现。

我们承诺：所有数字为本机实测，所有局限如实标注，官方口径与第三方实测分开标注。

## License

MIT（本仓库代码）。JPEG AI 参考软件部分遵循其原有 BSD 协议。
