#!/bin/bash
# restore_exr — EXR 压缩变体复原工具
# 用法: ./restore_exr.sh <压缩后的.exr> [输出目录]
# 产出: <out>/<名>_restored.exr（float32/zip 全精度生产格式）+ <名>_preview.png（gamma 预览）
set -e
IN="$1"; OUT="${2:-./restored}"
mkdir -p "$OUT"
N=$(basename "$IN" .exr)
# 1) 复原为生产格式（float32 zip，所有通道保留）
oiiotool "$IN" -d float --compression zip -o "$OUT/${N}_restored.exr"
# 2) beauty 预览 PNG（gamma 2.2 + clip）
oiiotool "$IN" --ch R,G,B --powc 0.4545,0.4545,0.4545 --clamp -d uint8 -o "$OUT/${N}_preview.png"
echo "✓ $N → restored.exr + preview.png  ($OUT/)"
