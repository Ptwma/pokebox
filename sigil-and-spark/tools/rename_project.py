# One-time rename of the project on the PC: PokeboxNext → SigilAndSpark (owner 2026-11-08: "rename the files once and for all,
# the game changed completely"). Classes keep their PBX* prefix (internal; CoreRedirects keep the assets/save working).
#   python rename_project.py            (Unreal Editor and the game must be closed)
# Nothing is deleted: Binaries/Intermediate/old solution go to <project>\_old_build_<date>, saves are COPIED to the new name.
import os, re, sys, json, shutil, subprocess, time

ROOT = r"E:\GAME-APP-DEV\POKEMON"
OLD, NEW = os.path.join(ROOT, "PokeboxNext"), os.path.join(ROOT, "SigilAndSpark")
OLDS, NEWS = os.path.join(ROOT, "PokeboxNext_src"), os.path.join(ROOT, "SigilAndSpark_src")
STAMP = time.strftime("%Y%m%d_%H%M")
log = []
def L(*a): s = " ".join(str(x) for x in a); log.append(s); print(s, flush=True)

r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq UnrealEditor.exe"], capture_output=True, text=True)
if "UnrealEditor" in r.stdout: sys.exit("Unreal Editor / the game is running: close it first")

for a, b in ((OLD, NEW), (OLDS, NEWS)):
    if os.path.isdir(a) and not os.path.exists(b): os.rename(a, b); L("renamed", a, "->", b)
    elif os.path.isdir(b): L("already", b)
    else: sys.exit("missing " + a)

P = NEW
keep = os.path.join(P, "_old_build_" + STAMP); os.makedirs(keep, exist_ok=True)
for d in ("Binaries", "Intermediate", ".vs", "PokeboxNext.sln"):
    s = os.path.join(P, d)
    if os.path.exists(s): shutil.move(s, os.path.join(keep, d)); L("moved aside", d)

# .uproject
up_old, up_new = os.path.join(P, "PokeboxNext.uproject"), os.path.join(P, "SigilAndSpark.uproject")
if os.path.exists(up_old):
    shutil.copy2(up_old, os.path.join(keep, "PokeboxNext.uproject"))
    j = json.load(open(up_old, encoding="utf-8"))
    for m in j.get("Modules", []):
        if m.get("Name") == "PokeboxNext": m["Name"] = "SigilAndSpark"
    json.dump(j, open(up_new, "w", encoding="utf-8"), indent="\t"); os.remove(up_old); L("uproject ->", up_new)

# Source: folder, file names, text
src = os.path.join(P, "Source")
if os.path.isdir(os.path.join(src, "PokeboxNext")): os.rename(os.path.join(src, "PokeboxNext"), os.path.join(src, "SigilAndSpark"))
for dp, dn, fn in os.walk(src):
    for f in fn:
        p = os.path.join(dp, f)
        if f.endswith((".cs", ".cpp", ".h")):
            t = open(p, encoding="utf-8", errors="surrogateescape").read()
            t2 = t.replace("POKEBOXNEXT_API", "SIGILANDSPARK_API").replace("PokeboxNext", "SigilAndSpark")
            if t2 != t: open(p, "w", encoding="utf-8", errors="surrogateescape").write(t2)
        if "PokeboxNext" in f: os.rename(p, os.path.join(dp, f.replace("PokeboxNext", "SigilAndSpark"))); L("file", f)

# Config: class paths, title, redirects for every asset/map/save that still says /Script/PokeboxNext
cfg = os.path.join(P, "Config")
for f in os.listdir(cfg):
    if not f.endswith(".ini"): continue
    p = os.path.join(cfg, f); shutil.copy2(p, os.path.join(keep, f))
    t = open(p, encoding="utf-8", errors="surrogateescape").read()
    t = t.replace("/Script/PokeboxNext", "/Script/SigilAndSpark")
    if f == "DefaultEngine.ini" and "/Script/PokeboxNext\",NewName" not in t:
        t += '\n[CoreRedirects]\n+PackageRedirects=(OldName="/Script/PokeboxNext",NewName="/Script/SigilAndSpark")\n'
        # the template classes (PokeboxNextCharacter/GameMode/PlayerController) got renamed with their files: redirect them too
        for c in ("PlayerController", "GameMode", "Character"):
            t = t.replace('NewClassName="PokeboxNext%s"' % c, 'NewClassName="SigilAndSpark%s"' % c)
            for pk in ("SigilAndSpark", "PokeboxNext"):
                t += '+ClassRedirects=(OldName="/Script/%s.PokeboxNext%s",NewName="/Script/SigilAndSpark.SigilAndSpark%s")\n' % (pk, c, c)
    if f == "DefaultGame.ini":
        t = re.sub(r"(?m)^ProjectName=.*$", "ProjectName=Sigil & Spark", t)
        if "ProjectDisplayedTitle" not in t:
            t = t.replace("[/Script/EngineSettings.GeneralProjectSettings]", '[/Script/EngineSettings.GeneralProjectSettings]\nProjectDisplayedTitle=NSLOCTEXT("[/Script/EngineSettings]", "SAS_Title", "Sigil & Spark")', 1)
    open(p, "w", encoding="utf-8", errors="surrogateescape").write(t); L("ini", f)

# saves: copies under the new slot name (the old files stay as they are)
sg = os.path.join(P, "Saved", "SaveGames")
if os.path.isdir(sg):
    for f in os.listdir(sg):
        if f.startswith("PokeboxNext_"):
            d = os.path.join(sg, f.replace("PokeboxNext_", "SigilAndSpark_", 1))
            if not os.path.exists(d): shutil.copy2(os.path.join(sg, f), d); L("save copy", os.path.basename(d))

# launcher
ob = os.path.join(P, "Play Pokebox Next.bat")
if os.path.exists(ob): shutil.move(ob, os.path.join(keep, "Play Pokebox Next.bat"))
open(os.path.join(P, "Play Sigil and Spark.bat"), "w").write(
    '@echo off\nrem Sigil & Spark - plays the latest version of the project directly (no packaging).\n'
    'start "" "C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor.exe" "%~dp0SigilAndSpark.uproject" -game -windowed -ResX=1600 -ResY=900\n')
L("launcher written")
open(os.path.join(P, "Saved", "rename_" + STAMP + ".log"), "w").write("\n".join(log))
print("RENAME DONE")
