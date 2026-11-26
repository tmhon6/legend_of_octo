"""The score: what earns points, the milestones that unlock new features, and the leaderboard.

The leaderboard is kept apart from saved games (leaderboard.json on desktop, the browser's local
storage on the web), so every run you play lands on it next to the townsfolk rivals.
"""
import json
import os
import random
import sys

WEB = sys.platform == 'emscripten'
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD_PATH = os.path.join(_ROOT, 'leaderboard.json')
WEB_KEY = 'legend_of_octo_leaderboard'

# points for each step of progress (counted as it happens -- see town.TownLife.score_watch)
POINTS = {'trial': 300, 'bell': 1000, 'guardian': 500, 'base_form': 300, 'fusion': 100, 'mega': 500,
          'heart': 200, 'grimfin': 2000, 'murk': 5000, 'region': 100, 'temple': 250, 'town': 250}

# (points, id, title, what it unlocks)
MILESTONES = [
    (1000, 'compass', "QUEST COMPASS", "YOUR MAP AND MINIMAP MARK WHERE YOUR SIDE QUESTS LEAD."),
    (2500, 'turbo', "TURBO FINS", "OCTO SWIMS 12% FASTER IN EVERY FORM."),
    (5000, 'express', "OCTO EXPRESS", "THE WARP MENU (PRESS T) CAN TAKE YOU TO OCTO CITY AND TURTLE TOWN."),
    (8000, 'magnet', "PEARL MAGNET", "PEARLS AND HEARTS DRIFT TO YOU FROM MUCH FARTHER AWAY."),
    (12000, 'museum', "3D MUSEUM", "PROFESSOR OCTAGON'S MUSEUM OPENS: EVERY GUARDIAN YOU BEAT STANDS THERE AS A 3D "
                                    "STATUE. ASK HIM, OR OPEN IT FROM THE JOURNAL."),
    (16000, 'goldcard', "GOLD CARD", "25% OFF AT HERMIE'S SHOP AND EVERY TOWN STALL."),
    (22000, 'quickjet', "QUICK JET", "YOUR INK JET RECHARGES TWICE AS FAST."),
    (30000, 'radio', "OCTO RADIO", "LISTEN TO EVERY TUNE IN THE GAME: JOURNAL (PRESS Q), EXTRAS."),
    (40000, 'heart', "HEART OF THE CITY", "ONE MORE HEART OF LIFE."),
    (55000, 'treasure', "TREASURE SENSE", "YOUR MAP SHOWS TREASURE YOU HAVEN'T PICKED UP YET."),
    (75000, 'megaink', "MEGA INK", "ONE HIT IN FOUR LANDS EXTRA HARD."),
    (100000, 'legend', "LIVING LEGEND", "A GOLDEN STATUE OF YOU IN OCTO CITY, THE CHAMPION CROWN AND "
                                        "LEGEND-GOLD INK."),
]
MILESTONE = {mid: (pts, title, desc) for pts, mid, title, desc in MILESTONES}


def next_milestone(score):
    for pts, mid, title, desc in MILESTONES:
        if score < pts:
            return pts, title
    return None, None


# ---- the leaderboard ---------------------------------------------------------------------------
def _storage():
    import platform
    return platform.window.localStorage


def load_board():
    try:
        if WEB:
            text = _storage().getItem(WEB_KEY)
            data = json.loads(str(text)) if text else {}
        elif os.path.exists(BOARD_PATH):
            with open(BOARD_PATH) as f:
                data = json.load(f)
        else:
            data = {}
    except Exception as e:
        print("leaderboard:", e)
        data = {}
    data.setdefault('runs', [])
    data.setdefault('name', None)
    return data


def save_board(board):
    board['runs'] = sorted(board['runs'], key=lambda r: -r['score'])[:30]
    try:
        text = json.dumps(board)
        if WEB:
            _storage().setItem(WEB_KEY, text)
        else:
            with open(BOARD_PATH, 'w') as f:
                f.write(text)
    except Exception as e:
        print("leaderboard:", e)


def new_run_id():
    return '%08x' % random.getrandbits(32)


def record(board, run_id, name, points, deep=False):
    for r in board['runs']:
        if r['id'] == run_id:
            r['score'] = max(r['score'], points)
            r['name'] = name
            r['deep'] = deep
            return
    board['runs'].append({'id': run_id, 'name': name, 'score': points, 'deep': deep})


def ranking(board, rivals, run_id=None, name=None, points=0, deep=False):
    """Everyone on the board, best first: (name, score, kind, is_you)."""
    rows = [(n, s, k, False) for n, s, k in rivals]
    seen_you = False
    for r in board['runs']:
        you = r['id'] == run_id
        sc = max(r['score'], points) if you else r['score']
        rows.append((r['name'] + (" *" if r.get('deep') else ""), sc, 'you' if you else 'run', you))
        seen_you |= you
    if run_id and not seen_you:
        rows.append(((name or "OCTO") + (" *" if deep else ""), points, 'you', True))
    rows.sort(key=lambda r: -r[1])
    return rows
