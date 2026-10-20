"""Blender headless：生成带动画的细分网格并导出 Alembic 缓存"""
import bpy, math
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6)  # ~40k 顶点
obj = bpy.context.active_object
obj.scale = (2, 2, 2)
# 50 帧动画：顶点级噪声变形 + 位移
import random
random.seed(7)
for f in range(1, 51):
    s = 1 + 0.3 * math.sin(f * 0.25)
    obj.scale = (2*s, 2*s, 2*s)
    obj.location = (math.sin(f*0.1)*2, 0, math.cos(f*0.1))
    obj.keyframe_insert("scale"); obj.keyframe_insert("location")
    # 顶点噪声（模拟布料/粒子的顶点级动画）
    for v in obj.data.vertices:
        v.co.x += random.uniform(-0.002, 0.002)
        v.co.y += random.uniform(-0.002, 0.002)
    obj.data.update()
bpy.ops.wm.alembic_export(filepath="cloth_sim.abc", start=1, end=50,
                          xsamples=1, gsamples=1, sh_open=0, flatten=False)
print("ABC exported")
