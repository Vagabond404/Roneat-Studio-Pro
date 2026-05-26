import sys
import os

with open("c:/Users/ange-/PycharmProjects/Roneat_Studio/ui/views/score_editor.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

s = -1
e = -1
for i, l in enumerate(lines):
    if l.startswith("    def _execute_mp4_export(self, opts):"):
        s = i
    if l.startswith("    def _mp4_done(self, success, msg):"):
        e = i
        break

if s != -1 and e != -1:
    new_code = """    def _execute_mp4_export(self, opts):
        raw_title = self.title_entry.get().strip()
        safe_name = "".join(ch for ch in raw_title if ch.isalnum() or ch in " _-").strip() or "roneat_video"

        from tkinter import filedialog
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
        opts["score"] = self._get_numeric_score_text()
        opts["bpm_raw"] = self.bpm_entry.get().strip()
        opts["two_mal"] = self.left_hand_var.get()
        opts["accent_col"] = self.C["doc_accent"]
        opts["song_title_raw"] = self.title_entry.get().strip()
        opts["view_mode"] = self.get_active_view_mode()

        self.export_mp4_btn.configure(text="Rendering...", state="disabled")
        self.mp4_prog_frame.pack(fill="x", padx=18, pady=(0, 14))
        self.mp4_prog_bar.set(0)
        self.mp4_progress_lbl.configure(text="Preparing...", text_color=self.C["text_dim"])

        import threading
        threading.Thread(
            target=self._mp4_worker, args=(filepath, opts), daemon=True).start()

    def _mp4_worker(self, filepath, opts):
        try:
            import os
            import shutil as _sh
            import sys as _sys
            from core.parse_score import expand_score
            from core.audio_player import RoneatPlayer, load_hz_preset

            show_title   = opts.get("show_title", True)
            dark_mode    = opts.get("dark_mode",  True)
            hits_per_sec = opts.get("hits_per_sec", 10.0)
            score        = opts.get("score", "")
            bpm_raw      = opts.get("bpm_raw", "120")
            bpm          = int(bpm_raw) if bpm_raw.isdigit() and 20 <= int(bpm_raw) <= 400 else 120
            two_mal      = opts.get("two_mal", True)
            accent_col   = opts.get("accent_col", "#c8a96e")
            song_title   = opts.get("song_title_raw", "") if show_title else ""
            view_mode    = opts.get("view_mode", "Numeric")

            beat_sec = 60.0 / max(bpm, 1)
            dt_hit   = 1.0 / max(1.0, hits_per_sec)

            events_mp4 = expand_score(score)
            tokens = []
            durations = []

            for ev in events_mp4:
                if ev['bar'] is None:
                    tokens.append("-")
                    dur = beat_sec
                    if self.current_sync_data:
                        dur = beat_sec
                    durations.append(dur)
                    continue

                if self.current_sync_data:
                    dur = beat_sec
                else:
                    if ev['is_tremolo']:
                        dur = ev['repeat'] * dt_hit
                    else:
                        dur = beat_sec * ev['beats']

                tok = f"{ev['bar']}#{ev['repeat']}" if ev['is_tremolo'] else str(ev['bar'])
                tokens.append(tok)
                durations.append(dur)

            if not any(t not in ('/', '-', '0', 'x') for t in tokens):
                self.after(0, lambda: self._mp4_done(False, "No notes to render."))
                return

            self.after(0, lambda: self.mp4_progress_lbl.configure(text="Synthesising audio..."))
            render_player = RoneatPlayer(load_hz_preset(), mode=self.player.mode,
                                         instrument_plugin=self._get_active_instrument_plugin())
            if self.player.mode == "samples":
                render_player.load_samples()

            audio_arr  = render_player.render_score_to_array(
                tokens, durations, two_mallets=two_mal, hits_per_sec=hits_per_sec)
            audio_rate = render_player.sample_rate

            self.after(0, lambda: self.mp4_progress_lbl.configure(text="Rendering frames..."))

            def _find_ffmpeg():
                if getattr(_sys, 'frozen', False):
                    exe_dir = os.path.dirname(_sys.executable)
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

            from core.video_exporter import export_mp4 as _vex

            def _progress(frac, label):
                self.after(0, lambda p=frac, lbl=label: (
                    self.mp4_prog_bar.set(p),
                    self.mp4_progress_lbl.configure(text=lbl)))

            _vex(
                filepath=filepath,
                score_text=score,
                bpm=bpm,
                hits_per_sec=hits_per_sec,
                audio_arr=audio_arr,
                audio_rate=audio_rate,
                dark_mode=dark_mode,
                song_title=song_title,
                two_mallets=two_mal,
                accent_hex=accent_col,
                view_mode=view_mode,
                sync_data=self.current_sync_data,
                ffmpeg_bin=_find_ffmpeg(),
                progress_cb=_progress,
            )

            self.after(0, lambda: self._mp4_done(True, "Video exported successfully!"))

        except Exception as e:
            import traceback; traceback.print_exc()
            self.after(0, lambda err=str(e): self._mp4_done(False, f"Error: {err}"))

"""
    lines[s:e] = [new_code]
    with open("c:/Users/ange-/PycharmProjects/Roneat_Studio/ui/views/score_editor.py", "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("SUCCESS: REPLACED mp4_worker")
else:
    print(f"FAILED: start={s}, end={e}")
