import os
import threading
import math
import customtkinter as ctk
from PIL import Image, ImageTk
import numpy as np

from core.video_exporter import build_timeline, render_frame, export_mp4, total_duration

class VideoExportStudioWindow(ctk.CTkToplevel):
    def __init__(self, parent, editor):
        super().__init__(parent)
        self.editor = editor
        self.title("Video Export Studio")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        self.transient(parent)
        self.grab_set()
        
        self.C = editor.C
        self.configure(fg_color=self.C["bg"])
        
        # --- State ---
        self.is_playing_preview = False
        self.time_offset = 0.0
        self.preview_job = None
        self.vid_dur = 0.0
        self.events = []
        self.event_frames = []
        
        self._build_ui()
        self._build_timeline_data()
        self.update()
        self.update_preview()
        
    def _build_ui(self):
        # Left Panel (Parameters)
        self.left_panel = ctk.CTkFrame(self, width=380, fg_color=self.C["card"], corner_radius=0)
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)
        
        # Right Panel (Preview)
        self.right_panel = ctk.CTkFrame(self, fg_color=self.C["bg"], corner_radius=0)
        self.right_panel.pack(side="right", fill="both", expand=True)
        
        self._build_left_panel()
        self._build_right_panel()
        
    def _build_left_panel(self):
        lbl_title = ctk.CTkLabel(self.left_panel, text="Export Settings", font=("Georgia", 22, "bold"), text_color=("#111111", self.C["accent"]))
        lbl_title.pack(pady=(20, 20))
        
        # Scrollable frame for settings
        scroll = ctk.CTkScrollableFrame(self.left_panel, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10)
        
        # Output File Name
        import os
        from pathlib import Path
        ctk.CTkLabel(scroll, text="File Name", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(5, 5))
        default_name = self.editor.title_entry.get().strip() or "roneat_export"
        # Sanitize filename
        default_name = "".join(c for c in default_name if c not in '<>:"/\\|?*' and ord(c) >= 32).strip()
        self.filename_var = ctk.StringVar(value=f"{default_name}.mp4")
        ctk.CTkEntry(scroll, textvariable=self.filename_var).pack(fill="x", padx=10)
        
        # Export Path
        ctk.CTkLabel(scroll, text="Export Path", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        default_path = str(Path.home() / "Downloads")
        self.path_var = ctk.StringVar(value=default_path)
        path_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        path_frame.pack(fill="x", padx=10)
        ctk.CTkEntry(path_frame, textvariable=self.path_var).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(path_frame, text="Browse", width=60, fg_color=self.C["accent"], hover_color="#deba7e", text_color="#0d1117", command=self._browse_path).pack(side="right", padx=(5, 0))
        
        # Aspect Ratio
        ctk.CTkLabel(scroll, text="Video Format", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(20, 5))
        self.format_var = ctk.StringVar(value="16:9 Landscape")
        for val in ["16:9 Landscape", "9:16 Portrait", "1:1 Square"]:
            ctk.CTkRadioButton(scroll, text=val, variable=self.format_var, value=val,
                               command=self.on_format_change, text_color=("#111111", "#EEEEEE"),
                               fg_color=self.C["accent"], hover_color=self.C["accent"]).pack(anchor="w", pady=5, padx=10)
                               
        # Resolution
        ctk.CTkLabel(scroll, text="Resolution", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        self.res_var = ctk.StringVar(value="1080p")
        ctk.CTkSegmentedButton(scroll, values=["720p", "1080p", "4K"], variable=self.res_var,
                               selected_color=self.C["accent"], selected_hover_color=self.C["accent"],
                               unselected_color=self.C["card"], unselected_hover_color=self.C["border"],
                               command=self.update_preview).pack(fill="x", padx=10)
                               
        # Framerate
        ctk.CTkLabel(scroll, text="Framerate", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        self.fps_var = ctk.StringVar(value="60 FPS (Premium Smooth)")
        ctk.CTkOptionMenu(scroll, values=["30 FPS (Fast Render)", "60 FPS (Premium Smooth)"], variable=self.fps_var,
                          fg_color=self.C["accent"], button_color="#deba7e", button_hover_color="#deba7e", text_color="#0d1117").pack(fill="x", padx=10)
                               
        # Audio Engine
        ctk.CTkLabel(scroll, text="Audio Engine", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        self.engine_var = ctk.StringVar(value="Samples" if self.editor.player.mode == "samples" else "Synthesizer")
        ctk.CTkSegmentedButton(scroll, values=["Synthesizer", "Samples"], variable=self.engine_var,
                               selected_color=self.C["accent"], selected_hover_color=self.C["accent"],
                               unselected_color=self.C["card"], unselected_hover_color=self.C["border"]).pack(fill="x", padx=10)

        # Speed / Tempo
        ctk.CTkLabel(scroll, text="Speed / Tempo (BPM)", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        # Read BPM from editor robustly (may be disabled/float string)
        try:
            _raw_bpm = int(float(self.editor.bpm_entry.get().strip()))
            _raw_bpm = max(20, min(_raw_bpm, 400))
        except (ValueError, TypeError):
            _raw_bpm = 120
        self.bpm_var = ctk.StringVar(value=str(_raw_bpm))
        self.bpm_entry = ctk.CTkEntry(scroll, textvariable=self.bpm_var)
        self.bpm_entry.pack(fill="x", padx=10)
        self.bpm_entry.bind("<KeyRelease>", lambda e: self._build_timeline_data())
        
        # Appearance
        ctk.CTkLabel(scroll, text="Appearance", font=("Helvetica", 14, "bold"), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 5))
        self.theme_var = ctk.StringVar(value="Dark")
        ctk.CTkSegmentedButton(scroll, values=["Dark", "Light"], variable=self.theme_var,
                               selected_color=self.C["accent"], selected_hover_color=self.C["accent"],
                               unselected_color=self.C["card"], unselected_hover_color=self.C["border"],
                               command=self.update_preview).pack(fill="x", padx=10)
                               
        self.view_mode_var = ctk.StringVar(value=self.editor.get_active_view_mode())
        ctk.CTkSegmentedButton(scroll, values=["Numeric", "Letters", "Syllabic"], variable=self.view_mode_var,
                               selected_color=self.C["accent"], selected_hover_color=self.C["accent"],
                               unselected_color=self.C["card"], unselected_hover_color=self.C["border"],
                               command=self.update_preview).pack(fill="x", padx=10, pady=10)
                               
        # Text Scales & Offsets
        ctk.CTkLabel(scroll, text="Title Size", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 0), padx=10)
        self.title_scale = ctk.CTkSlider(scroll, from_=0.5, to=2.0, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.title_scale.set(1.0)
        self.title_scale.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Title Y-Offset", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(5, 0), padx=10)
        self.title_y = ctk.CTkSlider(scroll, from_=-0.5, to=0.5, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.title_y.set(0.0)
        self.title_y.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Labels Size", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 0), padx=10)
        self.label_scale = ctk.CTkSlider(scroll, from_=0.5, to=2.0, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.label_scale.set(1.0)
        self.label_scale.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Labels Y-Offset", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(5, 0), padx=10)
        self.label_y = ctk.CTkSlider(scroll, from_=-0.5, to=0.5, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.label_y.set(0.0)
        self.label_y.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Status Size", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(15, 0), padx=10)
        self.status_scale = ctk.CTkSlider(scroll, from_=0.5, to=2.0, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.status_scale.set(1.0)
        self.status_scale.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(scroll, text="Status Y-Offset", font=("Helvetica", 13), text_color=("#111111", "#EEEEEE")).pack(anchor="w", pady=(5, 0), padx=10)
        self.status_y = ctk.CTkSlider(scroll, from_=-0.5, to=0.5, command=self.update_preview, button_color=self.C["accent"], button_hover_color="#deba7e")
        self.status_y.set(0.0)
        self.status_y.pack(fill="x", padx=10, pady=(0, 15))
        
        self.show_title_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Show Song Title", variable=self.show_title_var, text_color=("#111111", "#EEEEEE"),
                        command=self.update_preview,
                        fg_color=self.C["accent"], hover_color=self.C["accent"]).pack(anchor="w", pady=4, padx=10)
                        
        self.show_labels_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Show Note Labels", variable=self.show_labels_var, text_color=("#111111", "#EEEEEE"),
                        command=self.update_preview,
                        fg_color=self.C["accent"], hover_color=self.C["accent"]).pack(anchor="w", pady=4, padx=10)
                        
        self.show_status_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(scroll, text="Show Bottom Status", variable=self.show_status_var, text_color=("#111111", "#EEEEEE"),
                        command=self.update_preview,
                        fg_color=self.C["accent"], hover_color=self.C["accent"]).pack(anchor="w", pady=4, padx=10)
                        
        # Export Button
        self.export_btn = ctk.CTkButton(self.left_panel, text="Render Video", height=40, font=("Helvetica", 16, "bold"),
                                        fg_color=self.C["accent"], text_color="#0d1117", hover_color="#deba7e",
                                        command=self.start_export)
        self.export_btn.pack(side="bottom", fill="x", padx=20, pady=20)
        
        self.prog_bar = ctk.CTkProgressBar(self.left_panel, progress_color=self.C["green"])
        self.prog_bar.set(0)
        
        self.prog_lbl = ctk.CTkLabel(self.left_panel, text="", font=("Helvetica", 12))
        
    def _build_right_panel(self):
        # Canvas Container
        self.canvas_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.canvas_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.preview_lbl = ctk.CTkLabel(self.canvas_frame, text="")
        self.preview_lbl.pack(expand=True)
        
        # Controls
        ctrl_frame = ctk.CTkFrame(self.right_panel, height=60, fg_color=self.C["card"])
        ctrl_frame.pack(fill="x", side="bottom")
        
        self.play_btn = ctk.CTkButton(ctrl_frame, text="▶ Play Preview", width=120,
                                      fg_color=self.C["accent"], text_color="#0d1117", hover_color="#deba7e",
                                      command=self.toggle_playback)
        self.play_btn.pack(side="left", padx=20, pady=15)
        
        self.time_slider = ctk.CTkSlider(ctrl_frame, from_=0, to=100, command=self.on_slider_change,
                                         button_color=self.C["accent"], button_hover_color="#deba7e")
        self.time_slider.set(0)
        self.time_slider.pack(side="left", fill="x", expand=True, padx=20)
        
        self.time_lbl = ctk.CTkLabel(ctrl_frame, text="0.0s / 0.0s", width=80)
        self.time_lbl.pack(side="right", padx=20)
        
        self.canvas_frame.bind("<Configure>", self.on_resize)
        
    def on_format_change(self, *args):
        self.update_preview()
        
    def _browse_path(self):
        directory = ctk.filedialog.askdirectory(initialdir=self.path_var.get(), title="Select Export Folder")
        if directory:
            self.path_var.set(directory)
        
    def on_resize(self, event):
        if event.widget == self.canvas_frame:
            if hasattr(self, '_resize_job') and self._resize_job:
                self.after_cancel(self._resize_job)
            self._resize_job = self.after(100, self.update_preview)
            
    def _build_timeline_data(self, *args):
        bpm_str = self.bpm_var.get().strip()
        try:
            bpm = max(20, min(int(float(bpm_str)), 400))
        except (ValueError, TypeError):
            bpm = 120
        trem_speed_raw = self.editor.trem_speed_entry.get().strip()
        hits_per_sec = float(trem_speed_raw) if trem_speed_raw.replace('.','',1).isdigit() else 10.0
        
        score_text = self.editor._get_numeric_score_text()
        self.events = build_timeline(score_text, bpm, hits_per_sec, self.editor.current_sync_data)
        self.vid_dur = total_duration(self.events)
        self.time_slider.configure(to=max(0.1, self.vid_dur))
        
        # Precompute event_frames for quick lookup
        fps = 60
        self.event_frames = []
        for ev in self.events:
            f0 = int(ev.t_start * fps)
            f1 = max(f0 + 1, int((ev.t_start + ev.duration) * fps))
            self.event_frames.append((f0, f1, ev))
            
    def get_event_at_time(self, t):
        fi = int(t * 60)
        for f0, f1, ev in self.event_frames:
            if f0 <= fi < f1:
                return ev
        if self.events:
            last = self.events[-1]
            from core.video_exporter import VideoEvent
            return VideoEvent(last.t_start + last.duration, 0.001, None)
        return None

    def _get_preview_dims(self):
        fmt = self.format_var.get()
        cw = max(100, self.canvas_frame.winfo_width())
        ch = max(100, self.canvas_frame.winfo_height())
        
        if "16:9" in fmt:
            aspect = 16 / 9
        elif "9:16" in fmt:
            aspect = 9 / 16
        else:
            aspect = 1.0
            
        if cw / ch > aspect:
            # constrained by height
            ph = ch
            pw = int(ch * aspect)
        else:
            # constrained by width
            pw = cw
            ph = int(cw / aspect)
            
        return pw, ph

    def update_preview(self, *args):
        if not self.events:
            return
            
        t = self.time_offset
        ev = self.get_event_at_time(t)
        if not ev:
            return
            
        pw, ph = self._get_preview_dims()
        if pw < 50 or ph < 50:
            return
            
        dark_mode = self.theme_var.get() == "Dark"
        song_title = self.editor.title_entry.get().strip() if self.show_title_var.get() else ""
        
        # Render a single frame using the existing rendering engine
        frame_arr = render_frame(
            active_bar=ev.bar,
            active_left_bar=ev.left_bar,
            frame_t=t,
            event_t=ev.t_start,
            event_dur=ev.duration,
            W=pw,
            H=ph,
            dark_mode=dark_mode,
            song_title=song_title,
            two_mallets=self.editor.left_hand_var.get(),
            accent_hex=self.C["doc_accent"],
            view_mode=self.view_mode_var.get(),
            is_tremolo_hit=ev.is_tremolo_hit,
            sub_hit=ev.sub_hit,
            total_hits=ev.total_hits,
            title_scale=self.title_scale.get(),
            label_scale=self.label_scale.get(),
            status_scale=self.status_scale.get(),
            title_y_offset=self.title_y.get(),
            label_y_offset=self.label_y.get(),
            status_y_offset=self.status_y.get(),
            show_labels=self.show_labels_var.get(),
            show_status=self.show_status_var.get(),
        )
        
        img = Image.fromarray(frame_arr)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(pw, ph))
        self.preview_lbl.configure(image=ctk_img)
        self.preview_lbl.image = ctk_img  # Keep ref
        
        self.time_lbl.configure(text=f"{t:.1f}s / {self.vid_dur:.1f}s")

    def on_slider_change(self, val):
        self.time_offset = float(val)
        self._last_played_idx = -1
        for i, ev in enumerate(self.events):
            if ev.t_start >= self.time_offset:
                self._last_played_idx = i - 1
                break
        else:
            if self.events:
                self._last_played_idx = len(self.events) - 1
        self.update_preview()

    def toggle_playback(self):
        self.is_playing_preview = not self.is_playing_preview
        if self.is_playing_preview:
            # Sync audio engine with UI selection
            engine_str = "samples" if self.engine_var.get() == "Samples" else "adsr"
            if self.editor.player.mode != engine_str:
                self.editor.player.mode = engine_str
                # Force reload of C++ buffers for the newly selected engine mode
                import threading
                threading.Thread(target=self.editor.player.load_samples, daemon=True).start()
                
            self.play_btn.configure(text="⏸ Pause Preview")
            
            # Reset event tracker for audio sync
            self._last_played_idx = -1
            for i, ev in enumerate(self.events):
                if ev.t_start >= self.time_offset:
                    self._last_played_idx = i - 1
                    break
                    
            self._preview_loop()
        else:
            self.play_btn.configure(text="▶ Play Preview")

    def _preview_loop(self):
        if not self.is_playing_preview:
            return
            
        self.time_offset += 1.0 / 30.0  # simulate 30fps playback in UI
        
        # Audio Triggering
        if hasattr(self, '_last_played_idx') and self.events:
            idx = self._last_played_idx + 1
            two_mallets = self.editor.left_hand_var.get()
            
            while idx < len(self.events):
                ev = self.events[idx]
                if ev.t_start <= self.time_offset:
                    if ev.bar is not None:
                        self.editor.player.audio_core.trigger_note(ev.bar)
                        if two_mallets:
                            # Use ev.left_bar if explicitly set, otherwise default to bar+7
                            lh = ev.left_bar if ev.left_bar is not None else ev.bar + 7
                            if lh <= 21:
                                self.editor.player.audio_core.trigger_note(lh)
                    idx += 1
                    self._last_played_idx = idx - 1
                else:
                    break
        
        if self.time_offset >= self.vid_dur:
            self.time_offset = 0
            self.is_playing_preview = False
            self.play_btn.configure(text="▶ Play Preview")
            self.time_slider.set(0)
            self.update_preview()
            return
            
        self.time_slider.set(self.time_offset)
        self.update_preview()
        
        self.preview_job = self.after(33, self._preview_loop)

    def start_export(self):
        self.is_playing_preview = False
        self.play_btn.configure(text="▶ Play Preview")
        
        import os
        filename = self.filename_var.get().strip()
        if not filename:
            filename = "roneat_export.mp4"
        elif not filename.endswith(".mp4"):
            filename += ".mp4"
            
        out_dir = self.path_var.get().strip()
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir, exist_ok=True)
            except Exception:
                from pathlib import Path
                out_dir = str(Path.home() / "Downloads")
                
        filepath = os.path.join(out_dir, filename)
            
        res_str = self.res_var.get()
        fmt_str = self.format_var.get()
        if "16:9" in fmt_str:
            aspect = 16 / 9
        elif "9:16" in fmt_str:
            aspect = 9 / 16
        else:
            aspect = 1.0
            
        if res_str == "720p":
            h = 720
        elif res_str == "1080p":
            h = 1080
        else:
            h = 2160
            
        w = int(h * aspect)
        w = w - (w % 2) # ensure even width for ffmpeg
        
        fps = 30 if "30" in self.fps_var.get() else 60
        bpm_str = self.bpm_var.get().strip()
        try:
            bpm = max(20, min(int(float(bpm_str)), 400))
        except (ValueError, TypeError):
            bpm = 120
        
        opts = {
            "W": w,
            "H": h,
            "FPS": fps,
            "score": self.editor._get_numeric_score_text(),
            "bpm": bpm,
            "hits_per_sec": float(self.editor.trem_speed_entry.get().strip() if self.editor.trem_speed_entry.get().replace('.','',1).isdigit() else 10.0),
            "two_mal": self.editor.left_hand_var.get(),
            "accent_col": self.C["doc_accent"],
            "song_title_raw": self.editor.title_entry.get().strip() if self.show_title_var.get() else "",
            "view_mode": self.view_mode_var.get(),
            "dark_mode": self.theme_var.get() == "Dark",
            "title_scale": self.title_scale.get(),
            "label_scale": self.label_scale.get(),
            "status_scale": self.status_scale.get(),
            "title_y_offset": self.title_y.get(),
            "label_y_offset": self.label_y.get(),
            "status_y_offset": self.status_y.get(),
            "show_labels": self.show_labels_var.get(),
            "show_status": self.show_status_var.get(),
            "engine": "samples" if self.engine_var.get() == "Samples" else "synth"
        }
        
        self.export_btn.configure(text="Rendering...", state="disabled")
        self.prog_bar.pack(side="bottom", fill="x", padx=20, pady=(0, 10))
        self.prog_lbl.pack(side="bottom", pady=5)
        self.prog_bar.set(0)
        self.prog_lbl.configure(text="Preparing...")
        
        threading.Thread(target=self._export_worker, args=(filepath, opts), daemon=True).start()
        
    def _export_worker(self, filepath, opts):
        try:
            import os
            import sys
            import shutil
            from core.parse_score import expand_score
            from core.audio_player import RoneatPlayer
            from core.file_manager import load_hz_preset
            
            beat_sec = 60.0 / max(opts["bpm"], 1)
            dt_hit   = 1.0 / max(1.0, opts["hits_per_sec"])
            
            events_mp4 = expand_score(opts["score"])
            tokens = []
            durations = []
            
            for ev in events_mp4:
                if ev['bar'] is None:
                    tokens.append("-")
                    dur = beat_sec
                    durations.append(dur)
                    continue
                    
                if self.editor.current_sync_data:
                    dur = beat_sec
                else:
                    if ev['is_tremolo']:
                        dur = ev['repeat'] * dt_hit
                    else:
                        dur = beat_sec * ev['beats']
                        
                # Build token preserving explicit left-hand bar if set
                bar = ev['bar']
                left_bar = ev.get('left_bar')  # May be None or explicit value
                default_lh = min(bar + 7, 21)
                has_custom_lh = (left_bar is not None and left_bar != default_lh)
                
                if ev['is_tremolo']:
                    if has_custom_lh:
                        tok = f"({left_bar}){bar}#{ev['repeat']}"
                    else:
                        tok = f"{bar}#{ev['repeat']}"
                else:
                    if has_custom_lh:
                        tok = f"({left_bar}){bar}"
                    else:
                        tok = str(bar)
                tokens.append(tok)
                durations.append(dur)
                
            self.after(0, lambda: self.prog_lbl.configure(text="Synthesising audio..."))
            render_player = RoneatPlayer(load_hz_preset(), mode=opts["engine"],
                                         instrument_plugin=self.editor._get_active_instrument_plugin())
            if opts["engine"] == "samples":
                render_player.load_samples()
                
            audio_arr = render_player.render_score_to_array(
                tokens, durations, two_mallets=opts["two_mal"], hits_per_sec=opts["hits_per_sec"])
            audio_rate = render_player.sample_rate
            
            self.after(0, lambda: self.prog_lbl.configure(text="Rendering frames..."))
            
            def _find_ffmpeg():
                if getattr(sys, 'frozen', False):
                    exe_dir = os.path.dirname(sys.executable)
                    for name in ("ffmpeg.exe", "ffmpeg"):
                        c = os.path.join(exe_dir, name)
                        if os.path.exists(c): return c
                dev = os.path.normpath(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "..", "..", "ffmpeg.exe"))
                if os.path.exists(dev): return dev
                found = shutil.which("ffmpeg")
                return found if found else "ffmpeg"
                
            def _progress(frac, label):
                self.after(0, lambda p=frac, lbl=label: (
                    self.prog_bar.set(p),
                    self.prog_lbl.configure(text=lbl)))
                    
            export_mp4(
                filepath=filepath,
                score_text=opts["score"],
                bpm=opts["bpm"],
                hits_per_sec=opts["hits_per_sec"],
                audio_arr=audio_arr,
                audio_rate=audio_rate,
                dark_mode=opts["dark_mode"],
                song_title=opts["song_title_raw"],
                two_mallets=opts["two_mal"],
                accent_hex=opts["accent_col"],
                view_mode=opts["view_mode"],
                sync_data=self.editor.current_sync_data,
                ffmpeg_bin=_find_ffmpeg(),
                progress_cb=_progress,
                W=opts["W"],
                H=opts["H"],
                FPS=opts["FPS"],
                title_scale=opts["title_scale"],
                label_scale=opts["label_scale"],
                status_scale=opts["status_scale"],
                title_y_offset=opts["title_y_offset"],
                label_y_offset=opts["label_y_offset"],
                status_y_offset=opts["status_y_offset"],
                show_labels=opts["show_labels"],
                show_status=opts["show_status"]
            )
            
            self.after(0, lambda: self._export_done(True, "Video exported successfully!"))
        except Exception as e:
            import traceback; traceback.print_exc()
            self.after(0, lambda err=str(e): self._export_done(False, f"Error: {err}"))
            
    def _export_done(self, success, msg):
        self.prog_bar.set(1.0 if success else 0.0)
        self.prog_lbl.configure(text=msg, text_color=self.C["green"] if success else self.C["accent2"])
        txt = "✓ Video exported!" if success else "Export failed"
        col = self.C["green"] if success else self.C["accent2"]
        self.export_btn.configure(
            text=txt,
            fg_color=col if success else "transparent",
            text_color="#0d1117" if success else col,
            state="normal"
        )
        self.after(3500, lambda: (
            self.export_btn.configure(
                text="Render Video", fg_color=self.C["accent"],
                text_color="#0d1117", state="normal"),
            self.prog_bar.pack_forget(),
            self.prog_lbl.pack_forget(),
            self.prog_bar.set(0)
        ))
