import sys
import types
from typing import Any, Callable
import logging
from tkinter import messagebox
import threading

# ── Dynamic Module Injection ──────────────────────────────────────────────────
roneat_api = types.ModuleType('roneat_api')

roneat_api_core = types.ModuleType('roneat_api.core')
roneat_api_ui = types.ModuleType('roneat_api.ui')
roneat_api_audio = types.ModuleType('roneat_api.audio')
roneat_api_score = types.ModuleType('roneat_api.score')
roneat_api_project = types.ModuleType('roneat_api.project')

sys.modules['roneat_api'] = roneat_api
sys.modules['roneat_api.core'] = roneat_api_core
sys.modules['roneat_api.ui'] = roneat_api_ui
sys.modules['roneat_api.audio'] = roneat_api_audio
sys.modules['roneat_api.score'] = roneat_api_score
sys.modules['roneat_api.project'] = roneat_api_project

roneat_api.core = roneat_api_core
roneat_api.ui = roneat_api_ui
roneat_api.audio = roneat_api_audio
roneat_api.score = roneat_api_score
roneat_api.project = roneat_api_project

class PluginAPIError(Exception):
    pass

class RoneatAPI:
    """Singleton holding references to internal app components for the API."""
    def __init__(self):
        self.app = None
        self.plugin_manager = None

    def initialize(self, app, plugin_manager):
        self.app = app
        self.plugin_manager = plugin_manager

API_STATE = RoneatAPI()

def _require_app():
    if not API_STATE.app:
        raise PluginAPIError("application is not ready")
    return API_STATE.app

def _require_editor():
    app = _require_app()
    editor = app.frames.get("editor")
    if not editor:
        raise PluginAPIError("editor frame not found")
    return editor


# ── CORE API ──────────────────────────────────────────────────────────────────
def _core_get_settings() -> dict:
    from core.file_manager import load_app_settings
    return load_app_settings()

def _core_set_setting(key: str, value: Any):
    logging.info(f"Plugin setting generic preference {key}={value}")

roneat_api_core.get_settings = _core_get_settings
roneat_api_core.set_setting = _core_set_setting

# ── PROJECT API ───────────────────────────────────────────────────────────────
def _project_get_data() -> dict:
    app = _require_app()
    return app.get_project_data()

def _project_save():
    app = _require_app()
    app.save_proj()

def _project_load(filepath: str):
    if not isinstance(filepath, str):
        raise TypeError("filepath must be a string")
    app = _require_app()
    app.load_proj(filepath)

roneat_api_project.get_data = _project_get_data
roneat_api_project.save = _project_save
roneat_api_project.load = _project_load

# ── UI API ────────────────────────────────────────────────────────────────────
def _ui_get_main_window():
    return API_STATE.app

def _ui_add_menu_item(menu_name: str, label: str, command: Callable):
    if not callable(command): raise TypeError("command must be callable")
    if API_STATE.plugin_manager:
        API_STATE.plugin_manager.add_custom_menu_item(menu_name, label, command)

def _ui_add_toolbar_button(icon: str, tooltip: str, command: Callable):
    if not callable(command): raise TypeError("command must be callable")
    if API_STATE.plugin_manager:
        API_STATE.plugin_manager.add_custom_toolbar_button(icon, tooltip, command)

def _ui_create_sidebar_panel(title: str, content_widget):
    if API_STATE.plugin_manager:
        return API_STATE.plugin_manager.create_custom_sidebar_panel(title, content_widget)

def _ui_add_custom_tab(tab_id: str, label: str, icon: str, widget_class: Any):
    if API_STATE.plugin_manager:
        API_STATE.plugin_manager.add_custom_tab(tab_id, label, icon, widget_class)

def _ui_show_dialog(title: str, message: str, dialog_type: str = "info"):
    if dialog_type == "error":
        messagebox.showerror(title, message)
    elif dialog_type == "warning":
        messagebox.showwarning(title, message)
    else:
        messagebox.showinfo(title, message)

def _ui_show_toast(message: str, level: str = "info", duration: int = 3000):
    app = _require_app()
    if hasattr(app, "show_toast"):
        app.show_toast(message, level, duration)
    else:
        logging.info(f"TOAST ({level}): {message}")

def _ui_create_window(title: str, width: int = 400, height: int = 300):
    import customtkinter as ctk
    app = _require_app()
    win = ctk.CTkToplevel(app)
    win.title(title)
    win.geometry(f"{width}x{height}")
    win.transient(app)
    return win

def _ui_get_theme_colors() -> dict:
    if API_STATE.app and hasattr(API_STATE.app, "C"):
        return dict(API_STATE.app.C)
    return {}

def _ui_set_theme_color(key: str, hex_color: str):
    if not isinstance(key, str) or not isinstance(hex_color, str):
        raise TypeError("key and hex_color must be strings")
    app = _require_app()
    if hasattr(app, "C") and key in app.C:
        app.C[key] = hex_color
        
        pid = API_STATE.plugin_manager._current_executing_plugin if API_STATE.plugin_manager else None
        if pid:
            API_STATE.plugin_manager.plugin_state_history.append({
                "plugin_id": pid, "type": "theme", "key": key, "value": hex_color
            })
            
        editor = app.frames.get("editor") if hasattr(app, 'frames') else None
        if hasattr(app, "_request_update"):
            app._request_update()
        elif editor and hasattr(editor, "_request_update"):
            editor._request_update()
            if hasattr(app, "_refresh_plugin_ui"):
                app._refresh_plugin_ui()
        logging.info(f"Theme color '{key}' updated to {hex_color} by plugin.")

def _ui_set_language(lang_code: str):
    import core.i18n as i18n
    i18n.set_lang(lang_code)
    
    pid = API_STATE.plugin_manager._current_executing_plugin if API_STATE.plugin_manager else None
    if pid:
        API_STATE.plugin_manager.plugin_state_history.append({
            "plugin_id": pid, "type": "language", "value": lang_code
        })
        
    app = _require_app()
    if hasattr(app, '_refresh_nav_translations'):
        app._refresh_nav_translations()

roneat_api_ui.get_main_window = _ui_get_main_window
roneat_api_ui.add_menu_item = _ui_add_menu_item
roneat_api_ui.add_toolbar_button = _ui_add_toolbar_button
roneat_api_ui.create_sidebar_panel = _ui_create_sidebar_panel
roneat_api_ui.add_custom_tab = _ui_add_custom_tab
roneat_api_ui.show_dialog = _ui_show_dialog
roneat_api_ui.show_toast = _ui_show_toast
roneat_api_ui.create_window = _ui_create_window
roneat_api_ui.get_theme_colors = _ui_get_theme_colors
roneat_api_ui.set_theme_color = _ui_set_theme_color
roneat_api_ui.set_language = _ui_set_language

# ── AUDIO API ─────────────────────────────────────────────────────────────────
def _audio_play_note(bar_index: int, duration: float):
    if not isinstance(bar_index, int) or not isinstance(duration, (int, float)):
        raise TypeError("Invalid types for play_note")
    editor = _require_editor()
    if hasattr(editor, "player"):
        def _play():
            editor.player.is_playing = True
            editor.player._play_note(bar_index, duration, two_mallets=False)
            editor.player.is_playing = False
        threading.Thread(target=_play, daemon=True).start()

def _audio_play_frequency(hz: float, duration: float):
    if not isinstance(hz, (int, float)) or not isinstance(duration, (int, float)):
        raise TypeError("Invalid types for play_frequency")
    editor = _require_editor()
    if hasattr(editor, "player"):
        import sounddevice as sd
        def _play_freq():
            tone = editor.player.generate_tone(hz, duration, bar_num=None)
            sd.play(tone, editor.player.sample_rate)
            sd.wait()
        threading.Thread(target=_play_freq, daemon=True).start()

def _audio_stop_all():
    editor = _require_editor()
    if hasattr(editor, "player"):
        editor.player.stop()

def _audio_is_playing() -> bool:
    editor = _require_editor()
    if hasattr(editor, "player"):
        return getattr(editor.player, "is_playing", False)
    return False

roneat_api_audio.play_note = _audio_play_note
roneat_api_audio.play_frequency = _audio_play_frequency
roneat_api_audio.stop_all = _audio_stop_all
roneat_api_audio.is_playing = _audio_is_playing


# ── SCORE API ─────────────────────────────────────────────────────────────────
def _score_get_raw_text() -> str:
    editor = _require_editor()
    if hasattr(editor, "notes_box"):
        return editor.notes_box.get("1.0", "end-1c")
    return ""

def _score_replace_text(text: str):
    if not isinstance(text, str): raise TypeError("text must be string")
    editor = _require_editor()
    if hasattr(editor, "notes_box"):
        editor.notes_box.delete("1.0", "end")
        editor.notes_box.insert("1.0", text)
        if hasattr(editor, "_on_text_modified"):
            editor._on_text_modified(None)

def _score_insert_at_cursor(text: str):
    if not isinstance(text, str): raise TypeError("text must be string")
    editor = _require_editor()
    if hasattr(editor, "notes_box"):
        editor.notes_box.insert("insert", text)
        if hasattr(editor, "_on_text_modified"):
            editor._on_text_modified(None)

def _score_add_note(bar_index: int, time: float, duration: float):
    if not isinstance(bar_index, int) or not isinstance(time, (int, float)) or not isinstance(duration, (int, float)):
        raise TypeError("Invalid types for add_note parameters")
    editor = _require_editor()
    if hasattr(editor, "notes_box"):
        current = editor.notes_box.get("end-2c", "end-1c")
        prefix = "\n" if current and current != "\n" else ""
        note_str = f"{prefix}B{bar_index} {time:.2f} {duration:.2f}"
        editor.notes_box.insert("end", note_str)
        if hasattr(editor, "_on_text_modified"):
            editor._on_text_modified(None)

def _score_set_tempo(bpm: int):
    if not isinstance(bpm, int): raise TypeError("bpm must be integer")
    if not (20 <= bpm <= 400): raise ValueError("bpm must be between 20 and 400")
    editor = _require_editor()
    if hasattr(editor, "bpm_entry"):
        editor.bpm_entry.delete(0, "end")
        editor.bpm_entry.insert(0, str(bpm))

def _score_get_all_notes() -> list:
    editor = _require_editor()
    if hasattr(editor, 'get_all_notes'):
        try:
            return editor.get_all_notes()
        except Exception:
            pass
    return []

roneat_api_score.get_raw_text = _score_get_raw_text
roneat_api_score.replace_text = _score_replace_text
roneat_api_score.insert_at_cursor = _score_insert_at_cursor
roneat_api_score.add_note = _score_add_note
roneat_api_score.set_tempo = _score_set_tempo
roneat_api_score.get_all_notes = _score_get_all_notes

# ── V1 RETRO-COMPATIBILITY ALIASES ─────────────────────────────────────────────
roneat_api_core.get_score = _score_get_raw_text
roneat_api_core.get_current_project = _project_get_data
roneat_api_core.save_project = _project_save
roneat_api_core.export_pdf = lambda path, opts: None
roneat_api_core.export_mp4 = lambda path, opts: None
roneat_api_score.remove_note = lambda note_text: None
roneat_api_score.add_bar_line = lambda time: None
roneat_api_audio.get_player = lambda: None
roneat_api_audio.record_audio = lambda duration: None
roneat_api_audio.analyze_pitch = lambda audio_data: []

def init_api(app, plugin_manager):
    API_STATE.initialize(app, plugin_manager)
    logging.info("Roneat Plugin API v2.0 initialized and injected into sys.modules")
