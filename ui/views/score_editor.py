"""
ui/views/score_editor.py  v10.0
================================
Roneat Studio Pro — Score Editor

NEW IN v10.0:
  - 100% CustomTkinter In-App Overlays for Export Dialogs.
  - Fixes the Windows 11 Toplevel blank screen bug completely by abandoning OS-level popups.
  - Export menus now slide perfectly over the main UI.
  - Default tremolo speed set to 10 Hits/s.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import math
import threading
import json
import os
import io
import time
from typing import Optional

from core.pdf_exporter  import export_to_pdf
from core.audio_player  import RoneatPlayer
from core.file_manager  import load_hz_preset, DATA_DIR, load_app_settings
from core.calibration   import samples_available
from core.parse_score   import validate_score, expand_score, notes_and_durations, group_beats_into_rows
from core.file_format   import RoneatFileManager, RoneatNote, RoneatScore
from core.rendering.translation import translate_note

from ui.components.step_entry import StepEntryController, RhythmToolbarFrame
from ui.components.virtual_keyboard import VirtualRoneatKeyboard

PRESETS_FILE = os.path.join(DATA_DIR, "score_presets.json")


def load_score_presets():
    try:
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_score_presets(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Presets] Save error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Undo/Redo history manager
# ─────────────────────────────────────────────────────────────────────────────

class _UndoStack:
    MAX = 200

    def __init__(self, textbox):
        self._tb     = textbox
        self._stack  = []
        self._future = []
        self._lock   = False
        self._last   = ""

    def snapshot(self):
        if self._lock:
            return
        text = self._tb.get("0.0", "end-1c")
        if text != self._last:
            self._stack.append(text)
            if len(self._stack) > self.MAX:
                self._stack.pop(0)
            self._future.clear()
            self._last = text

    def on_key(self, event=None):
        if self._lock:
            return
        text = self._tb.get("0.0", "end-1c")
        if text != self._last:
            self._stack.append(self._last)
            if len(self._stack) > self.MAX:
                self._stack.pop(0)
            self._future.clear()
            self._last = text

    def undo(self, event=None):
        if not self._stack:
            return "break"
        self._future.append(self._tb.get("0.0", "end-1c"))
        prev = self._stack.pop()
        self._lock = True
        self._tb.delete("0.0", "end")
        self._tb.insert("0.0", prev)
        self._lock = False
        self._last = prev
        return "break"

    def redo(self, event=None):
        if not self._future:
            return "break"
        self._stack.append(self._tb.get("0.0", "end-1c"))
        nxt = self._future.pop()
        self._lock = True
        self._tb.delete("0.0", "end")
        self._tb.insert("0.0", nxt)
        self._lock = False
        self._last = nxt
        return "break"


# ─────────────────────────────────────────────────────────────────────────────

class ScoreEditor(ctk.CTkFrame):

    def _clr(self, color):
        """Resolve a (light, dark) color tuple to a single hex string."""
        if isinstance(color, (list, tuple)):
            return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def __init__(self, master, get_project_data_callback):
        super().__init__(master, fg_color="transparent")
        self.get_data          = get_project_data_callback
        audio_mode = load_app_settings().get("audio_mode", "adsr")
        self.player            = RoneatPlayer(load_hz_preset(), mode=audio_mode)
        self._jam_player       = RoneatPlayer(load_hz_preset(), mode=audio_mode)
        self.player.load_samples()
        self._jam_player.load_samples()
        self.current_sync_data = None
        self._last_audio_path  = None
        self._last_zip_path    = None
        self._preview_job      = None
        self._current_view     = "table"
        self._playing_bar      = None
        self._metro_job        = None
        self._metro_beat       = False
        self._undo             = None
        self.current_overlay     = None
        self._overlay_backdrop   = None
        self._overlay_backdrop_cv = None
        self._view_mode_var      = ctk.StringVar(value="Numeric")
        
        # ── RoneatScore: New universal file format state ─────────────────────
        self.current_score: Optional[RoneatScore] = self._create_default_score()
        self._syncing_text = False  # Prevent feedback loops during text ↔ RoneatScore sync
        self._prev_mode    = "Numeric"  # Mode the notes_box text is currently encoded in

        # ── 2D interactive state ──────────────────────────────────────────────
        self._roneat_mode   = "playback"   # "playback" | "edit" | "jam"
        self._press_time    = None
        self._press_bar     = None
        self._trem_job      = None
        self._hover_bar     = None
        self._last_play_time = 0.0
        
        # ── Plugin manager reference (set by MainWindow after initialization) ─
        self.plugin_manager = None

        # Premium DAW color palette — dark mode locked
        self.C = {
            "bg":       ("#F2F2F2", "#121212"),
            "panel":    ("#E8E8E8", "#1E1E1E"),
            "card":     ("#FFFFFF", "#252525"),
            "card2":    ("#F0F0F0", "#2A2A2A"),
            "border":   ("#CCCCCC", "#333333"),
            "accent":   "#D4AF37",
            "doc_accent": "#c8a96e",
            "accent2":  "#e85d4a",
            "blue":     "#3d8ec9",
            "green":    "#3ab87a",
            "text":     ("#1A1A1A", "#E0E0E0"),
            "text_dim": ("#666666", "#888888"),
            "warn":     "#f59e0b",
        }

        self.grid_columnconfigure(0, minsize=520, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

        self.bind("<Configure>", self._request_update)
        self.after(200, self.update_preview)
    
    # =========================================================================
    # RONEAT SCORE STATE MANAGEMENT
    # =========================================================================
    
    def set_plugin_manager(self, plugin_manager) -> None:
        """Set reference to the PluginManager for accessing instrument metadata.
        
        Called by MainWindow after plugin_manager_instance is initialized.
        
        Args:
            plugin_manager: Reference to the PluginManager instance.
        """
        self.plugin_manager = plugin_manager
        self._update_instrument_in_players()

    def _update_instrument_in_players(self) -> None:
        """Update the active instrument plugin in all audio players.
        
        Called when the active instrument changes, ensuring playback uses the
        correct frequencies and audio settings for the selected instrument.
        """
        try:
            if self.plugin_manager:
                active_plugin = self._get_active_instrument_plugin()
                if active_plugin:
                    # Update both regular and jam players with the active plugin
                    self.player.instrument_plugin = active_plugin
                    self._jam_player.instrument_plugin = active_plugin
                    
                    # Force plugin frequencies if available
                    if hasattr(active_plugin, 'get_note_frequencies'):
                        plugin_freqs = active_plugin.get_note_frequencies()
                        if plugin_freqs:
                            self.player.roneat_dict = plugin_freqs
                            self._jam_player.roneat_dict = plugin_freqs
                    
                    # Preload notes into the audio engines
                    self.player.load_samples()
                    self._jam_player.load_samples()
        except Exception as e:
            import logging
            logging.warning(f"Failed to update instrument in players: {e}")

    def get_active_view_mode(self) -> str:
        """Returns the active UI rendering view mode."""
        try:
            return self._view_mode_var.get()
        except Exception:
            return "Numeric"

    def set_active_view_mode(self, mode: str) -> None:
        """Sets the active UI rendering view mode."""
        self._view_mode_var.set(mode)
        self._request_update()
    
    def _get_active_note_range(self) -> tuple[int, int]:
        """Get the note range from the active instrument plugin.
        
        Queries the active instrument plugin for its note range. Falls back to
        (1, 21) if the plugin is not available or does not support the API.
        
        Returns:
            tuple[int, int]: (min_note, max_note) notation range.
        """
        try:
            if self.plugin_manager:
                plugin_module = self.plugin_manager.get_active_instrument_plugin_module()
                if plugin_module:
                    # Try to get the plugin instance and call get_note_range()
                    if hasattr(plugin_module, 'get_plugin'):
                        plugin = plugin_module.get_plugin()
                        if hasattr(plugin, 'get_note_range'):
                            return plugin.get_note_range()
        except Exception as e:
            # Log but don't crash - gracefully fall back
            import logging
            logging.warning(f"Failed to get note range from plugin: {e}")
        
        # Fallback to Roneat Ek standard range
        return (1, 21)
    
    def _get_note_label(self, note_numeric: int, notation_mode: str = "numeric") -> str:
        """Get the label for a note from the active instrument plugin.
        
        Queries the active instrument plugin for a note label in the specified
        notation mode. Falls back to numeric representation if unavailable.
        
        Args:
            note_numeric: The numeric note (1-based index).
            notation_mode: Display mode ("numeric", "solfege", "khmer", etc.).
            
        Returns:
            str: The label for the note.
        """
        try:
            if self.plugin_manager:
                plugin_module = self.plugin_manager.get_active_instrument_plugin_module()
                if plugin_module:
                    if hasattr(plugin_module, 'get_plugin'):
                        plugin = plugin_module.get_plugin()
                        if hasattr(plugin, 'get_note_label'):
                            return plugin.get_note_label(note_numeric, notation_mode)
        except Exception as e:
            # Log but don't crash
            import logging
            logging.warning(f"Failed to get note label from plugin: {e}")
        
        # Fallback to simple numeric representation
        return str(note_numeric)
    
    def _create_default_score(self) -> RoneatScore:
        """Create a default RoneatScore for a new project.
        
        Returns:
            RoneatScore with default metadata and empty notes list.
        """
        return RoneatScore(
            title="Untitled",
            author="Anonymous",
            tempo_bpm=120,
            time_signature="4/4",
            notes=[],
            notation_mode="numeric",
            theme="dark",
            software_version="3.0.0"
        )
    
    def _sync_notes_from_text(self) -> None:
        """Convert notes_box text notation to RoneatScore.notes.
        
        Parses the current notation text (e.g., '9 8 7#3 - / 5 6') and
        populates self.current_score.notes with RoneatNote objects.
        Falls back gracefully if text is invalid.
        """
        if self._syncing_text or not self.current_score:
            return

        numeric_text = self._get_numeric_score_text()
        if not numeric_text.strip():
            self.current_score.notes = []
            return

        try:
            errors = validate_score(numeric_text)
            if errors:
                return  # Invalid notation, keep existing notes

            # Parse the notation into structured note data
            events = expand_score(numeric_text)
            if not events:
                self.current_score.notes = []
                return
            
            # Convert events to RoneatNote objects
            notes = []
            note_id = 1
            for event in events:
                if isinstance(event, dict) and "pitch" in event:
                    notes.append(RoneatNote(
                        id=note_id,
                        bar=event.get("bar", 1),
                        beat=event.get("beat", 1.0),
                        duration=event.get("duration", 1.0),
                        pitch_numeric=int(event["pitch"]),
                        pitch_midi=event.get("midi", 60),  # Default MIDI
                        velocity=event.get("velocity", 100),
                        hand=event.get("hand", "right"),
                        repetition_count=event.get("repeat", 1)
                    ))
                    note_id += 1
            
            self.current_score.notes = notes
        except Exception:
            pass  # Silently ignore parse errors during typing
    
    def _update_metadata_from_ui(self) -> None:
        """Update RoneatScore metadata from current UI values.
        
        Reads title from the title_entry widget and applies to current_score.
        """
        if not self.current_score:
            return
        
        title = self.title_entry.get().strip()
        if title:
            self.current_score.title = title
        
        author = self.author_entry.get().strip()
        if author:
            self.current_score.author = author
    
    def open_roneat_file(self, filepath: str) -> bool:
        """Load a .roneat file using RoneatFileManager.
        
        Args:
            filepath: Path to .roneat file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            self._update_metadata_from_ui()
            score = RoneatFileManager.load(filepath)
            self.current_score = score
            
            # Update UI to reflect loaded score
            self._syncing_text = True
            self.title_entry.delete(0, "end")
            self.title_entry.insert(0, score.title)
            
            if hasattr(self, "author_entry"):
                self.author_entry.delete(0, "end")
                self.author_entry.insert(0, score.author)
                
            self._syncing_text = False
            
            self.update_preview()
            return True
        except Exception as e:
            # Lazy import jsonschema to check for validation errors
            try:
                import jsonschema
                if isinstance(e, jsonschema.ValidationError):
                    messagebox.showerror(
                        title="Corrupted File",
                        message=f"The .roneat file is corrupted or invalid:\n\n{str(e)[:200]}"
                    )
                    return False
            except ImportError:
                pass
            
            # Handle other exception types
            if isinstance(e, FileNotFoundError):
                messagebox.showerror(
                    title="File Not Found",
                    message="The file could not be found."
                )
            else:
                messagebox.showerror(
                    title="Error Loading File",
                    message=f"Error loading .roneat file:\n\n{str(e)[:200]}"
                )
            return False
    
    def save_roneat_file(self, filepath: str) -> bool:
        """Save current score to a .roneat file using RoneatFileManager.
        
        Args:
            filepath: Path where .roneat file should be saved.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if not self.current_score:
                messagebox.showwarning(
                    title="No Score",
                    message="No score loaded. Create or open a score first."
                )
                return False
            
            self._update_metadata_from_ui()
            self._sync_notes_from_text()
            
            RoneatFileManager.save(self.current_score, filepath)
            return True
        except ValueError as e:
            messagebox.showwarning(
                title="Validation Error",
                message=f"Score validation failed:\n\n{str(e)[:200]}"
            )
            return False
        except Exception as e:
            messagebox.showerror(
                title="Error Saving File",
                message=f"Error saving .roneat file:\n\n{str(e)[:200]}"
            )
            return False
    
    def set_notation_mode(self, mode: str) -> None:
        """Change notation display mode (numeric or syllabic).
        
        Updates the display_settings but does NOT modify the notes data,
        ensuring notation-agnostic format compatibility.
        
        Args:
            mode: "numeric" or "syllabic".
        """
        if self.current_score and mode in ("numeric", "syllabic"):
            self.current_score.notation_mode = mode
            
            # Update button visual state
            if hasattr(self, '_notation_btns'):
                for m, btn in self._notation_btns.items():
                    if m == mode:
                        btn.configure(
                            fg_color=self.C["accent"],
                            text_color="#0d0d0d"
                        )
                    else:
                        btn.configure(
                            fg_color="transparent",
                            text_color=self.C["text_dim"]
                        )
            
            self.update_preview()

    # =========================================================================
    # LEFT PANEL
    # =========================================================================

    def _build_left_panel(self):
        left = ctk.CTkFrame(self, fg_color = self.C["panel"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(2, weight=1)   # scroll area expands
        left.grid_columnconfigure(0, weight=1)

        # ── Header (row 0) ─────────────────────────────────────────────
        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 8))
        ctk.CTkLabel(hdr, text="🎼  Score Editor",
                     font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                     text_color = self.C["accent"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Edit, preview, play and export your Roneat score",
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color = self.C["text_dim"]).pack(anchor="w", pady=(2, 0))

        # ── Separator (row 1) ──────────────────────────────────────
        ctk.CTkFrame(left, height=1, fg_color = self.C["border"]).grid(
            row=1, column=0, sticky="ew", padx=16, pady=0)

        # ── Scrollable content (row 2) ─────────────────────────────
        scroll = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                        scrollbar_button_color = self.C["accent"])
        scroll.grid(row=2, column=0, sticky="nsew", pady=(4, 0))

        self._build_info_card(scroll)
        self._build_editor_card(scroll)
        self._build_presets_card(scroll)
        self._build_customize_card(scroll)
        self._build_export_card(scroll)

    def _build_info_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="SONG TITLE",
                     font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=16, pady=(14, 4))
        self.title_entry = ctk.CTkEntry(
            card, height=38, corner_radius=4,
            fg_color = self.C["card2"],
            border_width=1, border_color = self.C["border"],
            placeholder_text="Song title",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"))
        self.title_entry.insert(0, "Happy Birthday")
        self.title_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.title_entry.bind("<KeyRelease>", self._request_update)
        
        ctk.CTkLabel(card, text="COMPOSER / AUTHOR",
                     font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=16, pady=(4, 4))
        self.author_entry = ctk.CTkEntry(
            card, height=34, corner_radius=4,
            fg_color = self.C["card2"],
            border_width=1, border_color = self.C["border"],
            placeholder_text="Author name",
            font=ctk.CTkFont(family="Segoe UI", size=12))
        self.author_entry.insert(0, "")
        self.author_entry.pack(fill="x", padx=16, pady=(0, 16))
        self.author_entry.bind("<KeyRelease>", self._request_update)

    def _build_editor_card(self, parent):
        card = self._card(parent)

        hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=18, pady=(14, 0))
        self.notation_hint_lbl = ctk.CTkLabel(
            hdr_row, text="NOTATION  (e.g. 9 8 7#3 - / 5 6)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold", slant="italic"),
            text_color=self.C["text_dim"])
        self.notation_hint_lbl.pack(side="left")
        self.copy_notation_btn = ctk.CTkButton(
            hdr_row, text="⧉  Copy", command=self._copy_notation,
            width=70, height=26, corner_radius=6,
            fg_color="transparent", text_color = self.C["accent"],
            border_width=1, border_color = self.C["accent"],
            hover_color = self.C["card"], font=ctk.CTkFont(size=11))
        self.copy_notation_btn.pack(side="right")

        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.pack(fill="x", padx=16, pady=(2, 0))
        self.valid_dot = tk.Canvas(val_row, width=12, height=12,
                                   highlightthickness=0, bg=self._clr(self.C["card"]))
        self.valid_dot.pack(side="left", pady=2)
        self._draw_valid_dot(True)
        self.valid_lbl = ctk.CTkLabel(val_row, text="Score is valid",
                                      font=ctk.CTkFont(family="Courier", size=10),
                                      text_color = self.C["green"])
        self.valid_lbl.pack(side="left", padx=(6, 0))

        self.notes_box = ctk.CTkTextbox(
            card, height=150, corner_radius=4,
            fg_color = self.C["card2"],
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(family="Consolas", size=15), wrap="word")
        self.notes_box.insert("0.0",
            "10 10 9 10 7 8 /\n"
            "10 10 9 10 6 7 /\n"
            "10 10 3 5 7 8 9 /\n"
            "4 4 5 7 6 7")
        self.notes_box.pack(fill="x", padx=16, pady=(4, 0))
        self.notes_box.bind("<KeyRelease>", self._on_text_modified)

        self._undo = _UndoStack(self.notes_box)
        self.notes_box.bind("<KeyRelease>", self._undo.on_key, add="+")
        inner = self.notes_box._textbox
        inner.bind("<Control-z>",       self._undo.undo)
        inner.bind("<Control-Z>",       self._undo.undo)
        inner.bind("<Control-y>",       self._undo.redo)
        inner.bind("<Control-Y>",       self._undo.redo)
        inner.bind("<Control-Shift-Z>", self._undo.redo)

        # ── Slim toolbar: Undo/Redo inline, then Play/Stop + BPM/Hits/s ──────
        toolbar = ctk.CTkFrame(card, fg_color = self.C["card2"], corner_radius=4, height=40)
        toolbar.pack(fill="x", padx=16, pady=(8, 0))

        # Undo / Redo
        for txt, cmd in [("↩", self._undo.undo), ("↪", self._undo.redo)]:
            ctk.CTkButton(toolbar, text=txt, command=cmd,
                          width=32, height=30, corner_radius=4,
                          fg_color="transparent", text_color = self.C["text_dim"],
                          hover_color = self.C["card"],
                          font=ctk.CTkFont(size=13)).pack(side="left", padx=(4, 0), pady=5)

        # Thin divider
        ctk.CTkFrame(toolbar, width=1, height=22, fg_color = self.C["border"]).pack(
            side="left", padx=6, pady=9)

        # Play / Stop
        self.play_btn = ctk.CTkButton(
            toolbar, text="▶  Play", command=self.play_audio,
            width=82, height=30, corner_radius=4,
            fg_color = self.C["green"], hover_color="#2d8c5f",
            text_color="#0d0d0d",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.play_btn.pack(side="left", padx=(0, 4), pady=5)

        self.stop_btn = ctk.CTkButton(
            toolbar, text="⏹  Stop", command=self.stop_audio,
            width=76, height=30, corner_radius=4,
            fg_color=self.C["accent2"], hover_color="#c0392b",
            text_color="#0d0d0d",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"))
        self.stop_btn.pack(side="left", padx=(0, 8), pady=5)

        # Thin divider
        ctk.CTkFrame(toolbar, width=1, height=22, fg_color = self.C["border"]).pack(
            side="left", padx=(0, 6), pady=9)

        # BPM label + entry
        ctk.CTkLabel(toolbar, text="BPM",
                     font=ctk.CTkFont(family="Segoe UI", size=10),
                     text_color = self.C["text_dim"]).pack(side="left", padx=(0, 4))
        self.bpm_entry = ctk.CTkEntry(
            toolbar, width=46, height=28, corner_radius=4,
            fg_color = self.C["card"],
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(family="Courier", size=12))
        self.bpm_entry.insert(0, "170")
        self.bpm_entry.pack(side="left", padx=(0, 10), pady=6)

        # Hits/s label + entry
        ctk.CTkLabel(toolbar, text="Hits/s",
                     font=ctk.CTkFont(family="Segoe UI", size=10),
                     text_color = self.C["text_dim"]).pack(side="left", padx=(0, 4))
        self.trem_speed_entry = ctk.CTkEntry(
            toolbar, width=40, height=28, corner_radius=4,
            fg_color = self.C["card"],
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(family="Courier", size=12))
        self.trem_speed_entry.insert(0, "10")
        self.trem_speed_entry.pack(side="left", padx=(0, 8), pady=6)

        # Metronome dot
        self.metro_canvas = tk.Canvas(toolbar, width=20, height=20, highlightthickness=0,
                                      bg=self._clr(self.C["card2"]))
        self.metro_canvas.pack(side="left", pady=10)
        self._update_metro_canvas(False)

        self.sync_lbl = ctk.CTkLabel(card, text="",
                                     font=ctk.CTkFont(family="Courier", size=10),
                                     text_color = self.C["green"])
        self.sync_lbl.pack(anchor="w", padx=16, pady=(4, 8))

    def _build_presets_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="PRESETS",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold", slant="italic"),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=18, pady=(14, 6))
        self.preset_combo = ctk.CTkComboBox(
            card, values=self._get_preset_names(),
            command=self._load_preset,
            height=34, corner_radius=8,
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(size=12))
        self.preset_combo.set("Select a preset...")
        self.preset_combo.pack(fill="x", padx=18, pady=(0, 8))
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkButton(btn_row, text="+ Save", command=self._save_preset,
                      height=32, corner_radius=8, width=100,
                      fg_color = self.C["accent"], text_color="#0d1117",
                      hover_color="#deba7e",
                      font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Delete", command=self._delete_preset,
                      height=32, corner_radius=8, width=76,
                      fg_color="transparent", text_color=self.C["accent2"],
                      border_width=1, border_color=self.C["accent2"],
                      hover_color = self.C["card"],
                      font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Import", command=self._import_preset,
                      height=32, corner_radius=8, width=76,
                      fg_color="transparent", text_color = self.C["text"],
                      border_width=1, border_color = self.C["border"],
                      hover_color = self.C["card"],
                      font=ctk.CTkFont(size=12)).pack(side="left")

    def _build_customize_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="DISPLAY SETTINGS",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold", slant="italic"),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=18, pady=(14, 6))
        self._row_label(card, "Measure Style")
        self.measure_combo = ctk.CTkComboBox(
            card, values=["4 beats", "8 beats", "Manual (using '/')"],
            command=self._request_update,
            height=32, corner_radius=8,
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(size=12))
        self.measure_combo.set("Manual (using '/')")
        self.measure_combo.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Grid Columns")
        self.grid_combo = ctk.CTkComboBox(
            card, values=["8 Columns (Large)", "12 Columns",
                          "16 Columns (Medium)", "20 Columns", "24 Columns (Small)"],
            command=self._request_update,
            height=32, corner_radius=8,
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(size=12))
        self.grid_combo.set("8 Columns (Large)")
        self.grid_combo.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Note Font Size")
        self.font_size_slider = ctk.CTkSlider(
            card, from_=8, to=22, number_of_steps=14,
            command=self._request_update,
            progress_color = self.C["accent"],
            button_color = self.C["accent"], height=18)
        self.font_size_slider.set(14)
        self.font_size_slider.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Accent Color")
        color_row = ctk.CTkFrame(card, fg_color="transparent")
        color_row.pack(fill="x", padx=18, pady=(2, 8))
        for hex_col in ["#c8a96e", "#e85d4a", "#3d8ec9", "#3ab87a", "#a78bfa"]:
            ctk.CTkButton(color_row, text="", width=32, height=32, corner_radius=8,
                          fg_color=hex_col, hover_color=hex_col,
                          command=lambda h=hex_col: self._set_accent(h)
                          ).pack(side="left", padx=3)
        
        self.left_hand_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(card, text="Show Left Hand  (+7 bars)",
                      variable=self.left_hand_var, command=self._request_update,
                      font=ctk.CTkFont(size=12),
                      progress_color = self.C["accent"]).pack(anchor="w", padx=18, pady=(0, 6))
        self.show_numbers_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(card, text="Show Bar Numbers",
                      variable=self.show_numbers_var, command=self._request_update,
                      font=ctk.CTkFont(size=12),
                      progress_color = self.C["accent"]).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_export_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="EXPORT",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold", slant="italic"),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=18, pady=(14, 8))
        self.export_pdf_btn = ctk.CTkButton(
            card, text="Export to PDF", command=self.export_pdf,
            height=40, corner_radius=10,
            fg_color = self.C["accent"], text_color="#0d1117",
            hover_color="#deba7e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.export_pdf_btn.pack(fill="x", padx=18, pady=(0, 8))
        self.export_mp4_btn = ctk.CTkButton(
            card, text="Export 2D Video (MP4)", command=self.export_mp4,
            height=40, corner_radius=10,
            fg_color="transparent", text_color = self.C["accent"],
            border_width=1, border_color = self.C["accent"],
            hover_color = self.C["card"],
            font=ctk.CTkFont(size=13))
        self.export_mp4_btn.pack(fill="x", padx=18, pady=(0, 8))
        self.mp4_prog_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.mp4_progress_lbl = ctk.CTkLabel(
            self.mp4_prog_frame, text="",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color = self.C["text_dim"])
        self.mp4_progress_lbl.pack(anchor="w", padx=2, pady=(2, 4))
        self.mp4_prog_bar = ctk.CTkProgressBar(
            self.mp4_prog_frame, height=7, corner_radius=4,
            progress_color = self.C["accent"])
        self.mp4_prog_bar.set(0)
        self.mp4_prog_bar.pack(fill="x", padx=2, pady=(0, 4))
        ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=4)).pack()

    # =========================================================================
    # RIGHT PANEL
    # =========================================================================

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color = self.C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        ctk.CTkLabel(hdr, text="Score Preview",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color = self.C["accent"]).pack(side="left")

        view_frame = ctk.CTkFrame(hdr, fg_color = self.C["card2"], corner_radius=4)
        view_frame.pack(side="right")
        self._view_btns = {}
        for key, label in [("table", "Table"), ("roneat2d", "2D Roneat")]:
            is_active = key == "table"
            btn = ctk.CTkButton(
                view_frame, text=label,
                command=lambda k=key: self._switch_view(k),
                width=96, height=28, corner_radius=4,
                fg_color = self.C["accent"] if is_active else "transparent",
                text_color="#0d0d0d" if is_active else self.C["text"],
                hover_color = self.C["accent"],
                font=ctk.CTkFont(size=11))
            btn.pack(side="left", padx=2, pady=2)
            self._view_btns[key] = btn

        # The Multimodal Segmented Button
        mode_seg = ctk.CTkSegmentedButton(
            hdr, values=["Numeric", "Letters", "Syllabic"],
            variable=self._view_mode_var,
            command=self._on_mode_changed,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            selected_color=self.C["accent"],
            selected_hover_color=self.C["doc_accent"]
        )
        mode_seg.pack(side="right", padx=20)

        ctk.CTkFrame(right, height=1, fg_color = self.C["border"]).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(10, 0))

        self._canvas_container = tk.Frame(right, bg=self._clr(self.C["bg"]))
        self._canvas_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=(4, 0))
        self._canvas_container.grid_rowconfigure(0, weight=1)
        self._canvas_container.grid_columnconfigure(0, weight=1)

        self.vbar = tk.Scrollbar(self._canvas_container, orient="vertical")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.canvas = tk.Canvas(self._canvas_container, highlightthickness=0,
                                yscrollcommand=self.vbar.set, bg=self._clr(self.C["bg"]))
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.config(command=self.canvas.yview)
        self.canvas.bind("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        # Click-to-edit: store (beat_index, x0, y0, x1, y1) for each drawn cell
        self._beat_rects: list[tuple] = []
        self._active_cell_idx: int | None = None   # which cell is focused for keyboard nav
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        # Arrow key navigation (canvas must have focus)
        self.canvas.bind("<Left>",       lambda e: self._navigate_cell(-1))
        self.canvas.bind("<Right>",      lambda e: self._navigate_cell(+1))
        self.canvas.bind("<Tab>",        lambda e: self._navigate_cell(+1))
        self.canvas.bind("<Shift-Tab>",  lambda e: self._navigate_cell(-1))

        self._roneat2d_frame = ctk.CTkFrame(right, fg_color = self.C["bg"], corner_radius=0)
        self._build_roneat2d_view()

    # =========================================================================
    # 2D RONEAT VIEW — BUILD
    # =========================================================================

    def _build_roneat2d_view(self):
        f = self._roneat2d_frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(0, weight=0)
        f.grid_rowconfigure(1, weight=0)
        f.grid_rowconfigure(2, weight=0)
        f.grid_rowconfigure(3, weight=1)   # canvas grows

        # ── Row 0 : mode selector bar ─────────────────────────────────────────
        top = ctk.CTkFrame(f, fg_color = self.C["panel"], corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(top, text="MODE",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color = self.C["text_dim"]
                     ).grid(row=0, column=0, padx=(16, 8), pady=8)

        mode_frame = ctk.CTkFrame(top, fg_color = self.C["card2"], corner_radius=4)
        mode_frame.grid(row=0, column=1, pady=6)

        self._mode_btns = {}
        for mk, mlabel in [("playback", "⏵  Playback"),
                            ("edit",     "✏  Edit"),
                            ("jam",      "🥁  Jam")]:
            is_a = mk == "playback"
            btn = ctk.CTkButton(
                mode_frame, text=mlabel,
                command=lambda m=mk: self._set_roneat_mode(m),
                width=110, height=28, corner_radius=4,
                fg_color = self.C["accent"] if is_a else "transparent",
                text_color="#0d0d0d" if is_a else self.C["text"],
                hover_color = self.C["accent"],
                font=ctk.CTkFont(size=11))
            btn.pack(side="left", padx=2, pady=2)
            self._mode_btns[mk] = btn

        self._mode_hint_lbl = ctk.CTkLabel(
            top, text="Bars light up during playback",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color = self.C["text_dim"])
        self._mode_hint_lbl.grid(row=0, column=2, padx=12, pady=8, sticky="w")

        # ── Row 1 : settings bar (Edit / Jam) — hidden initially ──────────────
        self._2d_settings_frame = ctk.CTkFrame(f, fg_color = self.C["panel"],
                                               corner_radius=0)
        self._2d_settings_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(self._2d_settings_frame, text="Two Mallets",
                     font=ctk.CTkFont(size=11),
                     text_color = self.C["text"]
                     ).grid(row=0, column=0, padx=(16, 4), pady=7)
        self._2d_two_mallet_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self._2d_settings_frame, text="",
                      variable=self._2d_two_mallet_var,
                      width=44, height=22,
                      progress_color = self.C["accent"]
                      ).grid(row=0, column=1, padx=(0, 20), pady=7)

        ctk.CTkFrame(self._2d_settings_frame, width=1, height=28,
                     fg_color = self.C["border"]
                     ).grid(row=0, column=2, padx=(0, 16), pady=7)

        self._trem_lbl = ctk.CTkLabel(self._2d_settings_frame,
                                      text="Tremolo hold time",
                                      font=ctk.CTkFont(size=11),
                                      text_color = self.C["text_dim"])
        self._trem_lbl.grid(row=0, column=3, padx=(0, 6), pady=7)
        self._trem_slider = ctk.CTkSlider(
            self._2d_settings_frame, from_=0.2, to=1.5,
            number_of_steps=13, width=110,
            progress_color = self.C["accent"],
            button_color = self.C["accent"])
        self._trem_slider.set(0.4)
        self._trem_slider.grid(row=0, column=4, padx=(0, 4), pady=7)
        self._trem_val_lbl = ctk.CTkLabel(self._2d_settings_frame, text="0.4s",
                                          font=ctk.CTkFont(family="Courier", size=10),
                                          text_color = self.C["accent"])
        self._trem_val_lbl.grid(row=0, column=5, padx=(0, 16), pady=7, sticky="w")
        self._trem_slider.configure(command=self._on_trem_edit_slider)

        self._2d_feedback_lbl = ctk.CTkLabel(
            self._2d_settings_frame, text="",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color = self.C["accent"])
        self._2d_feedback_lbl.grid(row=0, column=6, padx=(0, 16), pady=7, sticky="e")

        # ── Row 2 : thin separator ────────────────────────────────────────────
        self._2d_sep = ctk.CTkFrame(f, height=1, fg_color = self.C["border"])
        self._2d_sep.grid(row=2, column=0, sticky="ew")

        # ── Row 3 : interactive canvas ────────────────────────────────────────
        self.roneat_label = ctk.CTkLabel(f, text="")
        self.roneat_label.grid(row=3, column=0, sticky="nsew")

        self.roneat_label.bind("<Configure>",
            lambda e: self._draw_roneat2d(self._playing_bar))
        self.roneat_label.bind("<ButtonPress-1>",   self._on_bar_press)
        self.roneat_label.bind("<ButtonRelease-1>", self._on_bar_release)
        self.roneat_label.bind("<ButtonPress-3>",   self._on_bar_right_click)
        self.roneat_label.bind("<Motion>",          self._on_canvas_motion)
        self.roneat_label.bind("<Leave>",           self._on_canvas_leave)

    # =========================================================================
    # MODE MANAGEMENT
    # =========================================================================

    def _set_roneat_mode(self, mode):
        self._roneat_mode = mode
        hints = {
            "playback": "Bars light up during playback",
            "edit":     "Click = write note  |  Hold longer = tremolo  |  Right-click = bar line /",
            "jam":      "Click any bar to play it instantly — nothing is written",
        }
        for mk, btn in self._mode_btns.items():
            a = mk == mode
            btn.configure(fg_color = self.C["accent"] if a else "transparent",
                          text_color="#0d1117" if a else self.C["text"])
        self._mode_hint_lbl.configure(text=hints[mode])

        if mode in ("edit", "jam"):
            self._2d_settings_frame.grid(row=1, column=0, sticky="ew")
            is_edit = mode == "edit"
            self._trem_slider.configure(state="normal" if is_edit else "disabled")
            self._trem_lbl.configure(
                text_color = self.C["text"] if is_edit else self.C["text_dim"])
            self._trem_val_lbl.configure(
                text_color = self.C["accent"] if is_edit else self.C["text_dim"])
        else:
            self._2d_settings_frame.grid_remove()

        self._draw_roneat2d(self._playing_bar)

    def _on_trem_edit_slider(self, val):
        self._trem_val_lbl.configure(text=f"{float(val):.1f}s")

    # =========================================================================
    # VIEW SWITCHING (Table ↔ 2D)
    # =========================================================================

    def _switch_view(self, key):
        self._current_view = key
        for k, btn in self._view_btns.items():
            btn.configure(
                fg_color = self.C["accent"] if k == key else "transparent",
                text_color="#0d1117" if k == key else self.C["text"])
        if key == "roneat2d":
            self._canvas_container.grid_remove()
            self._roneat2d_frame.grid(row=2, column=0, sticky="nsew")
            self._draw_roneat2d(self._playing_bar)
        else:
            try:
                self._roneat2d_frame.grid_remove()
            except Exception:
                pass
            self._canvas_container.grid()
            self.update_preview()

    # =========================================================================
    # 2D RONEAT — GEOMETRY HELPERS
    # =========================================================================

    def _bar_geometry(self, W, H):
        """Calculate bar positions for 2D roneat display.
        
        Dynamically calculates bar positions based on the active instrument's
        note range. Bars are arranged horizontally with varying heights.
        
        Args:
            W: Canvas width in pixels.
            H: Canvas height in pixels.
            
        Returns:
            tuple: (bars, rail_y, rail_h, bar_w) where bars is a list of
                   (bar_num, xl, xr, yt, yb, cx) tuples for each bar.
        """
        # Get dynamic note range from active instrument plugin
        min_note, max_note = self._get_active_note_range()
        n_bars = max_note - min_note + 1
        
        margin_x  = 18
        margin_top = 44
        margin_bot = 32
        bar_gap   = 3
        total_w   = W - margin_x * 2
        bar_w     = (total_w - bar_gap * (n_bars - 1)) / n_bars if n_bars > 0 else total_w
        avail_h   = H - margin_top - margin_bot - 10
        rail_h    = 8
        min_bar_h = avail_h * 0.22
        max_bar_h = avail_h * 0.78
        rail_y    = margin_top

        bars = []
        for i in range(n_bars):
            bar_num = max_note - i
            t       = i / (n_bars - 1) if n_bars > 1 else 0
            bh      = max_bar_h - t * (max_bar_h - min_bar_h)
            xl      = margin_x + i * (bar_w + bar_gap)
            xr      = xl + bar_w
            yt      = rail_y + rail_h
            yb      = yt + bh
            cx      = (xl + xr) / 2
            bars.append((bar_num, xl, xr, yt, yb, cx))
        return bars, rail_y, rail_h, bar_w

    def _bar_at_xy(self, x, y):
        """
        Determine which bar/note is at the given canvas coordinates.
        
        For instruments with custom 2D rendering (like Kong Thom), attempts to use
        the plugin's custom click detection. Falls back to flat grid detection.
        """
        W = self.roneat_label.winfo_width()
        H = self.roneat_label.winfo_height()
        if W < 10 or H < 10:
            return None
        
        # Check if active plugin has custom click detection
        active_plugin = self._get_active_instrument_plugin()
        if active_plugin and hasattr(active_plugin, 'get_note_at_xy'):
            try:
                bar_num = active_plugin.get_note_at_xy(x, y, W, H)
                if bar_num is not None:
                    return bar_num
            except Exception as e:
                import logging
                logging.warning(f"Plugin click detection failed: {e}")
        
        # Fallback to standard flat grid detection
        bars, _, _, _ = self._bar_geometry(W, H)
        for (bar_num, xl, xr, yt, yb, _cx) in bars:
            if xl <= x <= xr and yt <= y <= yb:
                return bar_num
        return None

    # =========================================================================
    # 2D RONEAT — DRAWING
    # =========================================================================

    def _get_active_instrument_plugin(self):
        """Get the active instrument plugin instance.
        
        Returns the plugin instance if available, or None if not found.
        """
        try:
            if self.plugin_manager:
                plugin_module = self.plugin_manager.get_active_instrument_plugin_module()
                if plugin_module and hasattr(plugin_module, 'get_plugin'):
                    return plugin_module.get_plugin()
        except Exception as e:
            import logging
            logging.warning(f"Failed to get active instrument plugin: {e}")
        return None

    def generate_preview_frame(self, W, H, active_bar, hover_bar, press_bar, trem_repeat, active_hand, active_left_bar=None):
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
        from core.rendering.translation import translate_note
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_col = (18, 18, 18) if is_dark else (240, 240, 240)
        
        # Base image
        img = Image.new("RGBA", (W, H), bg_col + (255,))
        draw = ImageDraw.Draw(img)
        
        bars, rail_y, rail_h, bar_w = self._bar_geometry(W, H)
        min_note, max_note = self._get_active_note_range()
        mode = self._roneat_mode
        use_2m = (self._2d_two_mallet_var.get() if mode in ("edit", "jam") else self.left_hand_var.get())
        
        # Load font
        try:
            font = ImageFont.truetype("consola.ttf", max(8, int(bar_w * 0.4)))
        except:
            font = ImageFont.load_default()
 
        # Draw Rail
        rail_col = (62, 62, 66) if is_dark else (166, 124, 82)
        if bars:
            draw.rectangle([bars[0][1] - 6, rail_y, bars[-1][2] + 6, rail_y + rail_h], fill=rail_col)
 
        # Draw Notes
        bar_face = (42, 45, 46) if is_dark else (210, 180, 140)
        bar_edge = (21, 23, 24) if is_dark else (139, 69, 19)
 
        accent_hex = self.C["accent"]
        # Convert hex to RGB
        accent_rgb = tuple(int(accent_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
 
        for (bar_num, xl, xr, yt, yb, cx) in bars:
            is_rh = active_bar is not None and bar_num == active_bar and active_hand in ("both", "right")
            lh_target = active_left_bar if active_left_bar is not None else (active_bar + 7 if active_bar else None)
            is_lh = lh_target is not None and use_2m and bar_num == lh_target and bar_num <= max_note and active_hand in ("both", "left")
            is_press = press_bar is not None and bar_num == press_bar
            is_press_lh = press_bar is not None and use_2m and bar_num == press_bar + 7 and bar_num <= max_note
            is_hov = hover_bar is not None and bar_num == hover_bar and not (is_rh or is_press)
            is_hov_lh = hover_bar is not None and use_2m and bar_num == hover_bar + 7 and bar_num <= max_note and not (is_lh or is_press_lh)
 
            fc = bar_face
            sc = bar_edge
 
            if is_rh or is_press:
                fc = accent_rgb
            elif is_lh or is_press_lh:
                fc = (28, 78, 128) if is_dark else (255, 179, 0)
            elif is_hov:
                fc = (212, 175, 55)
            elif is_hov_lh:
                fc = (184, 134, 11)
 
            # Base shadow/edge
            draw.rounded_rectangle([xl, yt, xr, yb], radius=2, fill=bar_edge)
            # Inner face
            draw.rounded_rectangle([xl + 1, yt, xr - 1, yb - 2], radius=2, fill=fc)
 
            # Draw string (playhead representation)
            i_idx = max_note - bar_num
            tube_r = max(3, min(bar_w * 0.36, 10))
            tube_cy = yb + tube_r + 5 + (tube_r * 0.5 if i_idx % 2 == 0 else 0)
            
            draw.line([(cx, yb), (cx, tube_cy - tube_r)], fill=(68, 68, 68), width=1)
            
            # Strike point / Playhead (Neon ring effect)
            tc = fc if (is_rh or is_press or is_lh or is_press_lh) else ((37, 37, 38) if is_dark else (245, 245, 245))
            draw.ellipse([cx - tube_r, tube_cy - tube_r, cx + tube_r, tube_cy + tube_r], fill=tc)
            
            # Draw Text
            view_lbl = translate_note(bar_num, self.get_active_view_mode())
            lbl_y = tube_cy + tube_r + 5
            lbl_c = accent_rgb
            # center text
            bbox = draw.textbbox((0,0), view_lbl, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw/2, lbl_y), view_lbl, fill=lbl_c, font=font)
 
        return img

    def _draw_roneat2d(self, active_bar=None, hover_bar=None, press_bar=None, trem_repeat=0, active_hand="both", active_left_bar=None):
        import customtkinter as ctk
        
        lbl = getattr(self, 'roneat_label', None)
        if not lbl:
            return
            
        lbl.update_idletasks()
        W = lbl.winfo_width()
        H = lbl.winfo_height()
        if W < 50 or H < 50:
            return
            
        pil_img = self.generate_preview_frame(W, H, active_bar, hover_bar, press_bar, trem_repeat, active_hand, active_left_bar)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(W, H))
        
        lbl.configure(image=ctk_img, text="")
        lbl.image = ctk_img  # Prevent garbage collection

    # =========================================================================
    # 2D RONEAT — MOUSE INTERACTION
    # =========================================================================

    def _on_canvas_motion(self, event):
        if self._roneat_mode not in ("edit", "jam"):
            return
        bar = self._bar_at_xy(event.x, event.y)
        if bar != self._hover_bar:
            self._hover_bar = bar
            self._draw_roneat2d(
                self._playing_bar, hover_bar=bar,
                press_bar=self._press_bar,
                trem_repeat=self._current_trem_repeat())

    def _on_canvas_leave(self, event):
        self._hover_bar = None
        if self._roneat_mode in ("edit", "jam"):
            self._draw_roneat2d(self._playing_bar)

    def _current_trem_repeat(self):
        if self._press_time is None or self._press_bar is None:
            return 0
        held      = time.time() - self._press_time
        try:
            threshold = float(self._trem_slider.get())
        except Exception:
            threshold = 0.4

        if held < threshold:
            return 0
        extra = held - threshold
        return max(2, min(32, 2 + int(extra / 0.18)))

    def _on_bar_press(self, event):
        if self._roneat_mode not in ("edit", "jam"):
            return
        bar = self._bar_at_xy(event.x, event.y)
        if bar is None:
            return
        
        # Validate bar number against active instrument range
        min_note, max_note = self._get_active_note_range()
        if not (min_note <= bar <= max_note):
            return
        
        self._press_bar  = bar
        self._press_time = time.time()

        self._play_interactive_note(bar)

        if self._roneat_mode == "edit":
            self._poll_trem_hold()

        self._draw_roneat2d(self._playing_bar, hover_bar=self._hover_bar,
                            press_bar=bar, trem_repeat=0)

    def _poll_trem_hold(self):
        if self._press_bar is None or self._roneat_mode != "edit":
            return
        rep = self._current_trem_repeat()
        self._draw_roneat2d(self._playing_bar, hover_bar=self._hover_bar,
                            press_bar=self._press_bar, trem_repeat=rep)
        self._trem_job = self.after(80, self._poll_trem_hold)

    def _on_bar_release(self, event):
        if self._roneat_mode not in ("edit", "jam"):
            return

        if self._trem_job:
            try:
                self.after_cancel(self._trem_job)
            except Exception:
                pass
            self._trem_job = None

        bar        = self._press_bar
        press_time = self._press_time

        self._press_bar  = None
        self._press_time = None

        if bar is None or press_time is None:
            self._draw_roneat2d(self._playing_bar, hover_bar=self._hover_bar)
            return

        if self._roneat_mode == "jam":
            self._draw_roneat2d(self._playing_bar, hover_bar=self._hover_bar)
            return

        try:
            held      = time.time() - press_time
            threshold = float(self._trem_slider.get())
            if held >= threshold:
                repeat   = max(2, min(32, 2 + int((held - threshold) / 0.18)))
                token    = f"{bar}#{repeat}"
                feedback = f"✏  {bar}#{repeat}  (tremolo ×{repeat})"
            else:
                token    = str(bar)
                feedback = f"✏  bar {bar}"

            self._edit_append_token(token)

            self._2d_feedback_lbl.configure(text=feedback)
            self.after(1400, lambda: self._2d_feedback_lbl.configure(text=""))
        except Exception as e:
            print(f"[Edit Append Error] {e}")

        self._draw_roneat2d(self._playing_bar, hover_bar=self._hover_bar)

    def _on_bar_right_click(self, event):
        if self._roneat_mode != "edit":
            return
        self._edit_append_token("/")
        self._2d_feedback_lbl.configure(text="Inserted  /  bar line")
        self.after(1000, lambda: self._2d_feedback_lbl.configure(text=""))

    def _edit_append_token(self, token: str):
        """
        Append *token* to notes_box in the current display mode.

        *token* is always a raw numeric string (e.g. "9", "9#3", "-", "/").
        If the active mode is Letters or Syllabic the numeric part is
        translated before appending so the textbox stays in the display mode.
        """
        try:
            import re
            from core.rendering.translation import NotationTranslator

            mode = self.get_active_view_mode()
            display_token = token
            if mode != "Numeric" and token not in ('/', '-', '0', 'x'):
                _NRE = re.compile(r'^(\d+)(#(\d+))?$')
                m = _NRE.match(token)
                if m:
                    label = NotationTranslator.index_to_string(int(m.group(1)), mode)
                    display_token = f"{label}#{m.group(3)}" if m.group(2) else label

            current = self.notes_box.get("0.0", "end-1c").rstrip()
            sep = " " if current else ""
            self.notes_box.insert("end", sep + display_token)
            self.notes_box.see("end")

            if self._undo:
                self._undo.snapshot()
            self._on_text_modified()
        except Exception as e:
            print(f"[_edit_append_token error] {e}")

    def _play_interactive_note(self, bar):
        """Play a note interactively in Jam mode.
        
        Uses the active instrument plugin's frequencies and audio samples if available.
        Falls back to default Roneat Ek frequencies if no plugin is active.
        """
        now = time.time()
        if now - self._last_play_time < 0.05:
            return
        self._last_play_time = now

        # Validate bar number against active instrument range
        min_note, max_note = self._get_active_note_range()
        if not (min_note <= bar <= max_note):
            return

        use_2m = self._2d_two_mallet_var.get()

        def _play():
            try:
                jp = self._jam_player
                if jp.mode == "samples":
                    # Real samples: C++ backend plays pre-loaded audio, zero latency
                    jp.audio_core.trigger_note(bar)
                    if use_2m:
                        lh_idx = bar + 7
                        if lh_idx <= 21:
                            jp.audio_core.trigger_note(lh_idx)
                else:
                    # ADSR synthesis: compute waveform in Python and send to C++ mixer
                    tone = jp._build_single_note(bar_idx=bar, left_bar_idx=min(bar + 7, 21), duration=0.8, two_mallets=use_2m)
                    jp.audio_core.play_buffer(tone)
            except Exception as e:
                import logging
                logging.warning(f"[Interactive play] Error: {e}")

        threading.Thread(target=_play, daemon=True).start()

    # =========================================================================
    # METRONOME
    # =========================================================================

    def _update_metro_canvas(self, beat_on: bool):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#161b22" if is_dark else "#f0f4f8"
        try:
            self.metro_canvas.configure(bg=bg)
            self.metro_canvas.delete("all")
            col = self._clr(self.C["accent"]) if beat_on else ("#30363d" if is_dark else "#cbd5e1")
            self.metro_canvas.create_oval(2, 2, 20, 20, fill=col, outline="")
        except Exception:
            pass

    def _start_metronome(self, bpm):
        self._stop_metronome()
        interval_ms = max(60, int(60000 / max(bpm, 1)))
        self._metro_beat = False

        def tick():
            if not self.player.is_playing:
                self._update_metro_canvas(False)
                return
            self._metro_beat = not self._metro_beat
            self._update_metro_canvas(self._metro_beat)
            self._metro_job = self.after(interval_ms, tick)

        self._metro_job = self.after(0, tick)

    def _stop_metronome(self):
        if self._metro_job:
            try:
                self.after_cancel(self._metro_job)
            except Exception:
                pass
            self._metro_job = None
        self._update_metro_canvas(False)

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def _draw_valid_dot(self, ok: bool):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#1c2128" if is_dark else "#f0f4f8"
        try:
            self.valid_dot.configure(bg=bg)
            self.valid_dot.delete("all")
            col = "#3ab87a" if ok else "#e85d4a"
            self.valid_dot.create_oval(1, 1, 11, 11, fill=col, outline="")
        except Exception:
            pass

    def _run_validation(self):
        numeric_text = self._get_numeric_score_text()
        errors = validate_score(numeric_text)
        ok     = len(errors) == 0
        self._draw_valid_dot(ok)
        if ok:
            events = expand_score(numeric_text)
            n = sum(1 for e in events if e['bar'] is not None)
            self.valid_lbl.configure(
                text=f"Valid  —  {n} note{'s' if n != 1 else ''}",
                text_color = self.C["green"])
        else:
            msg = errors[0] if len(errors) == 1 else f"{len(errors)} errors  —  {errors[0]}"
            self.valid_lbl.configure(text=msg[:60], text_color=self.C["accent2"])

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _card(self, parent):
        c = ctk.CTkFrame(parent, fg_color = self.C["card"], corner_radius=4,
                         border_width=1, border_color = self.C["border"])
        c.pack(fill="x", padx=16, pady=(0, 12))
        return c

    def _row_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(family="Segoe UI", size=10),
                     text_color = self.C["text_dim"]).pack(anchor="w", padx=16)

    def _set_accent(self, hex_col):
        if hex_col.lower() == "#c8a96e":
            self.C["accent"] = "#D4AF37"
            self.C["doc_accent"] = "#c8a96e"
        else:
            self.C["accent"] = hex_col
            self.C["doc_accent"] = hex_col
        self._request_update()

    def _on_text_modified(self, event=None):
        self._sync_notes_from_text()  # Sync notation text to RoneatScore.notes
        self._request_update()
        self._run_validation()
        if self.current_sync_data:
            self.current_sync_data = None
            self.bpm_entry.configure(state="normal")
            self.sync_lbl.configure(text="")

    def _on_mode_changed(self, _=None) -> None:
        """
        Called by CTkSegmentedButton AFTER _view_mode_var has been updated.

        We must decode notes_box using _prev_mode (the mode the text is currently
        encoded in), translate to numeric, then re-encode in the new mode.
        """
        new_mode  = self.get_active_view_mode()   # already updated by CTk
        prev_mode = self._prev_mode               # mode the box is currently in

        if new_mode == prev_mode:
            return   # nothing to do

        # 1. Decode from the old encoding → pure numeric
        numeric_text = self._get_numeric_score_text(mode=prev_mode)

        # 2. Encode into the new display format
        new_text = self._numeric_to_mode(numeric_text, new_mode)

        # 3. Rewrite notes_box (suppress _on_text_modified feedback loop)
        self._syncing_text = True
        try:
            self.notes_box.delete("0.0", "end")
            self.notes_box.insert("0.0", new_text)
        finally:
            self._syncing_text = False

        # 4. Record that the box is now in new_mode
        self._prev_mode = new_mode

        # 5. Update the NOTATION hint label
        examples = {
            "Numeric":  "e.g. 9 8 7#3 - / 5 6",
            "Letters":  "e.g. A2 G2 F1#3 - / D1 E1",
            "Syllabic": "e.g. La2 Sol2 Fa1#3 - / Re1 Mi1",
        }
        if hasattr(self, "notation_hint_lbl"):
            self.notation_hint_lbl.configure(
                text=f"NOTATION  ({examples.get(new_mode, 'e.g. 9 8 7#3 - / 5 6')})")

        self._run_validation()
        self._request_update()

    # ── Notation normalisation helpers ────────────────────────────────────────

    def _get_numeric_score_text(self, mode: str | None = None) -> str:
        """
        Read notes_box and return a **pure numeric** notation string.

        Parameters
        ----------
        mode : str | None
            The notation mode that the notes_box is **currently encoded in**.
            Defaults to ``self._prev_mode`` (what was last written to the box).
            Pass this explicitly when calling from within _on_mode_changed,
            because _view_mode_var may already have been updated to the new mode.
        """
        import re
        from core.rendering.translation import NotationTranslator

        # Use the mode the box is actually encoded in (not the new/target mode)
        decode_mode = mode if mode is not None else self._prev_mode

        if decode_mode == "Numeric":
            return self.notes_box.get("0.0", "end-1c")

        _NUM_RE = re.compile(r'^(\d+)(#(\d+))?$')
        _LEFT_RIGHT_NUM_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
        out_tokens: list[str] = []
        raw = self.notes_box.get("0.0", "end-1c").replace('\n', ' ')
        for tok in raw.split():
            if tok in ('/', '-', '0', 'x', '_'):
                out_tokens.append(tok)
                continue
            
            # Already numeric?
            nm_lr = _LEFT_RIGHT_NUM_RE.match(tok)
            if nm_lr:
                out_tokens.append(tok)
                continue
            nm = _NUM_RE.match(tok)
            if nm:
                out_tokens.append(tok)
                continue

            # Check if left-right display mode format e.g. "(Sol1)Do2#3"
            m_lr = re.match(r'^\((.+?)\)(.+?)(#(\d+))?$', tok)
            if m_lr:
                left_part = m_lr.group(1)
                right_part = m_lr.group(2)
                left_idx = NotationTranslator.string_to_index(left_part, decode_mode)
                right_idx = NotationTranslator.string_to_index(right_part, decode_mode)
                if left_idx is not None and right_idx is not None:
                    if m_lr.group(3):
                        out_tokens.append(f"({left_idx}){right_idx}#{m_lr.group(4)}")
                    else:
                        out_tokens.append(f"({left_idx}){right_idx}")
                else:
                    out_tokens.append('-')
                continue

            # Single note display-mode token, possibly with #N tremolo suffix
            trem = re.match(r'^(.+?)#(\d+)$', tok)
            note_part = trem.group(1) if trem else tok
            idx = NotationTranslator.string_to_index(note_part, decode_mode)
            if idx is None:
                out_tokens.append('-')   # unrecognised → rest
            else:
                out_tokens.append(f"{idx}#{trem.group(2)}" if trem else str(idx))
        return ' '.join(out_tokens)

    @staticmethod
    def _numeric_to_mode(numeric_text: str, mode: str) -> str:
        """
        Translate a pure-numeric notation string into *mode*'s display format.
        Preserves '/', '-', '0', 'x', '_' and tremolo '#N' suffixes.
        """
        import re
        from core.rendering.translation import NotationTranslator

        if mode == "Numeric":
            return numeric_text

        _NUM_RE = re.compile(r'^(\d+)(#(\d+))?$')
        _LEFT_RIGHT_NUM_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
        out: list[str] = []
        for tok in numeric_text.replace('\n', ' ').split():
            if tok in ('/', '-', '0', 'x', '_'):
                out.append(tok)
                continue
            
            m_lr = _LEFT_RIGHT_NUM_RE.match(tok)
            if m_lr:
                left_val = int(m_lr.group(1))
                right_val = int(m_lr.group(2))
                left_label = NotationTranslator.index_to_string(left_val, mode)
                right_label = NotationTranslator.index_to_string(right_val, mode)
                if m_lr.group(3):
                    out.append(f"({left_label}){right_label}#{m_lr.group(4)}")
                else:
                    out.append(f"({left_label}){right_label}")
                continue

            m = _NUM_RE.match(tok)
            if m:
                label = NotationTranslator.index_to_string(int(m.group(1)), mode)
                out.append(f"{label}#{m.group(3)}" if m.group(2) else label)
            else:
                out.append(tok)   # passthrough (already non-numeric?)
        return ' '.join(out)

    def _request_update(self, event=None):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(150, self.update_preview)

    def _copy_notation(self):
        text = self.notes_box.get("0.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.copy_notation_btn.configure(text="✓ Copied!")
            self.after(1500, lambda: self.copy_notation_btn.configure(text="⧉  Copy"))

    # =========================================================================
    # PRESETS
    # =========================================================================

    def _get_preset_names(self):
        p = load_score_presets()
        return list(p.keys()) if p else []

    def _save_preset(self):
        name = simpledialog.askstring("Save Preset", "Enter a name:", parent=self)
        if not name:
            return
        p = load_score_presets()
        p[name] = {
            "measure":    self.measure_combo.get(),
            "grid":       self.grid_combo.get(),
            "left_hand":  self.left_hand_var.get(),
            "show_nums":  self.show_numbers_var.get(),
            "accent":     self.C["accent"],
            "font_size":  int(self.font_size_slider.get()),
            "hits_sec":   self.trem_speed_entry.get().strip()
        }
        save_score_presets(p)
        self.preset_combo.configure(values=list(p.keys()))
        self.preset_combo.set(name)

    def _load_preset(self, name):
        if not name or name == "Select a preset...":
            return
        p = load_score_presets()
        if name not in p:
            return
        d = p[name]
        self.measure_combo.set(d.get("measure", "Manual (using '/')"))
        self.grid_combo.set(d.get("grid", "16 Columns (Medium)"))
        self.left_hand_var.set(d.get("left_hand", True))
        self.show_numbers_var.set(d.get("show_nums", True))
        if "accent" in d:
            self.C["accent"] = d["accent"]
        if "font_size" in d:
            self.font_size_slider.set(d["font_size"])
        if "hits_sec" in d:
            self.trem_speed_entry.delete(0, "end")
            self.trem_speed_entry.insert(0, d["hits_sec"])

        self.current_sync_data = None
        self.bpm_entry.configure(state="normal")
        self.sync_lbl.configure(text="")
        self._request_update()

    def _delete_preset(self):
        name = self.preset_combo.get()
        if not name or name == "Select a preset...":
            return
        p = load_score_presets()
        if name in p:
            del p[name]
            save_score_presets(p)
            self.preset_combo.configure(values=list(p.keys()))
            self.preset_combo.set("Select a preset...")

    def _import_preset(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Roneat Preset", "*.roneat *.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            p    = load_score_presets()
            name = os.path.splitext(os.path.basename(path))[0]
            p[name] = data
            save_score_presets(p)
            self.preset_combo.configure(values=list(p.keys()))
            self.preset_combo.set(name)
            self._load_preset(name)
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    # =========================================================================
    # AUDIO PLAYBACK & VISUAL SYNC
    # =========================================================================

    def play_audio(self):
        if self.player.is_playing:
            self.player.stop()

        # Update instrument in player before playing
        self._update_instrument_in_players()
        
        self.player.roneat_dict = load_hz_preset()
        score       = self._get_numeric_score_text()
        bpm_raw     = self.bpm_entry.get().strip()
        try:
            bpm = max(20, min(int(float(bpm_raw)), 400))
        except (ValueError, TypeError):
            bpm = 120
        two_mallets = self.left_hand_var.get()

        trem_speed_raw = self.trem_speed_entry.get().strip()
        hits_per_sec = float(trem_speed_raw) if trem_speed_raw.replace('.','',1).isdigit() else 10.0
        hits_per_sec = max(2.0, min(hits_per_sec, 64.0))

        self.play_btn.configure(text="Playing...", state="disabled")
        if self.current_sync_data:
            self.bpm_entry.configure(state="disabled")
            self.sync_lbl.configure(text="Synced playback (real tempo)")

        self._start_metronome(bpm)
        threading.Thread(
            target=self._audio_worker, args=(score, bpm, two_mallets, hits_per_sec), daemon=True
        ).start()

    def _play_tremolo_visual(self, bar_idx, repeat, hits_per_sec, two_mallets):
        """Animates the alternating left/right hands exactly 'repeat' times."""
        if bar_idx is None:
            return
        lh_idx = bar_idx + 7 if two_mallets else None
        has_lh = (lh_idx is not None and lh_idx <= 21)

        total_hits = repeat
        hit_dur = 1.0 / max(1.0, hits_per_sec)

        def flash_hit(h):
            if not self.player.is_playing: return
            if self._current_view != "roneat2d" or self._roneat_mode != "playback": return

            if has_lh:
                hand = "right" if h % 2 == 0 else "left"
                self._draw_roneat2d(active_bar=bar_idx, active_hand=hand)
            else:
                self._draw_roneat2d(active_bar=bar_idx, active_hand="right")

            if h + 1 < total_hits:
                self.after(max(1, int(hit_dur * 1000)), lambda: flash_hit(h + 1))

        flash_hit(0)

    def _audio_worker(self, score, bpm, two_mallets, hits_per_sec):
        import re
        _TOK_RE = re.compile(r'^(\d+)(#(\d+))?$')
        _LEFT_RIGHT_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
        events = []

        if self.current_sync_data:
            for i, item in enumerate(self.current_sync_data):
                tok = str(item['note'])
                m_lr = _LEFT_RIGHT_RE.match(tok)
                if m_lr:
                    left_bar = int(m_lr.group(1))
                    bar = int(m_lr.group(2))
                    is_trem = bool(m_lr.group(3))
                    rep = int(m_lr.group(4)) if m_lr.group(4) else 1
                    dur = (min(self.current_sync_data[i+1]['time'] - item['time'], 0.9)
                           if i + 1 < len(self.current_sync_data) else 0.5)
                    events.append({'bar': bar, 'left_bar': left_bar, 'is_trem': is_trem, 'repeat': rep, 'dur': dur})
                    continue

                m = _TOK_RE.match(tok)
                if m:
                    bar = int(m.group(1))
                    is_trem = bool(m.group(2))
                    rep = int(m.group(3)) if m.group(3) else 1
                    dur = (min(self.current_sync_data[i+1]['time'] - item['time'], 0.9)
                           if i + 1 < len(self.current_sync_data) else 0.5)
                    events.append({'bar': bar, 'left_bar': bar + 7, 'is_trem': is_trem, 'repeat': rep, 'dur': dur})
        else:
            beat = 60.0 / max(bpm, 1)
            for tok in score.replace('\n', ' ').split():
                if tok in ('/', '-', '0', 'x', '_'): continue
                
                m_lr = _LEFT_RIGHT_RE.match(tok)
                if m_lr:
                    left_bar = int(m_lr.group(1))
                    bar = int(m_lr.group(2))
                    is_trem = bool(m_lr.group(3))
                    rep = int(m_lr.group(4)) if m_lr.group(4) else 1
                    events.append({'bar': bar, 'left_bar': left_bar, 'is_trem': is_trem, 'repeat': rep, 'dur': beat})
                    continue

                m = _TOK_RE.match(tok)
                if m:
                    bar = int(m.group(1))
                    is_trem = bool(m.group(2))
                    rep = int(m.group(3)) if m.group(3) else 1
                    events.append({'bar': bar, 'left_bar': bar + 7, 'is_trem': is_trem, 'repeat': rep, 'dur': beat})

        token_idx = [0]

        def on_bar(bar_num, left_bar_num=None):
            self._playing_bar = bar_num
            if not (self._current_view == "roneat2d" and self._roneat_mode == "playback"):
                return

            if bar_num is None:
                self.after(0, lambda: self._draw_roneat2d(None))
                return

            if token_idx[0] < len(events):
                ev = events[token_idx[0]]
                token_idx[0] += 1
                lb = left_bar_num if left_bar_num is not None else ev.get('left_bar', bar_num + 7)

                if ev['is_trem']:
                    self.after(0, lambda: self._play_tremolo_visual(bar_num, ev['repeat'], hits_per_sec, two_mallets))
                else:
                    self.after(0, lambda: self._draw_roneat2d(bar_num, active_hand="both", active_left_bar=lb))

        self.player.play_score(score, bpm, two_mallets,
                               sync_data=self.current_sync_data,
                               bar_callback=on_bar,
                               hits_per_sec=hits_per_sec)

        self._playing_bar = None
        def _restore():
            self.play_btn.configure(text="▶  Play", state="normal")
            self.bpm_entry.configure(state="disabled" if self.current_sync_data else "normal")
            self._stop_metronome()
            if self._current_view == "roneat2d":
                self._draw_roneat2d(None, hover_bar=self._hover_bar)

        self.after(0, _restore)

    def stop_audio(self):
        self.player.stop()
        self._playing_bar = None
        self.play_btn.configure(text="▶  Play", state="normal")
        self.bpm_entry.configure(
            state="disabled" if self.current_sync_data else "normal")
        self._stop_metronome()
        if self._current_view == "roneat2d":
            self._draw_roneat2d(None, hover_bar=self._hover_bar)

    # =========================================================================
    # IN-APP OVERLAY DIALOGS (REPLACES BUGGY WINDOWS TOPLEVEL)
    # =========================================================================

    def _show_overlay(self, title_text, build_content_cb):
        """
        Creates a modal overlay card centered internally inside the
        ScoreEditor frame, completely avoiding the window-level bugs.
        """
        self._close_overlay()   # close any existing one first

        # Place the overlay directly in the ScoreEditor frame
        parent = self

        # ── Dialog card ───────────────────────────────────────────────────────
        self.current_overlay = ctk.CTkFrame(parent,
                                            width=460,
                                            fg_color = self.C["card"],
                                            border_width=2,
                                            border_color = self.C["accent"],
                                            corner_radius=16)

        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(self.current_overlay, text=title_text,
                     font=("Georgia", 20, "bold"),
                     text_color = self.C["accent"]).pack(pady=(28, 18), padx=40)

        # Gold separator
        ctk.CTkFrame(self.current_overlay, height=1,
                     fg_color = self.C["border"]).pack(fill="x", padx=24, pady=(0, 8))

        build_content_cb(self.current_overlay)

        # Ensure it stays on top of the 2D Canvas and Textboxes
        self.current_overlay.lift()

    def _close_overlay(self):
        for attr in ("current_overlay", "_overlay_backdrop"):
            obj = getattr(self, attr, None)
            if obj is not None:
                try:
                    obj.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)
        self._overlay_backdrop_cv = None

    # =========================================================================
    # PDF EXPORT
    # =========================================================================

    def export_pdf(self):
        def build_pdf_content(parent):
            cover_var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(parent, text="Include cover page", variable=cover_var,
                            checkbox_height=20, checkbox_width=20,
                            fg_color = self.C["accent"], hover_color = self.C["accent"],
                            font=("Helvetica", 13)).pack(anchor="w", padx=44, pady=8)

            row_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(parent, text="Show row numbers", variable=row_var,
                            checkbox_height=20, checkbox_width=20,
                            fg_color = self.C["accent"], hover_color = self.C["accent"],
                            font=("Helvetica", 13)).pack(anchor="w", padx=44, pady=8)

            comp_row = ctk.CTkFrame(parent, fg_color="transparent")
            comp_row.pack(anchor="w", padx=44, pady=(10, 0), fill="x")

            ctk.CTkLabel(comp_row, text="Composer:", font=("Helvetica", 13)).pack(side="left")
            comp_entry = ctk.CTkEntry(comp_row, width=200, height=32, corner_radius=6,
                                      border_width=1, border_color = self.C["border"],
                                      font=("Helvetica", 13))
            
            # Use the current author from the main editor as default
            current_auth = ""
            if hasattr(self, "author_entry"):
                current_auth = self.author_entry.get().strip()
            comp_entry.insert(0, current_auth)
            
            comp_entry.pack(side="left", padx=(10, 0))

            def confirm():
                opts = {
                    "cover": cover_var.get(),
                    "composer": comp_entry.get().strip(),
                    "row_numbers": row_var.get()
                }
                self._close_overlay()
                self._execute_pdf_export(opts)

            btn_row = ctk.CTkFrame(parent, fg_color="transparent")
            btn_row.pack(pady=(25, 25))

            ctk.CTkButton(btn_row, text="Export", command=confirm,
                          width=100, height=36, corner_radius=8,
                          fg_color = self.C["accent"], text_color="#0d1117", hover_color="#deba7e",
                          font=("Helvetica", 13, "bold")).pack(side="left", padx=10)

            ctk.CTkButton(btn_row, text="Cancel", command=self._close_overlay,
                          width=100, height=36, corner_radius=8,
                          fg_color="transparent", border_width=1, border_color = self.C["border"],
                          text_color = self.C["text"], hover_color = self.C["card"],
                          font=("Helvetica", 13)).pack(side="left", padx=4)

        self._show_overlay("PDF Export Options", build_pdf_content)

    def _execute_pdf_export(self, opts):
        mode_map  = {"4 beats": "4", "8 beats": "8", "Manual (using '/')": "manual"}
        mode_val  = mode_map.get(self.measure_combo.get(), "manual")
        grid_val  = self.grid_combo.get().split(" ")[0]
        columns   = int(grid_val) if grid_val.isdigit() else 16
        raw_title = self.title_entry.get().strip()
        safe_name = "".join(ch for ch in raw_title if ch not in '<>:"/\\|?*' and ord(ch) >= 32).strip() or "score"

        filepath = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            initialfile=f"{safe_name}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")])

        if not filepath:
            return

        self.export_pdf_btn.configure(text="Exporting...", state="disabled")
        self.update()

        try:
            export_to_pdf(filepath, self.title_entry.get(),
                          self._get_numeric_score_text(),
                          mode_val, self.left_hand_var.get(), cols=columns,
                          show_cover=opts["cover"], composer=opts["composer"],
                          show_row_numbers=opts["row_numbers"],
                          accent_hex=self.C["doc_accent"],
                          view_mode=self.get_active_view_mode())
            self.export_pdf_btn.configure(text="✓ Exported!", fg_color = self.C["green"])
        except Exception as e:
            self.export_pdf_btn.configure(text="Failed", fg_color=self.C["accent2"])
            print(f"[PDF] {e}")

        self.after(2000, lambda: self.export_pdf_btn.configure(
            text="Export to PDF", fg_color = self.C["accent"], state="normal"))

    # =========================================================================
    # MP4 EXPORT
    # =========================================================================

    def export_mp4(self):
        import sys as _sys
        missing = []
        try:
            import imageio  # noqa
            if not getattr(_sys, 'frozen', False):
                try:
                    import imageio_ffmpeg  # noqa
                except ImportError:
                    pass
        except ImportError:
            missing.append("imageio[ffmpeg]")
        try:
            from PIL import Image  # noqa
        except ImportError:
            missing.append("Pillow")

        if missing:
            messagebox.showerror(
                "Missing Libraries",
                f"MP4 export requires:\n\n  pip install {' '.join(missing)}\n\n"
                "Please install and restart.")
            return

        from ui.views.video_export_studio import VideoExportStudioWindow
        studio = VideoExportStudioWindow(self.winfo_toplevel(), self)


    # =========================================================================
    # CANVAS PREVIEW (TABLE VIEW)
    # =========================================================================

    def update_preview(self):
        if self._current_view == "roneat2d":
            self._draw_roneat2d(self._playing_bar)
            return

        if hasattr(self, "_roneat2d_frame") and self._current_view != "roneat2d":
            self._roneat2d_frame.grid_remove()
        self._canvas_container.grid(row=2, column=0, sticky="nsew", padx=0, pady=(4, 0))

        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        if cw < 100:
            cw = 760
        self._draw_table_view(cw)

    def _draw_table_view(self, c_width):
        page_w   = min(860, c_width - 40)
        page_h   = int(page_w * 1.414)
        x_off    = int((c_width - page_w) / 2)
        page_gap = 36

        is_dark   = ctk.get_appearance_mode() == "Dark"
        bg_col = self._clr(self.C["bg"])       # #121212
        pg_col = self._clr(self.C["card"])     # #252525 — page card bg
        pg_bdr = self._clr(self.C["border"])   # #333333
        cell_bd = self._clr(self.C["border"])   # #333333
        bar_col   = "#555555"          # bar separator line
        note_col = self.C["doc_accent"]
        cell_bg = "#ffffff"  # white background like paper
        stroke_col = self._clr(("#EAEAEA", "#3E444D"))
        fill_col = self._clr(self.C["text"])
        sub_col = self._clr(self.C["text_dim"])
        trem_col  = self.C["doc_accent"]
        lh_col = self._clr(self.C["blue"])
        rest_col = self._clr(self.C["text_dim"])
        title_col = self.C["doc_accent"]

        self.canvas.configure(bg=bg_col)

        mode = self.get_active_view_mode()
        import re
        # Parse the NUMERIC form so _TOK_RE always matches integers —
        # notes_box may be encoded in Letters or Syllabic right now.
        numeric_text = self._get_numeric_score_text()
        _TOK_RE      = re.compile(r'^(\d+)(#(\d+))?$')
        _LEFT_RIGHT_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
        raw_tokens   = numeric_text.replace('\n', ' ').split()
        beats = []
        for tok in raw_tokens:
            if tok == '/':
                if beats:
                    beats[-1]['barline'] = True
                continue
            if tok == '_':
                beats.append({'bar': None, 'text': '_', 'barline': False,
                              'is_trem': False, 'repeat': 1, 'is_line_rest': True, 'left_bar': None})
                continue
            if tok in ('-', '0', 'x'):
                beats.append({'bar': None, 'text': '-', 'barline': False,
                              'is_trem': False, 'repeat': 1, 'is_line_rest': False, 'left_bar': None})
                continue
            
            m_lr = _LEFT_RIGHT_RE.match(tok)
            if m_lr:
                left_bar = int(m_lr.group(1))
                bar  = int(m_lr.group(2))
                is_t = bool(m_lr.group(3))
                rep  = int(m_lr.group(4)) if m_lr.group(4) else 1
                visual_bar = translate_note(bar, mode)
                beats.append({'bar': bar, 'left_bar': left_bar,
                              'visual_text': f"{visual_bar}~{rep}" if is_t else visual_bar,
                              'visual_bar': visual_bar,
                              'barline': False, 'is_trem': is_t, 'repeat': rep, 'is_line_rest': False})
                continue
                
            m = _TOK_RE.match(tok)
            if m:
                bar  = int(m.group(1))
                is_t = bool(m.group(2))
                rep  = int(m.group(3)) if m.group(3) else 1
                visual_bar = translate_note(bar, mode)
                beats.append({'bar': bar, 'left_bar': bar + 7,
                              'visual_text': f"{visual_bar}~{rep}" if is_t else visual_bar,
                              'visual_bar': visual_bar,
                              'barline': False, 'is_trem': is_t, 'repeat': rep, 'is_line_rest': False})

        grid_val   = self.grid_combo.get().split(" ")[0]
        cols       = int(grid_val) if grid_val.isdigit() else 16
        font_size  = int(self.font_size_slider.get())
        cell_w     = (page_w - 100) / cols
        cell_h     = min(62, max(30, cell_w * 1.2))
        row_gap    = 26

        for i, bd in enumerate(beats):
            bd['original_index'] = i
        grouped_rows = group_beats_into_rows(beats, cols)

        rows_pp    = max(1, math.floor((page_h - 180) / (cell_h + row_gap)))
        total_rows = len(grouped_rows) if grouped_rows else 1
        num_pages  = math.ceil(total_rows / rows_pp) if total_rows > 0 else 1
        total_h    = num_pages * (page_h + page_gap) + page_gap
        self.canvas.configure(scrollregion=(0, 0, c_width, total_h))

        show_left = self.left_hand_var.get()
        show_nums = self.show_numbers_var.get()
        self._beat_rects = []  # reset click regions

        row_global_idx = 0
        for pn in range(num_pages):
            ys     = page_gap + pn * (page_h + page_gap)
            shadow = "#0a0d14" if is_dark else "#c8d4e0"
            self.canvas.create_rectangle(x_off + 4, ys + 4,
                                         x_off + page_w + 4, ys + page_h + 4,
                                         fill=shadow, outline="")
            self.canvas.create_rectangle(x_off, ys, x_off + page_w, ys + page_h,
                                         fill=pg_col, outline=pg_bdr, width=1)
            if pn == 0:
                self.canvas.create_rectangle(
                    x_off + page_w // 2 - 60, ys + 88,
                    x_off + page_w // 2 + 60, ys + 90,
                    fill=title_col, outline="")
                self.canvas.create_text(x_off + page_w / 2, ys + 60,
                    text=self.title_entry.get(),
                    font=("Georgia", 24, "bold"), fill=title_col)
                author = self.author_entry.get().strip() if hasattr(self, 'author_entry') else ""
                if author and author.lower() != "anonymous":
                    self.canvas.create_text(x_off + page_w / 2, ys + 104,
                        text=f"Composer: {author}",
                        font=("Georgia", 10), fill=sub_col)
                grid_y = ys + 148
            else:
                grid_y = ys + 56

            row_i = 0
            while row_global_idx < len(grouped_rows) and row_i < rows_pp:
                row = grouped_rows[row_global_idx]
                cells = row['cells']
                cy_top = grid_y + row_i * (cell_h + row_gap)
                x      = x_off + 50
                
                for col_i in range(cols):
                    self.canvas.create_rectangle(x, cy_top, x + cell_w, cy_top + cell_h,
                                                 outline=cell_bd, fill=cell_bg)
                    
                    if col_i < len(cells):
                        bd = cells[col_i]
                        orig_idx = bd['original_index']
                        self._beat_rects.append((orig_idx, x, cy_top, x + cell_w, cy_top + cell_h))
                        cx_ = x + cell_w / 2
                        cy_ = cy_top + cell_h / 2
                        
                        if show_nums and bd['bar'] is not None:
                            bar  = bd['bar']
                            is_t = bd['is_trem']
                            rep  = bd['repeat']
                            lbl = bd['visual_text']
                            vbar = bd['visual_bar']
                            
                            fs = min(font_size, max(9, int(cell_w * 0.42)))
                            if mode in ["Syllabic", "Letters"]:
                                fs = int(fs * 0.8) # scale down for Solfeggio syllables

                            if is_t:
                                if show_left:
                                    self.canvas.create_text(cx_, cy_ - fs * 0.45, text=lbl,
                                        font=("Courier", int(fs * 0.82), "bold"), fill=trem_col)
                                    lh = bd.get('left_bar') or (bar + 7)
                                    lh_vbar = translate_note(lh, mode)
                                    if lh <= 21:
                                        self.canvas.create_text(cx_, cy_ + fs * 0.65,
                                            text=f"{lh_vbar}~{rep}",
                                            font=("Courier", int(fs * 0.55), "bold"), fill=lh_col)
                                else:
                                    self.canvas.create_text(cx_, cy_, text=lbl,
                                        font=("Courier", fs, "bold"), fill=trem_col)
                            else:
                                if show_left:
                                    self.canvas.create_text(cx_, cy_ - fs * 0.45, text=vbar,
                                        font=("Courier", int(fs * 0.9), "bold"), fill=note_col)
                                    lh = bd.get('left_bar') or (bar + 7)
                                    lh_vbar = translate_note(lh, mode)
                                    if lh <= 21:
                                        self.canvas.create_text(cx_, cy_ + fs * 0.65, text=lh_vbar,
                                            font=("Courier", int(fs * 0.6), "bold"), fill=lh_col)
                                else:
                                    self.canvas.create_text(cx_, cy_, text=vbar,
                                        font=("Courier", fs, "bold"), fill=note_col)
                        elif bd['bar'] is None:
                            fs = min(font_size, max(9, int(cell_w * 0.42)))
                            self.canvas.create_text(cx_, cy_, text="-",
                                font=("Courier", fs, "bold"), fill=rest_col)
                                
                        measure_val = self.measure_combo.get()
                        is_barline  = False
                        if "Manual" not in measure_val:
                            group = 4 if "4" in measure_val else 8
                            if (col_i + 1) % group == 0 and col_i < cols - 1:
                                is_barline = True
                        elif bd.get('barline'):
                            is_barline = True
                        if is_barline:
                            self.canvas.create_line(x + cell_w, cy_top, x + cell_w, cy_top + cell_h,
                                                    fill=bar_col, width=2)
                    
                    x += cell_w
                
                if row.get('line_below'):
                    line_color = "#000000" if not is_dark else "#FFFFFF"
                    self.canvas.create_line(x_off + 50, cy_top + cell_h + row_gap / 2,
                                            x_off + 50 + cols * cell_w, cy_top + cell_h + row_gap / 2,
                                            width=1.5, fill=line_color)
                row_global_idx += 1
                row_i += 1

            self.canvas.create_text(x_off + page_w / 2, ys + page_h - 18,
                text=f"- {pn + 1} / {num_pages} -",
                font=("Georgia", 9), fill=sub_col)

    def _on_canvas_click(self, event) -> None:
        """Handle canvas left-click: open inline editor for the clicked note cell."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        for (beat_idx, x0, y0, x1, y1) in self._beat_rects:
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                self._active_cell_idx = beat_idx
                self.canvas.focus_set()   # canvas must have keyboard focus for arrow keys
                self._open_cell_editor(beat_idx, x0, y0, x1, y1)
                return

    def _navigate_cell(self, delta: int) -> None:
        """
        Move the active cell by *delta* positions (-1 = previous, +1 = next)
        and open its inline editor.  Wraps at list boundaries.
        """
        if not self._beat_rects:
            return
        n = len(self._beat_rects)
        # Start from current position or beginning
        if self._active_cell_idx is None:
            next_idx = 0
        else:
            # Find the position of active_cell_idx within _beat_rects
            positions = [r[0] for r in self._beat_rects]
            try:
                pos = positions.index(self._active_cell_idx)
            except ValueError:
                pos = 0
            pos = (pos + delta) % n
            next_idx = positions[pos]

        self._active_cell_idx = next_idx
        # Find the rect for this cell
        for (beat_idx, x0, y0, x1, y1) in self._beat_rects:
            if beat_idx == next_idx:
                # Scroll canvas so the cell is visible
                canvas_h = self.canvas.winfo_height()
                _, _, _, scroll_h = self.canvas.bbox("all") if self.canvas.find_all() else (0, 0, 0, 1)
                if scroll_h > 0:
                    frac = max(0.0, min(1.0, (y0 - canvas_h / 3) / scroll_h))
                    self.canvas.yview_moveto(frac)
                self._open_cell_editor(beat_idx, x0, y0, x1, y1)
                return

    def _open_cell_editor(self, beat_idx: int, x0: float, y0: float,
                          x1: float, y1: float) -> None:
        """
        Floating Entry widget overlaid on the clicked canvas cell.

        - Populates with the *display* string for the current notation mode.
        - Accepts input in the current mode (case-insensitive for Letters/Syllabic).
        - On commit, converts back to a raw integer token via NotationTranslator
          and writes that integer to notes_box (keeping the data model numeric).
        """
        import re
        from core.rendering.translation import NotationTranslator

        mode = self.get_active_view_mode()   # "Numeric" | "Letters" | "Syllabic"

        text = self.notes_box.get("0.0", "end-1c")
        raw_tokens: list[str] = []
        beat_map: list[int] = []   # maps beat_idx → position in raw_tokens

        for raw in text.replace('\n', ' ').split():
            if raw == '/':
                raw_tokens.append(raw)
                continue
            raw_tokens.append(raw)
            beat_map.append(len(raw_tokens) - 1)

        if beat_idx >= len(beat_map):
            return
        tok_pos = beat_map[beat_idx]
        current_raw = raw_tokens[tok_pos]   # raw integer string, e.g. "9" or "9#3" or "-"

        # ── Determine display value for the editor ────────────────────────
        # notes_box is already in the current display mode, so current_raw
        # is already the display string (e.g. "Si2", "B2", "9", "-").
        # For numeric mode we still want the plain integer shown.
        _LEFT_RIGHT_NUM_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
        _NOTE_RE = re.compile(r'^(\d+)(#(\d+))?$')
        
        m_lr = _LEFT_RIGHT_NUM_RE.match(current_raw)
        m = _NOTE_RE.match(current_raw)
        
        if mode != "Numeric" and (m_lr or m):
            if m_lr:
                left_bar = int(m_lr.group(1))
                right_bar = int(m_lr.group(2))
                lh_str = NotationTranslator.index_to_string(left_bar, mode)
                rh_str = NotationTranslator.index_to_string(right_bar, mode)
                if m_lr.group(3):
                    display_val = f"({lh_str}){rh_str}#{m_lr.group(4)}"
                else:
                    display_val = f"({lh_str}){rh_str}"
            else:
                bar_int = int(m.group(1))
                display_val = NotationTranslator.index_to_string(bar_int, mode)
                if m.group(2):
                    display_val = f"{display_val}#{m.group(3)}"
        else:
            display_val = current_raw   # already in display mode ("-", "Si2", "B2", "9")

        # ── Overlay dimensions ────────────────────────────────────────────
        w = int(x1 - x0)
        h = int(y1 - y0)

        hint = NotationTranslator.valid_hints(mode)
        entry_var = tk.StringVar(value=display_val)
        entry = tk.Entry(
            self.canvas,
            textvariable=entry_var,
            font=("Courier", max(9, min(14, int(w * 0.38)))),
            bd=0, highlightthickness=2,
            highlightcolor=self._clr(self.C["accent"]),
            highlightbackground=self._clr(self.C["accent"]),
            bg="#FFFFFF", fg="#111111",
            justify="center"
        )
        entry_win = self.canvas.create_window(x0, y0, anchor="nw",
                                              window=entry, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, "end")

        # Tooltip showing valid values
        _tip = tk.Label(
            self.canvas, text=hint,
            bg="#2b2b2b", fg="#cccccc",
            font=("Courier", 8), bd=0, padx=4, pady=2
        )
        _tip_win = self.canvas.create_window(x0, y1, anchor="nw", window=_tip)

        def _destroy_tip():
            try:
                self.canvas.delete(_tip_win)
                _tip.destroy()
            except Exception:
                pass

        def _commit(ev=None):
            _destroy_tip()
            raw_input = entry_var.get().strip()

            if not raw_input or raw_input in ('-', '0', 'x', '_'):
                # Rest / silence / visual separator
                raw_tokens[tok_pos] = "-" if raw_input in ('', '-', '0', 'x') else raw_input
                _flush()
                return

            # Convert display string → integer index
            if mode == "Numeric":
                # Accept plain int or int#trem or (left)right or (left)right#trem
                _LR_NUM = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
                _N_NUM = re.compile(r'^(\d+)(#(\d+))?$')
                nm_lr = _LR_NUM.match(raw_input)
                nm = _N_NUM.match(raw_input)
                if nm_lr:
                    left_bar = int(nm_lr.group(1))
                    right_bar = int(nm_lr.group(2))
                    if 1 <= left_bar <= 21 and 1 <= right_bar <= 21:
                        raw_tokens[tok_pos] = raw_input
                        _flush()
                        return
                elif nm:
                    idx = int(nm.group(1))
                    if 1 <= idx <= 21:
                        raw_tokens[tok_pos] = raw_input
                        _flush()
                        return
                _cancel()
                return
            else:
                # Check for double note format in Letters/Syllabic: e.g. "(G1)C2#3"
                lr_match = re.match(r'^\((.+?)\)(.+?)(#(\d+))?$', raw_input)
                if lr_match:
                    left_part = lr_match.group(1)
                    right_part = lr_match.group(2)
                    trem_part = lr_match.group(4) if lr_match.group(3) else None
                    left_idx = NotationTranslator.string_to_index(left_part, mode)
                    right_idx = NotationTranslator.string_to_index(right_part, mode)
                    if left_idx is not None and right_idx is not None:
                        lh_str = NotationTranslator.index_to_string(left_idx, mode)
                        rh_str = NotationTranslator.index_to_string(right_idx, mode)
                        new_token = f"({lh_str}){rh_str}"
                        if trem_part:
                            new_token = f"{new_token}#{trem_part}"
                        raw_tokens[tok_pos] = new_token
                        _flush()
                    else:
                        _cancel()
                    return

                # Check for single note tremolo suffix in Letters/Syllabic: e.g. "Sol#3"
                trem_match = re.match(r'^(.+?)#(\d+)$', raw_input)
                note_part  = trem_match.group(1) if trem_match else raw_input
                trem_part  = trem_match.group(2) if trem_match else None

                idx = NotationTranslator.string_to_index(note_part, mode)
                if idx is None:
                    _cancel()   # invalid input — do nothing
                    return
                display_token = NotationTranslator.index_to_string(idx, mode)
                new_token = display_token
                if trem_part:
                    new_token = f"{display_token}#{trem_part}"
                raw_tokens[tok_pos] = new_token
                _flush()

        def _flush():
            new_text = ' '.join(raw_tokens)
            self.notes_box.delete("0.0", "end")
            self.notes_box.insert("0.0", new_text)
            self._on_text_modified()
            self.canvas.delete(entry_win)
            entry.destroy()

        def _cancel(ev=None):
            _destroy_tip()
            self.canvas.delete(entry_win)
            entry.destroy()

        entry.bind("<Return>",   _commit)
        entry.bind("<KP_Enter>", _commit)
        entry.bind("<FocusOut>", _commit)
        entry.bind("<Escape>",   _cancel)
        # Arrow key / Tab navigation: commit current cell and move to next/prev
        def _commit_and_move(delta, ev=None):
            _commit()
            self.after(30, lambda: self._navigate_cell(delta))
        entry.bind("<Right>",      lambda e: _commit_and_move(+1))
        entry.bind("<Tab>",        lambda e: _commit_and_move(+1))
        entry.bind("<Left>",       lambda e: _commit_and_move(-1))
        entry.bind("<Shift-Tab>",  lambda e: _commit_and_move(-1))