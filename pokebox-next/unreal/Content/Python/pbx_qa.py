# Pokebox Next — world QA pass (2026-10-31, user: "check if any ground is missing, trees inside the mountain we can remove,
# water coming through a boat because of its placement — everything in this part").
#   import pbx_qa as Q; Q.run(fix=True)      → Saved/pbx_qa_<map>.txt + log lines '[qa] ...'
# - trees / instanced plants: base vs the real ground under them (the terrain plus every rock, cliff and building placed later):
#   ground > 1.2 m above the base = inside the mountain / a rock → removed; base > 0.6 m above the ground = floating → dropped
# - holes: a 10 m grid of traces over the playable ground and the mountain flanks; no hit at all = missing ground
# - boats: freeboard (deck / floor height above the waterline) — what the masked sea material must hide
import unreal, math, os, json

EAL = unreal.EditorAssetLibrary
def log(*a): print('[qa]', *a)
def _world(): return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

def _hit_z(world, x, y, z_top=60000.0, z_bot=-60000.0, ignore=()):
    h = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, z_top), unreal.Vector(x, y, z_bot), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               True, list(ignore), unreal.DrawDebugTrace.NONE, True)
    if not h: return None, None
    t = h.to_tuple(); z = None; act = None
    for v in t[4:7]:
        if isinstance(v, unreal.Vector): z = v.z; break
    for v in t:
        if isinstance(v, unreal.Actor): act = v; break
    return z, act

def _hosts():
    return [a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_actor_label().startswith('Instances')]

def trees(fix=False, report=None):
    world = _world(); hosts = _hosts(); buried = floating = total = 0; samples = []
    for host in hosts:
        for c in host.get_components_by_class(unreal.InstancedStaticMeshComponent):
            sm = c.get_editor_property('static_mesh'); nm = sm.get_name() if sm else '?'
            n = c.get_instance_count(); rm = []; moves = []
            # r59 lesson: the Poly Haven sets share ONE pivot (tree b/c sit metres away from it) → measure at the mesh's own
            # footprint centre and its lowest point, transformed by the instance, never at the instance origin
            b = sm.get_bounding_box() if sm else None
            if not b: continue
            foot = unreal.Vector((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2, b.min.z)
            for i in range(n):
                t = c.get_instance_transform(i, True)
                if isinstance(t, tuple): t = t[-1]
                p = t.transform_location(foot); total += 1
                gz, act = _hit_z(world, p.x, p.y, p.z + 8000.0, p.z - 4000.0, ignore=[host])
                if gz is None: continue
                if gz - p.z > 150.0:
                    rm.append(i); buried += 1
                    if len(samples) < 25: samples.append(('buried', nm, round(p.x), round(p.y), round(gz - p.z), act.get_actor_label() if act else ''))
                elif p.z - gz > 60.0:
                    floating += 1; t.translation = t.translation + unreal.Vector(0, 0, gz - 10.0 - p.z); moves.append((i, t))
            if fix:
                for i, t in moves: c.update_instance_transform(i, t, True, False, True)
                if rm: c.remove_instances(rm)

            if rm or moves: log('instances', nm, 'buried', len(rm), 'floating', len(moves), 'of', n)
    log('trees/plants', total, 'buried', buried, 'floating', floating, 'fixed' if fix else 'report only')
    if report is not None: report += [f'instances {total}: buried {buried} (removed={fix}), floating {floating} (dropped={fix})'] + [str(s) for s in samples]
    return buried, floating

def holes(report=None, step=1000.0, cx=0.0, cy=-800.0, r=45000.0):
    """no ground at all under a point of the world (inside r around the village / mountain)"""
    world = _world(); miss = []
    n = int(r // step)
    for ix in range(-n, n + 1):
        for iy in range(-n, n + 1):
            x, y = cx + ix * step, cy + iy * step
            if math.hypot(x - cx, y - cy) > r: continue
            z, _ = _hit_z(world, x, y)
            if z is None: miss.append((round(x), round(y)))
    log('holes', len(miss), miss[:40])
    if report is not None: report += [f'holes (no ground, {step/100:.0f} m grid, r {r/100:.0f} m): {len(miss)}'] + [str(m) for m in miss[:200]]
    return miss

def boats(report=None):
    out = []
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        tags = [str(t) for t in a.tags]
        if not any(t.startswith(('PBX_Boat', 'PBX_Bob', 'PBX_Sail')) for t in tags): continue
        c = a.get_component_by_class(unreal.StaticMeshComponent); sm = c.get_editor_property('static_mesh') if c else None
        b = sm.get_bounding_box() if sm else None
        out.append((tags[0], sm.get_name() if sm else '?', round(a.get_actor_location().z), round(b.min.z) if b else None, round(b.max.z) if b else None))
    log('boats', out)
    if report is not None: report += ['boats (tag, mesh, actor z, mesh min z, max z): ' + str(out)]
    return out

def run(fix=False, map_name='L_Town'):
    rep = [f'QA {map_name} fix={fix}']
    trees(fix, rep); holes(rep); boats(rep)
    if fix: unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    p = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()) + f'pbx_qa_{map_name}.txt'
    open(p, 'w', encoding='utf-8').write('\n'.join(rep)); log('report ->', p)
