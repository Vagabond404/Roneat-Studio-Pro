"""
ui/views/settings_page.py
=========================
Roneat Studio Pro — Settings Page
Includes: Theme, Hz Tuning, and Fingerprint Calibration
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
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        self.C = {
            "bg":       ("gray96", "#090a0f"),
            "card":     ("white",  "#161a22"),
            "card2":    ("gray97", "#1c212b"),
            "border":   ("gray80", "#242933"),
            "accent":   "#D4AF37",
            "accent2":  "#e85d4a",
            "blue":     "#3d8ec9",
            "green":    "#3ab87a",
            "text":     ("gray10", "gray95"),
            "text_dim": ("gray45", "#8b949e"),
            "warn":     "#f59e0b",
        }

        self._single_full_path = None
        self._two_full_path    = None
        self._single_path_var  = tk.StringVar(value="No file selected")
        self._two_path_var     = tk.StringVar(value="No file selected")

        scroll = ctk.CTkScrollableFrame(
            self, fg_color=self.C["bg"],
            scrollbar_button_color=self.C["accent"]
        )
        scroll.pack(fill="both", expand=True)

        # Header
        hdr = ctk.CTkFrame(scroll, fg_color="transparent")
        hdr.pack(fill="x", padx=36, pady=(36, 0))
        ctk.CTkLabel(
            hdr, text="⚙  Settings",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.C["accent"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            hdr, text="Appearance, tuning presets, and instrument calibration",
            font=ctk.CTkFont(family="Segoe UI", size=13), text_color=self.C["text_dim"]
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkFrame(scroll, height=1, fg_color=self.C["border"]).pack(
            fill="x", padx=28, pady=(16, 24)
        )

        self._build_appearance(scroll)
        self._build_calibration(scroll)
        self._build_tuning(scroll)

        self.status_lbl = ctk.CTkLabel(
            scroll, text="",
            font=ctk.CTkFont(family="Courier", size=12),
            text_color=self.C["green"]
        )
        self.status_lbl.pack(pady=(0, 36))

        self._reset_default()

    # ─────────────────────────────────────────────────────────────────────────

    def _build_appearance(self, parent):
        card = self._section_card(parent, "🎨  Appearance")
        row  = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=22, pady=(0, 18))
        ctk.CTkLabel(
            row, text="Theme Mode",
            font=ctk.CTkFont(size=13), text_color=self.C["text"]
        ).pack(side="left")
        self.theme_combo = ctk.CTkComboBox(
            row, values=["System", "Light", "Dark"],
            command=self._change_theme,
            width=150, height=36, corner_radius=8,
            border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(size=13)
        )
        self.theme_combo.set(load_app_settings().get("theme", "Dark"))
        self.theme_combo.pack(side="right")

    # ─────────────────────────────────────────────────────────────────────────

    def _build_calibration(self, parent):
        card = self._section_card(parent, "🎯  Instrument Calibration  —  Audio AI Fingerprinting")

        # Status banner
        self.cal_banner = ctk.CTkFrame(
            card, fg_color=self.C["card2"], corner_radius=10
        )
        self.cal_banner.pack(fill="x", padx=22, pady=(0, 16))
        self._refresh_banner()

        # Instructions
        instr = ctk.CTkFrame(card, fg_color=self.C["card2"], corner_radius=10)
        instr.pack(fill="x", padx=22, pady=(0, 16))

        ctk.CTkLabel(
            instr, text="📋  Recording instructions",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.C["accent"]
        ).pack(anchor="w", padx=16, pady=(12, 6))

        text = (
            "WHAT IS CALIBRATION?\n"
            "You record every bar of your specific Roneat instrument once.\n"
            "The app learns the exact acoustic fingerprint of YOUR instrument,\n"
            "including its resonance box — turning a flaw into a feature.\n\n"
            "HOW TO RECORD:\n"
            "  1.  Use a DAW (Audacity is free) or your phone's voice recorder.\n"
            "  2.  Record in a quiet room — no background noise, no reverb.\n"
            "  3.  Single-mallet file:  Strike bars 1 → 21 one at a time, right hand only.\n"
            "  4.  Two-mallet file:  Strike bars 1 → 13 with BOTH mallets simultaneously.\n"
            "      (Left hand plays bar+7, so bar 13 + 7 = bar 20 = the max you need.)\n"
            "  5.  Wait at least 1.5 seconds between each strike — let the note fade.\n"
            "  6.  Do not move the instrument between strikes.\n"
            "  7.  Export as WAV (44100 Hz, 16-bit recommended) or MP3.\n\n"
            "You only need to calibrate ONCE.  Data is saved permanently on your computer."
        )
        ctk.CTkLabel(
            instr, text=text,
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=self.C["text_dim"],
            justify="left", wraplength=760, anchor="w"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # File import rows
        self._file_row(
            card,
            label="Single Mallet  (bars 1 – 21)",
            sub="Strike each bar once with the RIGHT mallet only · 21 notes in order",
            path_var=self._single_path_var,
            btn_color=self.C["blue"],
            tag="single"
        )
        self._file_row(
            card,
            label="Two Mallets  (bars 1 – 13)",
            sub="Strike each bar with BOTH mallets simultaneously · 13 notes in order",
            path_var=self._two_path_var,
            btn_color=self.C["accent"],
            tag="two"
        )

        # Calibrate button + progress
        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=22, pady=(6, 6))

        self.cal_btn = ctk.CTkButton(
            bottom, text="⚡  Run Calibration Now",
            command=self._run_calibration,
            height=46, corner_radius=12,
            fg_color=self.C["green"], hover_color="#2d8c5f",
            text_color="#090a0f",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            width=230
        )
        self.cal_btn.pack(side="left")

        self.cal_msg = ctk.CTkLabel(
            bottom, text="Import at least one audio file to calibrate.",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=self.C["text_dim"]
        )
        self.cal_msg.pack(side="left", padx=(16, 0))

        self.cal_bar = ctk.CTkProgressBar(
            card, height=6, corner_radius=3,
            progress_color=self.C["green"]
        )
        self.cal_bar.set(0)
        # pack later

    def _file_row(self, parent, label, sub, path_var, btn_color, tag):
        row = ctk.CTkFrame(
            parent, fg_color=self.C["card2"],
            corner_radius=10
        )
        row.pack(fill="x", padx=22, pady=(0, 8))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=14, pady=10)

        ctk.CTkLabel(
            info, text=label,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.C["text"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            info, text=sub,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.C["text_dim"]
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            info, textvariable=path_var,
            font=ctk.CTkFont(family="Courier", size=10),
            text_color=self.C["accent"]
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkButton(
            row, text="Browse",
            command=lambda t=tag: self._browse(t),
            width=90, height=34, corner_radius=8,
            fg_color=btn_color,
            hover_color="#2d6a9f" if btn_color == self.C["blue"] else "#b8943e",
            text_color="#0d1117",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="right", padx=14, pady=10)

    # ─────────────────────────────────────────────────────────────────────────

    def _build_tuning(self, parent):
        card = self._section_card(parent, "🎹  Roneat Bar Tuning  (Hz)")

        ctk.CTkLabel(
            card, text="Bar 1 = highest note (~1308 Hz)   ·   Bar 21 = lowest note (~177 Hz)",
            font=ctk.CTkFont(size=11), text_color=self.C["text_dim"]
        ).pack(anchor="w", padx=22, pady=(0, 12))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=22, pady=(0, 14))

        self.hz_entries = {}
        for i in range(1, 22):
            col = (i - 1) % 7
            row = (i - 1) // 7
            grid.grid_columnconfigure(col, weight=1)

            cell = ctk.CTkFrame(
                grid, fg_color=self.C["card2"],
                corner_radius=10, border_width=1,
                border_color=self.C["border"]
            )
            cell.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

            badge = ctk.CTkFrame(
                cell, fg_color=self.C["accent"],
                width=26, height=26, corner_radius=6
            )
            badge.pack(side="left", padx=(8, 6), pady=8)
            badge.pack_propagate(False)
            ctk.CTkLabel(
                badge, text=str(i),
                font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
                text_color="#0d1117"
            ).pack(expand=True)

            entry = ctk.CTkEntry(
                cell, width=72, height=28, corner_radius=6,
                border_width=1, border_color=self.C["border"],
                font=ctk.CTkFont(family="Courier", size=12)
            )
            entry.pack(side="left", pady=8, padx=(0, 8))
            self.hz_entries[i] = entry

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=22, pady=(0, 18))

        ctk.CTkButton(
            btns, text="Reset to Default",
            command=self._reset_default,
            fg_color="transparent", text_color=self.C["accent"],
            border_width=1, border_color=self.C["accent"],
            hover_color=self.C["card"],
            height=38, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"), width=150
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btns, text="Save Tuning",
            command=self._apply_tuning,
            fg_color=self.C["green"], hover_color="#2d8c5f",
            text_color="#0d1117",
            height=38, corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"), width=130
        ).pack(side="left")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _section_card(self, parent, title):
        card = ctk.CTkFrame(
            parent, fg_color=self.C["card"],
            corner_radius=14, border_width=1,
            border_color=self.C["border"]
        )
        card.pack(fill="x", padx=28, pady=(0, 22))
        h = ctk.CTkFrame(card, fg_color="transparent")
        h.pack(fill="x", padx=22, pady=(16, 10))
        ctk.CTkLabel(
            h, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.C["accent"]
        ).pack(anchor="w")
        ctk.CTkFrame(card, height=1, fg_color=self.C["border"]).pack(
            fill="x", padx=18, pady=(0, 12)
        )
        return card

    def _refresh_banner(self):
        for w in self.cal_banner.winfo_children():
            w.destroy()
        single_fps, two_fps = load_fingerprints()
        has_s = single_fps and len(single_fps) > 0
        has_t = two_fps    and len(two_fps)    > 0
        if has_s or has_t:
            parts = []
            if has_s: parts.append(f"Single mallet: {len(single_fps)} bars ✓")
            if has_t: parts.append(f"Two mallets: {len(two_fps)} bars ✓")
            msg   = "  Calibration active:  " + "   |   ".join(parts)
            color = self.C["green"]
            icon  = "✅"
        else:
            msg   = "  No calibration found.  Audio AI will use pitch detection fallback (less accurate)."
            color = self.C["warn"]
            icon  = "⚠️"
        ctk.CTkLabel(
            self.cal_banner, text=f"{icon}  {msg}",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=color
        ).pack(anchor="w", padx=14, pady=10)

    def _browse(self, tag):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select calibration audio",
            filetypes=[("Audio Files", "*.wav *.mp3")]
        )
        if path:
            name = os.path.basename(path)
            if tag == "single":
                self._single_full_path = path
                self._single_path_var.set(f"  ✓  {name}")
            else:
                self._two_full_path = path
                self._two_path_var.set(f"  ✓  {name}")
            self.cal_msg.configure(
                text="Files ready. Click 'Run Calibration Now' to process.",
                text_color=self.C["accent"]
            )

    def _run_calibration(self):
        if not self._single_full_path and not self._two_full_path:
            self.cal_msg.configure(
                text="Please import at least one audio file first.",
                text_color=self.C["accent2"]
            )
            return
        self.cal_btn.configure(state="disabled", text="Calibrating…")
        self.cal_bar.pack(fill="x", padx=22, pady=(0, 12))
        self.cal_bar.set(0)
        threading.Thread(target=self._cal_worker, daemon=True).start()

    def _cal_worker(self):
        single_fps = None
        two_fps    = None

        def prog(pct, msg):
            self.after(0, lambda p=pct, m=msg: (
                self.cal_bar.set(p / 100.0),
                self.cal_msg.configure(text=m, text_color=self.C["text_dim"])
            ))

        try:
            if self._single_full_path:
                print("--- Calibrating single mallet (21 bars) ---")
                single_fps = calibrate_from_audio(
                    self._single_full_path, 21,
                    progress_callback=lambda p, m: prog(int(p * 0.5), m)
                )
            if self._two_full_path:
                print("--- Calibrating two mallets (13 bars) ---")
                two_fps = calibrate_from_audio(
                    self._two_full_path, 13,
                    progress_callback=lambda p, m: prog(50 + int(p * 0.5), m)
                )
            if single_fps or two_fps:
                save_fingerprints(single_fps, two_fps)
                self.after(0, self._cal_success)
            else:
                self.after(0, lambda: self._cal_fail(
                    "Could not detect enough onsets. Check audio and retry."
                ))
        except Exception as e:
            self.after(0, lambda err=str(e): self._cal_fail(err))

    def _cal_success(self):
        self.cal_bar.set(1.0)
        self.cal_btn.configure(state="normal", text="⚡  Run Calibration Now")
        self.cal_msg.configure(
            text="✅  Calibration saved! Audio AI will now use fingerprint matching.",
            text_color=self.C["green"]
        )
        self._refresh_banner()
        self.status_lbl.configure(
            text="Calibration complete — fingerprints saved permanently.",
            text_color=self.C["green"]
        )
        self.after(3000, lambda: self.cal_bar.pack_forget())

    def _cal_fail(self, msg):
        self.cal_btn.configure(state="normal", text="⚡  Run Calibration Now")
        self.cal_msg.configure(text=f"Error: {msg}", text_color=self.C["accent2"])
        self.after(3000, lambda: self.cal_bar.pack_forget())

    def _change_theme(self, choice):
        ctk.set_appearance_mode(choice)
        s = load_app_settings()
        s["theme"] = choice
        save_app_settings(s)
        self.status_lbl.configure(
            text=f"Theme saved: {choice}", text_color=self.C["green"]
        )

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
                valid = False
                entry.configure(border_color=self.C["accent2"])
            else:
                entry.configure(border_color=self.C["border"])
        if valid:
            data = {str(k): int(v.get())
                    for k, v in self.hz_entries.items() if v.get().isdigit()}
            save_hz_preset(os.path.join(PRESETS_DIR, 'default_hz.json'), data)
            self.status_lbl.configure(
                text="Tuning saved.", text_color=self.C["green"]
            )
        else:
            self.status_lbl.configure(
                text="Fix invalid values (100–2000 Hz).", text_color=self.C["accent2"]
            )