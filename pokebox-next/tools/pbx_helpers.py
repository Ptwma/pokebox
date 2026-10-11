# Pokebox Next — helpers Claude uses from the Blender MCP (exec this file once per Blender session):
#   exec(open(r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src\tools\pbx_helpers.py").read())
# Installs into builtins: PBXQ (editor queue), PBXRUN (async Blender script), PBXBUILD/PBXREPORT (C++ build),
# PBXED/PBXKILL (launch / stop Unreal), PBXAUTO (start the autotest), PBXRESTORE (put the user's save back).
import builtins, os, subprocess, time, traceback, shutil, glob
import bpy

PRJ = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext"; SRC = r"E:\GAME-APP-DEV\POKEMON\PokeboxNext_src"
UE = r"C:\Program Files\Epic Games\UE_5.8"
QD = os.path.join(PRJ, 'Saved', 'pbx_cmd')
AUTOLOG = os.path.join(PRJ, 'Saved', 'Logs', 'pbx_auto.log')

def _queue(name, code):
    os.makedirs(QD, exist_ok=True)
    out = os.path.join(QD, name + '.out')
    if os.path.exists(out): os.remove(out)
    tmp = os.path.join(QD, name + '.tmp'); open(tmp, 'w', encoding='utf-8').write(code); os.replace(tmp, os.path.join(QD, name + '.py'))
    return out

def _wait(name, secs=50):
    out = os.path.join(QD, name + '.out'); t = time.time()
    while time.time() - t < secs:
        if os.path.exists(out):
            s = open(out, encoding='utf-8', errors='replace').read()
            if '[pbx] DONE' in s or '[pbx] ERROR' in s: return s
        time.sleep(1)
    return open(out, encoding='utf-8', errors='replace').read() if os.path.exists(out) else None

def PBXRUN(script, tag):
    st = os.path.join(SRC, f'_{tag}.status'); open(st, 'w').write('running\n')
    def job():
        try:
            g = {'__name__': '__main__', '__file__': script}
            exec(compile(open(script, encoding='utf-8').read(), script, 'exec'), g)
            open(st, 'a').write('DONE\n')
        except Exception:
            open(st, 'a').write('ERROR\n' + traceback.format_exc())
        return None
    bpy.app.timers.register(job, first_interval=0.1)

def PBXBUILD():
    log = os.path.join(PRJ, 'Saved', 'pbx_build.log')
    cmd = [os.path.join(UE, 'Engine', 'Build', 'BatchFiles', 'Build.bat'), 'PokeboxNextEditor', 'Win64', 'Development',
           '-Project=' + os.path.join(PRJ, 'PokeboxNext.uproject'), '-WaitMutex', '-NoHotReload']
    f = open(log, 'w'); builtins._pbx_build = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, creationflags=0x08000000)
    return log

def PBXREPORT():
    p = builtins.__dict__.get('_pbx_build'); log = os.path.join(PRJ, 'Saved', 'pbx_build.log')
    rc = p.poll() if p else 'none'
    s = open(log, encoding='utf-8', errors='replace').read() if os.path.exists(log) else ''
    errs = [l for l in s.splitlines() if ' error ' in l.lower() or 'error:' in l.lower()]
    return rc, errs[:40], s[-1500:]

def PBXKILL():
    subprocess.run(['taskkill', '/IM', 'UnrealEditor.exe', '/F'], capture_output=True)

def PBXED(game=False, extra=''):
    args = [os.path.join(UE, 'Engine', 'Binaries', 'Win64', 'UnrealEditor.exe'), os.path.join(PRJ, 'PokeboxNext.uproject')]
    if game: args += ['-game', '-windowed', '-ResX=1600', '-ResY=900']
    if extra: args += extra.split(' ')
    subprocess.Popen(args, creationflags=0x00000008)

def PBXAUTO():
    for f in glob.glob(os.path.join(PRJ, 'Saved', 'pbx_auto', '*.png')): os.remove(f)
    if os.path.exists(AUTOLOG): os.remove(AUTOLOG)
    PBXED(game=True, extra='-pbxauto -abslog=' + AUTOLOG)

def PBXAUTOLOG(n=6):
    if not os.path.exists(AUTOLOG): return []
    s = open(AUTOLOG, encoding='utf-8', errors='replace').read().splitlines()
    return [l[30:200] for l in s if '[PBXAUTO]' in l][-n:]

def PBXRESTORE():
    sd = os.path.join(PRJ, 'Saved', 'SaveGames'); b = os.path.join(sd, 'PokeboxNext_Slot1.sav.pre_r1_autotest.bak')
    if os.path.exists(b): shutil.copy2(b, os.path.join(sd, 'PokeboxNext_Slot1.sav')); return True
    return False

def PBXEDREADY(secs=55):
    p = os.path.join(QD, 'editor_ready.txt'); n0 = open(p).read().count('\n') if os.path.exists(p) else 0
    t = time.time()
    while time.time() - t < secs:
        if os.path.exists(p) and open(p).read().count('\n') > n0: return True
        time.sleep(1)
    return False

builtins.PBXQ = {'queue': _queue, 'wait': _wait}
for _f in (PBXRUN, PBXBUILD, PBXREPORT, PBXKILL, PBXED, PBXAUTO, PBXAUTOLOG, PBXRESTORE, PBXEDREADY): setattr(builtins, _f.__name__, _f)
print('pbx helpers ready')
