import bpy, random
bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(3)
# 铺 500 个带材质的对象（模拟真实工程复杂度）
for i in range(500):
    bpy.ops.mesh.primitive_cube_add(location=(random.uniform(-20,20), random.uniform(-20,20), random.uniform(0,10)))
    o = bpy.context.active_object
    m = bpy.data.materials.new(f"mat{i}")
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (random.random(), random.random(), random.random(), 1)
    o.data.materials.append(m)
bpy.ops.wm.save_as_mainfile(filepath="scene_nocompress.blend", compress=False)
bpy.ops.wm.save_as_mainfile(filepath="scene_compress.blend", compress=True)
print("saved both")
