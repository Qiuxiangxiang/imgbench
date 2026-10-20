"""论文级加固：全量 Kodak(24) + AIGC(20) 的 cheng-q3 bpp × 高频能量 配对"""
import json, math, glob, os
import numpy as np, torch
import torch.nn.functional as F
import torchvision.transforms as T
from PIL import Image
from compressai import zoo

def radial_hi(img, size=512):
    g = img.convert("L").resize((size, size))
    a = np.asarray(g, dtype=np.float64); a -= a.mean()
    F2 = np.fft.fftshift(np.abs(np.fft.fft2(a))**2)
    yy, xx = np.mgrid[0:size, 0:size]
    r = np.sqrt((yy-size//2)**2 + (xx-size//2)**2).astype(int)
    return float(F2[r > size//4].sum() / F2.sum())

net = zoo.cheng2020_attn(quality=3, pretrained=True).eval()
base = "testimg"
sets = [("natural", sorted(glob.glob(f"{base}/kodim*.png"))),
        ("aigc", sorted(glob.glob(f"{base}/aigc/*")) + [f"{base}/aigc_face.png", f"{base}/aigc_cover.jpg"])]
rows = []
for kind, paths in sets:
    for p in paths:
        img = Image.open(p).convert("RGB")
        if max(img.size) > 1024:
            r = 1024/max(img.size)
            img = img.resize((int(img.size[0]*r)//8*8, int(img.size[1]*r)//8*8))
        W, H = img.size
        xo = T.ToTensor()(img).unsqueeze(0)
        h, w = xo.shape[2], xo.shape[3]
        x = F.pad(xo, (0,(w+63)//64*64-w,0,(h+63)//64*64-h), mode="reflect")
        with torch.no_grad():
            comp = net.compress(x)
        nb = sum(len(s[0]) for s in comp["strings"])*8
        rows.append({"image": os.path.basename(p), "kind": kind,
                     "bpp": round(nb/(W*H),4), "hi_freq": round(radial_hi(img),4)})
        print("done", kind, os.path.basename(p))
json.dump(rows, open("spectral_bpp_results.json","w"), indent=2, ensure_ascii=False)

nat = [r["bpp"] for r in rows if r["kind"]=="natural"]
aig = [r["bpp"] for r in rows if r["kind"]=="aigc"]
print(f"\ncheng-q3 bpp: natural n={len(nat)} 中位 {np.median(nat):.3f} | aigc n={len(aig)} 中位 {np.median(aig):.3f} | 比值 {np.median(nat)/np.median(aig):.2f}×")
# 相关性：高频能量 vs bpp
hf = [r["hi_freq"] for r in rows]; bp = [r["bpp"] for r in rows]
print(f"高频能量×bpp 相关系数 r = {np.corrcoef(hf, bp)[0,1]:.3f}（全体 44 张）")
