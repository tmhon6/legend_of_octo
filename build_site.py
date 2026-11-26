"""Build the whole website: one playable build per git tag, plus the newest development build,
and a start page that asks which version to play.

    .venv/bin/python build_site.py      # -> build/site/index.html, build/site/<tag>/, build/site/dev/

To release a version:   git tag -a v1.1.0 -m "What's new"  &&  git push origin v1.1.0
Each version keeps its own saved game.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'build', 'site')
TAG_RE = re.compile(r'^v\d+(\.\d+)*$')      # only plain version tags like v1.0 or v1.2.3


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def tags():
    found = []
    for t in git('tag', '-l', 'v*').split():
        if not TAG_RE.match(t):
            print("skipping tag with an unexpected name:", repr(t))
            continue
        date = git('log', '-1', '--format=%cs', t)
        note = git('tag', '-l', '--format=%(contents:subject)', t)
        if not note or note == git('log', '-1', '--format=%s', t):
            note = ''               # lightweight tag: no release note of its own
        found.append({'tag': t, 'date': date, 'note': note})
    found.sort(key=lambda v: [int(x) for x in v['tag'][1:].split('.')], reverse=True)
    return found


def build(src, out):
    subprocess.run([sys.executable, os.path.join(ROOT, 'build_web.py'), '--src', src, '--out', out], check=True)


def main():
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)
    versions = tags()
    with tempfile.TemporaryDirectory() as tmp:
        for v in versions:
            wt = os.path.join(tmp, v['tag'])
            git('worktree', 'add', '--detach', wt, v['tag'])
            try:
                build(wt, os.path.join(SITE, v['tag']))
            finally:
                git('worktree', 'remove', '--force', wt)
    build(ROOT, os.path.join(SITE, 'dev'))
    dev = {'tag': 'dev', 'label': git('describe', '--tags', '--always'), 'date': git('log', '-1', '--format=%cs')}
    write_launcher(versions, dev)
    print("site ready:", SITE)


def write_launcher(versions, dev):
    rows = []
    for i, v in enumerate(versions):
        badge = '<span class="badge">LATEST</span>' if i == 0 else ''
        note = f'<div class="note">{html.escape(v["note"])}</div>' if v['note'] else ''
        rows.append(f'''<a class="ver{' first' if i == 0 else ''}" href="{v['tag']}/">
          <div class="name">{html.escape(v['tag'])} {badge}</div>
          <div class="date">{v['date']}</div>{note}</a>''')
    if not rows:
        rows.append('<div class="empty">No released versions yet.</div>')
    rows.append(f'''<a class="ver dev" href="dev/">
          <div class="name">Development build</div>
          <div class="date">{html.escape(dev['label'])} &middot; {dev['date']} &middot; newest, may be unfinished</div></a>''')
    page = TEMPLATE.replace('%ROWS%', '\n'.join(rows)).replace('%DATA%', json.dumps(
        [v['tag'] for v in versions]))
    with open(os.path.join(SITE, 'index.html'), 'w') as f:
        f.write(page)


TEMPLATE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Legend of Octo</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
         color: #e8eeff; background: linear-gradient(#2a7fb8 0%, #11407a 35%, #061634 100%);
         display: flex; justify-content: center; padding: 32px 16px; }
  main { width: 100%; max-width: 460px; }
  h1 { margin: 0; text-align: center; line-height: 1; }
  h1 .of { display: block; font-size: 20px; color: #ffd27a; letter-spacing: 4px; }
  h1 .octo { display: block; font-size: 64px; color: #9cc8ff; letter-spacing: 6px;
             text-shadow: 4px 4px 0 #0b1b40; }
  .by { text-align: center; color: #b9c8ec; margin: 10px 0 28px; }
  h2 { font-size: 14px; color: #ffd27a; letter-spacing: 2px; margin: 0 0 10px; }
  .ver { display: block; text-decoration: none; color: inherit; background: rgba(4, 12, 34, .72);
         border: 1px solid #5b74b8; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; }
  .ver:hover, .ver:focus { border-color: #ffd27a; outline: none; background: rgba(10, 24, 60, .85); }
  .ver.first { border-width: 2px; }
  .name { font-size: 18px; font-weight: bold; }
  .badge { font-size: 11px; background: #ffd27a; color: #1a1400; border-radius: 4px; padding: 2px 6px;
           margin-left: 6px; vertical-align: middle; }
  .date { font-size: 13px; color: #9fb0d8; margin-top: 4px; }
  .note { font-size: 13px; margin-top: 6px; color: #d8e2ff; }
  .dev { opacity: .8; border-style: dashed; }
  .empty { color: #9fb0d8; margin-bottom: 10px; }
  footer { font-size: 12px; color: #8fa2d0; margin-top: 22px; line-height: 1.6; }
  footer a { color: #b9cffb; }
</style>
</head>
<body>
<main>
  <h1><span class="of">LEGEND OF</span><span class="octo">OCTO</span></h1>
  <div class="by">by Minu Hong</div>
  <h2>WHICH VERSION DO YOU WANT TO PLAY?</h2>
%ROWS%
  <footer>
    Each version keeps its own saved game. Works with a keyboard on a computer, or with touch
    controls on a phone. The first load takes about 15 seconds.<br>
    <a href="https://github.com/tmhon6/legend_of_octo">Source code on GitHub</a>
  </footer>
</main>
<script>/* released versions: %DATA% */</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
