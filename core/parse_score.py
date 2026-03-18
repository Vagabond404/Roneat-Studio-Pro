"""
core/parse_score.py
===================
Roneat Studio Pro — Unified Score Notation Parser

Notation reference:
  9        → bar 9, plays 1 beat
  9#3      → bar 9, tremolo roll of 3 rapid hits (occupies 3 beats total)
  -        → rest, 1 beat silence
  0  x     → rest aliases
  /        → visual bar line (no timing)

API
---
expand_score(text)      → list[dict]
    {bar:int|None, beats:float, is_tremolo:bool, repeat:int}

validate_score(text)    → list[str]   (empty = valid)

notes_and_durations(text, bpm, sync_data=None)
    → (list[int], list[float])
    note values: positive = normal, negative = tremolo
"""

import re

_TOKEN_RE = re.compile(r'^(\d+)(#(\d+))?$')
_RESTS    = {'-', '0', 'x'}


def _safe_bar(val: str):
    try:
        b = int(val)
        return b if 1 <= b <= 21 else None
    except (ValueError, TypeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────

def expand_score(text: str) -> list:
    """
    Parse notation text into a list of event dicts.

    Returns
    -------
    list of dict with keys:
        bar        : int | None   (None = rest)
        beats      : float        (beats this event occupies)
        is_tremolo : bool
        repeat     : int          (number of tremolo hits; 1 for normal notes)
    """
    events = []
    for raw in text.replace('\n', ' ').split():
        if raw == '/':
            continue

        if raw in _RESTS:
            events.append({'bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1})
            continue

        m = _TOKEN_RE.match(raw)
        if not m:
            # Unknown token — treated as rest so playback doesn't crash
            events.append({'bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1})
            continue

        bar = _safe_bar(m.group(1))
        if bar is None:
            events.append({'bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1})
            continue

        if m.group(2):                          # has "#N"
            repeat = int(m.group(3)) if m.group(3) else 1
            repeat = max(1, min(repeat, 32))
            events.append({'bar': bar, 'beats': float(repeat),
                           'is_tremolo': True, 'repeat': repeat})
        else:
            events.append({'bar': bar, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1})
    return events


# ─────────────────────────────────────────────────────────────────────────────

def validate_score(text: str) -> list:
    """
    Return a list of human-readable error strings.
    Empty list means the notation is valid.
    """
    errors = []
    for raw in text.replace('\n', ' ').split():
        if raw in ('/', '-', '0', 'x'):
            continue
        m = _TOKEN_RE.match(raw)
        if not m:
            errors.append(f'Invalid token: "{raw}"')
            continue
        bar = _safe_bar(m.group(1))
        if bar is None:
            errors.append(f'Bar out of range 1-21: "{raw}"')
        if m.group(2):
            try:
                r = int(m.group(3))
                if not 1 <= r <= 32:
                    errors.append(f'Repeat count must be 1–32: "{raw}"')
            except (ValueError, TypeError):
                errors.append(f'Invalid repeat count: "{raw}"')
    return errors


# ─────────────────────────────────────────────────────────────────────────────

def notes_and_durations(text: str, bpm: int,
                         sync_data: list = None) -> tuple:
    """
    Convert score text to parallel (notes, durations) lists for
    audio rendering and video export.

    Parameters
    ----------
    text      : raw notation string
    bpm       : beats per minute (used when sync_data is None)
    sync_data : list of {'note': str, 'time': float} from audio analysis

    Returns
    -------
    notes     : list[int]   — negative = tremolo bar (abs = bar number)
    durations : list[float] — seconds each note lasts
    """
    beat_sec = 60.0 / max(bpm, 1)
    events   = expand_score(text)

    notes, durations = [], []

    if sync_data:
        sd_idx = 0
        for ev in events:
            if ev['bar'] is None:
                continue
            bar      = ev['bar']
            note_val = -bar if ev['is_tremolo'] else bar

            if sd_idx < len(sync_data):
                t_curr = sync_data[sd_idx]['time']
                t_next = (sync_data[sd_idx + 1]['time']
                          if sd_idx + 1 < len(sync_data) else t_curr + 0.6)
                dur = max(0.1, min(t_next - t_curr, 2.0))
                sd_idx += 1
            else:
                dur = beat_sec

            # Tremolo occupies repeat beats
            if ev['is_tremolo']:
                dur = dur * ev['repeat']

            notes.append(note_val)
            durations.append(dur)
    else:
        for ev in events:
            if ev['bar'] is None:
                continue
            bar      = ev['bar']
            note_val = -bar if ev['is_tremolo'] else bar
            dur      = beat_sec * ev['beats']
            notes.append(note_val)
            durations.append(dur)

    return notes, durations