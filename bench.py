#!/usr/bin/env python3
"""imgbench — 消费硬件图片编解码一键 benchmark（方向②工具包雏形）

用法:
  python bench.py <图片或目录> [--codecs cheng,jpeg,avif,jpegai] [--out results.json]
例:
  python bench.py testimg/kodim23.png
  python bench.py testimg/aigc/ --codecs cheng,avif
"""
import argparse, io, json, math, os, subprocess, sys, time
import torch
import torchvision.transforms as T
import torch.nn.functional as F
from PIL import Image

def psnr(a, b):
    mse = torch.mean((a-b)**2).item()
    return 20*math.log10(1.0/math.sqrt(mse)) if mse>0 else 99.0

_lpips = None
def lpips_val(a, b):
    global _lpips
    if _lpips is None:
        import lpips as L; _lpips = L.LPIPS(net="alex").eval()
    with torch.no_grad():
        return _lpips(a*2-1, b*2-1).item()

def load_img(path, max_side=1024):
    img = Image.open(path).convert("RGB")
    if max(img.size) > max_side:
        r = max_side/max(img.size)
        img = img.resize((int(img.size[0]*r)//8*8, int(img.size[1]*r)//8*8))
    return img

def bench_cheng(img, qs=(1,3,6)):
    from compressai import zoo
    xo = T.ToTensor()(img).unsqueeze(0)
    h, w = xo.shape[2], xo.shape[3]
    x = F.pad(xo, (0,(w+63)//64*64-w,0,(h+63)//64*64-h), mode="reflect")
    W, H = img.size
    out = []
    for q in qs:
        net = zoo.cheng2020_attn(quality=q, pretrained=True).eval()
        with torch.no_grad():
            t0=time.time(); comp = net.compress(x); t1=time.time()
            xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1)[:,:,:h,:w]; t2=time.time()
        nb = sum(len(s[0]) for s in comp["strings"])*8
        out.append({"codec": f"cheng-q{q}", "bpp": round(nb/(W*H),4),
                    "psnr": round(psnr(xo,xhat),2), "lpips": round(lpips_val(xo,xhat),4),
                    "enc_s": round(t1-t0,2), "dec_s": round(t2-t1,2)})
        del net
    return out

def bench_trad(img, fmt, qs):
    W, H = img.size
    xo = T.ToTensor()(img).unsqueeze(0)
    out = []
    for q in qs:
        buf = io.BytesIO(); t0=time.time(); img.save(buf, fmt, quality=q); t1=time.time()
        nb = buf.getbuffer().nbytes*8; buf.seek(0)
        x2 = T.ToTensor()(Image.open(buf).convert("RGB")).unsqueeze(0)
        out.append({"codec": f"{fmt}-q{q}", "bpp": round(nb/(W*H),4),
                    "psnr": round(psnr(xo,x2),2), "lpips": round(lpips_val(xo,x2),4),
                    "enc_s": round(t1-t0,3)})
    return out

def bench_jpegai(img, targets=(12,25)):
    """调 jpeg-ai-rs 参考实现（需已完成 M2 移植）"""
    import tempfile
    # JPEG AI 参考软件路径：环境变量 JPEGAI_RS 指定，或本仓库同级目录 jpeg-ai-rs
    rs = os.environ.get("JPEGAI_RS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "jpeg-ai-rs")
    if not os.path.isdir(rs):
        return [{"codec": "jpegai", "error": "jpeg-ai-rs 未就绪"}]
    W, H = img.size
    xo = T.ToTensor()(img).unsqueeze(0)
    out = []
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.png"); img.save(src)
        for t in targets:
            jai = os.path.join(td, f"o{t}.jai"); png = os.path.join(td, f"o{t}.png")
            env = dict(os.environ, PYTHONPATH=rs)
            py = os.environ.get("JPEGAI_PY", sys.executable)
            t0=time.time()
            r1 = subprocess.run([py,"-m","src.reco.coders.encoder",src,jai,"--set_target_bpp",str(t)],
                                cwd=rs, env=env, capture_output=True)
            t1=time.time()
            r2 = subprocess.run([py,"-m","src.reco.coders.decoder",jai,png],
                                cwd=rs, env=env, capture_output=True)
            t2=time.time()
            if r1.returncode or r2.returncode or not os.path.exists(png):
                out.append({"codec": f"jpegai-t{t}", "error": "编解码失败"}); continue
            x2 = T.ToTensor()(Image.open(png).convert("RGB")).unsqueeze(0)
            nb = os.path.getsize(jai)*8
            out.append({"codec": f"jpegai-t{t}", "bpp": round(nb/(W*H),4),
                        "psnr": round(psnr(xo,x2),2), "lpips": round(lpips_val(xo,x2),4),
                        "enc_s": round(t1-t0,1), "dec_s": round(t2-t1,1)})
    return out

def main():
    ap = argparse.ArgumentParser(description="imgbench: 图片编解码 benchmark")
    ap.add_argument("input")
    ap.add_argument("--codecs", default="cheng,jpeg,avif")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    import pillow_avif  # noqa

    paths = sorted(glob.glob(os.path.join(a.input, "*"))) if os.path.isdir(a.input) else [a.input]
    paths = [p for p in paths if p.lower().endswith((".png",".jpg",".jpeg",".webp"))]
    codecs = set(a.codecs.split(","))
    all_rows = []
    for p in paths:
        img = load_img(p)
        rows = []
        if "cheng" in codecs: rows += bench_cheng(img)
        if "jpeg" in codecs: rows += bench_trad(img, "JPEG", (15,50,90))
        if "avif" in codecs: rows += bench_trad(img, "AVIF", (20,45,75))
        if "jxl" in codecs:
            try:
                import pillow_jxl  # noqa
                rows += bench_trad(img, "JXL", (50,75,90))
            except ImportError:
                rows.append({"codec": "jxl", "error": "需 pillow-jxl-plugin + brew jpeg-xl"})
        if "jpegai" in codecs: rows += bench_jpegai(img)
        for r in rows: r["image"] = os.path.basename(p)
        all_rows += rows
        print(f"== {os.path.basename(p)}")
        for r in rows:
            if "error" in r: print(f"  {r['codec']:<12} {r['error']}"); continue
            print(f"  {r['codec']:<12} {r['bpp']:>7.3f}bpp  PSNR {r['psnr']:>6.2f}  LPIPS {r['lpips']:.4f}")
    out = a.out or "bench_results.json"
    json.dump(all_rows, open(out,"w"), indent=2, ensure_ascii=False)
    print(f"\n→ {out}（{len(all_rows)} 行）")

if __name__ == "__main__":
    import glob
    main()
