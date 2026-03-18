"""
ui/views/audio_to_score.py  v3.0
=================================
Roneat Studio Pro — Audio AI Converter

Layout: single panel with beautiful loading animation
  - File picker + options on the left
  - Central animated progress display during analysis
  - Results + copy button when done
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import math
import threading
import logging

from core.audio_analyzer import audio_to_notes
from core.file_manager    import load_hz_preset
from core.calibration     import load_fingerprints


class AudioToScore(ctk.CTkFrame):
    def __init__(self, master, import_callback):
        super().__init__(master, fg_color="transparent")
        self.import_callback = import_callback
        self.is_analyzing    = False
        self.selected_file   = None
        self.generated_notes = ""
        self._last_sync_data = []
        self._anim_angle     = 0
        self._anim_job       = None

        self.C = {
            "bg":       ("gray96", "#0d1117"),
            "card":     ("white",  "#161b22"),
            "card2":    ("gray95", "#1c2128"),
            "border":   ("gray80", "#30363d"),
            "accent":   "#c8a96e",
            "accent2":  "#e85d4a",
            "blue":     "#3d8ec9",
            "green":    "#3ab87a",
            "warn":     "#f59e0b",
            "text":     ("gray10", "gray92"),
            "text_dim": ("gray45", "#8b949e"),
        }

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_ui()
        self._setup_drag_drop()

    def _build_ui(self):
        # Scrollable main area
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color=self.C["bg"],
            scrollbar_button_color=self.C["accent"]
        )
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.scroll, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=48, pady=(40, 0))
        ctk.CTkLabel(
            hdr, text="🎤  Audio AI  —  Convert Audio to Score",
            font=ctk.CTkFont(family="Georgia", size=26, weight="bold"),
            text_color=self.C["accent"]
        ).pack(anchor="w")
        ctk.CTkLabel(
            hdr,
            text="Import a recording and let the AI transcribe it into Roneat notation.",
            font=ctk.CTkFont(size=13), text_color=self.C["text_dim"]
        ).pack(anchor="w", pady=(5, 0))
        ctk.CTkFrame(self.scroll, height=1, fg_color=self.C["border"]).grid(
            row=1, column=0, sticky="ew", padx=40, pady=(14, 20)
        )

        # ── Calibration banner ────────────────────────────────────────────────
        self.cal_banner = ctk.CTkFrame(
            self.scroll, fg_color=self.C["card2"],
            corner_radius=12, border_width=1, border_color=self.C["border"]
        )
        self.cal_banner.grid(row=2, column=0, sticky="ew", padx=40, pady=(0, 16))
        self._refresh_cal_banner()

        # ── Polyphony warning (hidden) ─────────────────────────────────────────
        self.poly_banner = ctk.CTkFrame(
            self.scroll, fg_color=("#fffbeb", "#2d2008"),
            corner_radius=12, border_width=1, border_color=self.C["warn"]
        )
        # Not gridded until needed
        ctk.CTkLabel(
            self.poly_banner,
            text="⚠️  Polyphonic audio detected — multiple instruments playing simultaneously",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.C["warn"]
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self.poly_detail_lbl = ctk.CTkLabel(
            self.poly_banner, text="",
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=self.C["warn"]
        )
        self.poly_detail_lbl.pack(anchor="w", padx=16, pady=(0, 4))
        ctk.CTkLabel(
            self.poly_banner,
            text=(
                "The app will attempt to isolate the melody, but accuracy may be reduced.\n"
                "For best results: use a solo piano/instrument version, or record "
                "the melody directly on your Roneat and calibrate."
            ),
            font=ctk.CTkFont(size=11), text_color=self.C["text_dim"],
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # ── Two-column layout: File+Options | Action ──────────────────────────
        cols = ctk.CTkFrame(self.scroll, fg_color="transparent")
        cols.grid(row=3, column=0, sticky="ew", padx=40, pady=(0, 16))
        cols.grid_columnconfigure(0, weight=1)
        cols.grid_columnconfigure(1, weight=1)

        # Left col: File + Options
        left = ctk.CTkFrame(cols, fg_color=self.C["card"],
                            corner_radius=14, border_width=1,
                            border_color=self.C["border"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        ctk.CTkLabel(
            left, text="AUDIO FILE",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.C["text_dim"]
        ).pack(anchor="w", padx=20, pady=(18, 4))

        file_row = ctk.CTkFrame(left, fg_color="transparent")
        file_row.pack(fill="x", padx=20, pady=(0, 4))
        self.file_lbl = ctk.CTkLabel(
            file_row, text="No file selected",
            font=ctk.CTkFont(size=12), text_color=self.C["text_dim"], anchor="w"
        )
        self.file_lbl.pack(side="left", fill="x", expand=True)
        self.browse_btn = ctk.CTkButton(
            file_row, text="Browse",
            command=self.select_file,
            width=90, height=34, corner_radius=8,
            fg_color=self.C["blue"], hover_color="#2d6a9f",
            text_color="#0d1117",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.browse_btn.pack(side="right")

        ctk.CTkFrame(left, height=1, fg_color=self.C["border"]).pack(
            fill="x", padx=16, pady=(12, 12)
        )
        ctk.CTkLabel(
            left, text="OPTIONS",
            font=ctk.CTkFont(family="Courier", size=10, weight="bold"),
            text_color=self.C["text_dim"]
        ).pack(anchor="w", padx=20, pady=(0, 6))
        self.two_mallets_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            left, text="Two Mallets Mode  (left hand +7 bars)",
            variable=self.two_mallets_var,
            font=ctk.CTkFont(size=12),
            progress_color=self.C["accent"]
        ).pack(anchor="w", padx=20, pady=(0, 18))

        # Right col: Action button + status
        right = ctk.CTkFrame(cols, fg_color=self.C["card"],
                             corner_radius=14, border_width=1,
                             border_color=self.C["border"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_rowconfigure(0, weight=1)

        self.gen_btn = ctk.CTkButton(
            right,
            text="✨  Generate Score with AI",
            command=self.start_analysis,
            state="disabled", height=56, corner_radius=12,
            fg_color=self.C["accent"], text_color="#0d1117",
            hover_color="#deba7e",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold")
        )
        self.gen_btn.pack(fill="x", padx=20, pady=(20, 8))
        ctk.CTkLabel(
            right,
            text="The AI will analyze your recording and\nproduce Roneat bar notation automatically.",
            font=ctk.CTkFont(size=11), text_color=self.C["text_dim"],
            justify="center"
        ).pack(pady=(0, 20))

        # ── Progress / Animation area (hidden until analysis starts) ──────────
        self.progress_card = ctk.CTkFrame(
            self.scroll, fg_color=self.C["card"],
            corner_radius=14, border_width=1, border_color=self.C["border"]
        )
        # Not gridded until needed

        # Canvas for spinner animation
        is_dark = True  # default
        self._canvas_bg = "#161b22"
        self.anim_canvas = tk.Canvas(
            self.progress_card,
            width=100, height=100, bg=self._canvas_bg,
            highlightthickness=0
        )
        self.anim_canvas.pack(pady=(28, 8))

        self.stage_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
            text_color=self.C["accent"]
        )
        self.stage_lbl.pack()

        self.detail_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Courier", size=12),
            text_color=self.C["text_dim"]
        )
        self.detail_lbl.pack(pady=(4, 0))

        self.pct_lbl = ctk.CTkLabel(
            self.progress_card, text="",
            font=ctk.CTkFont(family="Courier", size=28, weight="bold"),
            text_color=self.C["accent"]
        )
        self.pct_lbl.pack(pady=(8, 4))

        self.prog_bar = ctk.CTkProgressBar(
            self.progress_card, height=8, corner_radius=4,
            progress_color=self.C["accent"]
        )
        self.prog_bar.set(0)
        self.prog_bar.pack(fill="x", padx=40, pady=(0, 28))

        # ── Result area ───────────────────────────────────────────────────────
        self.result_card = ctk.CTkFrame(
            self.scroll, fg_color=self.C["card"],
            corner_radius=14, border_width=1, border_color=self.C["border"]
        )
        # Not gridded until done

        res_hdr = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_hdr.pack(fill="x", padx=20, pady=(18, 6))
        ctk.CTkLabel(
            res_hdr,
            text="Generated Score",
            font=ctk.CTkFont(family="Georgia", size=15, weight="bold"),
            text_color=self.C["accent"]
        ).pack(side="left")
        self.copy_btn = ctk.CTkButton(
            res_hdr, text="⧉  Copy",
            command=self._copy_result,
            width=80, height=30, corner_radius=8,
            fg_color="transparent", text_color=self.C["accent"],
            border_width=1, border_color=self.C["accent"],
            hover_color=self.C["card2"],
            font=ctk.CTkFont(size=12)
        )
        self.copy_btn.pack(side="right")

        self.result_box = ctk.CTkTextbox(
            self.result_card, height=120, corner_radius=8,
            fg_color=self.C["card2"],
            font=ctk.CTkFont(family="Courier", size=15), wrap="word",
            border_width=0
        )
        self.result_box.pack(fill="x", padx=20, pady=(0, 16))

        self.import_btn = ctk.CTkButton(
            self.result_card,
            text="➔  Import to Score Editor",
            command=self.send_to_editor,
            state="disabled", height=48, corner_radius=10,
            fg_color=self.C["green"], hover_color="#2d8c5f",
            text_color="#0d1117",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.import_btn.pack(fill="x", padx=20, pady=(0, 20))

    # ─────────────────────────────────────────────────────────────────────────
    # Animation
    # ─────────────────────────────────────────────────────────────────────────

    def _start_spinner(self):
        self._anim_angle = 0
        self._draw_spinner()

    def _draw_spinner(self):
        if not self.is_analyzing:
            return
        c  = self.anim_canvas
        w, h = 100, 100
        cx, cy, r = w//2, h//2, 36
        c.delete("all")
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#161b22" if is_dark else "#f0f4f8"
        c.configure(bg=bg)
        # Background ring
        c.create_arc(cx-r, cy-r, cx+r, cy+r,
                     start=0, extent=359, style="arc",
                     outline="#30363d", width=6)
        # Animated arc
        start = self._anim_angle % 360
        c.create_arc(cx-r, cy-r, cx+r, cy+r,
                     start=start, extent=270, style="arc",
                     outline="#c8a96e", width=6)
        # Inner dot
        c.create_oval(cx-8, cy-8, cx+8, cy+8,
                      fill="#c8a96e", outline="")
        self._anim_angle = (self._anim_angle + 6) % 360
        self._anim_job = self.after(30, self._draw_spinner)

    def _stop_spinner(self):
        if self._anim_job:
            self.after_cancel(self._anim_job)
            self._anim_job = None
        # Draw checkmark
        c = self.anim_canvas
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#161b22" if is_dark else "#f0f4f8"
        c.configure(bg=bg)
        c.delete("all")
        cx, cy, r = 50, 50, 36
        c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#3ab87a", outline="")
        c.create_line(34, 50, 46, 62, 66, 38, fill="white", width=5,
                      joinstyle="round", capstyle="round")

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────


    def _setup_drag_drop(self):
        """Enable drag-and-drop of audio files onto this panel."""
        try:
            self.scroll.drop_target_register('DND_Files')
            self.scroll.dnd_bind('<<Drop>>', self._on_dnd_drop)
        except Exception as e:
            logging.info("tkinterdnd2 not available for audio_to_score, drag and drop disabled.")

    def _on_dnd_drop(self, event):
        raw = event.data.strip()
        if raw.startswith('{') and raw.endswith('}'):
            raw = raw[1:-1]
        fp = raw.strip('"')
        if os.path.isfile(fp):
            self._drop_file(fp)

    def _refresh_cal_banner(self):
        for w in self.cal_banner.winfo_children():
            w.destroy()
        single_fps, two_fps = load_fingerprints()
        has_cal = (single_fps and len(single_fps) > 0) or (two_fps and len(two_fps) > 0)
        if has_cal:
            parts = []
            if single_fps: parts.append(f"single: {len(single_fps)} bars")
            if two_fps:    parts.append(f"two-mallet: {len(two_fps)} bars")
            msg   = "✅  Calibrated — " + ", ".join(parts) + "  |  Using fingerprint matching"
            color = self.C["green"]
        else:
            msg   = "⚠️  No calibration found — using pitch detection (less accurate for real Roneat).  Go to Settings → Calibration."
            color = self.C["warn"]
        ctk.CTkLabel(
            self.cal_banner, text=msg,
            font=ctk.CTkFont(family="Courier", size=11),
            text_color=color
        ).pack(anchor="w", padx=16, pady=10)

    def _show_poly_banner(self, poly_info):
        if poly_info and poly_info.get("is_polyphonic"):
            r = poly_info["poly_ratio"]
            p = poly_info["avg_peaks"]
            self.poly_detail_lbl.configure(
                text=f"Polyphonic frames: {r:.0%}   |   Avg simultaneous peaks: {p:.1f}"
            )
            self.poly_banner.grid(row=2, column=0, sticky="ew", padx=40,
                                   pady=(0, 12), in_=self.scroll)
        else:
            try:
                self.poly_banner.grid_forget()
            except Exception as e:
                pass

    def _copy_result(self):
        text = self.result_box.get("0.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.copy_btn.configure(text="✓  Copied!")
            self.after(1500, lambda: self.copy_btn.configure(text="⧉  Copy"))

    # ─────────────────────────────────────────────────────────────────────────
    # Actions
    # ─────────────────────────────────────────────────────────────────────────

    def select_file(self):
        path = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Audio Files", "*.mp3 *.wav")]
        )
        if path:
            self.selected_file = path
            name = os.path.basename(path)
            self.file_lbl.configure(text=name, text_color=self.C["text"])
            self.gen_btn.configure(state="normal")
            self._refresh_cal_banner()
            try:
                self.poly_banner.grid_forget()
            except Exception as e:
                pass


    def _drop_file(self, path):
        """Called by MainWindow when a file is drag-dropped onto the app."""
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.mp3', '.wav'):
            return
        self.selected_file = path
        name = os.path.basename(path)
        self.file_lbl.configure(text=f"📎  {name}", text_color=self.C["text"])
        self.gen_btn.configure(state="normal")
        self._refresh_cal_banner()
        try:
            self.poly_banner.grid_forget()
        except Exception:
            pass

    def _on_progress(self, pct, msg, note_data, poly_info):
        # Map progress message to stage label
        STAGES = {
            3: "Loading",  8: "Analyzing",  12: "Processing",
            18: "Separating", 25: "Detecting Onsets", 32: "Transcribing",
            100: "Complete"
        }
        stage = "Transcribing"
        for threshold in sorted(STAGES.keys()):
            if pct >= threshold:
                stage = STAGES[threshold]

        def _do():
            self.stage_lbl.configure(text=stage)
            self.detail_lbl.configure(text=msg[:80])
            self.pct_lbl.configure(text=f"{pct}%")
            self.prog_bar.set(pct / 100.0)
            if poly_info is not None:
                self._show_poly_banner(poly_info)
        self.after(0, _do)

    def start_analysis(self):
        if self.is_analyzing or not self.selected_file:
            return

        self.is_analyzing = True
        self.gen_btn.configure(state="disabled", text="Analyzing…")
        self.browse_btn.configure(state="disabled")
        self.generated_notes = ""
        self._last_sync_data = []

        # Hide result, show progress
        try:
            self.result_card.grid_forget()
        except Exception:
            pass
        self.progress_card.grid(row=4, column=0, sticky="ew", padx=40, pady=(0, 16),
                                 in_=self.scroll)
        self.prog_bar.set(0)
        self.stage_lbl.configure(text="Loading")
        self.detail_lbl.configure(text="Starting analysis…")
        self.pct_lbl.configure(text="0%")
        self._start_spinner()

        is_two_mallets = self.two_mallets_var.get()
        threading.Thread(target=self._worker, args=(is_two_mallets,), daemon=True).start()

    def _worker(self, is_two_mallets):
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
                notes_str  = result if isinstance(result, str) else ""
                poly_info  = None
                sync_data  = []
            self.generated_notes = notes_str
            self._last_sync_data = sync_data
            self._last_poly_info = poly_info
        except Exception as e:
            logging.error(f"[AudioToScore] AI transcription failed: {e}", exc_info=True)
            self.generated_notes = ""
            self._last_sync_data = []
            self._last_poly_info = None
        self.after(0, self._finish)

    def _finish(self):
        self._stop_spinner()
        self.is_analyzing = False
        self.gen_btn.configure(state="normal", text="✨  Generate Score with AI")
        self.browse_btn.configure(state="normal")

        n = len(self.generated_notes.split()) if self.generated_notes.strip() else 0

        if self.generated_notes.strip():
            self.stage_lbl.configure(text="Complete ✓")
            self.detail_lbl.configure(text=f"{n} notes detected")
            self.pct_lbl.configure(text="100%", text_color=self.C["green"])
            self.prog_bar.set(1.0)

            self.result_box.delete("0.0", "end")
            self.result_box.insert("0.0", self.generated_notes)
            self.import_btn.configure(state="normal")
            self.result_card.grid(row=5, column=0, sticky="ew", padx=40, pady=(0, 40),
                                   in_=self.scroll)
        else:
            self.stage_lbl.configure(text="No notes detected")
            self.detail_lbl.configure(
                text="Check audio quality, or try a cleaner recording.",
                text_color=self.C["accent2"]
            )

    def send_to_editor(self):
        if self.generated_notes:
            self.import_btn.configure(text="✓  Imported!", state="disabled")
            self.update()
            self.import_callback(
                self.generated_notes,
                self.two_mallets_var.get(),
                self._last_sync_data,
                self.selected_file      # pass source audio path for MP4 export
            )
            self.after(1500, lambda: self.import_btn.configure(
                text="➔  Import to Score Editor", state="normal"
            ))