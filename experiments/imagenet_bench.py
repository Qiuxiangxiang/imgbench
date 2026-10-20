"""ImageNet 子集规模验证：压缩前后数据规模降低倍率
用法: python imagenet_bench.py --n 100 [--jpegai-n 20]
"""
import argparse, io, json, math, os, time, glob
import torch, pillow_avif
import torchvision.transforms as T
import torch.nn.functional as F
from PIL import Image
from compressai import zoo

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=100)
ap.add_argument("--src", default="testimg/imagenet-sample")
ap.add_argument("--out", default="imagenet_bench_results.json")
a = ap.parse_args()

def psnr(a_, b_):
    mse = torch.mean((a_-b_)**2).item()
    return 20*math.log10(1.0/math.sqrt(mse)) if mse>0 else 99.0

paths = sorted(glob.glob(f"{a.src}/*.JPEG") + glob.glob(f"{a.src}/*.jpg") + glob.glob(f"{a.src}/*.png"))[:a.n]
print(f"样本 {len(paths)} 张")

nets = {q: zoo.cheng2020_attn(quality=q, pretrained=True).eval() for q in [1,3,6]}
rows = []
for i, p in enumerate(paths):
    try:
        img = Image.open(p).convert("RGB")
    except Exception:
        continue
    W, H = img.size
    orig_bytes = os.path.getsize(p)
    raw_bytes = W*H*3
    xo = T.ToTensor()(img).unsqueeze(0)
    h, w = xo.shape[2], xo.shape[3]
    x = F.pad(xo, (0,(w+63)//64*64-w,0,(h+63)//64*64-h), mode="reflect")
    rec = {"image": os.path.basename(p), "w": W, "h": H,
           "orig_bytes": orig_bytes, "raw_bytes": raw_bytes}
    for q, net in nets.items():
        with torch.no_grad():
            comp = net.compress(x)
            xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1)[:,:,:h,:w]
        nb = sum(len(s[0]) for s in comp["strings"])*8
        rec[f"cheng_q{q}_bytes"] = nb//8
        rec[f"cheng_q{q}_psnr"] = round(psnr(xo,xhat),2)
    for fmt, q, tag in [("JPEG",75,"jpeg75"),("AVIF",45,"avif45")]:
        buf = io.BytesIO(); img.save(buf, fmt, quality=q)
        rec[f"{tag}_bytes"] = buf.getbuffer().nbytes
    rows.append(rec)
    if (i+1) % 20 == 0: print(f"  {i+1}/{len(paths)}")

json.dump(rows, open(a.out,"w"), indent=2)
# 聚合
import statistics as st
tot_orig = sum(r["orig_bytes"] for r in rows)
tot_raw = sum(r["raw_bytes"] for r in rows)
print(f"\n=== 数据规模汇总（{len(rows)} 张）===")
print(f"原始文件（JPEG 分发态）: {tot_orig/1048576:.1f} MB")
print(f"无损 RGB 体积:           {tot_raw/1048576:.1f} MB")
for k, label in [("cheng_q1","cheng-q1(低码率)"),("cheng_q3","cheng-q3(中)"),("cheng_q6","cheng-q6(高)"),
                 ("avif45","AVIF-q45"),("jpeg75","JPEG-q75")]:
    tot = sum(r[f"{k}_bytes"] for r in rows)
    ps = [r[f"{k}_psnr"] for r in rows if f"{k}_psnr" in r]
    psnr_s = f"PSNR 中位 {st.median(ps):.1f}" if ps else ""
    print(f"{label:<16} {tot/1048576:>7.1f} MB  vs原图 {tot_orig/tot:>5.1f}×  vs无损 {tot_raw/tot:>5.1f}×  {psnr_s}")
