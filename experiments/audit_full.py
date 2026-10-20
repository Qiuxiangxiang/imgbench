"""全量审计矩阵：8 图 × 3 codec 族 × PSNR/LPIPS/OCR"""
import io, json, math, time, difflib, os
import torch, pillow_avif  # noqa
from PIL import Image
import torchvision.transforms as T
from compressai import zoo
import lpips as lpips_lib

GT = {
 "text_dense.png": "2026 年度影像报告\nCompression ratio: 0.05 bpp achieved\n订单编号 KM-2026-0917 金额 ¥3,580.00\n分辨率 768x512 帧率 23.976fps 码率 8Mbps\nThe quick brown fox jumps over 13 lazy dogs.\n电话 138-0013-8000 邮箱 test@example.com\n合格率 98.7% 不良率 0.3% 批次 A-2206\n第 42 章节 · 实验数据汇总\nGPS: 31.2304° N, 121.4737° E 海拔 4m\nSerial: SN-8842-XKCD-2026-AB",
 "text_poster.png": "限时特惠 ¥99.00 起\n活动截止 2026-11-11 23:59\n券码 DOUBLE-ELEVEN-2026\n库存 8,888 件 已售 6,543 件\n客服热线 400-888-1234",
 "text_subtitle.png": "第 3 集：他转身离开了 137 号公路\nEP03 1080P",
}
IMAGES = ["kodim01.png","kodim08.png","kodim15.png","kodim23.png",
          "aigc_face.png","aigc_cover.jpg",
          "text_dense.png","text_poster.png","text_subtitle.png"]

lpips_fn = lpips_lib.LPIPS(net="alex").eval()
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()

def ocr_acc(pil, gt):
    res, _ = ocr(pil)
    text = "\n".join(r[1] for r in res) if res else ""
    return difflib.SequenceMatcher(None, gt, text).ratio()

def psnr(a, b):
    mse = torch.mean((a-b)**2).item()
    return 20*math.log10(1.0/math.sqrt(mse)) if mse>0 else 99.0

def lpips_val(a, b):
    with torch.no_grad():
        return lpips_fn(a*2-1, b*2-1).item()

nets = {q: zoo.cheng2020_attn(quality=q, pretrained=True).eval() for q in [1,3,6]}
rows = []
for name in IMAGES:
    path = f"testimg/{name}"
    img = Image.open(path).convert("RGB")
    W, H = img.size
    xo = T.ToTensor()(img).unsqueeze(0)   # 原始尺寸，指标基准
    import torch.nn.functional as F
    h, w = xo.shape[2], xo.shape[3]
    ph = max(256, (h + 63) // 64 * 64) - h
    pw = max(256, (w + 63) // 64 * 64) - w
    x = F.pad(xo, (0, pw, 0, ph), mode="reflect")  # cheng 专用 padded
    gt = GT.get(name)
    kind = "text" if gt else ("aigc" if name.startswith("aigc") else "natural")
    base = {"image": name, "kind": kind, "codec": "original",
            "ocr": round(ocr_acc(img, gt),3) if gt else None}
    rows.append(base)

    for q, net in nets.items():
        with torch.no_grad():
            t0=time.time(); comp = net.compress(x); t1=time.time()
            xhat = net.decompress(comp["strings"], comp["shape"])["x_hat"].clamp(0,1); t2=time.time()
        nb = sum(len(s[0]) for s in comp["strings"])*8
        xhat = xhat[:, :, :h, :w]
        rec = T.ToPILImage()(xhat.squeeze(0))
        rows.append({"image": name, "kind": kind, "codec": f"cheng-q{q}",
                     "bpp": round(nb/(W*H),4), "psnr": round(psnr(xo,xhat),2),
                     "lpips": round(lpips_val(xo,xhat),4),
                     "ocr": round(ocr_acc(rec, gt),3) if gt else None,
                     "enc_s": round(t1-t0,2), "dec_s": round(t2-t1,2)})
    for fmt, qs in [("JPEG",[15,50,90]), ("AVIF",[20,45,75])]:
        for q in qs:
            buf = io.BytesIO(); img.save(buf, fmt, quality=q)
            nb = buf.getbuffer().nbytes*8; buf.seek(0)
            r = Image.open(buf).convert("RGB")
            x2 = T.ToTensor()(r).unsqueeze(0)
            rows.append({"image": name, "kind": kind, "codec": f"{fmt}-q{q}",
                         "bpp": round(nb/(W*H),4), "psnr": round(psnr(xo,x2),2),
                         "lpips": round(lpips_val(xo,x2),4),
                         "ocr": round(ocr_acc(r, gt),3) if gt else None})
    print(f"done: {name}")

json.dump(rows, open("audit_full_results.json","w"), indent=2, ensure_ascii=False)
print(f"\n总数据点 {len(rows)}")
