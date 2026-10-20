"""方向③：AIGC 20 图 × cheng q1/q3/q6 + AVIF q20/45/75 → bpp/PSNR/LPIPS"""
import io, json, math, glob, os
import torch, pillow_avif  # noqa
from PIL import Image
import torchvision.transforms as T
import torch.nn.functional as F
from compressai import zoo
import lpips as lpips_lib

lpips_fn = lpips_lib.LPIPS(net="alex").eval()
def psnr(a, b):
    mse = torch.mean((a-b)**2).item()
    return 20*math.log10(1.0/math.sqrt(mse)) if mse>0 else 99.0

nets = {q: zoo.cheng2020_attn(quality=q, pretrained=True).eval() for q in [1,3,6]}
rows = []
for path in sorted(glob.glob("testimg/aigc/*")) + ["testimg/aigc_face.png","testimg/aigc_cover.jpg"]:
    name = os.path.basename(path)
    img = Image.open(path).convert("RGB")
    # 大图缩到长边 1024 控时
    if max(img.size) > 1024:
        r = 1024/max(img.size)
        img = img.resize((int(img.size[0]*r)//8*8, int(img.size[1]*r)//8*8))
    W, H = img.size
    xo = T.ToTensor()(img).unsqueeze(0)
    h, w = xo.shape[2], xo.shape[3]
    ph, pw = (h+63)//64*64 - h, (w+63)//64*64 - w
    x = F.pad(xo, (0,pw,0,ph), mode="reflect")
    for q, net in nets.items():
        with torch.no_grad():
            comp = net.compress(x)
            xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1)[:,:,:h,:w]
        nb = sum(len(s[0]) for s in comp["strings"])*8
        with torch.no_grad(): lp = lpips_fn(xo*2-1, xhat*2-1).item()
        rows.append({"image": name, "codec": f"cheng-q{q}", "bpp": round(nb/(W*H),4),
                     "psnr": round(psnr(xo,xhat),2), "lpips": round(lp,4)})
    for fmt, qs in [("AVIF",[45]),("JPEG",[50])]:
        for q in qs:
            buf = io.BytesIO(); img.save(buf, fmt, quality=q)
            nb = buf.getbuffer().nbytes*8; buf.seek(0)
            x2 = T.ToTensor()(Image.open(buf).convert("RGB")).unsqueeze(0)
            with torch.no_grad(): lp = lpips_fn(xo*2-1, x2*2-1).item()
            rows.append({"image": name, "codec": f"{fmt}-q{q}", "bpp": round(nb/(W*H),4),
                         "psnr": round(psnr(xo,x2),2), "lpips": round(lp,4)})
    print("done", name)

json.dump(rows, open("aigc_matrix_results.json","w"), indent=2, ensure_ascii=False)
import statistics
for c in ["cheng-q1","cheng-q3","cheng-q6","AVIF-q45","JPEG-q50"]:
    bpps = [r["bpp"] for r in rows if r["codec"]==c]
    psnrs = [r["psnr"] for r in rows if r["codec"]==c]
    print(f"{c:<10} bpp 中位 {statistics.median(bpps):.3f}  均值 {statistics.mean(bpps):.3f}  PSNR 均值 {statistics.mean(psnrs):.1f}")
