# JPEG AI 参考软件 · Apple Silicon 移植补丁

官方仓库：https://gitlab.com/wg1/jpeg-ai/jpeg-ai-reference-software
（ISO/IEC 6048-3 参考实现，BSD 协议；注意 BSD 不覆盖标准可能的专利权）

## 移植步骤（M 系列 Mac 实测通过，M2 / macOS 26）

```bash
git clone https://gitlab.com/wg1/jpeg-ai/jpeg-ai-reference-software.git
cd jpeg-ai-reference-software && git lfs pull          # 模型权重（~1GB）

# 1) 应用 Python 补丁（2 个文件）
git apply /path/to/jpegai-apple-silicon.patch

# 2) 现代依赖（不要用官方 requirements.txt 的 2022 年钉版，除 ptflops 外）
pip install torch numpy==1.26.4 addict einops opencv-python-headless \
    prettytable psutil "ptflops==0.6.5" pynvml commentjson GPUtil pybind11 pandas

# 3) 构建两个 C++ 熵编码扩展
brew install libomp
bash /path/to/build_ec_mac.sh

# 4) 编解码
PYTHONPATH=. python -m src.reco.coders.encoder in.png out.jai --set_target_bpp 25  # 0.25bpp
PYTHONPATH=. python -m src.reco.coders.decoder out.jai rec.png
```

## 补丁内容

| 文件 | 改动 | 原因 |
|---|---|---|
| `gpu_memory_usage.py` | pynvml 导入 try/except 退化 | 新版 pynvml 无 `.smi` 子模块；Mac 无 NVIDIA |
| `ec_lib_mans.py` | `torch.load(..., weights_only=False)` | torch 2.6+ 默认拒载熵编码缓存（官方可信文件） |
| `build_ec_mac.sh`（新增脚本） | clang++ 构建 me-tANS/direct 扩展 | 官方 Makefile 依赖 gcc OpenMP；macOS 需 libomp + `-undefined dynamic_lookup` |
| 环境 | numpy==1.26.4 | numpy 2.x 标量转换破坏 Exp-Golomb 解码 |

实测：kodim23（768×512）编码 5.7s / 解码 9.7s（CPU），0.057 bpp 默认档往返成功。
