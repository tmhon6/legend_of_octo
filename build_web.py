"""Build the browser (pygbag / WebAssembly) version of Legend of Octo.

    .venv/bin/pip install pygbag        # first time only (ffmpeg must be installed too)
    .venv/bin/python build_web.py       # -> build/web/index.html + legend_of_octo.apk
    .venv/bin/python build_web.py --serve   # build, then play it at http://localhost:8000

Only the game's own files are copied into the build (not .venv, saves or the assets folder).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STAGE = os.path.join(ROOT, 'build', 'stage', 'legend_of_octo')
OUT = os.path.join(ROOT, 'build', 'web')


def main():
    serve = '--serve' in sys.argv
    if not shutil.which('ffmpeg'):
        sys.exit("ffmpeg is needed to turn the chiptunes into .ogg files")

    # 1. stage just the game code
    shutil.rmtree(os.path.dirname(STAGE), ignore_errors=True)
    os.makedirs(os.path.join(STAGE, 'octo'))
    shutil.copy(os.path.join(ROOT, 'main.py'), STAGE)
    for name in os.listdir(os.path.join(ROOT, 'octo')):
        if name.endswith('.py'):
            shutil.copy(os.path.join(ROOT, 'octo', name), os.path.join(STAGE, 'octo'))

    # 2. pre-render every sound effect and song to .ogg
    print("rendering audio...")
    sys.path.insert(0, os.path.join(ROOT, 'octo'))
    import sound
    sound.export_ogg(os.path.join(STAGE, 'octo', 'audio'))

    # 3. package with pygbag
    print("packaging with pygbag...")
    args = [sys.executable, '-m', 'pygbag', '--title', 'Legend of Octo', '--app_name', 'legend_of_octo']
    if not serve:
        args.append('--build')
    args.append(STAGE)
    if serve:
        print("open http://localhost:8000 (Ctrl+C to stop)")
    subprocess.run(args, check=True)

    shutil.rmtree(OUT, ignore_errors=True)
    shutil.copytree(os.path.join(STAGE, 'build', 'web'), OUT)

    # keep the pixel art crisp when the browser scales the canvas up
    index = os.path.join(OUT, 'index.html')
    html = open(index).read()
    html = html.replace("canvas.emscripten {", "canvas.emscripten {\n            image-rendering: pixelated;", 1)
    # clearer loading / start messages
    html = html.replace("Loading, please wait ...", "Loading Legend of Octo... (about 15 seconds)", 1)
    html = html.replace('msg  = "Ready to start ! Please click/touch page"', 'msg  = "Ready! Click here to play"', 1)
    open(index, 'w').write(html)
    print("built:", OUT)
    for f in sorted(os.listdir(OUT)):
        print(f"  {f}  {os.path.getsize(os.path.join(OUT, f)) // 1024} KB")


if __name__ == '__main__':
    main()
