import io, json, time, math
import torch
from PIL import Image
from compressai import zoo

IMG = "testimg/kodim23.png"
img = Image.open(IMG).convert("RGB")
W, H = img.size
x = torch.from_numpy(torch.ByteTensor(torch.ByteStorage.from_buffer(img.tobytes())).numpy().copy()
     ).permute(2,0,1).float().div_(255).unsqueeze(0) if False else None
# simpler load
import torchvision.transforms as T
x = T.ToTensor()(img).unsqueeze(0)

def psnr(a, b):
    mse = torch.mean((a - b) ** 2).item()
    return 20 * math.log10(1.0 / math.sqrt(mse)) if mse > 0 else 99.0

results = []
for dev in (["mps", "cpu"] if torch.backends.mps.is_available() else ["cpu"]):
    xd = x.to(dev)
    for q in [1, 3, 6]:
        net = zoo.cheng2020_attn(quality=q, pretrained=True).eval().to(dev)
        with torch.no_grad():
            t0 = time.time(); comp = net.compress(xd); t1 = time.time()
            dec = net.decompress(comp["strings"], comp["shape"]); t2 = time.time()
        xhat = dec["x_hat"].clamp(0, 1).cpu()
        nbits = sum(len(s[0]) for s in comp["strings"]) * 8
        results.append({
            "codec": f"cheng2020_attn-q{q}", "device": dev,
            "bpp": round(nbits / (W * H), 4),
            "psnr": round(psnr(x, xhat), 2),
            "enc_s": round(t1 - t0, 2), "dec_s": round(t2 - t1, 2),
        })
        del net
        if dev == "mps": torch.mps.empty_cache()

# 传统基线：JPEG / AVIF 同 bpp 对照
from compressai.utils import *  # noqa
def trad(fmt, quality):
    buf = io.BytesIO()
    img.save(buf, fmt, quality=quality)
    nb = buf.getbuffer().nbytes * 8
    buf.seek(0)
    x2 = T.ToTensor()(Image.open(buf).convert("RGB")).unsqueeze(0)
    return {"codec": f"{fmt}-q{quality}", "bpp": round(nb/(W*H), 4), "psnr": round(psnr(x, x2), 2)}

for q in [10, 30, 50, 75, 90]:
    results.append(trad("JPEG", q))
try:
    import pillow_avif  # noqa
    for q in [20, 40, 60, 80]:
        results.append(trad("AVIF", q))
except ImportError:
    print("pillow-avif 未装，AVIF 基线跳过")

json.dump(results, open("smoke_results.json", "w"), indent=2, ensure_ascii=False)
for r in results:
    print(r)
