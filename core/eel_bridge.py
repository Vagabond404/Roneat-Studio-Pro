import eel
import os
import sys
import logging
import threading
import time
import shutil
from tkinter import filedialog
import sounddevice as sd

# Backend imports
from core.file_manager import (
    load_app_settings, save_app_settings, load_hz_preset,
    save_roneat_project, load_roneat_project
)
from core.audio_player import RoneatPlayer, samples_available
from core.plugin_manager import PluginManager
from core.plugin_api import init_api
from core.audio_analyzer import audio_to_notes
from core.calibration import load_fingerprints

# ── Global Application State ────────────────────────────────────────────────
current_project = {
    "title": "Happy Birthday",
    "author": "Traditional",
    "notes": "1 1 2 1 4 3 / 1 1 2 1 5 4 / 1 1 8 6 4 3 2 / 10 10 9 6 7 6",
    "bpm": "170",
    "grid": "8 Columns (Large)",
    "measure": "Manual (using '/')",
    "font_size": 14,
    "accent": "#c8a96e",
    "left_hand": True,
    "show_nums": True,
    "hits_sec": "10",
    "instrument_id": "roneat_ek",
    "sync_data": None,
    "last_audio_path": None
}

class EelApp:
    """Mock main window class to support existing plugin infrastructure."""
    def __init__(self):
        self.C = {
            "accent": "#d4af37",
            "accent2": "#e85d4a",
            "success": "#3ab87a",
            "text": "#e0e0e0",
            "text_dim": "#888888",
            "sidebar_bg": "#1e1e1e",
            "border": "#3e3e42",
            "hover": "#2a2a2a",
            "main_bg": "#121212",
            "card": "#252526"
        }
        self.frames = {}
        self._app_is_ready = True

    def get_project_data(self):
        return current_project

    def save_proj(self):
        pass

    def load_proj(self, filepath):
        load_project_file(filepath)

    def show_toast(self, message: str, level: str = "info", duration: int = 3000):
        # Call JS toaster if exposed
        try:
            eel.js_show_toast(message, level, duration)
        except Exception:
            logging.info(f"Toast ({level}): {message}")

    def _request_update(self):
        pass

    def _refresh_plugin_ui(self):
        pass

    def _refresh_nav_translations(self):
        pass

# Instantiate global singletons
eel_app = EelApp()
plugin_manager_instance = PluginManager()

# Initialize dynamic audio players (Samples mode if samples are present, else ADSR synthesis)
play_mode = "samples" if samples_available() else "adsr"
score_player = RoneatPlayer(load_hz_preset(), mode=play_mode)
jam_player = RoneatPlayer(load_hz_preset(), mode=play_mode)

def init_bridge():
    """Bootstraps plugin manager and loads active plugins."""
    plugin_manager_instance.initialize(eel_app)
    rebuild_players()

def rebuild_players():
    """Sets active instrument plugin on players and loads samples if needed."""
    active_plugin = get_active_instrument_plugin()
    score_player.instrument_plugin = active_plugin
    jam_player.instrument_plugin = active_plugin

    # Re-read frequencies from plugin if custom
    if active_plugin and hasattr(active_plugin, 'get_note_frequencies'):
        try:
            freqs = active_plugin.get_note_frequencies()
            if freqs:
                score_player.roneat_dict = freqs
                jam_player.roneat_dict = freqs
        except Exception as e:
            logging.warning(f"Failed to read custom frequencies: {e}")

    # Load audio buffers (both adsr and samples need to be loaded into the C++ audio core)
    threading.Thread(target=score_player.load_samples, daemon=True).start()
    threading.Thread(target=jam_player.load_samples, daemon=True).start()

def get_active_instrument_plugin():
    try:
        plugin_module = plugin_manager_instance.get_active_instrument_plugin_module()
        if plugin_module and hasattr(plugin_module, 'get_plugin'):
            return plugin_module.get_plugin()
    except Exception as e:
        logging.warning(f"Error loading active plugin: {e}")
    return None

def get_active_note_range():
    active_plugin = get_active_instrument_plugin()
    if active_plugin and hasattr(active_plugin, 'get_note_range'):
        return active_plugin.get_note_range()
    return (1, 21) # standard Roneat Ek range

# ── EEL RPC ENDPOINTS ─────────────────────────────────────────────────────────

@eel.expose
def get_settings():
    return load_app_settings()

@eel.expose
def save_settings_api(settings_dict):
    save_app_settings(settings_dict)
    
    # Update active player modes and reload samples
    audio_mode = settings_dict.get("audio_mode", "adsr")
    global play_mode
    play_mode = audio_mode
    score_player.mode = audio_mode
    jam_player.mode = audio_mode
    rebuild_players()

    try:
        import core.i18n as i18n
        i18n.set_lang(settings_dict.get("language", "fr"))
    except Exception:
        pass
    return True

@eel.expose
def get_project_data_api():
    # Sync with active instrument ID
    current_project["instrument_id"] = plugin_manager_instance.get_active_instrument_plugin_id()
    return current_project

@eel.expose
def update_project_data_field(key, value):
    current_project[key] = value

@eel.expose
def get_available_instruments_api():
    instruments = plugin_manager_instance.get_available_instruments()
    if not instruments:
        instruments = [("roneat_ek", "Roneat Ek (Standard)")]
    return instruments

@eel.expose
def change_instrument_api(instrument_id):
    success = plugin_manager_instance.set_active_instrument_plugin_id(instrument_id)
    if success:
        current_project["instrument_id"] = instrument_id
        rebuild_players()
    return success

@eel.expose
def get_installed_plugins_api():
    plugins = plugin_manager_instance.get_installed_plugins()
    res = []
    for p in plugins:
        res.append({
            "id": p.id,
            "name": p.name,
            "version": p.version,
            "author": p.author,
            "description": p.description,
            "active": p.active
        })
    return res

@eel.expose
def toggle_plugin_active_api(plugin_id, active_bool):
    if active_bool:
        success = plugin_manager_instance.enable_plugin(plugin_id)
    else:
        success = plugin_manager_instance.disable_plugin(plugin_id)
    if success:
        rebuild_players()
    return success

@eel.expose
def install_plugin_zip_api(zip_path):
    success = plugin_manager_instance.install_plugin(zip_path)
    if success:
        rebuild_players()
    return success

@eel.expose
def reload_all_plugins_api():
    plugin_manager_instance.scan_and_load_plugins()
    rebuild_players()
    return True

@eel.expose
def select_audio_file_dialog():
    path = filedialog.askopenfilename(
        filetypes=[("Audio Files", "*.mp3 *.wav")]
    )
    return path if path else None

@eel.expose
def select_zip_file_dialog():
    path = filedialog.askopenfilename(
        filetypes=[("Plugin Archives", "*.zip")]
    )
    return path if path else None

@eel.expose
def check_calibration_api():
    single_fps, two_fps = load_fingerprints()
    return bool((single_fps and len(single_fps) > 0) or (two_fps and len(two_fps) > 0))

@eel.expose
def start_audio_transcription(file_path, two_mallets):
    def _worker():
        try:
            roneat_dict = load_hz_preset()
            
            def progress_cb(pct, msg, poly_info):
                # When done, get final notes string and sync details
                if pct == 100:
                    result = audio_to_notes(
                        file_path, roneat_dict,
                        two_mallets=two_mallets,
                        progress_callback=None
                    )
                    if isinstance(result, tuple) and len(result) == 3:
                        notes_str, poly_info_res, sync_data = result
                    else:
                        notes_str, poly_info_res, sync_data = result, None, []
                        
                    sync_list = list(sync_data) if sync_data else []
                    eel.js_transcribe_progress(100, msg, poly_info_res, notes_str, sync_list)
                else:
                    eel.js_transcribe_progress(pct, msg, poly_info, "", [])
                    
            # Trigger analysis
            audio_to_notes(
                file_path, roneat_dict,
                two_mallets=two_mallets,
                progress_callback=progress_cb
            )
        except Exception as e:
            logging.error(f"Transcription error: {e}", exc_info=True)
            eel.js_transcribe_progress(0, f"Error: {str(e)}", None, "", [])

    threading.Thread(target=_worker, daemon=True).start()
    return True

@eel.expose
def import_transcribed_score_api(notes, two_mallets, sync_data, audio_path):
    current_project["notes"] = notes
    current_project["left_hand"] = two_mallets
    current_project["sync_data"] = sync_data
    current_project["last_audio_path"] = audio_path
    return True

@eel.expose
def play_score_api(notes_text, bpm, two_mallets, hits_sec):
    def _play():
        try:
            bpm_val = int(bpm) if bpm else 120
            hits_val = float(hits_sec) if hits_sec else 10.0
            
            # Count played beats to increment active note highlights in React
            token_idx = [0]
            raw_tokens = notes_text.replace('\n', ' ').split()
            beats_list = []
            
            # Map raw tokens (ignore barlines for UI indexing)
            for i, tok in enumerate(raw_tokens):
                if tok != '/':
                    beats_list.append(tok)
            
            def on_bar(bar_num, left_bar_num=None):
                if bar_num is None:
                    eel.js_active_beat_highlight(None, None)
                    return
                    
                lb = left_bar_num if left_bar_num is not None else bar_num + 7
                
                # Check highlight index boundaries
                idx = token_idx[0]
                if idx < len(beats_list):
                    token_idx[0] += 1
                    eel.js_active_beat_highlight(idx, lb)
                else:
                    eel.js_active_beat_highlight(bar_num, lb)
                    
            score_player.play_score(
                notes_text, bpm_val, two_mallets,
                sync_data=current_project.get("sync_data"),
                bar_callback=on_bar,
                hits_per_sec=hits_val
            )
        except Exception as e:
            logging.error(f"Playback error: {e}", exc_info=True)
        finally:
            eel.js_active_beat_highlight(None, None)

    threading.Thread(target=_play, daemon=True).start()
    return True

@eel.expose
def stop_score_api():
    score_player.stop()
    return True

@eel.expose
def trigger_jam_note(note, two_mallets):
    def _play():
        try:
            if jam_player.mode == "samples":
                jam_player.audio_core.trigger_note(note)
                if two_mallets:
                    lh = note + 7
                    if lh <= 21:
                        jam_player.audio_core.trigger_note(lh)
            else:
                tone = jam_player._build_single_note(
                    bar_idx=note, left_bar_idx=min(note + 7, 21),
                    duration=0.8, two_mallets=two_mallets
                )
                jam_player.audio_core.play_buffer(tone)
        except Exception as e:
            logging.warning(f"Jam note trigger error: {e}")

    threading.Thread(target=_play, daemon=True).start()
    return True

@eel.expose
def export_pdf_api():
    raw_title = current_project.get("title", "Untitled").strip()
    safe_name = "".join(c for c in raw_title if c not in '<>:"/\\|?*' and ord(c) >= 32).strip() or "score"
    
    filepath = filedialog.asksaveasfilename(
        initialfile=f"{safe_name}.pdf",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not filepath:
        return None

    # Call pdf exporter
    from core.pdf_exporter import export_to_pdf
    
    measure_style = current_project.get("measure", "Manual (using '/')")
    mode_map = {"4 beats": "4", "8 beats": "8", "Manual (using '/')": "manual"}
    measure_mode = mode_map.get(measure_style, "manual")
    
    grid_str = current_project.get("grid", "8 Columns (Large)")
    try:
        cols = int(grid_str.split()[0])
    except Exception:
        cols = 8
        
    success = export_to_pdf(
        filepath=filepath,
        title=current_project.get("title", ""),
        notes_text=current_project.get("notes", ""),
        measure_mode=measure_mode,
        left_hand=current_project.get("left_hand", True),
        cols=cols,
        show_cover=False,
        composer=current_project.get("author", "Anonymous"),
        show_row_numbers=True,
        accent_hex=current_project.get("accent", "#c8a96e"),
        view_mode=current_project.get("viewMode", "Numeric")
    )
    
    return filepath if success else None

@eel.expose
def export_mp4_api():
    raw_title = current_project.get("title", "Untitled").strip()
    safe_name = "".join(c for c in raw_title if c not in '<>:"/\\|?*' and ord(c) >= 32).strip() or "score"
    
    filepath = filedialog.asksaveasfilename(
        initialfile=f"{safe_name}.mp4",
        defaultextension=".mp4",
        filetypes=[("MP4 Video", "*.mp4")]
    )
    if not filepath:
        return False

    # Perform background render
    from core.video_exporter import build_timeline, render_frame, export_mp4, total_duration
    from core.parse_score import expand_score
    
    bpm_val = int(current_project.get("bpm", 120))
    hits_val = float(current_project.get("hits_sec", 10.0))
    
    events_mp4 = expand_score(current_project.get("notes", ""))
    tokens = []
    durations = []
    beat_sec = 60.0 / max(bpm_val, 1)
    dt_hit = 1.0 / max(1.0, hits_val)

    for ev in events_mp4:
        if ev['bar'] is None:
            tokens.append("-")
            dur = beat_sec
            durations.append(dur)
            continue
            
        if current_project.get("sync_data"):
            dur = beat_sec
        else:
            if ev['is_tremolo']:
                dur = ev['repeat'] * dt_hit
            else:
                dur = beat_sec * ev['beats']
                
        bar = ev['bar']
        left_bar = ev.get('left_bar')
        default_lh = min(bar + 7, 21)
        has_custom_lh = (left_bar is not None and left_bar != default_lh)
        
        if ev['is_tremolo']:
            tok = f"({left_bar}){bar}#{ev['repeat']}" if has_custom_lh else f"{bar}#{ev['repeat']}"
        else:
            tok = f"({left_bar}){bar}" if has_custom_lh else str(bar)
            
        tokens.append(tok)
        durations.append(dur)

    # Render audio array
    render_player = RoneatPlayer(load_hz_preset(), mode=play_mode, instrument_plugin=get_active_instrument_plugin())
    if play_mode == "samples":
        render_player.load_samples()
        
    audio_arr = render_player.render_score_to_array(
        tokens, durations, two_mallets=current_project.get("left_hand", True), hits_per_sec=hits_val
    )
    audio_rate = render_player.sample_rate

    # Find ffmpeg binary
    def _find_ffmpeg():
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            for name in ("ffmpeg.exe", "ffmpeg"):
                c = os.path.join(exe_dir, name)
                if os.path.exists(c): return c
        dev = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "ffmpeg.exe"))
        if os.path.exists(dev): return dev
        found = shutil.which("ffmpeg")
        return found if found else "ffmpeg"

    # Progress wrapper
    def _progress(frac, label):
        eel.js_video_export_progress(int(frac * 100), label)

    # Call backend video exporter
    from core.video_exporter import export_mp4 as export_mp4_backend
    
    grid_str = current_project.get("grid", "8 Columns (Large)")
    try:
        cols = int(grid_str.split()[0])
    except Exception:
        cols = 8

    # We default resolution to 1080p landscape (1920x1080)
    export_mp4_backend(
        filepath=filepath,
        score_text=current_project.get("notes", ""),
        bpm=bpm_val,
        hits_per_sec=hits_val,
        audio_arr=audio_arr,
        audio_rate=audio_rate,
        dark_mode=True,
        song_title=current_project.get("title", ""),
        two_mallets=current_project.get("left_hand", True),
        accent_hex=current_project.get("accent", "#c8a96e"),
        view_mode=current_project.get("viewMode", "Numeric"),
        sync_data=current_project.get("sync_data"),
        ffmpeg_bin=_find_ffmpeg(),
        progress_cb=_progress,
        W=1920,
        H=1080,
        FPS=60,
        title_scale=1.0,
        label_scale=1.0,
        status_scale=1.0,
        title_y_offset=0.0,
        label_y_offset=0.0,
        status_y_offset=0.0,
        show_labels=current_project.get("show_nums", True),
        show_status=True
    )
    
    return True

@eel.expose
def save_project_dialog_api():
    raw_title = current_project.get("title", "Untitled").strip()
    safe_name = "".join(c for c in raw_title if c.isalnum() or c in " _-").strip() or "roneat_project"
    
    fp = filedialog.asksaveasfilename(
        initialfile=f"{safe_name}.roneat",
        defaultextension=".roneat",
        filetypes=[("Roneat Projects", "*.roneat")]
    )
    if not fp:
        return None
        
    if save_roneat_project(fp, current_project):
        plugin_manager_instance.trigger_hook("on_project_save", current_project)
        return fp
    return None

@eel.expose
def load_project_dialog_api():
    fp = filedialog.askopenfilename(
        filetypes=[("Roneat Projects", "*.roneat")]
    )
    if fp:
        load_project_file(fp)
    return fp if fp else None

def load_project_file(filepath):
    data = load_roneat_project(filepath)
    if data:
        global current_project
        current_project = {
            "title": data.get("title", ""),
            "author": data.get("author", "Anonymous"),
            "notes": data.get("notes", ""),
            "sync_data": data.get("sync_data", None),
            "last_audio_path": data.get("last_audio_path", None),
            "measure": data.get("measure", "Manual (using '/')"),
            "grid": f"{data.get('grid_columns', 8)} Columns",
            "font_size": data.get("font_size", 14),
            "accent": data.get("accent", "#c8a96e"),
            "left_hand": bool(data.get("left_hand", True)),
            "show_nums": bool(data.get("show_nums", True)),
            "bpm": str(data.get("bpm", 120)),
            "hits_sec": str(data.get("hits_sec", 10)),
            "instrument_id": data.get("instrument_id", "roneat_ek")
        }
        
        # Switch instrument
        plugin_manager_instance.set_active_instrument_plugin_id(current_project["instrument_id"])
        rebuild_players()
        
        # Send project back to JS
        eel.js_load_project_data(current_project, filepath)
        
        # Trigger plugins hook
        plugin_manager_instance.trigger_hook("on_project_open", current_project)

@eel.expose
def get_plugin_custom_tabs_api():
    res = []
    for tab in plugin_manager_instance.custom_tabs:
        res.append({
            "tab_id": tab["tab_id"],
            "label": tab["label"],
            "icon": tab["icon"]
        })
    return res

@eel.expose
def trigger_custom_plugin_tab_action_api(tab_id):
    # If a plugin registered a dynamic tab, we execute its primary window trigger or callback
    # For compatibility, trigger custom menu/toolbar bindings associated with it
    plugin_id = None
    for tab in plugin_manager_instance.custom_tabs:
        if tab["tab_id"] == tab_id:
            plugin_id = tab["plugin_id"]
            break
            
    if plugin_id:
        # Trigger dynamic hook for this plugin action
        plugin_manager_instance.trigger_hook_for_plugin(plugin_id, "on_app_start")
        return f"Ran hooks for {plugin_id}"
    return "No plugin found"

@eel.expose
def get_audio_devices_api():
    try:
        devices = []
        for dev in sd.query_devices():
            if dev['max_output_channels'] > 0:
                devices.append(dev['name'])
        return list(set(devices)) # unique names
    except Exception:
        return []

@eel.expose
def get_hz_preset_api():
    try:
        return load_hz_preset()
    except Exception as e:
        logging.error(f"Error getting Hz preset: {e}")
        from core.file_manager import DEFAULT_HZ
        return DEFAULT_HZ.copy()

@eel.expose
def save_hz_preset_api(hz_dict):
    try:
        clean_dict = {int(k): float(v) for k, v in hz_dict.items()}
        from core.file_manager import PRESETS_DIR, save_hz_preset
        filepath = os.path.join(PRESETS_DIR, 'default_hz.json')
        success = save_hz_preset(filepath, clean_dict)
        if success:
            score_player.roneat_dict = clean_dict
            jam_player.roneat_dict = clean_dict
            rebuild_players()
        return success
    except Exception as e:
        logging.error(f"Error saving Hz preset: {e}", exc_info=True)
        return False

@eel.expose
def get_default_hz_api():
    try:
        from core.file_manager import DEFAULT_HZ
        return {str(k): float(v) for k, v in DEFAULT_HZ.items()}
    except Exception as e:
        logging.error(f"Error getting default Hz: {e}")
        return {}

@eel.expose
def get_samples_available_api():
    return samples_available()

@eel.expose
def run_calibration_api(single_path, two_path):
    def _worker():
        try:
            s_fps = None
            t_fps = None
            
            def prog(pct, msg):
                eel.js_calibration_progress(pct, msg)
                
            from core.calibration import calibrate_from_audio, save_fingerprints
            
            if single_path:
                prog(10, "Analyzing single mallet hits...")
                s_fps = calibrate_from_audio(
                    single_path, 21,
                    progress_callback=lambda p, m: prog(int(p * 0.5), m)
                )
            if two_path:
                prog(60, "Analyzing two mallets hits...")
                t_fps = calibrate_from_audio(
                    two_path, 13,
                    progress_callback=lambda p, m: prog(50 + int(p * 0.5), m)
                )
                
            if s_fps or t_fps:
                save_fingerprints(s_fps, t_fps)
                prog(100, "Calibration saved successfully!")
            else:
                prog(-1, "Calibration failed: Spectral density too low.")
        except Exception as e:
            logging.error(f"Calibration error: {e}", exc_info=True)
            eel.js_calibration_progress(-1, f"Error: {str(e)}")

    threading.Thread(target=_worker, daemon=True).start()
    return True
