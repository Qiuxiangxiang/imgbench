# 大文件域压缩实测（2026-10-20）

> 对象：单文件 30MB-1.1GB 的四类资产——GLB 3D 资产、3DGS 点云、模型权重、npz 数据集。

## 实测矩阵

| 域 | 素材 | 方案 | 结果 | 判定 |
|---|---|---|---|---|
| **GLB 3D 资产** | tripoSG barrel（31.1MB） | Draco 几何压缩 | 1.6MB（**19×**） | ✅ 行业标准，加载验证通过 |
| | | meshopt | 4.9MB（6.3×） | 更快解码，倍率较低 |
| | | **meshopt+WebP 纹理全家桶** | **1.5MB（20.6×）** | ✅ 发布级推荐 |
| **3DGS 点云** | miku_herb.ply（61.5MB，26 万高斯，62 属性/个，248B/个） | 位置 f16 + SH int8 量化测算 | ~3.1×（20MB） | ⚠️ 数据级指标；渲染质量需渲染器复验 |
| **模型权重** | Audio8-TTS safetensors（1.12GB） | zstd-3 | 0.87GB（1.29×），**2 秒** | ✅ 归档/传输白捡 |
| | | zstd-19 | 0.87GB（同），**351 秒** | ❌ 同倍率慢 175 倍，别用高档 |
| **npz 数据集** | trajectories_20k（73MB） | zstd-19 | 73.4MB（**0.99× 反涨**） | ❌ npz 内部已 deflate，外压无意义 |

## 断言

1. **GLB 是大文件域最大的白捡空间**：gltf-transform 一条命令 20 倍，游戏/Web3D 资产直接可用（你的 char3d-pipeline 产物就该走这条）
2. **权重文件（f16 浮点）熵高，无损外压只有 1.3×**：要再小只能量化（f16→int8/int4），那是模型质量敏感的活——需推理验证，接 model-router 的领域
3. **zstd 永远用 -3 档**：-19 在同熵数据上零收益慢 175 倍，实测证伪「更高档更省」的直觉
4. **已压缩容器（npz/usdz/jxl 等）别再外压**：实测反涨。先认容器再动手
5. **3DGS 的正规军是专用压缩器**（SOG/Compact3D 系 10-20×），量化 DIY 只适合传输应急；它们的评测要渲染器在环，列为下一步

## 复现

`bigfile_test/`：GLB 用 `npx @gltf-transform/cli optimize`；3DGS 分析 `ply_quantize.py`；权重 `zstd -3/-19` 计时命令如上。

## 可用性验证（2026-10-20 补，「能压≠能用」逐项实测）

| 产物 | 验证方式 | 结果 |
|---|---|---|
| GLB+Draco | Blender 实际导入 | ✅ 905,534 顶点全在，与原文件一致 |
| GLB+meshopt / optimize | Blender 导入 | ❌ **Blender 不支持 meshopt 扩展**——meshopt 只适用于 Web/three.js 管线；要 Blender 兼容用 Draco |
| 视频 x264/x265/AV1 转码 | 全程解码 | ✅ 零错误，时长一致（47.21s） |
| safetensors zstd-3 | sha256 往返 | ✅ 逐位一致 |
| npz | numpy 加载 | ✅ 正常（但外压无收益，别压） |
| EXR 各变体 | 复原+通道+crypto 逐位 | ✅ 昨日已验（crypto PASS，78 通道完整） |

**GLB 修正结论**：Blender/生产管线用 **Draco**（19×）；Web 发布可用 meshopt 全家桶（20.6×）但别进 Blender。
