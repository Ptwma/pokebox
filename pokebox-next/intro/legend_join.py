# join all 8 pages (frames) + the full mix → legend_intro_full.mp4  (run: blender -b --factory-startup --python this)
import bpy, os
SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
LF = os.path.join(SRC, 'intro_render', 'legend_full'); LB = os.path.join(SRC, 'intro_render', 'legend_book', 'frames')
order = [('P1', LF, None), ('P2', LF, None), ('P3', LF, None), ('P4', LF, None), ('P5', LB, (1, 270)), ('P6', LF, None), ('P7', LB, (271, 384)), ('P8', LF, None)]
ed = bpy.data.scenes.new("LF_JOIN"); ed.render.resolution_x, ed.render.resolution_y = 1920, 1080; ed.render.fps = 24
se = ed.sequence_editor_create(); coll = se.strips if hasattr(se, "strips") else se.sequences
f0 = 1
for name, base, rng in order:
    if rng:
        files = [f"f_{i:04d}.png" for i in range(rng[0], rng[1] + 1)]; d = base
    else:
        d = os.path.join(base, name); files = sorted(f for f in os.listdir(d) if f.startswith('f_') and f.endswith('.png'))
    st = coll.new_image(name, os.path.join(d, files[0]), 1, f0)
    for f in files[1:]: st.elements.append(f)
    f0 += len(files)
ed.frame_start, ed.frame_end = 1, f0 - 1
snd = coll.new_sound("mix", os.path.join(LF, "legend_full_mix.wav"), 2, 1)
ed.render.image_settings.media_type = "VIDEO"; ed.render.image_settings.file_format = "FFMPEG"
ed.render.ffmpeg.format = "MPEG4"; ed.render.ffmpeg.codec = "H264"; ed.render.ffmpeg.constant_rate_factor = "HIGH"
ed.render.ffmpeg.audio_codec = "AAC"; ed.render.ffmpeg.audio_bitrate = 256
ed.render.filepath = os.path.join(LF, "legend_intro_full.mp4"); ed.render.use_sequencer = True
bpy.context.window.scene = ed
bpy.ops.render.render(animation=True, scene=ed.name)
open(os.path.join(LF, "_join_done"), "w").write(str(f0 - 1))
