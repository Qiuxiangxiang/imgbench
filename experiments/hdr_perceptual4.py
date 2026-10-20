"""HDR 感知压缩 v4：log域 → {JXL16(oiiotool), AVIF12(PNG16+avifenc)} 全指标"""
import os, math, subprocess
import numpy as np
import OpenEXR, Imath

def read_rgb(path):
    f = OpenEXR.InputFile(path); h = f.header()
    dw = h["dataWindow"]; W, H = dw.max.x-dw.min.x+1, dw.max.y-dw.min.y+1
    pt = Imath.PixelType(Imath.PixelType.FLOAT)
    return np.stack([np.frombuffer(f.channel(c, pt), dtype=np.float32).reshape(H, W) for c in "RGB"], -1)
def metrics(ref, test):
    eps = 1e-6
    rel = np.abs(test-ref)/(np.abs(ref)+eps)
    rms = float(np.sqrt(np.mean(rel**2)))
    lr, lt = np.log2(np.maximum(ref,eps)), np.log2(np.maximum(test,eps))
    mse = float(np.mean((lr-lt)**2)); dr = float(lr.max()-lr.min())
    return rms, (10*math.log10(dr*dr/mse) if mse>0 else 99.0)

SRC = os.path.expanduser("~/Desktop/masterLayer.0001.exr")
ref = read_rgb(SRC)
LOG_MIN, LOG_RANGE = -10.0, 20.0

def invert(arr01):
    return np.power(2.0, arr01.astype(np.float64)*LOG_RANGE+LOG_MIN).astype(np.float32)

def oiio_read_float(p):
    subprocess.run(["oiiotool", p, "-d", "float", "-o", "/tmp/rt_read.exr"], capture_output=True)
    return read_rgb("/tmp/rt_read.exr")

print(f"{'路线':<16}{'体积':>8}{'relRMS':>10}{'logPSNR':>9}")
# JXL 阶梯
for q in [40, 70, 90, 100]:
    enc = f"rt_jxl_q{q}.jxl"
    subprocess.run(["oiiotool","beauty_logn.exr","--clamp","-d","uint16","--quality",str(q),"-o",enc], capture_output=True)
    rec = invert(oiio_read_float(enc))
    rms, ps = metrics(ref, rec)
    print(f"log→JXL16 q{q:<3}  {os.path.getsize(enc)/1024:>6.0f}KB  {rms:>8.5f}  {ps:>7.1f}dB")
# AVIF 阶梯（PNG16 → avifenc → avifdec -d16 → PNG16）
for q in [40, 70, 90]:
    enc = f"rt_avif_q{q}.avif"
    subprocess.run(["avifenc","--depth","12","--yuv","444","--range","full","-q",str(q),
                    "beauty_logn16.png", enc], capture_output=True)
    subprocess.run(["avifdec","-d","16",enc,f"/tmp/rt_avif_{q}.png"], capture_output=True)
    rec = invert(oiio_read_float(f"/tmp/rt_avif_{q}.png"))
    rms, ps = metrics(ref, rec)
    print(f"log→AVIF12 q{q:<3}  {os.path.getsize(enc)/1024:>6.0f}KB  {rms:>8.5f}  {ps:>7.1f}dB")
# 对照
for p, tag in [("orig_rgba.exr","f32-zip"),("half_rgba.exr","half-f16"),("dwaa_rgba.exr","DWAA-q45")]:
    r2 = read_rgb(p); rms, ps = metrics(ref, r2)
    print(f"{tag:<16}  {os.path.getsize(p)/1024:>6.0f}KB  {rms:>8.6f}  {ps:>7.1f}dB")
