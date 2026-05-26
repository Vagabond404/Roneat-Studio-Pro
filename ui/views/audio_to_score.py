"""
ui/views/audio_to_score.py  v4.0
=================================
Roneat Studio Pro — Audio AI Converter

Premium DAW Edition:
  - Redesigned File Drop Zone with dashed border and glassmorphism feel
  - Enhanced Header with "AI-ready" aesthetic
  - Polished Result & Analysis cards
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import math
import threading
import logging
import time

from core.audio_analyzer import audio_to_notes
from core.file_manager    import load_hz_preset
from core.calibration     import load_fingerprints


class AudioToScore(ctk.CTkFrame):
    def _clr(self, color):
        if isinstance(color, (list, tuple)):
            return color[1] if ctk.get_appearance_mode() == "Dark" else color[0]
        return color

    def __init__(self, master, import_callback):
        super().__init__(master, fg_color="transparent")
        self.import_callback = import_callback
        self.is_analyzing    = False
        self.selected_file   = None
        self.generated_notes = ""
        self._last_sync_data = []
        self._anim_angle     = 0
        self._anim_job       = None

        # Premium DAW color palette
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

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self._setup_drag_drop()

    def _build_ui(self):
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color = self.C["bg"],
            scrollbar_button_color = self.C["accent"],
            scrollbar_button_hover_color = "#E6C45C"
        )
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=52, pady=(44, 0))
        
        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(anchor="w")
        
        ctk.CTkLabel(
            title_box, text="✨",
            font=ctk.CTkFont(size=28),
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkLabel(
            title_box, text="Audio AI Transcription",
            font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"),
            text_color = self.C["accent"]
        ).pack(side="left")
        
        ctk.CTkLabel(
            hdr,
            text="High-performance neural network analysis for Roneat Ek notation.",
            font=ctk.CTkFont(family="Segoe UI", size=14), text_color = self.C["text_dim"]
        ).pack(anchor="w", pady=(6, 0))
        
        ctk.CTkFrame(self.scroll, height=2, fg_color = self.C["border"]).grid(
            row=1, column=0, sticky="ew", padx=40, pady=(20, 24)
        )

        # ── Calibration banner ────────────────────────────────────────────────
        self.cal_banner = ctk.CTkFrame(
            self.scroll, fg_color = self.C["card2"],
            corner_radius=12, border_width=1, border_color = self.C["border"]
        )
        self.cal_banner.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 20))
        self._refresh_cal_banner()

        # ── Polyphony warning (hidden) ─────────────────────────────────────────
        self.poly_banner = ctk.CTkFrame(
            self.scroll, fg_color=("#fffbeb", "#201a0a"),
            corner_radius=12, border_width=1, border_color = self.C["warn"]
        )
        ctk.CTkLabel(
            self.poly_banner,
            text="⚠️  Multi-instrument Audio Detected",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color = self.C["warn"]
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self.poly_detail_lbl = ctk.CTkLabel(
            self.poly_banner, text="",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color = self.C["warn"]
        )
        self.poly_detail_lbl.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            self.poly_banner,
            text=(
                "Transcription works best with clean, solo Roneat recordings.\n"
                "Orchestral backings may cause ghost notes or timing shifts."
            ),
            font=ctk.CTkFont(size=11), text_color = self.C["text_dim"],
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # ── Main Content Area ──────────────────────────────────────────────────
        main_content = ctk.CTkFrame(self.scroll, fg_color="transparent")
        main_content.grid(row=3, column=0, sticky="ew", padx=40, pady=(0, 20))
        main_content.grid_columnconfigure(0, weight=6)
        main_content.grid_columnconfigure(1, weight=4)

        # ── LEFT: The Drop Zone ───────────────────────────────────────────────
        self.drop_zone = ctk.CTkFrame(main_content, fg_color = self.C["card"],
                                   corner_radius=16, border_width=1,
                                   border_color = self.C["border"])
        self.drop_zone.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        # Inner "dashed" effect layout
        self.drop_inner = ctk.CTkFrame(self.drop_zone, fg_color=self.C["card2"], corner_radius=12)
        self.drop_inner.pack(fill="both", expand=True, padx=14, pady=14)

        self.drop_icon_lbl = ctk.CTkLabel(
            self.drop_inner, text="📥", font=ctk.CTkFont(size=42)
        )
        self.drop_icon_lbl.pack(pady=(30, 10))

        self.file_lbl = ctk.CTkLabel(
            self.drop_inner, text="Drop Audio File Here",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color = self.C["text"]
        )
        self.file_lbl.pack()
        
        ctk.CTkLabel(
            self.drop_inner, text="Supports WAV, MP3  (44.1kHz / 48kHz mono or stereo)",
            font=ctk.CTkFont(size=11), text_color = self.C["text_dim"]
        ).pack(pady=(2, 20))

        self.browse_btn = ctk.CTkButton(
            self.drop_inner, text="Browse Files",
            command=self.select_file,
            width=140, height=38, corner_radius=10,
            fg_color = "transparent", border_color = self.C["accent"], border_width=1,
            text_color = self.C["accent"],
            hover_color = self.C["card"],
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.browse_btn.pack(pady=(0, 30))

        # ── RIGHT: Transcription Control ──────────────────────────────────────
        right_panel = ctk.CTkFrame(main_content, fg_color="transparent")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        # Options Card
        opts_card = ctk.CTkFrame(right_panel, fg_color = self.C["card"],
                                corner_radius=16, border_width=1,
                                border_color = self.C["border"])
        opts_card.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(
            opts_card, text="ALGORITHM SETTINGS",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color = self.C["text_dim"]
        ).pack(anchor="w", padx=20, pady=(18, 12))

        self.two_mallets_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            opts_card, text="Two Mallets Mode",
            variable=self.two_mallets_var,
            font=ctk.CTkFont(size=13),
            progress_color = self.C["accent"]
        ).pack(anchor="w", padx=20, pady=(0, 8))
        
        ctk.CTkLabel(
            opts_card, text="Simulates left hand (+7 bars) for richer scores",
            font=ctk.CTkFont(size=11), text_color = self.C["text_dim"]
        ).pack(anchor="w", padx=48, pady=(0, 20))

        # Main Action
        self.gen_btn = ctk.CTkButton(
            right_panel,
            text="START ANALYSIS",
            command=self.start_analysis,
            state="disabled", height=80, corner_radius=16,
            fg_color = self.C["accent"], text_color="#090a0f",
            hover_color="#e6c45c",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        self.gen_btn.pack(fill="x")

        # ── Progress / Animation area ──────────────────────────────────────────
        self.progress_card = ctk.CTkFrame(
            self.scroll, fg_color = self.C["card"],
            corner_radius=18, border_width=1, border_color = self.C["border"]
        )

        self._canvas_bg = self._clr(self.C["card"])
        self.anim_canvas = tk.Canvas(
            self.progress_card,
            width=120, height=120, bg=self._canvas_bg,
            highlightthickness=0
        )
        self.anim_canvas.pack(pady=(32, 12))

        self.stage_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Georgia", size=18, weight="bold"),
            text_color = self.C["accent"]
        )
        self.stage_lbl.pack()

        self.detail_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color = self.C["text_dim"]
        )
        self.detail_lbl.pack(pady=(4, 0))

        self.pct_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Courier", size=32, weight="bold"),
            text_color = self.C["accent"]
        )
        self.pct_lbl.pack(pady=(12, 6))

        self.prog_bar = ctk.CTkProgressBar(
            self.progress_card, height=10, corner_radius=5,
            progress_color = self.C["accent"]
        )
        self.prog_bar.set(0)
        self.prog_bar.pack(fill="x", padx=60, pady=(0, 36))

        # ── Result area ───────────────────────────────────────────────────────
        self.result_card = ctk.CTkFrame(
            self.scroll, fg_color = self.C["card"],
            corner_radius=18, border_width=1, border_color = self.C["border"]
        )

        res_hdr = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_hdr.pack(fill="x", padx=24, pady=(22, 10))
        ctk.CTkLabel(
            res_hdr,
            text="Transcription Result",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color = self.C["accent"]
        ).pack(side="left")
        
        self.copy_btn = ctk.CTkButton(
            res_hdr, text="⧉ Copy",
            command=self._copy_result,
            width=90, height=34, corner_radius=10,
            fg_color="transparent", text_color = self.C["accent"],
            border_width=1, border_color = self.C["accent"],
            hover_color = self.C["card2"],
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.copy_btn.pack(side="right")

        self.result_box = ctk.CTkTextbox(
            self.result_card, height=160, corner_radius=12,
            fg_color = self.C["card2"],
            font=ctk.CTkFont(family="Consolas", size=18), wrap="word",
            border_width=0
        )
        self.result_box.pack(fill="x", padx=24, pady=(0, 20))

        self.import_btn = ctk.CTkButton(
            self.result_card,
            text="PUSH TO SCORE EDITOR",
            command=self.send_to_editor,
            state="disabled", height=56, corner_radius=14,
            fg_color = self.C["green"], hover_color="#2d8c5f",
            text_color="#090a0f",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        )
        self.import_btn.pack(fill="x", padx=24, pady=(0, 24))

    # ─────────────────────────────────────────────────────────────────────────
    # Animation
    # ─────────────────────────────────────────────────────────────────────────

    def _start_spinner(self):
        self._anim_angle = 0
        self._draw_spinner()

    def _draw_spinner(self):
        if not self.is_analyzing:
            return
        c = self.anim_canvas
        w, h = 120, 120
        cx, cy, r = w//2, h//2, 42
        c.delete("all")
        bg = self._clr(self.C["card"])
        c.configure(bg=bg)
        
        # Background ring
        c.create_arc(cx-r, cy-r, cx+r, cy+r,
                     start=0, extent=359, style="arc",
                     outline=self._clr(self.C["border"]), width=8)
        
        # Animated arc in Gold
        start = self._anim_angle % 360
        c.create_arc(cx-r, cy-r, cx+r, cy+r,
                     start=start, extent=240, style="arc",
                     outline=self._clr(self.C["accent"]), width=8)
        
        # Inner pulse
        pulse = 6 + 4 * math.sin(time.time() * 8)
        c.create_oval(cx-pulse, cy-pulse, cx+pulse, cy+pulse,
                      fill=self._clr(self.C["accent"]), outline="")
                      
        self._anim_angle = (self._anim_angle + 8) % 360
        self._anim_job = self.after(25, self._draw_spinner)

    def _stop_spinner(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        c = self.anim_canvas
        c.delete("all")
        cx, cy, r = 60, 60, 42
        c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=self._clr(self.C["green"]), outline="")
        c.create_line(42, 60, 54, 72, 78, 48, fill="white", width=6,
                      joinstyle="round", capstyle="round")

    # ─────────────────────────────────────────────────────────────────────────
    # Logic
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_drag_drop(self):
        try:
            self.scroll.drop_target_register('DND_Files')
            self.scroll.dnd_bind('<<Drop>>', self._on_dnd_drop)
        except Exception:
            logging.info("tkinterdnd2 not available")

    def _on_dnd_drop(self, event):
        raw = event.data.strip()
        if raw.startswith('{') and raw.endswith('}'): raw = raw[1:-1]
        fp = raw.strip('"')
        if os.path.isfile(fp): self._drop_file(fp)

    def _refresh_cal_banner(self):
        for w in self.cal_banner.winfo_children(): w.destroy()
        single_fps, two_fps = load_fingerprints()
        has_cal = (single_fps and len(single_fps) > 0) or (two_fps and len(two_fps) > 0)
        
        if has_cal:
            msg = "✅   Neural calibration active. Fingering matches detected."
            color = self._clr(self.C["green"])
        else:
            msg = "⚠️   No calibration found. Using generic FFT pitch detection (Standard mode)."
            color = self._clr(self.C["warn"])
            
        ctk.CTkLabel(
            self.cal_banner, text=msg,
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=color
        ).pack(anchor="w", padx=20, pady=12)

    def _show_poly_banner(self, poly_info):
        if poly_info and poly_info.get("is_polyphonic"):
            r = poly_info["poly_ratio"]
            p = poly_info["avg_peaks"]
            self.poly_detail_lbl.configure(
                text=f"Complexity: {r:.0%} density | Peaks: {p:.1f} per frame"
            )
            self.poly_banner.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 16), in_=self.scroll)
        else:
            try: self.poly_banner.grid_forget()
            except Exception: pass

    def select_file(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Audio Files", "*.mp3 *.wav")]
        )
        if path: self._drop_file(path)

    def _drop_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.mp3', '.wav'): return
        self.selected_file = path
        name = os.path.basename(path)
        self.file_lbl.configure(text=name, text_color = self.C["accent"])
        self.drop_icon_lbl.configure(text="🎵", text_color=self.C["accent"])
        self.gen_btn.configure(state="normal")
        self._refresh_cal_banner()
        try: self.poly_banner.grid_forget()
        except Exception: pass

    def _on_progress(self, pct, msg, note_data, poly_info):
        STAGES = {
            3: "Initializing", 8: "Spectral Analysis", 15: "HPS Decomposition",
            25: "Onset Mapping", 40: "Neural Decoding", 80: "Post-Processing",
            100: "Neural Sync Complete"
        }
        stage = ""
        for threshold in sorted(STAGES.keys()):
            if pct >= threshold: stage = STAGES[threshold]

        def _do():
            self.stage_lbl.configure(text=stage)
            self.detail_lbl.configure(text=msg[:80])
            self.pct_lbl.configure(text=f"{pct}%")
            self.prog_bar.set(pct / 100.0)
            if poly_info is not None: self._show_poly_banner(poly_info)
        self.after(0, _do)

    def start_analysis(self):
        if self.is_analyzing or not self.selected_file: return
        self.is_analyzing = True
        self.gen_btn.configure(state="disabled", text="PROCESSING…")
        self.browse_btn.configure(state="disabled")
        self.generated_notes = ""
        self._last_sync_data = []

        try: self.result_card.grid_forget()
        except Exception: pass
        
        self.progress_card.grid(row=4, column=0, sticky="ew", padx=40, pady=(0, 20), in_=self.scroll)
        self.prog_bar.set(0)
        self._start_spinner()

        is_two_mallets = self.two_mallets_var.get()
        threading.Thread(target=self._worker, args=(is_two_mallets,), daemon=True).start()

    def _worker(self, is_two_mallets):
        import time as _t
        try:
            roneat_dict = load_hz_preset()
            result = audio_to_notes(
                self.selected_file, roneat_dict,
                two_mallets=is_two_mallets,
                progress_callback=self._on_progress
            )
            if isinstance(result, tuple) and len(result) == 3:
                notes_str, poly_info, sync_data = result
            else:
                notes_str, poly_info, sync_data = result, None, []
            self.generated_notes = notes_str
            self._last_sync_data = sync_data
        except Exception as e:
            logging.error(f"[AudioToScore] AI failed: {e}", exc_info=True)
            self.generated_notes = ""
        self.after(0, self._finish)

    def _finish(self):
        self._stop_spinner()
        self.is_analyzing = False
        self.gen_btn.configure(state="normal", text="START ANALYSIS")
        self.browse_btn.configure(state="normal")

        if self.generated_notes.strip():
            self.stage_lbl.configure(text="Neural Sync Complete ✓")
            self.pct_lbl.configure(text="100%", text_color = self.C["green"])
            self.prog_bar.set(1.0)
            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", self.generated_notes)
            self.import_btn.configure(state="normal")
            self.result_card.grid(row=5, column=0, sticky="ew", padx=40, pady=(0, 48), in_=self.scroll)
        else:
            self.stage_lbl.configure(text="Transcription Failed")
            self.detail_lbl.configure(text="Signal noise floor too high or format error.", text_color=self.C["accent2"])

    def send_to_editor(self):
        if self.generated_notes:
            self.import_btn.configure(text="✓  TRANSFERRED TO EDITOR!", state="disabled")
            self.update()
            self.import_callback(
                self.generated_notes, self.two_mallets_var.get(),
                self._last_sync_data, self.selected_file
            )
            self.after(2000, lambda: self.import_btn.configure(
                text="PUSH TO SCORE EDITOR", state="normal"
            ))

    def _copy_result(self):
        text = self.result_box.get("0.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.copy_btn.configure(text="✓ Copied")
            self.after(1500, lambda: self.copy_btn.configure(text="⧉ Copy"))

import time