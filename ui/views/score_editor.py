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
import time

from core.pdf_exporter  import export_to_pdf
from core.audio_player  import RoneatPlayer
from core.file_manager  import load_hz_preset, DATA_DIR
from core.calibration   import samples_available
from core.parse_score   import validate_score, expand_score, notes_and_durations

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
    def __init__(self, master, get_project_data_callback):
        super().__init__(master, fg_color="transparent")
        self.get_data          = get_project_data_callback
        self.player            = RoneatPlayer(load_hz_preset(), mode="adsr")
        self._jam_player       = RoneatPlayer(load_hz_preset(), mode="adsr")
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

        # ── 2D interactive state ──────────────────────────────────────────────
        self._roneat_mode   = "playback"   # "playback" | "edit" | "jam"
        self._press_time    = None
        self._press_bar     = None
        self._trem_job      = None
        self._hover_bar     = None
        self._last_play_time = 0.0

        self.C = {
            "bg":       ("gray96", "#0d1117"),
            "panel":    ("gray93", "#161b22"),
            "card":     ("white",  "#1c2128"),
            "card2":    ("gray95", "#1c2128"),
            "border":   ("gray80", "#30363d"),
            "accent":   "#c8a96e",
            "accent2":  "#e85d4a",
            "blue":     "#3d8ec9",
            "green":    "#3ab87a",
            "text":     ("gray10", "gray92"),
            "text_dim": ("gray45", "#8b949e"),
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
    # LEFT PANEL
    # =========================================================================

    def _build_left_panel(self):
        left = ctk.CTkFrame(self, fg_color=self.C["panel"], corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 0))
        ctk.CTkLabel(hdr, text="🎼  Score Editor",
                     font=ctk.CTkFont(family="Georgia", size=24, weight="bold"),
                     text_color=self.C["accent"]).pack(anchor="w")
        ctk.CTkLabel(hdr, text="Edit, preview, play and export your Roneat score",
                     font=ctk.CTkFont(size=12),
                     text_color=self.C["text_dim"]).pack(anchor="w", pady=(4, 0))
        ctk.CTkFrame(left, height=1, fg_color=self.C["border"]).grid(
            row=0, column=0, sticky="ew", padx=20, pady=(74, 0))

        scroll = ctk.CTkScrollableFrame(left, fg_color="transparent",
                                        scrollbar_button_color=self.C["accent"])
        scroll.grid(row=1, column=0, sticky="nsew")

        self._build_info_card(scroll)
        self._build_editor_card(scroll)
        self._build_notation_guide(scroll)
        self._build_audio_mode_card(scroll)
        self._build_presets_card(scroll)
        self._build_customize_card(scroll)
        self._build_export_card(scroll)

    def _build_info_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="SONG TITLE",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(anchor="w", padx=18, pady=(14, 4))
        self.title_entry = ctk.CTkEntry(
            card, height=38, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            placeholder_text="Song title",
            font=ctk.CTkFont(family="Georgia", size=14))
        self.title_entry.insert(0, "Bot Sathukar")
        self.title_entry.pack(fill="x", padx=18, pady=(0, 14))
        self.title_entry.bind("<KeyRelease>", self._request_update)

    def _build_editor_card(self, parent):
        card = self._card(parent)

        hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(hdr_row, text="NOTATION  (e.g. 9 8 7#3 - / 5 6)",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(side="left")
        self.copy_notation_btn = ctk.CTkButton(
            hdr_row, text="⧉  Copy", command=self._copy_notation,
            width=70, height=26, corner_radius=6,
            fg_color="transparent", text_color=self.C["accent"],
            border_width=1, border_color=self.C["accent"],
            hover_color=self.C["card"], font=ctk.CTkFont(size=11))
        self.copy_notation_btn.pack(side="right")

        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.pack(fill="x", padx=18, pady=(2, 0))
        self.valid_dot = tk.Canvas(val_row, width=12, height=12,
                                   highlightthickness=0, bg="#1c2128")
        self.valid_dot.pack(side="left", pady=2)
        self._draw_valid_dot(True)
        self.valid_lbl = ctk.CTkLabel(val_row, text="Score is valid",
                                      font=ctk.CTkFont(family="Courier", size=10),
                                      text_color=self.C["green"])
        self.valid_lbl.pack(side="left", padx=(6, 0))

        self.notes_box = ctk.CTkTextbox(
            card, height=145, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(family="Courier", size=15), wrap="word")
        self.notes_box.insert("0.0",
            "9 8 6 5 6 4 5 6 9 11 12 9 10 11 12 9 / "
            "10 9 8 7 8 7 5 4 2 4 5 7 4 5 7 8")
        self.notes_box.pack(fill="x", padx=18, pady=(4, 0))
        self.notes_box.bind("<KeyRelease>", self._on_text_modified)

        self._undo = _UndoStack(self.notes_box)
        self.notes_box.bind("<KeyRelease>", self._undo.on_key, add="+")
        inner = self.notes_box._textbox
        inner.bind("<Control-z>",       self._undo.undo)
        inner.bind("<Control-Z>",       self._undo.undo)
        inner.bind("<Control-y>",       self._undo.redo)
        inner.bind("<Control-Y>",       self._undo.redo)
        inner.bind("<Control-Shift-Z>", self._undo.redo)

        undo_row = ctk.CTkFrame(card, fg_color="transparent")
        undo_row.pack(fill="x", padx=18, pady=(4, 0))
        for txt, cmd in [("↩ Undo", self._undo.undo), ("↪ Redo", self._undo.redo)]:
            ctk.CTkButton(undo_row, text=txt, command=cmd,
                          width=72, height=26, corner_radius=6,
                          fg_color="transparent", text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0],
                          border_width=1, border_color=self.C["border"],
                          hover_color=self.C["card2"],
                          font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 6))

        pb = ctk.CTkFrame(card, fg_color="transparent")
        pb.pack(fill="x", padx=18, pady=(10, 0))
        self.play_btn = ctk.CTkButton(pb, text="▶  Play", command=self.play_audio,
                                      width=80, height=36, corner_radius=8,
                                      fg_color=self.C["green"], hover_color="#2d8c5f",
                                      text_color="#0d1117",
                                      font=ctk.CTkFont(size=13, weight="bold"))
        self.play_btn.pack(side="left", padx=(0, 6))
        self.stop_btn = ctk.CTkButton(pb, text="⏹  Stop", command=self.stop_audio,
                                      width=70, height=36, corner_radius=8,
                                      fg_color=self.C["accent2"], hover_color="#c0392b",
                                      text_color="#0d1117",
                                      font=ctk.CTkFont(size=13, weight="bold"))
        self.stop_btn.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(pb, text="BPM",
                     font=ctk.CTkFont(family="Courier", size=11),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(side="left", padx=(0, 5))
        self.bpm_entry = ctk.CTkEntry(pb, width=45, height=36, corner_radius=8,
                                      border_width=1, border_color=self.C["border"],
                                      font=ctk.CTkFont(family="Courier", size=13))
        self.bpm_entry.insert(0, "120")
        self.bpm_entry.pack(side="left", padx=(0, 10))

        # --- Entrée Hits/s ---
        ctk.CTkLabel(pb, text="Hits/s",
                     font=ctk.CTkFont(family="Courier", size=11),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(side="left", padx=(0, 5))
        self.trem_speed_entry = ctk.CTkEntry(pb, width=40, height=36, corner_radius=8,
                                      border_width=1, border_color=self.C["border"],
                                      font=ctk.CTkFont(family="Courier", size=13))
        self.trem_speed_entry.insert(0, "10") # Default set to 10
        self.trem_speed_entry.pack(side="left", padx=(0, 10))

        self.metro_canvas = tk.Canvas(pb, width=22, height=22, highlightthickness=0)
        self.metro_canvas.pack(side="left")
        self._update_metro_canvas(False)
        self.sync_lbl = ctk.CTkLabel(card, text="",
                                     font=ctk.CTkFont(family="Courier", size=10),
                                     text_color=self.C["green"])
        self.sync_lbl.pack(anchor="w", padx=18, pady=(4, 8))

    def _build_notation_guide(self, parent):
        card = self._card(parent)
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(12, 0))
        ctk.CTkLabel(hdr, text="NOTATION GUIDE",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(side="left")
        self._guide_visible = False
        self._guide_toggle_btn = ctk.CTkButton(
            hdr, text="Show ▾", command=self._toggle_guide,
            width=70, height=24, corner_radius=6,
            fg_color="transparent", text_color=self.C["accent"],
            border_width=1, border_color=self.C["accent"],
            hover_color=self.C["card2"], font=ctk.CTkFont(size=11))
        self._guide_toggle_btn.pack(side="right")
        self._guide_frame = ctk.CTkFrame(card, fg_color="transparent")
        guide_text = (
            "  9          →  play bar 9  (1 beat)\n"
            "  9#6        →  bar 9, tremolo roll EXACTLY 6 times\n"
            "  -   0   x  →  rest  (1 beat silence)\n"
            "  /          →  bar line  (visual separator only)\n"
            "\n"
            "  Bars :  1 = highest / shortest  ←→  21 = lowest / longest\n"
            "  Left hand is automatically bar + 7  (when Two Mallets ON)\n"
            "\n"
            "  2D Edit mode tips\n"
            "  Click a bar        →  append its number\n"
            "  Hold ≥ threshold   →  tremolo (longer = more repeats)\n"
            "  Right-click        →  insert  /  bar line"
        )
        ctk.CTkLabel(self._guide_frame, text=guide_text,
                     font=ctk.CTkFont(family="Courier", size=11),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0],
                     justify="left", anchor="w").pack(anchor="w", padx=8, pady=(8, 14))

    def _toggle_guide(self):
        self._guide_visible = not self._guide_visible
        if self._guide_visible:
            self._guide_frame.pack(fill="x", padx=4, pady=(4, 0))
            self._guide_toggle_btn.configure(text="Hide ▴")
        else:
            self._guide_frame.pack_forget()
            self._guide_toggle_btn.configure(text="Show ▾")

    def _build_audio_mode_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="AUDIO ENGINE",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(anchor="w", padx=18, pady=(14, 6))
        self._audio_mode_var = ctk.StringVar(value="adsr")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 4))
        self._adsr_radio = ctk.CTkRadioButton(
            row, text="ADSR Synthesis  (always available)",
            variable=self._audio_mode_var, value="adsr",
            command=self._on_audio_mode_change,
            font=ctk.CTkFont(size=12),
            fg_color=self.C["accent"], hover_color=self.C["accent"])
        self._adsr_radio.pack(anchor="w", pady=(0, 6))
        self._smp_radio = ctk.CTkRadioButton(
            row, text="Real Samples  (requires calibration)",
            variable=self._audio_mode_var, value="samples",
            command=self._on_audio_mode_change,
            font=ctk.CTkFont(size=12),
            fg_color=self.C["accent"], hover_color=self.C["accent"])
        self._smp_radio.pack(anchor="w")
        self._audio_mode_lbl = ctk.CTkLabel(card, text="",
                                            font=ctk.CTkFont(family="Courier", size=10),
                                            text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
        self._audio_mode_lbl.pack(anchor="w", padx=18, pady=(4, 14))
        self._refresh_audio_mode_ui()

    def _refresh_audio_mode_ui(self):
        has_smp = samples_available()
        if has_smp:
            self._smp_radio.configure(state="normal")
            self._audio_mode_lbl.configure(
                text="✅  Real samples loaded from calibration",
                text_color=self.C["green"])
        else:
            self._smp_radio.configure(state="disabled")
            if self._audio_mode_var.get() == "samples":
                self._audio_mode_var.set("adsr")
            self._audio_mode_lbl.configure(
                text="⚠  No samples yet — run calibration in Settings",
                text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])

    def _on_audio_mode_change(self):
        mode = self._audio_mode_var.get()
        self.player.mode = mode
        self._jam_player.mode = mode
        if mode == "samples" and not self.player._samples_loaded:
            self.player.load_samples()
        if mode == "samples" and not self._jam_player._samples_loaded:
            self._jam_player.load_samples()

    def _build_presets_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="PRESETS",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(anchor="w", padx=18, pady=(14, 6))
        self.preset_combo = ctk.CTkComboBox(
            card, values=self._get_preset_names(),
            command=self._load_preset,
            height=34, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(size=12))
        self.preset_combo.set("Select a preset...")
        self.preset_combo.pack(fill="x", padx=18, pady=(0, 8))
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkButton(btn_row, text="+ Save", command=self._save_preset,
                      height=32, corner_radius=8, width=100,
                      fg_color=self.C["accent"], text_color="#0d1117",
                      hover_color="#deba7e",
                      font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Delete", command=self._delete_preset,
                      height=32, corner_radius=8, width=76,
                      fg_color="transparent", text_color=self.C["accent2"],
                      border_width=1, border_color=self.C["accent2"],
                      hover_color=self.C["card"],
                      font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="Import", command=self._import_preset,
                      height=32, corner_radius=8, width=76,
                      fg_color="transparent", text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0],
                      border_width=1, border_color=self.C["border"],
                      hover_color=self.C["card"],
                      font=ctk.CTkFont(size=12)).pack(side="left")

    def _build_customize_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="DISPLAY SETTINGS",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(anchor="w", padx=18, pady=(14, 6))
        self._row_label(card, "Measure Style")
        self.measure_combo = ctk.CTkComboBox(
            card, values=["4 beats", "8 beats", "Manual (using '/')"],
            command=self._request_update,
            height=32, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(size=12))
        self.measure_combo.set("Manual (using '/')")
        self.measure_combo.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Grid Columns")
        self.grid_combo = ctk.CTkComboBox(
            card, values=["8 Columns (Large)", "12 Columns",
                          "16 Columns (Medium)", "20 Columns", "24 Columns (Small)"],
            command=self._request_update,
            height=32, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(size=12))
        self.grid_combo.set("16 Columns (Medium)")
        self.grid_combo.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Note Font Size")
        self.font_size_slider = ctk.CTkSlider(
            card, from_=8, to=22, number_of_steps=14,
            command=self._request_update,
            progress_color=self.C["accent"],
            button_color=self.C["accent"], height=18)
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
                      progress_color=self.C["accent"]).pack(anchor="w", padx=18, pady=(0, 6))
        self.show_numbers_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(card, text="Show Bar Numbers",
                      variable=self.show_numbers_var, command=self._request_update,
                      font=ctk.CTkFont(size=12),
                      progress_color=self.C["accent"]).pack(anchor="w", padx=18, pady=(0, 14))

    def _build_export_card(self, parent):
        card = self._card(parent)
        ctk.CTkLabel(card, text="EXPORT",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]).pack(anchor="w", padx=18, pady=(14, 8))
        self.export_pdf_btn = ctk.CTkButton(
            card, text="Export to PDF", command=self.export_pdf,
            height=40, corner_radius=10,
            fg_color=self.C["accent"], text_color="#0d1117",
            hover_color="#deba7e",
            font=ctk.CTkFont(size=13, weight="bold"))
        self.export_pdf_btn.pack(fill="x", padx=18, pady=(0, 8))
        self.export_mp4_btn = ctk.CTkButton(
            card, text="Export 2D Video (MP4)", command=self.export_mp4,
            height=40, corner_radius=10,
            fg_color="transparent", text_color=self.C["accent"],
            border_width=1, border_color=self.C["accent"],
            hover_color=self.C["card"],
            font=ctk.CTkFont(size=13))
        self.export_mp4_btn.pack(fill="x", padx=18, pady=(0, 8))
        self.mp4_prog_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.mp4_progress_lbl = ctk.CTkLabel(
            self.mp4_prog_frame, text="",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
        self.mp4_progress_lbl.pack(anchor="w", padx=2, pady=(2, 4))
        self.mp4_prog_bar = ctk.CTkProgressBar(
            self.mp4_prog_frame, height=7, corner_radius=4,
            progress_color=self.C["accent"])
        self.mp4_prog_bar.set(0)
        self.mp4_prog_bar.pack(fill="x", padx=2, pady=(0, 4))
        ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=4)).pack()

    # =========================================================================
    # RIGHT PANEL
    # =========================================================================

    def _build_right_panel(self):
        right = ctk.CTkFrame(self, fg_color=self.C["bg"], corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 0))
        ctk.CTkLabel(hdr, text="Score Preview",
                     font=ctk.CTkFont(family="Georgia", size=20, weight="bold"),
                     text_color=self.C["accent"]).pack(side="left")

        view_frame = ctk.CTkFrame(hdr, fg_color=self.C["card"], corner_radius=10)
        view_frame.pack(side="right")
        self._view_btns = {}
        for key, label in [("table", "Table"), ("roneat2d", "2D Roneat")]:
            is_active = key == "table"
            btn = ctk.CTkButton(
                view_frame, text=label,
                command=lambda k=key: self._switch_view(k),
                width=100, height=32, corner_radius=8,
                fg_color=self.C["accent"] if is_active else "transparent",
                text_color="#0d1117" if is_active else self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0],
                hover_color=self.C["accent"],
                font=ctk.CTkFont(size=12))
            btn.pack(side="left", padx=2, pady=2)
            self._view_btns[key] = btn

        ctk.CTkFrame(right, height=1, fg_color=self.C["border"]).grid(
            row=1, column=0, sticky="ew", padx=20, pady=(10, 0))

        self._canvas_container = tk.Frame(right, bg="#0d1117")
        self._canvas_container.grid(row=2, column=0, sticky="nsew", padx=8, pady=(4, 8))
        self._canvas_container.grid_rowconfigure(0, weight=1)
        self._canvas_container.grid_columnconfigure(0, weight=1)

        self.vbar = tk.Scrollbar(self._canvas_container, orient="vertical")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.canvas = tk.Canvas(self._canvas_container, highlightthickness=0,
                                yscrollcommand=self.vbar.set, bg="#0d1117")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.config(command=self.canvas.yview)
        self.canvas.bind("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        self._roneat2d_frame = ctk.CTkFrame(right, fg_color=self.C["bg"], corner_radius=0)
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
        top = ctk.CTkFrame(f, fg_color=self.C["card"], corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(top, text="MODE",
                     font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                     text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0]
                     ).grid(row=0, column=0, padx=(16, 8), pady=8)

        mode_frame = ctk.CTkFrame(top, fg_color=self.C["card2"], corner_radius=8)
        mode_frame.grid(row=0, column=1, pady=6)

        self._mode_btns = {}
        for mk, mlabel in [("playback", "⏵  Playback"),
                            ("edit",     "✏  Edit"),
                            ("jam",      "🥁  Jam")]:
            is_a = mk == "playback"
            btn = ctk.CTkButton(
                mode_frame, text=mlabel,
                command=lambda m=mk: self._set_roneat_mode(m),
                width=115, height=30, corner_radius=6,
                fg_color=self.C["accent"] if is_a else "transparent",
                text_color="#0d1117" if is_a else self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0],
                hover_color=self.C["accent"],
                font=ctk.CTkFont(size=12))
            btn.pack(side="left", padx=2, pady=2)
            self._mode_btns[mk] = btn

        self._mode_hint_lbl = ctk.CTkLabel(
            top, text="Bars light up during playback",
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
        self._mode_hint_lbl.grid(row=0, column=2, padx=12, pady=8, sticky="w")

        # ── Row 1 : settings bar (Edit / Jam) — hidden initially ──────────────
        self._2d_settings_frame = ctk.CTkFrame(f, fg_color=self.C["panel"],
                                               corner_radius=0)
        self._2d_settings_frame.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(self._2d_settings_frame, text="Two Mallets",
                     font=ctk.CTkFont(size=11),
                     text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0]
                     ).grid(row=0, column=0, padx=(16, 4), pady=7)
        self._2d_two_mallet_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(self._2d_settings_frame, text="",
                      variable=self._2d_two_mallet_var,
                      width=44, height=22,
                      progress_color=self.C["accent"]
                      ).grid(row=0, column=1, padx=(0, 20), pady=7)

        ctk.CTkFrame(self._2d_settings_frame, width=1, height=28,
                     fg_color=self.C["border"]
                     ).grid(row=0, column=2, padx=(0, 16), pady=7)

        self._trem_lbl = ctk.CTkLabel(self._2d_settings_frame,
                                      text="Tremolo hold time",
                                      font=ctk.CTkFont(size=11),
                                      text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
        self._trem_lbl.grid(row=0, column=3, padx=(0, 6), pady=7)
        self._trem_slider = ctk.CTkSlider(
            self._2d_settings_frame, from_=0.2, to=1.5,
            number_of_steps=13, width=110,
            progress_color=self.C["accent"],
            button_color=self.C["accent"])
        self._trem_slider.set(0.4)
        self._trem_slider.grid(row=0, column=4, padx=(0, 4), pady=7)
        self._trem_val_lbl = ctk.CTkLabel(self._2d_settings_frame, text="0.4s",
                                          font=ctk.CTkFont(family="Courier", size=10),
                                          text_color=self.C["accent"])
        self._trem_val_lbl.grid(row=0, column=5, padx=(0, 16), pady=7, sticky="w")
        self._trem_slider.configure(command=self._on_trem_edit_slider)

        self._2d_feedback_lbl = ctk.CTkLabel(
            self._2d_settings_frame, text="",
            font=ctk.CTkFont(family="Courier", size=11, weight="bold"),
            text_color=self.C["accent"])
        self._2d_feedback_lbl.grid(row=0, column=6, padx=(0, 16), pady=7, sticky="e")

        # ── Row 2 : thin separator ────────────────────────────────────────────
        self._2d_sep = ctk.CTkFrame(f, height=1, fg_color=self.C["border"])
        self._2d_sep.grid(row=2, column=0, sticky="ew")

        # ── Row 3 : interactive canvas ────────────────────────────────────────
        self.roneat_canvas = tk.Canvas(f, highlightthickness=0)
        self.roneat_canvas.grid(row=3, column=0, sticky="nsew")

        self.roneat_canvas.bind("<Configure>",
            lambda e: self._draw_roneat2d(self._playing_bar))
        self.roneat_canvas.bind("<ButtonPress-1>",   self._on_bar_press)
        self.roneat_canvas.bind("<ButtonRelease-1>", self._on_bar_release)
        self.roneat_canvas.bind("<ButtonPress-3>",   self._on_bar_right_click)
        self.roneat_canvas.bind("<Motion>",          self._on_canvas_motion)
        self.roneat_canvas.bind("<Leave>",           self._on_canvas_leave)

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
            btn.configure(fg_color=self.C["accent"] if a else "transparent",
                          text_color="#0d1117" if a else self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0])
        self._mode_hint_lbl.configure(text=hints[mode])

        if mode in ("edit", "jam"):
            self._2d_settings_frame.grid(row=1, column=0, sticky="ew")
            is_edit = mode == "edit"
            self._trem_slider.configure(state="normal" if is_edit else "disabled")
            self._trem_lbl.configure(
                text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0] if is_edit else self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
            self._trem_val_lbl.configure(
                text_color=self.C["accent"] if is_edit else self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])
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
                fg_color=self.C["accent"] if k == key else "transparent",
                text_color="#0d1117" if k == key else self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0])
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
        n_bars    = 21
        margin_x  = 18
        margin_top = 44
        margin_bot = 32
        bar_gap   = 3
        total_w   = W - margin_x * 2
        bar_w     = (total_w - bar_gap * (n_bars - 1)) / n_bars
        avail_h   = H - margin_top - margin_bot - 10
        rail_h    = 8
        min_bar_h = avail_h * 0.22
        max_bar_h = avail_h * 0.78
        rail_y    = margin_top

        bars = []
        for i in range(n_bars):
            bar_num = 21 - i
            t       = i / (n_bars - 1)
            bh      = max_bar_h - t * (max_bar_h - min_bar_h)
            xl      = margin_x + i * (bar_w + bar_gap)
            xr      = xl + bar_w
            yt      = rail_y + rail_h
            yb      = yt + bh
            cx      = (xl + xr) / 2
            bars.append((bar_num, xl, xr, yt, yb, cx))
        return bars, rail_y, rail_h, bar_w

    def _bar_at_xy(self, x, y):
        W = self.roneat_canvas.winfo_width()
        H = self.roneat_canvas.winfo_height()
        if W < 10 or H < 10:
            return None
        bars, _, _, _ = self._bar_geometry(W, H)
        for (bar_num, xl, xr, yt, yb, _cx) in bars:
            if xl <= x <= xr and yt <= y <= yb:
                return bar_num
        return None

    # =========================================================================
    # 2D RONEAT — DRAWING
    # =========================================================================

    def _draw_roneat2d(self, active_bar=None, hover_bar=None,
                       press_bar=None, trem_repeat=0, active_hand="both"):
        c = self.roneat_canvas
        c.update_idletasks()
        W = c.winfo_width()
        H = c.winfo_height()
        if W < 50 or H < 50:
            return
        c.delete("all")

        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_col  = "#0d1117" if is_dark else "#f0f4f8"
        c.configure(bg=bg_col)

        bars, rail_y, rail_h, bar_w = self._bar_geometry(W, H)

        rail_col  = "#5a6a7e" if is_dark else "#8fa0b0"
        bar_face  = "#4a6080" if is_dark else "#b8ccd8"
        bar_strip = "#3a4f68" if is_dark else "#a0b4c8"
        bar_edge  = "#2a3848" if is_dark else "#8090a4"
        tube_in   = "#2a3a50" if is_dark else "#c0ccd8"
        lbl_in    = "#5a7090" if is_dark else "#6080a0"
        hover_col = "#6a8aaa" if is_dark else "#90b0c8"

        mode   = self._roneat_mode
        use_2m = (self._2d_two_mallet_var.get()
                  if mode in ("edit", "jam") else self.left_hand_var.get())

        c.create_rectangle(bars[0][1] - 6, rail_y,
                            bars[-1][2] + 6, rail_y + rail_h,
                            fill=rail_col, outline="")

        for (bar_num, xl, xr, yt, yb, cx) in bars:

            is_rh = active_bar is not None and bar_num == active_bar and active_hand in ("both", "right")
            is_lh = active_bar is not None and use_2m and bar_num == active_bar + 7 and bar_num <= 21 and active_hand in ("both", "left")

            is_press    = press_bar is not None and bar_num == press_bar
            is_press_lh = press_bar is not None and use_2m and bar_num == press_bar + 7 and bar_num <= 21

            is_hov      = hover_bar is not None and bar_num == hover_bar and not (is_rh or is_press)
            is_hov_lh   = hover_bar is not None and use_2m and bar_num == hover_bar + 7 and bar_num <= 21 and not (is_lh or is_press_lh)

            if is_rh or is_press:
                c.create_rectangle(xl - 3, yt - 3, xr + 3, yb + 6,
                                   fill="#ffdf90", outline="")
            elif is_lh or is_press_lh:
                c.create_rectangle(xl - 3, yt - 3, xr + 3, yb + 6,
                                   fill="#80b8f8", outline="")
            elif is_hov:
                c.create_rectangle(xl - 2, yt - 2, xr + 2, yb + 4,
                                   fill="#3a5060", outline="")
            elif is_hov_lh:
                c.create_rectangle(xl - 2, yt - 2, xr + 2, yb + 4,
                                   fill="#1e3a55", outline="")

            if is_rh:
                fc, sc = self.C["accent"], "#a07828"
            elif is_press:
                fc, sc = "#e0c080", "#b09040"
            elif is_lh or is_press_lh:
                fc, sc = self.C["blue"], "#2060a0"
            elif is_hov:
                fc, sc = hover_col, "#4a7090"
            elif is_hov_lh:
                fc, sc = "#3060a0", "#204070"
            else:
                fc, sc = bar_face, bar_strip

            sw = max(2, bar_w * 0.22)
            c.create_rectangle(xl, yt, xr, yb, fill=bar_edge, outline="")
            c.create_rectangle(xl + 1, yt, xr - 1, yb - 1, fill=fc, outline="")
            c.create_rectangle(xl + 1, yt, xl + sw, yb - 1, fill=sc, outline="")

            i_idx   = 21 - bar_num
            tube_r  = max(3, min(bar_w * 0.36, 10))
            tube_cy = yb + tube_r + 5 + (tube_r * 0.5 if i_idx % 2 == 0 else 0)
            cord_c  = "#445566" if is_dark else "#8898a8"
            c.create_line(cx, yb, cx, tube_cy - tube_r, fill=cord_c, width=1)
            tc = (self.C["accent"] if (is_rh or is_press) else self.C["blue"] if (is_lh or is_press_lh) else tube_in)
            c.create_oval(cx - tube_r, tube_cy - tube_r,
                          cx + tube_r, tube_cy + tube_r, fill=tc, outline="")

            lbl_y  = tube_cy + tube_r + 5
            lbl_c  = (self.C["accent"] if (is_rh or is_press) else self.C["blue"] if (is_lh or is_press_lh) else lbl_in)
            lbl_sz = max(6, min(int(bar_w * 0.52), 11))
            c.create_text(cx, lbl_y, text=str(bar_num),
                          font=("Courier", lbl_sz, "bold"), fill=lbl_c)

        if mode == "edit":
            if press_bar and trem_repeat > 0:
                status = f"Bar {press_bar}  →  tremolo ×{trem_repeat}  (release to insert)"
                s_col  = self.C["warn"]
            elif press_bar:
                status = f"Bar {press_bar}  —  hold longer for tremolo…"
                s_col  = self.C["accent"]
            elif hover_bar:
                lh_n   = hover_bar + 7
                status = (f"Bar {hover_bar}  |  Left hand: {lh_n}"
                          if use_2m and lh_n <= 21 else f"Bar {hover_bar}")
                s_col  = self.C["text_dim"][1] if is_dark else self.C["text_dim"][0]
            else:
                status = "Click a bar to write it  |  Right-click to insert  /"
                s_col  = "#4a5568"
        elif mode == "jam":
            if hover_bar:
                lh_n   = hover_bar + 7
                status = (f"Bar {hover_bar}  |  Left hand: {lh_n}"
                          if use_2m and lh_n <= 21 else f"Bar {hover_bar}")
                s_col  = self.C["text_dim"][1] if is_dark else self.C["text_dim"][0]
            else:
                status = "Click any bar to play it instantly"
                s_col  = "#4a5568"
        elif active_bar and 1 <= active_bar <= 21:
            lh_n   = active_bar + 7
            status = (f"Right: {active_bar}   Left: {lh_n}"
                      if use_2m and lh_n <= 21 else f"Bar {active_bar}")
            s_col  = self.C["accent"]
        else:
            status = "No note playing"
            s_col  = "#4a5568" if is_dark else "#8090a0"

        c.create_text(W / 2, rail_y / 2, text=status,
                      font=("Georgia", 12, "bold"), fill=s_col)

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

    def _edit_append_token(self, token):
        try:
            current = self.notes_box.get("0.0", "end-1c").rstrip()
            sep = " " if current else ""
            self.notes_box.insert("end", sep + token)
            self.notes_box.see("end")

            if self._undo:
                self._undo.snapshot()
            self._on_text_modified()
        except Exception as e:
            print(f"[_edit_append_token error] {e}")

    def _play_interactive_note(self, bar):
        now = time.time()
        if now - self._last_play_time < 0.05:
            return
        self._last_play_time = now

        use_2m = self._2d_two_mallet_var.get()

        def _play():
            try:
                import sounddevice as sd
                jp = self._jam_player
                jp.roneat_dict = load_hz_preset()
                tone = jp._build_single_note(bar, 0.8, use_2m)
                sd.play(tone, jp.sample_rate)
            except Exception as e:
                print(f"[Interactive play] {e}")

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
            col = self.C["accent"] if beat_on else ("#30363d" if is_dark else "#cbd5e1")
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
        text   = self.notes_box.get("0.0", "end").strip()
        errors = validate_score(text)
        ok     = len(errors) == 0
        self._draw_valid_dot(ok)
        if ok:
            events = expand_score(text)
            n = sum(1 for e in events if e['bar'] is not None)
            self.valid_lbl.configure(
                text=f"Valid  —  {n} note{'s' if n != 1 else ''}",
                text_color=self.C["green"])
        else:
            msg = errors[0] if len(errors) == 1 else f"{len(errors)} errors  —  {errors[0]}"
            self.valid_lbl.configure(text=msg[:60], text_color=self.C["accent2"])

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _card(self, parent):
        c = ctk.CTkFrame(parent, fg_color=self.C["card"], corner_radius=12,
                         border_width=1, border_color=self.C["border"])
        c.pack(fill="x", padx=20, pady=(0, 14))
        return c

    def _row_label(self, parent, text):
        ctk.CTkLabel(parent, text=text,
                     font=ctk.CTkFont(size=12),
                     text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0]).pack(anchor="w", padx=18)

    def _set_accent(self, hex_col):
        self.C["accent"] = hex_col
        self._request_update()

    def _on_text_modified(self, event=None):
        self._request_update()
        self._run_validation()
        if self.current_sync_data:
            self.current_sync_data = None
            self.bpm_entry.configure(state="normal")
            self.sync_lbl.configure(text="")

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
            "title":      self.title_entry.get(),
            "notes":      self.notes_box.get("0.0", "end").strip(),
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
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, d.get("title", ""))
        self.notes_box.delete("0.0", "end")
        self.notes_box.insert("0.0", d.get("notes", ""))
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

        self.player.roneat_dict = load_hz_preset()
        score       = self.notes_box.get("0.0", "end")
        bpm_raw     = self.bpm_entry.get().strip()
        bpm         = int(bpm_raw) if bpm_raw.isdigit() and 20 <= int(bpm_raw) <= 400 else 120
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
        events = []

        if self.current_sync_data:
            for i, item in enumerate(self.current_sync_data):
                tok = str(item['note'])
                m = _TOK_RE.match(tok)
                if m:
                    bar = int(m.group(1))
                    is_trem = bool(m.group(2))
                    rep = int(m.group(3)) if m.group(3) else 1
                    dur = (min(self.current_sync_data[i+1]['time'] - item['time'], 0.9)
                           if i + 1 < len(self.current_sync_data) else 0.5)
                    events.append({'bar': bar, 'is_trem': is_trem, 'repeat': rep, 'dur': dur})
        else:
            beat = 60.0 / max(bpm, 1)
            for tok in score.replace('\n', ' ').split():
                if tok in ('/', '-', '0', 'x'): continue
                m = _TOK_RE.match(tok)
                if m:
                    bar = int(m.group(1))
                    is_trem = bool(m.group(2))
                    rep = int(m.group(3)) if m.group(3) else 1
                    events.append({'bar': bar, 'is_trem': is_trem, 'repeat': rep, 'dur': beat})

        token_idx = [0]

        def on_bar(bar_num):
            self._playing_bar = bar_num
            if not (self._current_view == "roneat2d" and self._roneat_mode == "playback"):
                return

            if token_idx[0] < len(events):
                ev = events[token_idx[0]]
                token_idx[0] += 1

                if ev['is_trem']:
                    self.after(0, lambda: self._play_tremolo_visual(bar_num, ev['repeat'], hits_per_sec, two_mallets))
                else:
                    self.after(0, lambda: self._draw_roneat2d(bar_num, active_hand="both"))

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
                                            fg_color=self.C["card"],
                                            border_width=2,
                                            border_color=self.C["accent"],
                                            corner_radius=16)

        self.current_overlay.place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(self.current_overlay, text=title_text,
                     font=("Georgia", 20, "bold"),
                     text_color=self.C["accent"]).pack(pady=(28, 18), padx=40)

        # Gold separator
        ctk.CTkFrame(self.current_overlay, height=1,
                     fg_color=self.C["border"]).pack(fill="x", padx=24, pady=(0, 8))

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
                            fg_color=self.C["accent"], hover_color=self.C["accent"],
                            font=("Helvetica", 13)).pack(anchor="w", padx=44, pady=8)

            row_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(parent, text="Show row numbers", variable=row_var,
                            checkbox_height=20, checkbox_width=20,
                            fg_color=self.C["accent"], hover_color=self.C["accent"],
                            font=("Helvetica", 13)).pack(anchor="w", padx=44, pady=8)

            comp_row = ctk.CTkFrame(parent, fg_color="transparent")
            comp_row.pack(anchor="w", padx=44, pady=(10, 0), fill="x")

            ctk.CTkLabel(comp_row, text="Composer:", font=("Helvetica", 13)).pack(side="left")
            comp_entry = ctk.CTkEntry(comp_row, width=200, height=32, corner_radius=6,
                                      border_width=1, border_color=self.C["border"],
                                      font=("Helvetica", 13))
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
                          fg_color=self.C["accent"], text_color="#0d1117", hover_color="#deba7e",
                          font=("Helvetica", 13, "bold")).pack(side="left", padx=10)

            ctk.CTkButton(btn_row, text="Cancel", command=self._close_overlay,
                          width=100, height=36, corner_radius=8,
                          fg_color="transparent", border_width=1, border_color=self.C["border"],
                          text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0], hover_color=self.C["card"],
                          font=("Helvetica", 13)).pack(side="left", padx=4)

        self._show_overlay("PDF Export Options", build_pdf_content)

    def _execute_pdf_export(self, opts):
        mode_map  = {"4 beats": "4", "8 beats": "8", "Manual (using '/')": "manual"}
        mode_val  = mode_map.get(self.measure_combo.get(), "manual")
        grid_val  = self.grid_combo.get().split(" ")[0]
        columns   = int(grid_val) if grid_val.isdigit() else 16
        raw_title = self.title_entry.get().strip()
        safe_name = "".join(ch for ch in raw_title if ch.isalnum() or ch in " _-").strip() or "score"

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
                          self.notes_box.get("0.0", "end"),
                          mode_val, self.left_hand_var.get(), cols=columns,
                          show_cover=opts["cover"], composer=opts["composer"],
                          show_row_numbers=opts["row_numbers"])
            self.export_pdf_btn.configure(text="✓ Exported!", fg_color=self.C["green"])
        except Exception as e:
            self.export_pdf_btn.configure(text="Failed", fg_color=self.C["accent2"])
            print(f"[PDF] {e}")

        self.after(2000, lambda: self.export_pdf_btn.configure(
            text="Export to PDF", fg_color=self.C["accent"], state="normal"))

    # =========================================================================
    # MP4 EXPORT
    # =========================================================================

    def export_mp4(self):
        missing = []
        try:
            import imageio
            try: import imageio_ffmpeg  # noqa
            except ImportError: pass
        except ImportError: missing.append("imageio[ffmpeg]")
        try:
            from PIL import Image  # noqa
        except ImportError: missing.append("Pillow")

        if missing:
            messagebox.showerror(
                "Missing Libraries",
                f"MP4 export requires:\n\n  pip install {' '.join(missing)}\n\n"
                "Please install and restart.")
            return

        def build_video_content(parent):
            show_title_var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(parent, text="Show song title above the instrument",
                            variable=show_title_var,
                            checkbox_height=20, checkbox_width=20,
                            fg_color=self.C["accent"], hover_color=self.C["accent"],
                            font=("Helvetica", 13)).pack(anchor="w", padx=44, pady=8)

            theme_var = ctk.StringVar(value="dark")
            theme_row = ctk.CTkFrame(parent, fg_color="transparent")
            theme_row.pack(anchor="w", padx=44, pady=10)

            ctk.CTkLabel(theme_row, text="Video theme:", font=("Helvetica", 13)).pack(side="left", padx=(0, 14))

            ctk.CTkRadioButton(theme_row, text="Dark", variable=theme_var, value="dark",
                               radiobutton_width=20, radiobutton_height=20,
                               fg_color=self.C["accent"], hover_color=self.C["accent"],
                               font=("Helvetica", 13)).pack(side="left", padx=6)

            ctk.CTkRadioButton(theme_row, text="Light (beige)", variable=theme_var, value="light",
                               radiobutton_width=20, radiobutton_height=20,
                               fg_color=self.C["accent"], hover_color=self.C["accent"],
                               font=("Helvetica", 13)).pack(side="left", padx=6)

            def confirm():
                opts = {
                    "show_title": show_title_var.get(),
                    "dark_mode": theme_var.get() == "dark"
                }
                self._close_overlay()
                self._execute_mp4_export(opts)

            btn_row = ctk.CTkFrame(parent, fg_color="transparent")
            btn_row.pack(pady=(25, 25))

            ctk.CTkButton(btn_row, text="Export", command=confirm,
                          width=100, height=36, corner_radius=8,
                          fg_color=self.C["accent"], text_color="#0d1117", hover_color="#deba7e",
                          font=("Helvetica", 13, "bold")).pack(side="left", padx=10)

            ctk.CTkButton(btn_row, text="Cancel", command=self._close_overlay,
                          width=100, height=36, corner_radius=8,
                          fg_color="transparent", border_width=1, border_color=self.C["border"],
                          text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0], hover_color=self.C["card"],
                          font=("Helvetica", 13)).pack(side="left", padx=4)

        self._show_overlay("Video Export Options", build_video_content)

    def _execute_mp4_export(self, opts):
        raw_title = self.title_entry.get().strip()
        safe_name = "".join(ch for ch in raw_title if ch.isalnum() or ch in " _-").strip() or "roneat_video"

        filepath = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            initialfile=f"{safe_name}.mp4",
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")])

        if not filepath:
            return

        trem_speed_raw = self.trem_speed_entry.get().strip()
        hits_per_sec = float(trem_speed_raw) if trem_speed_raw.replace('.','',1).isdigit() else 10.0
        opts["hits_per_sec"] = max(2.0, min(hits_per_sec, 64.0))
        opts["score"] = self.notes_box.get("0.0", "end")
        opts["bpm_raw"] = self.bpm_entry.get().strip()
        opts["two_mal"] = self.left_hand_var.get()
        opts["accent_col"] = self.C["accent"]
        opts["song_title_raw"] = self.title_entry.get().strip()

        self.export_mp4_btn.configure(text="Rendering...", state="disabled")
        self.mp4_prog_frame.pack(fill="x", padx=18, pady=(0, 14))
        self.mp4_prog_bar.set(0)
        self.mp4_progress_lbl.configure(text="Preparing...", text_color=self.C["text_dim"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text_dim"][0])

        threading.Thread(
            target=self._mp4_worker, args=(filepath, opts), daemon=True).start()

    def _mp4_worker(self, filepath, opts):
        try:
            import imageio
            import numpy as np
            import soundfile as sf

            show_title   = opts.get("show_title", True)
            dark_mode    = opts.get("dark_mode",  True)
            hits_per_sec = opts.get("hits_per_sec", 10.0)
            score        = opts.get("score", "")
            bpm_raw      = opts.get("bpm_raw", "120")
            bpm          = int(bpm_raw) if bpm_raw.isdigit() and 20 <= int(bpm_raw) <= 400 else 120
            two_mal      = opts.get("two_mal", True)
            accent_col   = opts.get("accent_col", "#c8a96e")
            song_title   = opts.get("song_title_raw", "") if show_title else ""

            events_mp4 = expand_score(score)
            beat_sec   = 60.0 / max(bpm, 1)
            notes = []; durations = []; tokens = []

            if self.current_sync_data:
                sd_idx = 0
                for ev in events_mp4:
                    if ev['bar'] is None:
                        continue
                    if sd_idx < len(self.current_sync_data):
                        t_curr = self.current_sync_data[sd_idx]['time']
                        t_next = (self.current_sync_data[sd_idx + 1]['time']
                                  if sd_idx + 1 < len(self.current_sync_data) else t_curr + 0.6)
                        dur = max(0.1, min(t_next - t_curr, 2.0))
                        sd_idx += 1
                    else:
                        dur = beat_sec
                    if ev['is_tremolo']:
                        dur = ev['repeat'] / hits_per_sec
                    notes.append(ev['bar']); durations.append(dur)
                    tokens.append(f"{ev['bar']}#{ev['repeat']}" if ev['is_tremolo'] else str(ev['bar']))
            else:
                for ev in events_mp4:
                    if ev['bar'] is None:
                        continue
                    if ev['is_tremolo']:
                        dur = ev['repeat'] / hits_per_sec
                    else:
                        dur = beat_sec * ev['beats']
                    notes.append(ev['bar']); durations.append(dur)
                    tokens.append(f"{ev['bar']}#{ev['repeat']}" if ev['is_tremolo'] else str(ev['bar']))

            if not notes:
                self.after(0, lambda: self._mp4_done(False, "No notes to render."))
                return

            fps = 30; W, H = 1920, 1080
            total_frames = sum(max(1, int(d * fps)) for d in durations)

            self.after(0, lambda: self.mp4_progress_lbl.configure(text="Synthesising audio..."))
            render_player = RoneatPlayer(load_hz_preset(), mode=self.player.mode)
            if self.player.mode == "samples":
                render_player.load_samples()

            audio_arr  = render_player.render_score_to_array(tokens, durations, two_mallets=two_mal, hits_per_sec=hits_per_sec)
            audio_rate = render_player.sample_rate
            tmp_wav    = filepath + "_tmp_audio.wav"
            sf.write(tmp_wav, audio_arr, audio_rate)

            self.after(0, lambda: self.mp4_progress_lbl.configure(text="Rendering frames..."))
            tmp_video = filepath + "_tmp_video.mp4"
            writer = imageio.get_writer(
                tmp_video, fps=fps, codec="libx264", macro_block_size=1,
                output_params=["-crf", "18", "-preset", "fast"])

            frame_idx = 0
            for ni, (bar, dur) in enumerate(zip(notes, durations)):
                n_frames = max(1, int(dur * fps))
                for fr in range(n_frames):
                    frame = self._render_frame_hd(
                        abs(int(bar)), W, H, fr, n_frames,
                        dark_mode=dark_mode, song_title=song_title,
                        two_mallets=two_mal, accent_hex=accent_col)
                    writer.append_data(frame)
                    frame_idx += 1
                    if frame_idx % 15 == 0 or frame_idx == total_frames:
                        pct = frame_idx / max(total_frames, 1)
                        _ni, _tot = ni + 1, len(notes)
                        _fi, _ft  = frame_idx, total_frames
                        self.after(0, lambda p=pct, a=_ni, b=_tot, fi=_fi, ft=_ft: (
                            self.mp4_prog_bar.set(p),
                            self.mp4_progress_lbl.configure(
                                text=f"Frame {fi}/{ft}  —  note {a}/{b}")))
            writer.close()

            self.after(0, lambda: self.mp4_progress_lbl.configure(text="Muxing audio + video..."))
            import subprocess
            import shutil as _sh

            def _find_ffmpeg():
                import sys
                if getattr(sys, 'frozen', False):
                    exe_dir = os.path.dirname(sys.executable)
                    for name in ("ffmpeg.exe", "ffmpeg"):
                        c = os.path.join(exe_dir, name)
                        if os.path.exists(c):
                            return c
                dev = os.path.normpath(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "ffmpeg.exe"))
                if os.path.exists(dev):
                    return dev
                found = _sh.which("ffmpeg")
                return found if found else "ffmpeg"

            ffmpeg_bin = _find_ffmpeg()
            cmd = [ffmpeg_bin, "-y",
                   "-i", tmp_video, "-i", tmp_wav,
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                   "-shortest", filepath]
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000
            res = subprocess.run(cmd, capture_output=True, **kwargs)

            for tmp in (tmp_video, tmp_wav):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

            if res.returncode != 0:
                err = res.stderr.decode(errors="ignore")[-400:]
                print(f"[ffmpeg] {err}")
                if os.path.exists(tmp_video):
                    _sh.move(tmp_video, filepath)
                self.after(0, lambda: self._mp4_done(
                    True, "Video exported (no audio — ffmpeg not in PATH)."))
            else:
                self.after(0, lambda: self._mp4_done(True, "Video exported successfully!"))

        except Exception as e:
            import traceback; traceback.print_exc()
            self.after(0, lambda err=str(e): self._mp4_done(False, f"Error: {err}"))

    def _render_frame_hd(self, active_bar, W, H, frame_idx, total_frames,
                         dark_mode=True, song_title="",
                         two_mallets=True, accent_hex="#c8a96e"):
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont

        if dark_mode:
            bg_rgb       = (13, 17, 23);  rail_rgb   = (60, 80, 100)
            bar_face_rgb = (55, 75, 100); bar_strip  = (38, 55, 78)
            tube_rgb     = (32, 48, 68);  lbl_rgb    = (70, 100, 130)
            lh_face_rgb  = (40, 100, 170); lh_tube   = (30, 80, 140)
            status_rgb   = (180, 150, 80); title_rgb = (200, 169, 110)
        else:
            bg_rgb       = (245, 238, 218); rail_rgb  = (140, 120, 88)
            bar_face_rgb = (195, 175, 135); bar_strip = (160, 140, 100)
            tube_rgb     = (215, 200, 165); lbl_rgb   = (90, 70, 40)
            lh_face_rgb  = (50, 100, 180);  lh_tube  = (70, 130, 200)
            status_rgb   = (110, 80, 25);   title_rgb = (90, 60, 15)

        def hex_rgb(h):
            h = h.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        accent_rgb = hex_rgb(accent_hex)
        img  = Image.new("RGB", (W, H), bg_rgb)
        draw = ImageDraw.Draw(img)

        def gfont(size, bold=False):
            names = (["C:/Windows/Fonts/LeelawUI.ttf",
                      "C:/Windows/Fonts/KhmerUI.ttf",
                      "C:/Windows/Fonts/DaunPenh.ttf",
                      "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
                     if bold else
                     ["C:/Windows/Fonts/LeelawUI.ttf",
                      "C:/Windows/Fonts/KhmerUI.ttf",
                      "C:/Windows/Fonts/DaunPenh.ttf",
                      "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])
            for n in names:
                try:
                    return ImageFont.truetype(n, size)
                except Exception:
                    pass
            return ImageFont.load_default()

        title_h = 0
        if song_title:
            title_h = 100
            tf = gfont(125, True)
            bb = draw.textbbox((0, 0), song_title, font=tf)
            draw.text(((W - (bb[2] - bb[0])) // 2, 30), song_title,
                      fill=title_rgb, font=tf)

        n_bars = 21; pad_x = 130; gap = 8
        bar_w  = (W - pad_x * 2 - gap * (n_bars - 1)) / n_bars
        rail_t = title_h + 140; rail_h2 = 20
        avail  = H - rail_t - rail_h2 - 130
        min_bh = int(avail * 0.22); max_bh = int(avail * 0.82)

        draw.rectangle([pad_x - 14, rail_t, W - pad_x + 14, rail_t + rail_h2], fill=rail_rgb)

        for i in range(n_bars):
            bar_num = 21 - i
            t       = i / (n_bars - 1)
            bh      = int(max_bh - t * (max_bh - min_bh))
            x0      = int(pad_x + i * (bar_w + gap))
            x1      = int(x0 + bar_w)
            y0      = rail_t + rail_h2; y1 = y0 + bh
            cx      = (x0 + x1) // 2

            is_rh = active_bar is not None and bar_num == active_bar
            is_lh = (two_mallets and active_bar is not None
                     and bar_num == active_bar + 7 and bar_num <= 21)

            if is_rh:
                glow = tuple(min(255, c + 90) for c in accent_rgb)
                draw.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 10], fill=glow)
            elif is_lh:
                draw.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 10], fill=(110, 185, 240))

            face  = accent_rgb if is_rh else (lh_face_rgb if is_lh else bar_face_rgb)
            strip = (tuple(max(0, c - 55) for c in accent_rgb) if is_rh
                     else (lh_tube if is_lh else bar_strip))
            draw.rectangle([x0, y0, x1, y1], fill=face)
            sp = max(3, int(bar_w * 0.20))
            draw.rectangle([x0, y0, x0 + sp, y1], fill=strip)

            if is_rh and total_frames > 0:
                pulse  = 0.4 + 0.6 * math.sin(frame_idx / total_frames * math.pi)
                bright = tuple(min(255, int(c + pulse * 70)) for c in face)
                draw.rectangle([x0 + sp, y0, x1, y0 + int(bh * 0.25)], fill=bright)

            tr  = max(10, int(bar_w * 0.33))
            tcy = y1 + tr + 12 + (tr // 2 if i % 2 == 0 else 0)
            cord = (70, 95, 115) if dark_mode else (120, 100, 70)
            draw.line([(cx, y1), (cx, tcy - tr)], fill=cord, width=2)
            tf2 = (accent_rgb if is_rh else lh_face_rgb if is_lh else tube_rgb)
            draw.ellipse([cx - tr, tcy - tr, cx + tr, tcy + tr], fill=tf2)

            lbl_y  = tcy + tr + 10
            lbl_sz = max(12, min(int(bar_w * 0.45), 24))
            lc     = (accent_rgb if is_rh else lh_face_rgb if is_lh else lbl_rgb)
            lf     = gfont(lbl_sz, True)
            bb2    = draw.textbbox((0, 0), str(bar_num), font=lf)
            draw.text((cx - (bb2[2] - bb2[0]) // 2, lbl_y), str(bar_num),
                      fill=lc, font=lf)

        if active_bar and 1 <= active_bar <= 21:
            lh_n = active_bar + 7
            status = (f"Right hand: {active_bar}     Left hand: {lh_n}"
                      if two_mallets and lh_n <= 21 else f"Bar {active_bar}")
            sf2 = gfont(58, True)
            bb3 = draw.textbbox((0, 0), status, font=sf2)
            draw.text(((W - (bb3[2] - bb3[0])) // 2, H - 90), status,
                      fill=status_rgb, font=sf2)

        return np.array(img)

    def _mp4_done(self, success, msg):
        self.mp4_prog_bar.set(1.0 if success else 0.0)
        self.mp4_progress_lbl.configure(
            text=msg,
            text_color=self.C["green"] if success else self.C["accent2"])
        txt = "✓ Video exported!" if success else "Export failed"
        col = self.C["green"]     if success else self.C["accent2"]
        self.export_mp4_btn.configure(
            text=txt,
            fg_color=col if success else "transparent",
            text_color="#0d1117" if success else col,
            state="normal")
        self.after(3500, lambda: (
            self.export_mp4_btn.configure(
                text="Export 2D Video (MP4)", fg_color="transparent",
                text_color=self.C["accent"], state="normal"),
            self.mp4_prog_frame.pack_forget(),
            self.mp4_prog_bar.set(0)))

    # =========================================================================
    # CANVAS PREVIEW (TABLE VIEW)
    # =========================================================================

    def update_preview(self):
        if self._current_view == "roneat2d":
            self._draw_roneat2d(self._playing_bar)
            return
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
        bg_col    = "#0d1117" if is_dark else "#f1f5f9"
        pg_col    = "#161b22" if is_dark else "#ffffff"
        pg_bdr    = "#30363d" if is_dark else "#cbd5e1"
        cell_bg   = "#1c2128" if is_dark else "#f8fafc"
        cell_bd   = "#30363d" if is_dark else "#94a3b8"
        bar_col   = "#30363d" if is_dark else "#0f172a"
        note_col  = self.C["accent"]
        lh_col    = self.C["blue"]
        rest_col  = "#8b949e"
        title_col = self.C["accent"]
        sub_col   = "#8b949e" if is_dark else "#64748b"
        trem_col  = "#f59e0b"

        self.canvas.configure(bg=bg_col)

        import re
        text      = self.notes_box.get("0.0", "end-1c")
        _TOK_RE   = re.compile(r'^(\d+)(#(\d+))?$')
        raw_tokens = text.replace('\n', ' ').split()
        beats = []
        for tok in raw_tokens:
            if tok == '/':
                if beats:
                    beats[-1]['barline'] = True
                continue
            if tok in ('-', '0', 'x'):
                beats.append({'bar': None, 'text': '-', 'barline': False,
                              'is_trem': False, 'repeat': 1})
                continue
            m = _TOK_RE.match(tok)
            if m:
                bar  = int(m.group(1))
                is_t = bool(m.group(2))
                rep  = int(m.group(3)) if m.group(3) else 1
                beats.append({'bar': bar, 'text': f"{bar}~{rep}" if is_t else str(bar),
                              'barline': False, 'is_trem': is_t, 'repeat': rep})

        grid_val   = self.grid_combo.get().split(" ")[0]
        cols       = int(grid_val) if grid_val.isdigit() else 16
        font_size  = int(self.font_size_slider.get())
        cell_w     = (page_w - 100) / cols
        cell_h     = min(62, max(30, cell_w * 1.2))
        row_gap    = 26
        rows_pp    = max(1, math.floor((page_h - 180) / (cell_h + row_gap)))
        total_rows = math.ceil(len(beats) / cols) if beats else 1
        num_pages  = math.ceil(total_rows / rows_pp) if total_rows > 0 else 1
        total_h    = num_pages * (page_h + page_gap) + page_gap
        self.canvas.configure(scrollregion=(0, 0, c_width, total_h))

        show_left = self.left_hand_var.get()
        show_nums = self.show_numbers_var.get()
        idx = 0

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
                self.canvas.create_text(x_off + page_w / 2, ys + 104,
                    text="Roneat Ek Score",
                    font=("Georgia", 10), fill=sub_col)
                grid_y = ys + 148
            else:
                grid_y = ys + 56

            row_i = 0
            while idx < len(beats) and row_i < rows_pp:
                cy_top = grid_y + row_i * (cell_h + row_gap)
                x      = x_off + 50
                for col_i in range(cols):
                    if idx >= len(beats):
                        self.canvas.create_rectangle(x, cy_top, x + cell_w, cy_top + cell_h,
                                                     outline=cell_bd, fill=cell_bg)
                        x += cell_w; continue
                    self.canvas.create_rectangle(x, cy_top, x + cell_w, cy_top + cell_h,
                                                 outline=cell_bd, fill=cell_bg)
                    cx_ = x + cell_w / 2
                    cy_ = cy_top + cell_h / 2
                    bd  = beats[idx]
                    if show_nums and bd['bar'] is not None:
                        bar  = bd['bar']
                        is_t = bd['is_trem']
                        rep  = bd['repeat']
                        fs   = min(font_size, max(9, int(cell_w * 0.42)))
                        if is_t:
                            lbl = f"{bar}~{rep}"
                            if show_left:
                                self.canvas.create_text(cx_, cy_ - fs * 0.45, text=lbl,
                                    font=("Courier", int(fs * 0.82), "bold"), fill=trem_col)
                                lh = bar + 7
                                if lh <= 21:
                                    self.canvas.create_text(cx_, cy_ + fs * 0.65,
                                        text=f"{lh}~{rep}",
                                        font=("Courier", int(fs * 0.55), "bold"), fill=lh_col)
                            else:
                                self.canvas.create_text(cx_, cy_, text=lbl,
                                    font=("Courier", fs, "bold"), fill=trem_col)
                        else:
                            if show_left:
                                self.canvas.create_text(cx_, cy_ - fs * 0.45, text=str(bar),
                                    font=("Courier", int(fs * 0.9), "bold"), fill=note_col)
                                lh = bar + 7
                                if lh <= 21:
                                    self.canvas.create_text(cx_, cy_ + fs * 0.65, text=str(lh),
                                        font=("Courier", int(fs * 0.6), "bold"), fill=lh_col)
                            else:
                                self.canvas.create_text(cx_, cy_, text=str(bar),
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
                    idx += 1
                    x   += cell_w
                row_i += 1

            self.canvas.create_text(x_off + page_w / 2, ys + page_h - 18,
                text=f"- {pn + 1} / {num_pages} -",
                font=("Georgia", 9), fill=sub_col)