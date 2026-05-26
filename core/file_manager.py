"""
core/file_manager.py  v2.0
============================
Roneat Studio Pro — File & Settings Manager

Changes in v2:
  - .roneat format is now a compressed ZIP archive containing:
      data.json       — score metadata (title, notes, sync_data, etc.)
      audio/source.*  — original source audio (if any)
      midi/score.mid  — generated MIDI (if any)
  - Backward-compatible: plain JSON .roneat files are still readable
"""

import json
import os
import sys
import zipfile
import shutil
import tempfile
import logging

from core.file_format import RoneatFileManager, RoneatNote, RoneatScore

# ── Default frequencies ───────────────────────────────────────────────────────
DEFAULT_HZ = {
    1: 1308.0, 2: 1174.0, 3: 1064.0, 4: 977.0,  5: 884.0,  6: 791.0,  7: 720.0,
    8:  655.0, 9:  589.0, 10: 536.0, 11: 490.0, 12: 444.0, 13: 399.0, 14: 359.0,
    15: 328.0, 16: 295.0, 17: 266.0, 18: 243.0, 19: 221.0, 20: 198.0, 21: 177.0
}

RONEAT_ARCHIVE_VERSION = 2


def get_appdata_dir():
    if sys.platform == 'win32':
        base_path = os.getenv('APPDATA')
    else:
        base_path = os.path.expanduser('~')
    app_dir = os.path.join(base_path, 'RoneatStudioPro')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


DATA_DIR          = get_appdata_dir()
PRESETS_DIR       = os.path.join(DATA_DIR, 'presets')
APP_SETTINGS_FILE = os.path.join(DATA_DIR, 'app_settings.json')


def ensure_dirs():
    os.makedirs(PRESETS_DIR, exist_ok=True)


# ── App settings ──────────────────────────────────────────────────────────────

def load_app_settings():
    if os.path.exists(APP_SETTINGS_FILE):
        try:
            with open(APP_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading app settings: {e}", exc_info=True)
    return {"theme": "System"}


def save_app_settings(settings_dict):
    try:
        with open(APP_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Error saving app settings: {e}", exc_info=True)
        return False


# ── Hz presets ────────────────────────────────────────────────────────────────

def load_hz_preset(filepath=None):
    if not filepath:
        filepath = os.path.join(PRESETS_DIR, 'default_hz.json')
    if not os.path.exists(filepath):
        return DEFAULT_HZ.copy()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {int(k): float(v) for k, v in data.items()}
    except Exception as e:
        logging.error(f"Error loading preset: {e}", exc_info=True)
        return DEFAULT_HZ.copy()


def save_hz_preset(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving preset: {e}", exc_info=True)
        return False


# ── .roneat archive format (v2) ───────────────────────────────────────────────

def save_roneat_project(filepath, project_data):
    """
    Save a .roneat project using the requested ZIP format (info.json and notes.json).
    """
    if not filepath.endswith('.roneat'):
        filepath += '.roneat'

    try:
        from core.parse_score import expand_score
        
        try:
            bpm_val = float(project_data.get('bpm', 120))
        except (ValueError, TypeError):
            bpm_val = 120.0
            
        try:
            hits_sec_val = float(project_data.get('hits_sec', 10))
        except (ValueError, TypeError):
            hits_sec_val = 10.0
            
        grid_str = project_data.get('grid', '16 Columns (Medium)')
        try:
            grid_cols = int(grid_str.split()[0])
        except (ValueError, TypeError, IndexError):
            grid_cols = 16

        info = {
            "file_version": "2.0.0",
            "title": project_data.get('title', 'Untitled'),
            "author": project_data.get('author', ''),
            "sync_data": project_data.get('sync_data', None),
            "measure_style": project_data.get('measure', 'Manual (using \'/\')'),
            "grid_columns": grid_cols,
            "font_size": int(project_data.get('font_size', 14)),
            "accent_color": project_data.get('accent', '#c8a96e'),
            "show_left_hand": bool(project_data.get('left_hand', True)),
            "show_bar_numbers": bool(project_data.get('show_nums', True)),
            "bpm": bpm_val,
            "hits_sec": hits_sec_val,
            "instrument_id": project_data.get('instrument_id', 'roneat_ek')
        }
        
        raw_notes = project_data.get('notes', '')
        events = expand_score(raw_notes)
        sync_data = project_data.get('sync_data', None)
        
        beat_sec = 60.0 / max(bpm_val, 1.0)
        
        notes_array = []
        note_id = 1
        current_time_sec = 0.0
        sd_idx = 0
        
        # Calculate Measure Context
        measure_val = 4
        if "8" in info["measure_style"]:
            measure_val = 8
            
        current_beat_count = 0.0
        
        for e in events:
            pitch_lame = e.get('bar') # For expand_score, 'bar' meant the wooden lame/pitch
            beats = e.get('beats', 1.0)
            
            # Time calculations
            if sync_data and sd_idx < len(sync_data):
                note_time = sync_data[sd_idx].get('time', current_time_sec)
                t_curr = note_time
                t_next = (sync_data[sd_idx + 1]['time'] if sd_idx + 1 < len(sync_data) else t_curr + 0.6)
                dur = max(0.1, min(t_next - t_curr, 2.0))
                if e.get('is_tremolo'):
                    dur = dur * e.get('repeat', 1)
                
                if pitch_lame is not None:
                    sd_idx += 1
                current_time_sec = t_curr + dur
            else:
                note_time = current_time_sec
                dur = beat_sec * beats
                current_time_sec += dur

            # Musical Measure calculation
            musical_measure = int(current_beat_count // measure_val) + 1
            current_beat_count += beats

            mins, secs = divmod(note_time, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{int(hours):02d}:{int(mins):02d}:{secs:06.3f}"
            
            evt = {
                "id": note_id,
                "time_sec": round(note_time, 3),
                "time_str": time_str,
                "musical_measure": musical_measure,
                "beat": beats,
                "duration": round(dur, 3),
                "is_rest": pitch_lame is None,
                "is_line_rest": e.get("is_line_rest", False),
                "barline": e.get("barline", False)
            }
            
            if pitch_lame is not None:
                evt["pitch_numeric"] = pitch_lame
                evt["pitch_midi"] = 60 + pitch_lame
                evt["velocity"] = 100
                evt["hand"] = "left" if pitch_lame > 21 else "right"
                evt["repetition_count"] = e.get("repeat", 1)
                evt["left_bar"] = e.get("left_bar")
            else:
                evt["pitch_numeric"] = None
                evt["repetition_count"] = 1
                
            notes_array.append(evt)
            note_id += 1
                
        notes_dict = {
            "events": notes_array
        }
                
        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('info.json', json.dumps(info, indent=2))
            zf.writestr('notes.json', json.dumps(notes_dict, indent=2))
            
        return True
    except Exception as e:
        logging.error(f"Error saving project: {e}", exc_info=True)
        return False


def load_roneat_project(filepath):
    """
    Load a .roneat project.
    Reads info.json from ZIP containing title, author, and notes_text.
    Falls back to legacy format support.
    """
    try:
        # ── Try reading info.json from ZIP first ──────────────────────────────
        if zipfile.is_zipfile(filepath):
            with zipfile.ZipFile(filepath, 'r') as zf:
                if 'info.json' in zf.namelist():
                    info = json.loads(zf.read('info.json').decode('utf-8'))
                    notes_text = ""
                    if 'notes.json' in zf.namelist():
                        try:
                            n_data = json.loads(zf.read('notes.json').decode('utf-8'))
                            events = n_data.get('events', [])
                            
                            # Dynamically rebuild notes_text from events array (Single Source of Truth)
                            tokens = []
                            for ev in events:
                                if ev.get('is_rest'):
                                    if ev.get('is_line_rest'):
                                        tokens.append("_")
                                    else:
                                        tokens.append("-")
                                else:
                                    pitch = ev.get('pitch_numeric')
                                    rep = ev.get('repetition_count', 1)
                                    left_bar = ev.get('left_bar')
                                    if pitch is not None:
                                        default_lh = min(pitch + 7, 21)
                                        if left_bar is not None and left_bar != default_lh:
                                            token = f"({left_bar}){pitch}"
                                        else:
                                            token = str(pitch)
                                        if rep > 1:
                                            token = f"{token}#{rep}"
                                        tokens.append(token)
                                if ev.get('barline'):
                                    tokens.append("/")
                            notes_text = " ".join(tokens)
                            
                        except:
                            pass
                    
                    return {
                        'title': info.get('title', ''),
                        'author': info.get('author', ''),
                        'notes': notes_text,
                        'sync_data': info.get('sync_data', None),
                        'last_audio_path': None,
                        'measure': info.get('measure_style', info.get('measure')),
                        'grid_columns': info.get('grid_columns'),
                        'font_size': info.get('font_size'),
                        'accent': info.get('accent_color', info.get('accent')),
                        'left_hand': info.get('show_left_hand', info.get('left_hand')),
                        'show_nums': info.get('show_bar_numbers', info.get('show_nums')),
                        'bpm': info.get('bpm'),
                        'hits_sec': info.get('hits_sec'),
                        'instrument_id': info.get('instrument_id', 'roneat_ek'),
                    }
        
        # ── Fallback to RoneatScore new file format ─────────────────────────
        try:
            score = RoneatFileManager.load(filepath)
            return {
                'title':           score.title,
                'author':          score.author,
                'notes':           '',  
                'sync_data':       None,
                'last_audio_path': None,
            }
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        
        # ── v2: ZIP archive (legacy backward compat) ──────────────────────────
        if zipfile.is_zipfile(filepath):
            with zipfile.ZipFile(filepath, 'r') as zf:
                meta = json.loads(zf.read('data.json').decode('utf-8'))

                # Extract embedded audio to a temp file so the player can use it
                audio_path = None
                if meta.get('has_audio'):
                    names = [n for n in zf.namelist() if n.startswith('audio/source')]
                    if names:
                        ext      = os.path.splitext(names[0])[1]
                        tmp_dir  = tempfile.mkdtemp(prefix='roneat_')
                        out_path = os.path.join(tmp_dir, f"source{ext}")
                        with open(out_path, 'wb') as f:
                            f.write(zf.read(names[0]))
                        audio_path = out_path

            return {
                'title':           meta.get('title', ''),
                'notes':           meta.get('notes', ''),
                'sync_data':       meta.get('sync_data', None),
                'last_audio_path': audio_path,
            }

        # ── v1: plain JSON (legacy backward compat) ───────────────────────────
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {
            'title':           data.get('title', ''),
            'notes':           data.get('notes', ''),
            'sync_data':       data.get('sync_data', None),
            'last_audio_path': data.get('last_audio_path', None),
        }

    except Exception as e:
        logging.error(f"Error loading project from {filepath}: {e}", exc_info=True)
        return None