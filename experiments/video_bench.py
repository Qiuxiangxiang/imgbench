"""视频编码矩阵：5 路线 × 体积/耗时/SSIM/PSNR"""
import os, subprocess, time, json, re

FF = "/opt/homebrew/bin/ffmpeg"
FFP = "/opt/homebrew/bin/ffprobe"
V = os.path.expanduser("~/dev/workflow/sd_mcn/projects/holdovers-essay/v_seg5.mp4")
ORIG = os.path.getsize(V)

ROUTES = [
    ("x264_crf23",  ["-c:v","libx264","-crf","23","-preset","medium"], "mp4"),
    ("h264_hw",     ["-c:v","h264_videotoolbox","-q:v","60"], "mp4"),
    ("x265_crf28",  ["-c:v","libx265","-crf","28","-preset","medium","-tag:v","hvc1"], "mp4"),
    ("hevc_hw",     ["-c:v","hevc_videotoolbox","-q:v","60","-tag:v","hvc1"], "mp4"),
    ("svtav1_crf35",["-c:v","libsvtav1","-crf","35","-preset","8"], "mp4"),
]
rows = []
for tag, args, ext in ROUTES:
    out = f"out_{tag}.{ext}"
    t0 = time.time()
    r = subprocess.run([FF,"-hide_banner","-loglevel","error","-y","-i",V,"-c:a","copy",*args,out],
                       capture_output=True, text=True)
    dt = time.time() - t0
    if r.returncode or not os.path.exists(out):
        print(f"{tag} 编码失败: {r.stderr[-200:]}"); continue
    # SSIM/PSNR vs 源
    m = subprocess.run([FF,"-hide_banner","-i",out,"-i",V,
                        "-lavfi","ssim;[0:v][1:v]psnr","-f","null","-"],
                       capture_output=True, text=True).stderr
    ssim = re.findall(r"All:([\d.]+)", m)
    psnr = re.findall(r"average:([\d.inf]+)", m)
    rows.append({"route": tag, "bytes": os.path.getsize(out), "enc_s": round(dt,1),
                 "ssim": float(ssim[0]) if ssim else None,
                 "psnr": float(psnr[0]) if psnr and psnr[0]!="inf" else 99.0})
    print(f"{tag:<14} {os.path.getsize(out)/1048576:>5.2f}MB  {dt:>5.1f}s  SSIM {ssim[0] if ssim else '?'}  PSNR {psnr[0] if psnr else '?'}")

json.dump({"source_bytes": ORIG, "rows": rows}, open("video_bench_results.json","w"), indent=2)
print(f"\n源文件 {ORIG/1048576:.2f}MB")
for r in rows:
    print(f"{r['route']:<14} 压缩 {ORIG/r['bytes']:.1f}×")
