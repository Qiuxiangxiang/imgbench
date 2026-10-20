"""字号梯度实验：8-48pt 阶梯，逐行 OCR，找崩坏阈值"""
import io, json, math, difflib
import torch, pillow_avif
from PIL import Image, ImageDraw, ImageFont
import torchvision.transforms as T
import torch.nn.functional as F
from compressai import zoo

SIZES = [8, 10, 12, 14, 18, 24, 32, 48]
W, H = 768, 640
img = Image.new("RGB", (W, H), (250, 248, 243))
d = ImageDraw.Draw(img)
y = 20
lines = []
for sz in SIZES:
    f = None
    for p in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/STHeiti Light.ttc"]:
        try: f = ImageFont.truetype(p, sz); break
        except Exception: continue
    assert f
    t = f"{sz}pt 订单 KM-2026 金额 ¥3,580 ABcd"
    d.text((30, y), t, font=f, fill=(20, 20, 25))
    lines.append((sz, t, y))
    y += sz + 22
img = img.crop((0, 0, W, min(H, y+10)))
img.save("testimg/font_ladder.png")
H = img.size[1]

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

def ocr_lines(pil_img):
    """逐行裁切 OCR，返回 {size: 相似度}"""
    out = {}
    for sz, gt, yy in lines:
        band = pil_img.crop((0, max(0,yy-4), W, min(pil_img.size[1], yy+sz+10)))
        res, _ = ocr(band)
        text = res[0][1] if res else ""
        out[sz] = difflib.SequenceMatcher(None, gt, text).ratio()
    return out

xo = T.ToTensor()(img).unsqueeze(0)
h, w = xo.shape[2], xo.shape[3]
ph, pw = (h+63)//64*64-h, (w+63)//64*64-w
x = F.pad(xo, (0,pw,0,ph), mode="reflect")

results = {"original": ocr_lines(img)}
for q in [1, 3, 6]:
    net = zoo.cheng2020_attn(quality=q, pretrained=True).eval()
    with torch.no_grad():
        comp = net.compress(x)
        xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1)[:,:,:h,:w]
    nb = sum(len(s[0]) for s in comp["strings"])*8
    rec = T.ToPILImage()(xhat.squeeze(0))
    results[f"cheng-q{q}@{nb/(W*H):.3f}bpp"] = ocr_lines(rec)
    del net
for fmt, q in [("AVIF",20),("AVIF",45),("JPEG",30),("JPEG",75)]:
    buf = io.BytesIO(); img.save(buf, fmt, quality=q)
    nb = buf.getbuffer().nbytes*8; buf.seek(0)
    r = Image.open(buf).convert("RGB")
    results[f"{fmt}-q{q}@{nb/(W*H):.4f}bpp"] = ocr_lines(r)

json.dump(results, open("font_gradient_results.json","w"), indent=2, ensure_ascii=False)
hdr = "codec@bpp".ljust(22) + "".join(f"{s}pt".rjust(7) for s in SIZES)
print(hdr)
for k, v in results.items():
    print(k.ljust(22) + "".join(f"{v[s]:.2f}".rjust(7) for s in SIZES))
