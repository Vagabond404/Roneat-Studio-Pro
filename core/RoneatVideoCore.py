"""
core/RoneatVideoCore.py
======================
Python wrapper for the C++ Roneat Video Engine (pybind11 module).
Handles signature differences, font paths, and graceful fallback to Python PIL.
"""

import sys
import os
import numpy as np
from typing import Optional

# ─── Font Detection Helper ────────────────────────────────────────────────────
def find_system_font_path() -> str:
    """Find a suitable TrueType font for rendering labels (supporting English & Khmer)."""
    candidates = [
        "C:/Windows/Fonts/KhmerUI.ttf",
        "C:/Windows/Fonts/DaunPenh.ttf",
        "C:/Windows/Fonts/Nirmala.ttf",
        "C:/Windows/Fonts/LeelawUI.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/Arial.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Fallback to standard system directories or defaults
    if sys.platform == "darwin":
        osx_paths = [
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"
        ]
        for p in osx_paths:
            if os.path.exists(p):
                return p
    elif sys.platform.startswith("linux"):
        linux_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        for p in linux_paths:
            if os.path.exists(p):
                return p
    return "Arial.ttf"  # Let stb_truetype look in current directory or fail gracefully


# ─── Load C++ Video Core ──────────────────────────────────────────────────────
_cpp_module_available = False
_cpp_has_left_bar = False

try:
    try:
        from core import roneat_video_core
    except ImportError:
        import roneat_video_core
    
    _cpp_module_available = True
    # Check if render_frame signature includes active_left_bar
    doc = roneat_video_core.RoneatVideoEngine.render_frame.__doc__ or ""
    if "active_left_bar" in doc:
        _cpp_has_left_bar = True
except ImportError as e:
    print(f"[Warning] Could not import C++ video engine 'roneat_video_core': {e}", file=sys.stderr)
    print("[Warning] Falling back to Python Pillow/imageio rendering pipeline.", file=sys.stderr)


class RoneatVideoCore:
    def __init__(self):
        self.is_cpp_available = _cpp_module_available
        self.has_left_bar = _cpp_has_left_bar
        self.font_path = find_system_font_path()
        self._title_cache = {}
        
        if self.is_cpp_available:
            self._engine = roneat_video_core.RoneatVideoEngine()
        else:
            self._engine = None

    def _pre_render_title(self, song_title: str, W: int, H: int, title_scale: float, dark_mode: bool) -> Optional[np.ndarray]:
        if not song_title:
            return None
        
        from PIL import Image, ImageDraw, ImageFont
        
        # Select title color
        if dark_mode:
            TITLE_C = (210, 178, 120, 255)
        else:
            TITLE_C = (88, 58, 12, 255)
            
        tf_size = int(max(24, int(min(W, H) * 0.077)) * title_scale)
        
        # Load font
        try:
            tf = ImageFont.truetype(self.font_path, tf_size)
        except Exception:
            tf = ImageFont.load_default()
            
        # Create a dummy image to measure text size
        dummy = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), song_title, font=tf)
        tw = max(1, bbox[2] - bbox[0])
        th = max(1, bbox[3] - bbox[1])
        
        # Create transparent image for title
        title_img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(title_img)
        tdraw.text((-bbox[0], -bbox[1]), song_title, fill=TITLE_C, font=tf)
        
        return np.array(title_img, dtype=np.uint8)

    def build_timeline(self, score_text: str, bpm: int, hits_per_sec: float, sync_data: Optional[list] = None, tail_sec: float = 2.0):
        if self._engine:
            try:
                return self._engine.build_timeline(score_text, bpm, hits_per_sec, sync_data, tail_sec)
            except Exception as e:
                print(f"[RoneatVideoCore] C++ build_timeline failed, using Python fallback. Error: {e}", file=sys.stderr)
        
        # Fallback to Python implementation
        from core.video_exporter import _build_timeline_impl
        return _build_timeline_impl(score_text, bpm, hits_per_sec, sync_data, tail_sec)

    def render_frame(
        self,
        active_bar: Optional[int],
        active_left_bar: Optional[int] = None,
        frame_t: float = 0.0,
        event_t: float = 0.0,
        event_dur: float = 1.0,
        *,
        W: int = 1920,
        H: int = 1080,
        dark_mode: bool = True,
        song_title: str = "",
        two_mallets: bool = True,
        accent_hex: str = "#c8a96e",
        view_mode: str = "Numeric",
        is_tremolo_hit: bool = False,
        sub_hit: int = 0,
        total_hits: int = 1,
        title_scale: float = 1.0,
        label_scale: float = 1.0,
        status_scale: float = 1.0,
        title_y_offset: float = 0.0,
        label_y_offset: float = 0.0,
        status_y_offset: float = 0.0,
        show_labels: bool = True,
        show_status: bool = True,
    ) -> np.ndarray:
        if self._engine:
            try:
                # Pre-render the title using PIL for correct shaping (Khmer, etc.)
                title_img = None
                if song_title:
                    cache_key = (song_title, W, H, title_scale, dark_mode, self.font_path)
                    if cache_key in self._title_cache:
                        title_img = self._title_cache[cache_key]
                    else:
                        title_img = self._pre_render_title(song_title, W, H, title_scale, dark_mode)
                        self._title_cache[cache_key] = title_img

                if self.has_left_bar:
                    # New C++ signature supporting active_left_bar & title_img
                    return self._engine.render_frame(
                        active_bar,
                        active_left_bar,
                        frame_t,
                        event_t,
                        event_dur,
                        W, H,
                        dark_mode,
                        song_title,
                        two_mallets,
                        accent_hex,
                        view_mode,
                        is_tremolo_hit,
                        sub_hit,
                        total_hits,
                        title_scale,
                        label_scale,
                        status_scale,
                        title_y_offset,
                        label_y_offset,
                        status_y_offset,
                        show_labels,
                        show_status,
                        self.font_path,
                        title_img
                    )
                else:
                    # Old C++ signature (no active_left_bar parameter)
                    return self._engine.render_frame(
                        active_bar,
                        frame_t,
                        event_t,
                        event_dur,
                        W, H,
                        dark_mode,
                        song_title,
                        two_mallets,
                        accent_hex,
                        view_mode,
                        is_tremolo_hit,
                        sub_hit,
                        total_hits,
                        title_scale,
                        label_scale,
                        status_scale,
                        title_y_offset,
                        label_y_offset,
                        status_y_offset,
                        show_labels,
                        show_status,
                        self.font_path
                    )
            except Exception as e:
                print(f"[RoneatVideoCore] C++ render_frame failed, using Python fallback. Error: {e}", file=sys.stderr)
        
        # Fallback to Python implementation
        from core.video_exporter import _render_frame_impl
        return _render_frame_impl(
            active_bar,
            active_left_bar,
            frame_t,
            event_t,
            event_dur,
            W=W, H=H,
            dark_mode=dark_mode,
            song_title=song_title,
            two_mallets=two_mallets,
            accent_hex=accent_hex,
            view_mode=view_mode,
            is_tremolo_hit=is_tremolo_hit,
            sub_hit=sub_hit,
            total_hits=total_hits,
            title_scale=title_scale,
            label_scale=label_scale,
            status_scale=status_scale,
            title_y_offset=title_y_offset,
            label_y_offset=label_y_offset,
            status_y_offset=status_y_offset,
            show_labels=show_labels,
            show_status=show_status
        )

    def export_mp4(
        self,
        filepath: str,
        score_text: str,
        bpm: int,
        hits_per_sec: float,
        audio_arr: np.ndarray,
        audio_rate: int,
        *,
        dark_mode: bool = True,
        song_title: str = "",
        two_mallets: bool = True,
        accent_hex: str = "#c8a96e",
        view_mode: str = "Numeric",
        sync_data: Optional[list] = None,
        ffmpeg_bin: str = "ffmpeg",
        progress_cb=None,
        W: int = 1920,
        H: int = 1080,
        FPS: int = 60,
        title_scale: float = 1.0,
        label_scale: float = 1.0,
        status_scale: float = 1.0,
        title_y_offset: float = 0.0,
        label_y_offset: float = 0.0,
        status_y_offset: float = 0.0,
        show_labels: bool = True,
        show_status: bool = True,
    ) -> None:
        if self._engine:
            try:
                # Pre-render the title using PIL for correct shaping (Khmer, etc.)
                title_img = None
                if song_title:
                    cache_key = (song_title, W, H, title_scale, dark_mode, self.font_path)
                    if cache_key in self._title_cache:
                        title_img = self._title_cache[cache_key]
                    else:
                        title_img = self._pre_render_title(song_title, W, H, title_scale, dark_mode)
                        self._title_cache[cache_key] = title_img

                self._engine.export_mp4(
                    filepath,
                    score_text,
                    bpm,
                    hits_per_sec,
                    audio_arr.astype(np.float32),
                    audio_rate,
                    dark_mode,
                    song_title,
                    two_mallets,
                    accent_hex,
                    view_mode,
                    sync_data,
                    ffmpeg_bin,
                    progress_cb,
                    W, H, FPS,
                    title_scale,
                    label_scale,
                    status_scale,
                    title_y_offset,
                    label_y_offset,
                    status_y_offset,
                    show_labels,
                    show_status,
                    self.font_path,
                    title_img
                )
                return
            except Exception as e:
                print(f"[RoneatVideoCore] C++ export_mp4 failed, using Python fallback. Error: {e}", file=sys.stderr)
        
        # Fallback to Python implementation
        from core.video_exporter import _export_mp4_impl
        _export_mp4_impl(
            filepath=filepath,
            score_text=score_text,
            bpm=bpm,
            hits_per_sec=hits_per_sec,
            audio_arr=audio_arr,
            audio_rate=audio_rate,
            dark_mode=dark_mode,
            song_title=song_title,
            two_mallets=two_mallets,
            accent_hex=accent_hex,
            view_mode=view_mode,
            sync_data=sync_data,
            ffmpeg_bin=ffmpeg_bin,
            progress_cb=progress_cb,
            W=W, H=H, FPS=FPS,
            title_scale=title_scale,
            label_scale=label_scale,
            status_scale=status_scale,
            title_y_offset=title_y_offset,
            label_y_offset=label_y_offset,
            status_y_offset=status_y_offset,
            show_labels=show_labels,
            show_status=show_status
        )
