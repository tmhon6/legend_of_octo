"""Choose which version of Legend of Octo to play, in a terminal - like the website's start page: the
newest release, the development build (this folder as it is now), or any older release.

    .venv/bin/python main.py            # shows the list (Enter on its own plays the newest release)
    .venv/bin/python main.py dev        # plays this folder straight away
    .venv/bin/python main.py latest     # plays the newest release straight away
    .venv/bin/python main.py v2.5.0     # plays that release straight away
    .venv/bin/python main.py list       # just shows the list

A release runs from its own copy of the game in .versions/<tag>/ (a git worktree: that version's
files, set up the first time you choose it). Every version keeps its own saved game, here in this
folder like the development build's (releases from before v2.9.0 keep theirs in their own
.versions/<tag>/ folder instead, since they don't know about this list).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SHELF = os.path.join(ROOT, '.versions')
TAG_RE = re.compile(r'^v\d+(\.\d+)*$')


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True,
                          timeout=10).stdout.strip()


def releases():
    """Every release, newest first, as dicts: tag, date, note (what's new)."""
    try:
        out = _git('for-each-ref', '--sort=-v:refname', 'refs/tags/v*',
                   '--format=%(refname:short)%09%(creatordate:short)%09%(contents:subject)')
    except Exception:                       # no git, or not a git folder (a downloaded copy)
        return []
    found = []
    for line in out.splitlines():
        tag, date, note = (line.split('\t') + ['', ''])[:3]
        if TAG_RE.match(tag):
            if note.startswith(tag + ':'):  # ("v2.4.0: friendly characters..." -> "friendly characters...")
                note = note[len(tag) + 1:].strip()
            found.append({'tag': tag, 'date': date, 'note': note[:1].upper() + note[1:]})
    return found


def _same_as(tag):
    """Is this folder exactly that release (no changes since)?"""
    try:
        return _git('describe', '--tags', '--exact-match', 'HEAD') == tag and \
            not _git('status', '--porcelain', '--untracked-files=no')
    except Exception:
        return False


def _dev_label():
    try:
        return _git('describe', '--tags', '--always', '--dirty=+changes')
    except Exception:
        return 'this folder'


# ---- the list -----------------------------------------------------------------------------------
def _paint(code):
    use = sys.stdout.isatty() and os.environ.get('TERM', '') not in ('', 'dumb') and not os.environ.get('NO_COLOR')
    return (lambda s: f"\033[{code}m{s}\033[0m") if use else (lambda s: s)


GOLD, BLUE, DIM, BOLD = _paint('33;1'), _paint('94;1'), _paint('2'), _paint('1')


def _fit(s, room):
    return s if len(s) <= room else s[:max(0, room - 3)] + '...'


def _main_list(rel, same):
    width = shutil.get_terminal_size((90, 24)).columns
    newest = rel[0]
    print()
    print('  ' + GOLD('LEGEND OF') + ' ' + BLUE('OCTO') + DIM('   by Minu Hong'))
    print()
    print('  ' + GOLD('WHICH VERSION DO YOU WANT TO PLAY?'))
    print()
    head = f"   1  {newest['tag']}  LATEST  {newest['date']}  "
    print(f"   {BOLD('1')}  {BOLD(newest['tag'])}  {GOLD('LATEST')}  {DIM(newest['date'])}  "
          + _fit(newest['note'], width - len(head) - 1))
    what = f"the same as {newest['tag']} right now" if same else f"{_dev_label()}: the newest changes, may be unfinished"
    print(f"   {BOLD('2')}  {BOLD('Development build')}  {BLUE('DEV')}  " + DIM(_fit(what, width - 30)))
    if len(rel) > 1:
        print(f"   {BOLD('3')}  Older versions...  {DIM(f'({len(rel) - 1} more)')}")
    print()


def _older_list(rel):
    width = shutil.get_terminal_size((90, 24)).columns
    print()
    print('  ' + GOLD('OLDER VERSIONS'))
    print()
    for i, r in enumerate(rel[1:], 1):
        head = f"  {i:>3}  {r['tag']:<8}  {r['date']}  "
        print(f"  {BOLD(f'{i:>3}')}  {r['tag']:<8}  {DIM(r['date'])}  " + _fit(r['note'], width - len(head) - 1))
    print()


def _ask(prompt):
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def pick(args):
    """Which version to play: None means this folder (the development build), otherwise a release's
    tag. Asks in the terminal, unless the command line says which (or there's no terminal to ask in)."""
    if os.environ.get('OCTO_PICKED'):       # (a version this list started: don't ask again)
        return None
    rel = releases()
    if not rel:
        return None
    tags = [r['tag'] for r in rel]
    same = _same_as(tags[0])

    def release(tag):                       # (the newest release, when this folder is exactly it, plays here)
        return None if tag == tags[0] and same else tag
    for a in args:
        a = a.lower().lstrip('-')
        if a == 'dev':
            return None
        if a == 'latest':
            return release(tags[0])
        if a in tags:
            return release(a)
        if a == 'list':
            _main_list(rel, same)
            _older_list(rel)
            sys.exit(0)
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    while True:
        _main_list(rel, same)
        ans = _ask(f"  Type {'1, 2 or 3' if len(rel) > 1 else '1 or 2'} and press Enter "
                   "(Enter on its own plays 1, Q quits): ")
        if ans in ('', '1'):
            return release(tags[0])
        if ans == '2':
            return None
        if ans in ('q', 'quit', 'exit'):
            sys.exit(0)
        if ans in tags:
            return release(ans)
        if ans == '3' and len(rel) > 1:
            _older_list(rel)
            ans = _ask("  Type a number and press Enter (Enter on its own goes back): ")
            if ans.isdigit() and 1 <= int(ans) < len(rel):
                return rel[int(ans)]['tag']
            if ans in tags:
                return release(ans)
            continue
        print(f"  {GOLD('?')} Type one of the numbers in the list.")


def play(tag):
    """Run a release from its own folder (setting it up the first time). Returns its exit code."""
    where = os.path.join(SHELF, tag)
    if not os.path.exists(os.path.join(where, 'main.py')):
        if os.path.exists(where):
            print(f"  {where} is there but isn't a copy of the game: move it away, then try again.")
            return 1
        print(f"  Setting up {tag} (the first time only)...")
        os.makedirs(SHELF, exist_ok=True)
        try:
            _git('worktree', 'prune')
            _git('worktree', 'add', '--detach', where, tag)
        except Exception as e:
            print("  Couldn't set it up:", getattr(e, 'stderr', '') or e)
            return 1
    if [int(x) for x in tag[1:].split('.')] < [2, 8]:
        print("  (The first time an older version starts, it makes all its music first: about half a minute.)")
    print(f"  Starting {tag}...")
    env = dict(os.environ, OCTO_PICKED='1', OCTO_HOME=ROOT, PYGAME_HIDE_SUPPORT_PROMPT='1')
    return subprocess.call([sys.executable, 'main.py'], cwd=where, env=env)
