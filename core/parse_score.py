"""
core/parse_score.py
===================
Roneat Studio Pro — Unified Score Notation Parser

Notation reference:
  9        → bar 9, plays 1 beat, left_bar = 9+7 = 16 (auto)
  (9)6     → bar 6 right hand, bar 9 left hand (explicit left)
  9#3      → bar 9, tremolo roll of 3 rapid hits (occupies 3 beats total)
  -        → rest, 1 beat silence
  0  x     → rest aliases
  _        → line rest (empty line with black divider)
  /        → visual bar line (no timing)

API
---
expand_score(text)      → list[dict]
    {bar:int|None, left_bar:int|None, beats:float, is_tremolo:bool, repeat:int, is_line_rest:bool}

validate_score(text)    → list[str]   (empty = valid)

notes_and_durations(text, bpm, sync_data=None)
    → (list[int], list[float])
    note values: positive = normal, negative = tremolo
"""

import re

_TOKEN_RE = re.compile(r'^(\d+)(#(\d+))?$')
_LEFT_RIGHT_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')  # NEW: (left)right or (left)right#N
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
        bar         : int | None   (None = rest)
        left_bar    : int | None   (left hand bar, auto-calculated if not specified)
        beats       : float        (beats this event occupies)
        is_tremolo  : bool
        repeat      : int          (number of tremolo hits; 1 for normal notes)
        is_line_rest: bool         (True if "_" token for empty line with black divider)
    """
    events = []
    for raw in text.replace('\n', ' ').split():
        if raw == '/':
            if events:
                events[-1]['barline'] = True
            continue

        # NEW: Handle line rest "_"
        if raw == '_':
            events.append({'bar': None, 'left_bar': None, 'beats': 0.0,
                           'is_tremolo': False, 'repeat': 1, 'is_line_rest': True})
            continue

        if raw in _RESTS:
            events.append({'bar': None, 'left_bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
            continue

        # NEW: Try (left)right format first
        m_lr = _LEFT_RIGHT_RE.match(raw)
        if m_lr:
            left_bar = _safe_bar(m_lr.group(1))
            right_bar = _safe_bar(m_lr.group(2))
            if left_bar is None or right_bar is None:
                events.append({'bar': None, 'left_bar': None, 'beats': 1.0,
                               'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
                continue
            
            if m_lr.group(3):  # has "#N"
                repeat = int(m_lr.group(4)) if m_lr.group(4) else 1
                repeat = max(1, min(repeat, 32))
                events.append({'bar': right_bar, 'left_bar': left_bar, 'beats': float(repeat),
                               'is_tremolo': True, 'repeat': repeat, 'is_line_rest': False})
            else:
                events.append({'bar': right_bar, 'left_bar': left_bar, 'beats': 1.0,
                               'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
            continue

        # Original format: just right bar
        m = _TOKEN_RE.match(raw)
        if not m:
            # Unknown token — treated as rest so playback doesn't crash
            events.append({'bar': None, 'left_bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
            continue

        bar = _safe_bar(m.group(1))
        if bar is None:
            events.append({'bar': None, 'left_bar': None, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
            continue

        # Auto-calculate left_bar = bar + 7 (default behavior)
        left_bar = min(bar + 7, 21)  # Cap at 21

        if m.group(2):                          # has "#N"
            repeat = int(m.group(3)) if m.group(3) else 1
            repeat = max(1, min(repeat, 32))
            events.append({'bar': bar, 'left_bar': left_bar, 'beats': float(repeat),
                           'is_tremolo': True, 'repeat': repeat, 'is_line_rest': False})
        else:
            events.append({'bar': bar, 'left_bar': left_bar, 'beats': 1.0,
                           'is_tremolo': False, 'repeat': 1, 'is_line_rest': False})
    return events


# ─────────────────────────────────────────────────────────────────────────────

def validate_score(text: str) -> list:
    """
    Return a list of human-readable error strings.
    Empty list means the notation is valid.
    """
    errors = []
    for raw in text.replace('\n', ' ').split():
        if raw in ('/', '-', '0', 'x', '_'):  # NEW: added '_'
            continue
        
        # NEW: Check (left)right format
        m_lr = _LEFT_RIGHT_RE.match(raw)
        if m_lr:
            left_bar = _safe_bar(m_lr.group(1))
            right_bar = _safe_bar(m_lr.group(2))
            if left_bar is None:
                errors.append(f'Left bar out of range 1-21: "{raw}"')
            if right_bar is None:
                errors.append(f'Right bar out of range 1-21: "{raw}"')
            if m_lr.group(3):
                try:
                    r = int(m_lr.group(4))
                    if not 1 <= r <= 32:
                        errors.append(f'Repeat count must be 1–32: "{raw}"')
                except (ValueError, TypeError):
                    errors.append(f'Invalid repeat count: "{raw}"')
            continue
        
        # Original validation
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
            if ev['bar'] is None or ev['is_line_rest']:  # Skip rests and line rests
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
            if ev['bar'] is None or ev['is_line_rest']:  # Skip rests and line rests
                continue
            bar      = ev['bar']
            note_val = -bar if ev['is_tremolo'] else bar
            dur      = beat_sec * ev['beats']
            notes.append(note_val)
            durations.append(dur)

    return notes, durations


def group_beats_into_rows(beats: list, cols: int) -> list:
    """
    Group a flat list of beat dicts into rows of maximum size `cols`.
    If a beat has `is_line_rest` (or `is_line_rest` is True), it does not
    become a cell. Instead, it marks that the row immediately preceding it
    (or, if none, the first row) should have a separator line below it.
    """
    rows = []
    current_cells = []
    line_above_first = False
    
    for b in beats:
        if b.get('is_line_rest'):
            if current_cells:
                rows.append({
                    'cells': current_cells,
                    'line_below': True
                })
                current_cells = []
            else:
                if rows:
                    rows[-1]['line_below'] = True
                else:
                    line_above_first = True
        else:
            current_cells.append(b)
            if len(current_cells) == cols:
                rows.append({
                    'cells': current_cells,
                    'line_below': False
                })
                current_cells = []
                
    if current_cells:
        rows.append({
            'cells': current_cells,
            'line_below': False
        })
        
    if rows and line_above_first:
        rows[0]['line_above'] = True
        
    return rows
