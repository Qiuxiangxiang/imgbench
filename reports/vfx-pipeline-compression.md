# 渲染特效管线压缩实测（2026-10-20）

> 素材：OpenVDB 官方 bunny_cloud.vdb（72.8MB 体积云）、Blender 现场生成的 50 帧顶点动画 Alembic、500 对象 .blend 工程。
> 工具：oiiotool / vdb_print / zstd / xz / Blender headless。

## 实测矩阵

| 格式 | 原始 | 最优方案 | 倍率 | 性质 |
|---|---|---|---|---|
| **VDB 体积云** | 72.78 MB | xz -9 外压 → 60.3 MB | 1.2× | VDB **内部已带 zip/blosc 压缩**，外压收益小 |
| **Alembic 动画缓存** | 1.45 MB | gzip -9 → 0.49 MB | **3.0×** | Ogawa 容器冗余大，外压显著 |
| **.blend 工程** | 13.86 MB | **自带压缩开关** → 0.74 MB | **18.7×** | 无损！只是保存时一个勾选项 |
| EXR 渲染层 | 19.19 MB | half+crypto保f32 → 5.62 MB | 3.4× | （昨日已交付） |

## 渲染特效管线的压缩地图（按资产类型）

| 资产 | 格式 | 正确姿势 | 坑 |
|---|---|---|---|
| 渲染帧 | EXR | half+crypto保f32（3.4×）/ beauty-only（36×） | DWAA 毁 cryptomatte |
| 体积特效 | VDB | 内部压缩已最优；再大要动 NanoVDB 量化（f32→f16/f8 网格值） | 外压只有 1.2×，别浪费时间 |
| 动画缓存 | Alembic | Ogawa + gzip/zstd 传输（3×） | 长期归档可转 USD(usdc) |
| 工程文件 | .blend | **打开自带压缩：无损 18.7×** | 默认不压，很多人不知道 |
| 贴图 | TIFF/EXR/PNG | 生产转 .tx（tiled+mipmap）；传输走 brotli | 别压源图，压的是衍生版 |
| 渲染农场传输 | 任意 | **zstd -3 流式**（速度优先于倍率） | gzip 单线程是农场瓶颈 |
| 几何/场景交换 | USD | usda（文本）→usdc（二进制）→usdz（zip 容器） | usdz 不支持外部引用，归档注意 |

## 行动清单

1. **Blender 工程立刻开压缩**：Preferences → Save & Load → Compress File（或保存对话框勾选），无损 18.7×，白捡
2. **渲染农场/节点间传输统一 zstd**：比 gzip 快 3-5 倍，倍率相当
3. **VDB 别外压**：要再小只能 NanoVDB 量化——那是降精度换体积，特效质量敏感，个案评估
4. **EXR 沿用已交付管线**（压缩+复原+验收）

## 复现

`vfx_test/`：gen_abc.py（Blender 生成 Alembic）、gen_blend.py（.blend 对照）、外压命令如上文
