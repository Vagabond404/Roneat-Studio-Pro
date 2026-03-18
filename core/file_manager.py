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
    Save a .roneat project as a compressed ZIP archive.

    project_data keys:
        title           : str
        notes           : str
        sync_data       : list | None
        last_audio_path : str | None   — will be embedded if it exists
    """
    if not filepath.endswith('.roneat'):
        filepath += '.roneat'

    audio_src = project_data.get('last_audio_path')

    # Build the JSON metadata (never embed the raw path — store filename only)
    meta = {
        'version':    RONEAT_ARCHIVE_VERSION,
        'title':      project_data.get('title', ''),
        'notes':      project_data.get('notes', ''),
        'sync_data':  project_data.get('sync_data', None),
        'has_audio':  bool(audio_src and os.path.exists(str(audio_src))),
        'audio_name': os.path.basename(str(audio_src)) if audio_src else None,
    }

    try:
        with zipfile.ZipFile(filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('data.json', json.dumps(meta, indent=2, ensure_ascii=False))

            # Embed source audio
            if audio_src and os.path.exists(str(audio_src)):
                ext  = os.path.splitext(audio_src)[1]
                name = f"audio/source{ext}"
                zf.write(audio_src, name)

        return True
    except Exception as e:
        logging.error(f"Error saving project: {e}", exc_info=True)
        return False


def load_roneat_project(filepath):
    """
    Load a .roneat project.
    Supports both v2 ZIP archives and legacy v1 plain JSON files.

    Returns a dict with keys: title, notes, sync_data, last_audio_path
    """
    try:
        # ── v2: ZIP archive ───────────────────────────────────────────────────
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

        # ── v1: plain JSON (backward compat) ──────────────────────────────────
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