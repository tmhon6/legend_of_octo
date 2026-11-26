"""Build the browser (pygbag / WebAssembly) version of Legend of Octo.

    .venv/bin/pip install pygbag        # first time only (ffmpeg must be installed too)
    .venv/bin/python build_web.py       # -> build/web/index.html + legend_of_octo.apk
    .venv/bin/python build_web.py --serve   # build, then play it at http://localhost:8000

Options (used by build_site.py to build every tagged version):
    --src DIR      game source to build (default: this folder)
    --out DIR      where to put the finished web build (default: build/web)

Only the game's own files are copied into the build (not .venv, saves or the assets folder).
The version shown on the title screen comes from `git describe --tags` in the source folder.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def arg(name, default):
    if name in sys.argv:
        return os.path.abspath(sys.argv[sys.argv.index(name) + 1])
    return default


def git_version(src):
    try:
        out = subprocess.run(['git', 'describe', '--tags', '--always'], cwd=src, capture_output=True,
                             text=True, timeout=10)
        return out.stdout.strip() or 'dev'
    except Exception:
        return 'dev'


def main():
    serve = '--serve' in sys.argv
    src = arg('--src', ROOT)
    out = arg('--out', os.path.join(ROOT, 'build', 'web'))
    work = os.path.join(os.path.dirname(out), '_stage_' + os.path.basename(out))
    stage = os.path.join(work, 'legend_of_octo')
    if not shutil.which('ffmpeg'):
        sys.exit("ffmpeg is needed to turn the chiptunes into .ogg files")

    # 1. stage just the game code, stamped with its version
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(os.path.join(stage, 'octo'))
    shutil.copy(os.path.join(src, 'main.py'), stage)
    for name in os.listdir(os.path.join(src, 'octo')):
        if name.endswith('.py') and name != 'version.py':
            shutil.copy(os.path.join(src, 'octo', name), os.path.join(stage, 'octo'))
    version = git_version(src)
    with open(os.path.join(stage, 'octo', 'version.py'), 'w') as f:
        f.write(f'VERSION = {version!r}\n')
    print("building version", version)

    # 2. pre-render every sound effect and song to .ogg
    print("rendering audio...")
    sys.path.insert(0, os.path.join(src, 'octo'))
    import sound
    sound.export_ogg(os.path.join(stage, 'octo', 'audio'))

    # 3. package with pygbag
    print("packaging with pygbag...")
    args = [sys.executable, '-m', 'pygbag', '--title', 'Legend of Octo', '--app_name', 'legend_of_octo']
    if not serve:
        args.append('--build')
    args.append(stage)
    if serve:
        print("open http://localhost:8000 (Ctrl+C to stop)")
    subprocess.run(args, check=True)

    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(os.path.join(stage, 'build', 'web'), out)
    shutil.rmtree(work, ignore_errors=True)

    index = os.path.join(out, 'index.html')
    html = open(index).read()
    # keep the pixel art crisp when the browser scales the canvas up, and let touch go to the game
    html = html.replace("canvas.emscripten {", "canvas.emscripten {\n            image-rendering: pixelated;\n"
                        "            touch-action: none;", 1)
    # clearer loading / start messages
    html = html.replace("Loading, please wait ...", "Loading Legend of Octo... (about 15 seconds)", 1)
    html = html.replace('msg  = "Ready to start ! Please click/touch page"', 'msg  = "Ready! Click here to play"', 1)
    html = html.replace("Authors : pgw", "Authors : Minu Hong", 1)
    open(index, 'w').write(html)
    print("built:", out)
    for f in sorted(os.listdir(out)):
        print(f"  {f}  {os.path.getsize(os.path.join(out, f)) // 1024} KB")


if __name__ == '__main__':
    main()
