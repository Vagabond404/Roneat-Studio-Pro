"""
ui/views/settings_page.py  v4.0
=================================
Roneat Studio Pro — Settings Page

Premium DAW Edition:
  - Unified aesthetic with Score Editor and Audio AI
  - Improved layout for Calibration instructions
  - Sleeker Hz tuning grid
  - Polished color palette and typography
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import threading

from core.file_manager import (
    load_hz_preset, save_hz_preset,
    PRESETS_DIR, load_app_settings, save_app_settings
)
from core.calibration import (
    calibrate_from_audio, save_fingerprints, load_fingerprints
)


class SettingsPage(ctk.CTkFrame):
    def _clr(self, color):
        if isinstance(color, (list, tuple)):
            return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.C = {
            "bg":       ("#F2F2F2", "#0F1115"),
            "panel":    ("#E8E8E8", "#16191E"),
            "card":     ("#FFFFFF", "#1E2229"),
            "card2":    ("#F8F8F8", "#252A33"),
            "border":   ("#CCCCCC", "#303642"),
            "accent":   "#D4AF37",
            "accent2":  "#e85d4a",
            "blue":     "#3d8ec9",
            "green":    "#3ab87a",
            "text":     ("#1A1A1A", "#E0E6ED"),
            "text_dim": ("#666666", "#7A8496"),
            "warn":     "#f59e0b",
        }

        self._single_full_path = None
        self._two_full_path    = None
        self._single_path_var  = tk.StringVar(value="No file selected")
        self._two_path_var     = tk.StringVar(value="No file selected")

        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color = self.C["bg"],
            scrollbar_button_color = self.C["accent"],
            scrollbar_button_hover_color = "#E6C45C"
        )
        self.scroll.pack(fill="both", expand=True)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=52, pady=(44, 0))
        
        ctk.CTkLabel(
            hdr, text="⚙  System Preferences",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color = self.C["accent"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            hdr, text="Configure appearance, audio engine, and hardware calibration.",
            font=ctk.CTkFont(family="Segoe UI", size=14), text_color = self.C["text_dim"]
        ).pack(anchor="w", pady=(6, 0))

        ctk.CTkFrame(self.scroll, height=2, fg_color = self.C["border"]).pack(
            fill="x", padx=40, pady=(20, 24)
        )

        # ── Sections ──────────────────────────────────────────────────────────
        self._build_appearance(self.scroll)
        self._build_audio_engine(self.scroll)
        self._build_calibration(self.scroll)
        self._build_tuning(self.scroll)

        self.status_lbl = ctk.CTkLabel(
            self.scroll, text="",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color = self.C["green"]
        )
        self.status_lbl.pack(pady=(0, 48))

        self._reset_default()

    def _section_card(self, parent, title):
        card = ctk.CTkFrame(
            parent, fg_color = self.C["card"],
            corner_radius=18, border_width=1,
            border_color = self.C["border"]
        )
        card.pack(fill="x", padx=40, pady=(0, 24))
        
        h = ctk.CTkFrame(card, fg_color="transparent")
        h.pack(fill="x", padx=24, pady=(20, 12))
        
        ctk.CTkLabel(
            h, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color = self.C["accent"]
        ).pack(anchor="w")
        
        ctk.CTkFrame(card, height=1, fg_color = self.C["border"]).pack(
            fill="x", padx=20, pady=(0, 16)
        )
        return card

    # ─────────────────────────────────────────────────────────────────────────

    def _build_appearance(self, parent):
        card = self._section_card(parent, "🎨  Interface")
        row  = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(0, 20))
        
        ctk.CTkLabel(
            row, text="Theme Mode",
            font=ctk.CTkFont(size=14), text_color = self.C["text"]
        ).pack(side="left")
        
        self.theme_combo = ctk.CTkComboBox(
            row, values=["System", "Light", "Dark"],
            command=self._change_theme,
            width=160, height=38, corner_radius=10,
            border_width=1, border_color = self.C["border"],
            font=ctk.CTkFont(size=13),
            dropdown_hover_color = self.C["accent"]
        )
        self.theme_combo.set(load_app_settings().get("theme", "Dark"))
        self.theme_combo.pack(side="right")

    def _build_audio_engine(self, parent):
        card = self._section_card(parent, "🔊  Audio Engine")
        from core.audio_player import samples_available
        
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(0, 20))
        
        self._audio_mode_var = ctk.StringVar(value=load_app_settings().get("audio_mode", "adsr"))
        
        ctk.CTkRadioButton(
            row, text="Synthesis (High Perf)", variable=self._audio_mode_var, value="adsr",
            command=self._on_audio_mode_change, fg_color = self.C["accent"],
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(0, 30))
        
        self._smp_radio = ctk.CTkRadioButton(
            row, text="Real Samples (High Quality)", variable=self._audio_mode_var, value="samples",
            command=self._on_audio_mode_change, fg_color = self.C["accent"],
            font=ctk.CTkFont(size=13)
        )
        self._smp_radio.pack(side="left")
        
        if not samples_available():
            self._smp_radio.configure(state="disabled")
            if self._audio_mode_var.get() == "samples":
                self._audio_mode_var.set("adsr")

    def _on_audio_mode_change(self):
        mode = self._audio_mode_var.get()
        s = load_app_settings()
        s["audio_mode"] = mode
        save_app_settings(s)
        
        app = self.winfo_toplevel()
        if hasattr(app, "frames") and "editor" in app.frames:
            editor = app.frames["editor"]
            editor.player.mode = mode
            editor._jam_player.mode = mode
            editor.player.load_samples()
            editor._jam_player.load_samples()
                
        self.status_lbl.configure(text=f"Engine switched to {mode}", text_color = self.C["green"])

    def _build_calibration(self, parent):
        card = self._section_card(parent, "🎯  Instrument Fingerprinting")

        # Status banner
        self.cal_banner = ctk.CTkFrame(card, fg_color = self.C["card2"], corner_radius=12)
        self.cal_banner.pack(fill="x", padx=24, pady=(0, 20))
        self._refresh_banner()

        # Instructions - Collapsible-like feel
        instr = ctk.CTkFrame(card, fg_color = self.C["card2"], corner_radius=12, border_width=1, border_color=self.C["border"])
        instr.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkLabel(
            instr, text="Expert Calibration Guide",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color = self.C["accent"]
        ).pack(anchor="w", padx=20, pady=(16, 12))

        text = (
            "Create a recording striking every bar of YOUR Roneat Ek from 1 to 21.\n"
            "This allows the AI to learn the unique harmonic soul of your instrument.\n\n"
            "• Use a quiet room (no fan/AC noise)\n"
            "• Single Mallet: Hit bars 1 → 21 in order (right hand)\n"
            "• Two Mallets: Hit bars 1 → 13 in order (both hands simultaneously)\n"
            "• Leave 2 seconds of silence between each hit\n"
            "• Export as high-quality WAV or MP3"
        )
        ctk.CTkLabel(
            instr, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color = self.C["text_dim"],
            justify="left", wraplength=720, anchor="w"
        ).pack(anchor="w", padx=20, pady=(0, 20))

        # File rows
        self._file_row(card, "Single Mallet  (Bars 1 – 21)", self._single_path_var, self.C["blue"], "single")
        self._file_row(card, "Two Mallets    (Bars 1 – 13)", self._two_path_var, self.C["accent"], "two")

        # Action Button
        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=24, pady=(12, 12))

        self.cal_btn = ctk.CTkButton(
            bottom, text="⚡  START CALIBRATION",
            command=self._run_calibration,
            height=48, corner_radius=12,
            fg_color = self.C["green"], hover_color="#2d8c5f",
            text_color="#090a0f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            width=240
        )
        self.cal_btn.pack(side="left")

        self.cal_msg = ctk.CTkLabel(
            bottom, text="Import audio to begin analysis.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color = self.C["text_dim"]
        )
        self.cal_msg.pack(side="left", padx=(20, 0))

        self.cal_bar = ctk.CTkProgressBar(card, height=10, corner_radius=5, progress_color = self.C["green"])
        self.cal_bar.set(0)

    def _file_row(self, parent, label, path_var, btn_color, tag):
        row = ctk.CTkFrame(parent, fg_color = self.C["card2"], corner_radius=12)
        row.pack(fill="x", padx=24, pady=(0, 10))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(
            info, text=label,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color = self.C["text"]
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            info, textvariable=path_var,
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color = self.C["accent"]
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            row, text="Select File",
            command=lambda t=tag: self._browse(t),
            width=110, height=36, corner_radius=10,
            fg_color=btn_color,
            hover_color=("#2d6a9f" if btn_color == self.C["blue"] else "#E6C45C"),
            text_color="#0D1117",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="right", padx=16, pady=12)

    def _build_tuning(self, parent):
        card = self._section_card(parent, "🎹  Hz Tuning Matrix")

        ctk.CTkLabel(
            card, text="Note: Bar 1 is the highest pitch (~1308 Hz), Bar 21 is the lowest (~177 Hz).",
            font=ctk.CTkFont(size=11), text_color = self.C["text_dim"]
        ).pack(anchor="w", padx=24, pady=(0, 16))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=(0, 10))

        self.hz_entries = {}
        for i in range(1, 22):
            col = (i - 1) % 7
            row = (i - 1) // 7
            grid.grid_columnconfigure(col, weight=1)

            cell = ctk.CTkFrame(grid, fg_color = self.C["card2"], corner_radius=10, border_width=1, border_color = self.C["border"])
            cell.grid(row=row, column=col, padx=5, pady=5, sticky="ew")

            badge = ctk.CTkFrame(cell, fg_color = self.C["accent"], width=28, height=28, corner_radius=7)
            badge.pack(side="left", padx=(8, 6), pady=8)
            badge.pack_propagate(False)
            ctk.CTkLabel(badge, text=str(i), font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), text_color="#0D1117").pack(expand=True)

            entry = ctk.CTkEntry(
                cell, width=80, height=30, corner_radius=6, border_width=0,
                fg_color="transparent", font=ctk.CTkFont(family="Consolas", size=13)
            )
            entry.pack(side="left", pady=8, padx=(0, 8))
            self.hz_entries[i] = entry

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=(16, 24))

        ctk.CTkButton(
            btns, text="RESET ALL",
            command=self._reset_default,
            fg_color="transparent", text_color = self.C["accent"],
            border_width=1, border_color = self.C["accent"],
            hover_color = self.C["card2"],
            height=40, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"), width=160
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btns, text="SAVE TUNING",
            command=self._apply_tuning,
            fg_color = self.C["green"], hover_color="#2d8c5f",
            text_color="#0d1117",
            height=40, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"), width=160
        ).pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────

    def _refresh_banner(self):
        for w in self.cal_banner.winfo_children(): w.destroy()
        single_fps, two_fps = load_fingerprints()
        has_s = single_fps and len(single_fps) > 0
        has_t = two_fps and len(two_fps) > 0
        
        if has_s or has_t:
            msg = "⚡  Calibration Matrix Loaded"
            color = self._clr(self.C["green"])
            icon = "✅"
        else:
            msg = "Calibration missing. Audio engine using FFT synthesis."
            color = self._clr(self.C["warn"])
            icon = "⚠️"
            
        ctk.CTkLabel(
            self.cal_banner, text=f"{icon}  {msg}",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=color
        ).pack(anchor="w", padx=20, pady=14)

    def _browse(self, tag):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select Source Audio",
            filetypes=[("Audio Files", "*.wav *.mp3")]
        )
        if path:
            name = os.path.basename(path)
            if tag == "single":
                self._single_full_path = path
                self._single_path_var.set(f"Selected: {name}")
            else:
                self._two_full_path = path
                self._two_path_var.set(f"Selected: {name}")
            self.cal_msg.configure(text="Source ready. Execute calibration.", text_color = self.C["accent"])

    def _run_calibration(self):
        if not self._single_full_path and not self._two_full_path:
            self.cal_msg.configure(text="Error: No audio source found.", text_color=self.C["accent2"])
            return
        self.cal_btn.configure(state="disabled", text="ANALYZING...")
        self.cal_bar.pack(fill="x", padx=24, pady=(0, 20))
        self.cal_bar.set(0)
        threading.Thread(target=self._cal_worker, daemon=True).start()

    def _cal_worker(self):
        s_fps = None; t_fps = None
        def prog(pct, msg):
            self.after(0, lambda p=pct, m=msg: (
                self.cal_bar.set(p / 100.0),
                self.cal_msg.configure(text=m, text_color = self.C["text_dim"])
            ))
        try:
            if self._single_full_path:
                s_fps = calibrate_from_audio(self._single_full_path, 21, progress_callback=lambda p, m: prog(int(p * 0.5), m))
            if self._two_full_path:
                t_fps = calibrate_from_audio(self._two_full_path, 13, progress_callback=lambda p, m: prog(50 + int(p * 0.5), m))
            if s_fps or t_fps:
                save_fingerprints(s_fps, t_fps)
                self.after(0, self._cal_success)
            else:
                self.after(0, lambda: self._cal_fail("Spectral density too low."))
        except Exception as e:
            self.after(0, lambda err=str(e): self._cal_fail(err))

    def _cal_success(self):
        self.cal_bar.set(1.0)
        self.cal_btn.configure(state="normal", text="⚡  START CALIBRATION")
        self.cal_msg.configure(text="Success: Calibration saved.", text_color = self.C["green"])
        self._refresh_banner()
        self.after(4000, lambda: self.cal_bar.pack_forget())

    def _cal_fail(self, msg):
        self.cal_btn.configure(state="normal", text="⚡  START CALIBRATION")
        self.cal_msg.configure(text=f"Fail: {msg}", text_color=self.C["accent2"])
        self.after(4000, lambda: self.cal_bar.pack_forget())

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        s = load_app_settings(); s["theme"] = choice; save_app_settings(s)
        self.status_lbl.configure(text=f"System appearance preset: {choice}", text_color=self.C["green"])
        app = self.winfo_toplevel()
        if hasattr(app, "frames"):
            for frame in app.frames.values():
                if hasattr(frame, "update_preview"): frame.update_preview()
                if hasattr(frame, "_draw_roneat2d"): frame._draw_roneat2d()

    def _reset_default(self):
        data = load_hz_preset(os.path.join(PRESETS_DIR, 'default_hz.json'))
        if data:
            for k, v in data.items():
                idx = int(k)
                if idx in self.hz_entries:
                    self.hz_entries[idx].delete(0, "end")
                    self.hz_entries[idx].insert(0, str(int(v)))

    def _apply_tuning(self):
        valid = True
        for entry in self.hz_entries.values():
            val = entry.get()
            if not val.isdigit() or not (100 <= int(val) <= 2000):
                valid = False; entry.configure(border_color=self.C["accent2"], border_width=1)
            else:
                entry.configure(border_color = self.C["border"], border_width=0)
        if valid:
            data = {str(k): int(v.get()) for k, v in self.hz_entries.items()}
            save_hz_preset(os.path.join(PRESETS_DIR, 'default_hz.json'), data)
            self.status_lbl.configure(text="Hz Matrix updated successfully.", text_color = self.C["green"])
        else:
            self.status_lbl.configure(text="Check invalid frequency (100–2000).", text_color=self.C["accent2"])