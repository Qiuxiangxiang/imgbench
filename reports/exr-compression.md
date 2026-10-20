# EXR 压缩实测：masterLayer.0001.exr（2026-10-20）

> 对象：桌面 `masterLayer.0001.exr`（Arnold 7.0 渲染输出，1920×1080，**66 通道全 float32**，
> zip 无损，19.19 MB）。含 beauty(RGBA) + N/P/Z + cryptomatte(asset/material/object 各3级) +
> diffuse/emission/specular/transmission/volume/shadow_matte 光路 AOV。
> 文件名带帧号（.0001），疑似序列帧首帧——若是序列，所有倍率按帧数放大。

## 方案矩阵（M2 本机实测）

| 方案 | 体积 | 倍率 | beauty 质量 | 判定 |
|---|---|---|---|---|
| 原始 zip/float32 | 19.19 MB | 1× | 无损 | 基准 |
| DWAA 全通道 | 10.26 MB | 1.9× | beauty 视觉无损（最大误差 0.8%@101 极亮像素） | ❌ **cryptomatte 被毁，生产不可用** |
| DWAB 全通道 | 10.40 MB | 1.8× | 同上 | ❌ 同上且不优于 DWAA |
| half 全通道 | 4.33 MB | 4.4× | crypto 转 half 后 ID 精度受损 | ⚠️ 糙用可，合成不可 |
| **half + crypto 保 float32** | **5.62 MB** | **3.4×** | crypto 完整；beauty 最大相对误差 0.03% | ✅ **生产推荐** |
| 双文件（颜色 DWAA + 工具 zip/f32） | 14.68 MB | 1.3× | 全保 | ❌ 本帧 crypto 太重，不如上一行 |
| beauty-only（RGBA, half+DWAA） | 0.53 MB | **36×** | 只留美颜层 | ✅ 审片/交付/归档预览 |
| SDR 预览 AVIF-q50 | 10 KB | **~1900×** | PSNR 46.9（对 gamma 预览图） | ✅ 评审/微信发送 |

## 结论与建议

1. **此帧的体积大头不是 beauty 是工具通道**：66 通道里 crypto 系（27 通道 float32）+ N/P/Z 占绝对大头。
   纯 DWAA 只省 1.9× 就是因为 DWAA 对这些离散 ID 数据无能为力（还会毁掉它们）
2. **生产管线推荐 `half + crypto 保 float32`**：3.4× 缩减，零合成风险。Arnold 默认全 float32 是浪费——
   颜色类 AOV 用 half 是行业惯例（float16 精度对颜色足够）
3. **如果下游只用 beauty**（审片/成片）：抽 RGBA 单独存，36×；再退到 SDR 预览则千倍级
4. **若是序列帧**：19MB/帧 × 帧数 ×3.4× 起步；100 帧动画 = 1.9GB → 560MB（生产档）或 53MB（beauty-only）
5. **DWAA/DWAB 的正确用法**：只用于纯颜色帧（无 crypto）；本帧 DWAB 反而不优于 DWAA（小图块效应）

## 复现

全部命令用 oiiotool（brew openimageio）；产物与脚本在 `codec-lab/exr_test/`。

## 复原验证（2026-10-20 补）

**复原工具**：`experiments/restore_exr.sh`——输入任何压缩变体，输出 float32/zip 生产格式 EXR + gamma 预览 PNG。
四个变体全部复原成功，实测：

| 变体 | beauty 复原误差 | crypto 逐位一致 | 通道完整 | 可逆性 |
|---|---|---|---|---|
| half+crypto保f32（推荐） | max 0.03% @ 极亮像素 | ✅ **PASS（逐位相同）** | ✅ 78/78 | 视觉无损，bit 级不可逆（float32→16 精度） |
| half 全转 | 同上 | ⚠️ crypto 精度降级 | ✅ 78/78 | 生产不推荐 |
| DWAA | max 0.8% @ 极亮像素 | ❌ crypto 报废 | ✅ | 有损不可逆 |
| beauty-only | 同 DWAA | （本来就不含） | 4/78（设计如此） | 有损，只含美颜层 |

**可逆性结论**：EXR 各方案的「复原」= 还原成任何合成软件（Nuke/Blender/DaVinci）都能打开的标准 EXR。
推荐方案下 crypto 遮罩逐位一致、颜色误差 0.03%（远低于人眼与显示器精度）。
要 bit 级完全可逆只有一个办法：不换精度只换 zip 打包方式（体积不变，无意义）。
