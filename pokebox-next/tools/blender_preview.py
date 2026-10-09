# Pokebox Next — quick Workbench preview of one generated building (geometry check, not the final look).
# exec() inside Blender with PBX_WHAT = 'player' | 'rival' | 'lab' and PBX_CAM = (x, y, z, pitch_deg, yaw_deg) in the globals.
import bpy, math, os
SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tools\blender_town.py"
g = {'__name__': 'pbx_town'}
exec(compile(open(SRC, encoding='utf-8').read().replace("if __name__ == '__main__' or True:\n    run()", ""), 'blender_town.py', 'exec'), g)
what = globals().get('PBX_WHAT', 'player'); camp = globals().get('PBX_CAM', (9, -14, 3.2, 82, 33))
g['reset']()
if what == 'lab': ob = g['house']('SM_Lab', 18.0, 11.0, 6.4, 'M_Roof_Blue', 'M_Siding_White', porch=False, chimney=False, two_storey=True, lab=True)
else: ob = g['house']('SM_House', 9.0, 7.0, 3.3, 'M_Roof_Red', 'M_Siding_White' if what == 'player' else 'M_Siding_Cream')
COL = {'M_Siding_White': (.93, .93, .9, 1), 'M_Siding_Cream': (.95, .9, .78, 1), 'M_Trim': (.98, .98, .98, 1), 'M_Roof_Red': (.55, .16, .12, 1), 'M_Roof_Blue': (.2, .3, .55, 1),
       'M_Stone': (.5, .5, .48, 1), 'M_Plaster': (.8, .8, .8, 1), 'M_Glass': (.3, .45, .6, 1), 'M_Door': (.3, .4, .6, 1), 'M_Metal': (.4, .4, .42, 1), 'M_Brick': (.55, .25, .2, 1), 'M_WoodBox': (.45, .3, .18, 1)}
for m in ob.data.materials: m.diffuse_color = COL.get(m.name, (1, 0, 1, 1))
sc = bpy.context.scene
cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam)
cam.location = camp[:3]; cam.rotation_euler = (math.radians(camp[3]), 0, math.radians(camp[4])); cd.lens = 24; sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'; sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'; sh.show_shadows = True; sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.filepath = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\preview_%s.png" % what
bpy.ops.render.render(write_still=True); print('preview', sc.render.filepath)
