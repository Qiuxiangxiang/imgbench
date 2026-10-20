"""字号梯度·多分辨率复验：同 pt 字号在 1536 宽画布（像素字高翻倍）"""
import io, json, difflib
import torch, pillow_avif
from PIL import Image, ImageDraw, ImageFont
import torchvision.transforms as T
import torch.nn.functional as F
from compressai import zoo

SIZES = [8, 10, 12, 14, 18, 24, 32, 48]
W0, H0 = 1536, 1280
img = Image.new("RGB", (W0, H0), (250, 248, 243))
d = ImageDraw.Draw(img)
y = 30; lines = []
for sz in SIZES:
    f = None
    for p in ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/Helvetica.ttc"]:
        try: f = ImageFont.truetype(p, sz*2); break  # pt→像素近似 ×2
        except Exception: continue
    t = f"{sz}pt 订单 KM-2026 金额 ¥3,580 ABcd"
    d.text((40, y), t, font=f, fill=(20, 20, 25))
    lines.append((sz, t, y, sz*2))
    y += sz*2 + 30
img = img.crop((0, 0, W0, min(H0, y+10)))
img.save("testimg/font_ladder_2x.png")
W, H = img.size

from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
def ocr_lines(pil_img):
    out = {}
    for sz, gt, yy, px in lines:
        band = pil_img.crop((0, max(0,yy-6), W, min(H, yy+px+14)))
        res, _ = ocr(band)
        out[sz] = difflib.SequenceMatcher(None, gt, res[0][1] if res else "").ratio()
    return out

xo = T.ToTensor()(img).unsqueeze(0)
h, w = xo.shape[2], xo.shape[3]
x = F.pad(xo, (0,(w+63)//64*64-w,0,(h+63)//64*64-h), mode="reflect")
results = {"original": ocr_lines(img)}
for q in [1, 3]:
    net = zoo.cheng2020_attn(quality=q, pretrained=True).eval()
    with torch.no_grad():
        comp = net.compress(x)
        xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1)[:,:,:h,:w]
    nb = sum(len(s[0]) for s in comp["strings"])*8
    results[f"cheng-q{q}@{nb/(W*H):.3f}bpp"] = ocr_lines(T.ToPILImage()(xhat.squeeze(0)))
    del net
for fmt, q in [("AVIF",20)]:
    buf = io.BytesIO(); img.save(buf, fmt, quality=q)
    nb = buf.getbuffer().nbytes*8; buf.seek(0)
    results[f"{fmt}-q{q}@{nb/(W*H):.4f}bpp"] = ocr_lines(Image.open(buf).convert("RGB"))

json.dump(results, open("font_gradient_2x_results.json","w"), indent=2, ensure_ascii=False)
print("1536宽(字高×2):".ljust(24) + "".join(f"{s}pt".rjust(7) for s in SIZES))
for k, v in results.items():
    print(k.ljust(24) + "".join(f"{v[s]:.2f}".rjust(7) for s in SIZES))
