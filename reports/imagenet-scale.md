# ImageNet 子集规模化验证：压缩后数据规模降低多少（2026-10-20）

> 样本：ImageNet sample 公开镜像 100 张（[EliSchwartz/imagenet-sample-images](https://github.com/EliSchwartz/imagenet-sample-images)）。
> 口径：M2 本机实测；所有 codec 对同一批图；PSNR 全量补测。
> ⚠️ 已知局限：ImageNet sample 图本身已是 JPEG（带既有压缩伪影），「原始体积」是分发态 JPEG 而非 pristine 原图。

## 数据规模汇总（100 张）

| codec | 体积 | vs 原图 JPEG | vs 无损 RGB | PSNR 中位 |
|---|---|---|---|---|
| 原始文件（JPEG 分发态） | 10.8 MB | 1× | 4.8× | — |
| 无损 RGB | 51.8 MB | — | 1× | ∞ |
| **cheng-q1（低码率）** | **0.4 MB** | **24.5×** | 117.1× | 26.8（可见损伤档） |
| **cheng-q3（中）** | **0.9 MB** | **11.9×** | 56.8× | 29.2 |
| **cheng-q6（高）** | **2.6 MB** | 4.2× | 20.2× | 33.9 |
| AVIF-q45 | 1.5 MB | 7.0× | 33.6× | 30.6 |
| JPEG-q75 | 3.6 MB | 3.0× | 14.4× | 32.8 |

## 回答「数据规模降低多少」

**三个口径，按场景取用**：

1. **数据集归档/传输场景**（训练数据动辄 TB 级）：学习型中码率档 cheng-q3 把数据压到 **1/12**（对分发态 JPEG）或 **1/57**（对无损存储），PSNR 29dB 对多数训练场景可用 ⚠️ 但注意：压缩伪影对训练的影响是另一个问题（下游任务效用，正是方向①的审计范围）
2. **等质量对照**（诚实版）：cheng-q6（33.9dB）比 JPEG-q75（32.8dB）**体积更小质量更高**（0.72×）；对 AVIF-q45，cheng-q3 体积小 40% 但 PSNR 低 1.4dB——**在学习型与 AVIF 之间，ImageNet 类自然照片上差距不大**（与 Kodak 上「拦腰砍」的结论相比收窄了，如实标注差异来源：ImageNet sample 图已带 JPEG 伪影且分辨率不一）
3. **你的 MCN AIGC 场景**：之前实测 AIGC 比自然照片还好压 2-3 倍，叠加后 AIGC 图库在学习型中码率档可到 **1/20-1/30** 分发态体积

## 复现

`imagenet_bench.py --n 100`，数据 `imagenet_bench_results.json`（逐图明细：尺寸/各 codec 字节数/PSNR）。
