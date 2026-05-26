"""
core/video_exporter.py  v2.0
=============================
Roneat Studio Pro — MP4 Video Export Engine

Architecture (strictly separated):
  1. build_timeline()     — Pure math: token → timed event list.
  2. render_frame()       — Pure drawing: PIL image from event state.
  3. export_mp4()         — Orchestration: renders frames → ffmpeg mux.

Bug fixes vs. v1:
  - Speed bug fixed: beat_sec = 60.0 / BPM used consistently.
  - Tremolo bug fixed: each sub-hit gets its own timed event row
    so the visual animates sequentially, not as a chord.
  - FPS raised to 60 for smooth scrolling.
  - Premium dark-mode visuals: glow effects, rounded rects, gradients.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# ─── Token regex (mirrors audio_player._parse_token) ──────────────────────────
_TOK_RE = re.compile(r'^(\d+)(#(\d+))?$')
_LEFT_RIGHT_RE = re.compile(r'^\((\d+)\)(\d+)(#(\d+))?$')
_RESTS  = {'-', '0', 'x'}

# ─── Video constants ───────────────────────────────────────────────────────────
FPS    = 60
WIDTH  = 1920
HEIGHT = 1080
N_BARS = 21


# ─────────────────────────────────────────────────────────────────────────────
# 1. TIMELINE MATH
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class VideoEvent:
    """One atomic visual/audio event on the export timeline."""
    t_start:   float          # absolute start time in seconds
    duration:  float          # how long this event lasts in seconds
    bar:       Optional[int]  # 1-21, or None for rest/silence
    left_bar:  Optional[int] = None # 1-21, explicitly set or auto-calc
    is_tremolo_hit: bool = False   # True only for individual sub-hits of a tremolo
    sub_hit:   int   = 0          # which sub-hit within the tremolo (0-indexed)
    total_hits: int  = 1          # total sub-hits in parent tremolo


def _build_timeline_impl(
    score_text: str,
    bpm: int,
    hits_per_sec: float,
    sync_data: Optional[list] = None,
    tail_sec: float = 2.0,
) -> list[VideoEvent]:
    """
    Convert a Roneat score string into a flat list of VideoEvents.

    Parameters
    ----------
    score_text  : raw notation (e.g. "9 8 7#3 - / 5 6")
    bpm         : beats per minute (20–400)
    hits_per_sec: tremolo speed in Hz (default 10–16)
    sync_data   : optional list of {'note': str, 'time': float}
    tail_sec    : silence padding appended at the end

    Timeline contract
    -----------------
    - Normal note  : occupies exactly 60/BPM seconds.
    - Rest (-, 0)  : occupies exactly 60/BPM seconds, bar=None.
    - Tremolo N#K  : produces K sub-events, each lasting 1/hits_per_sec seconds,
                     so total tremolo wall-time = K / hits_per_sec seconds.
    - Audio and video BOTH use the same dt, guaranteeing sync.
    """
    bpm      = max(20, min(int(bpm), 400))
    beat_sec = 60.0 / bpm
    dt_hit   = 1.0 / max(1.0, hits_per_sec)

    events: list[VideoEvent] = []
    cursor = 0.0  # current absolute wall-clock position

    if sync_data:
        # Sync-data path: use real timestamps from audio analysis
        t0 = sync_data[0]['time'] if sync_data else 0.0
        for i, item in enumerate(sync_data):
            t_abs = item['time'] - t0
            t_next_abs = (sync_data[i + 1]['time'] - t0
                          if i + 1 < len(sync_data)
                          else t_abs + beat_sec)
            slot_dur = max(0.05, t_next_abs - t_abs)

            tok = str(item.get('note', '-'))
            if tok == '/' or tok == '_':
                continue
            if tok in _RESTS:
                events.append(VideoEvent(t_abs, slot_dur, None, None))
                continue

            m_lr = _LEFT_RIGHT_RE.match(tok)
            if m_lr:
                left_bar = int(m_lr.group(1))
                bar = int(m_lr.group(2))
                if not (1 <= bar <= N_BARS) or not (1 <= left_bar <= N_BARS):
                    events.append(VideoEvent(t_abs, slot_dur, None, None))
                    continue

                if m_lr.group(3):  # tremolo
                    repeat = max(1, min(int(m_lr.group(4) or 1), 32))
                    sub_dt = slot_dur / repeat
                    for h in range(repeat):
                        events.append(VideoEvent(
                            t_start=t_abs + h * sub_dt,
                            duration=sub_dt,
                            bar=bar,
                            left_bar=left_bar,
                            is_tremolo_hit=True,
                            sub_hit=h,
                            total_hits=repeat,
                        ))
                else:
                    events.append(VideoEvent(t_abs, slot_dur, bar, left_bar))
                continue

            m = _TOK_RE.match(tok)
            if m:
                bar = int(m.group(1))
                if not (1 <= bar <= N_BARS):
                    events.append(VideoEvent(t_abs, slot_dur, None, None))
                    continue

                if m.group(2):  # tremolo
                    repeat = max(1, min(int(m.group(3) or 1), 32))
                    sub_dt = slot_dur / repeat
                    for h in range(repeat):
                        events.append(VideoEvent(
                            t_start=t_abs + h * sub_dt,
                            duration=sub_dt,
                            bar=bar,
                            left_bar=bar + 7,
                            is_tremolo_hit=True,
                            sub_hit=h,
                            total_hits=repeat,
                        ))
                else:
                    events.append(VideoEvent(t_abs, slot_dur, bar, bar + 7))
                continue

            events.append(VideoEvent(t_abs, slot_dur, None, None))
    else:
        # BPM path: pure math timeline
        for raw in score_text.replace('\n', ' ').split():
            if raw == '/':
                continue  # visual bar marker — no timing

            if raw == '_':
                continue

            if raw in _RESTS:
                events.append(VideoEvent(cursor, beat_sec, None))
                cursor += beat_sec
                continue

            m_lr = _LEFT_RIGHT_RE.match(raw)
            if m_lr:
                left_bar = int(m_lr.group(1))
                bar = int(m_lr.group(2))
                if not (1 <= bar <= N_BARS) or not (1 <= left_bar <= N_BARS):
                    events.append(VideoEvent(cursor, beat_sec, None, None))
                    cursor += beat_sec
                    continue

                if m_lr.group(3):  # tremolo
                    repeat    = max(1, min(int(m_lr.group(4) or 1), 32))
                    total_dur = repeat * dt_hit
                    for h in range(repeat):
                        events.append(VideoEvent(
                            t_start=cursor + h * dt_hit,
                            duration=dt_hit,
                            bar=bar,
                            left_bar=left_bar,
                            is_tremolo_hit=True,
                            sub_hit=h,
                            total_hits=repeat,
                        ))
                    cursor += total_dur
                else:
                    events.append(VideoEvent(cursor, beat_sec, bar, left_bar))
                    cursor += beat_sec
                continue

            m = _TOK_RE.match(raw)
            if not m:
                events.append(VideoEvent(cursor, beat_sec, None, None))
                cursor += beat_sec
                continue

            bar = int(m.group(1))
            if not (1 <= bar <= N_BARS):
                events.append(VideoEvent(cursor, beat_sec, None, None))
                cursor += beat_sec
                continue

            if m.group(2):  # tremolo  e.g.  9#3
                repeat    = max(1, min(int(m.group(3) or 1), 32))
                total_dur = repeat * dt_hit  # wall-clock for all sub-hits
                for h in range(repeat):
                    events.append(VideoEvent(
                        t_start=cursor + h * dt_hit,
                        duration=dt_hit,
                        bar=bar,
                        left_bar=bar + 7,
                        is_tremolo_hit=True,
                        sub_hit=h,
                        total_hits=repeat,
                    ))
                cursor += total_dur
            else:
                events.append(VideoEvent(cursor, beat_sec, bar, bar + 7))
                cursor += beat_sec

    # Tail silence so the last note has room to decay
    tail_start = max((e.t_start + e.duration for e in events), default=0.0)
    if tail_sec > 0:
        events.append(VideoEvent(tail_start, tail_sec, None))

    return events


def total_duration(events: list[VideoEvent]) -> float:
    """Return the wall-clock end time of the last event."""
    if not events:
        return 0.0
    last = events[-1]
    return last.t_start + last.duration


# ─────────────────────────────────────────────────────────────────────────────
# 2. FRAME RENDERER  (PIL-only, thread-safe)
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _lerp_color(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _glow_color(
    base: tuple[int, int, int],
    intensity: float,
) -> tuple[int, int, int]:
    """Brighten a colour by intensity ∈ [0, 1]."""
    return tuple(min(255, int(base[i] + (255 - base[i]) * intensity)) for i in range(3))


def _rounded_rect(draw, xy, radius, fill, outline=None, outline_width=2):
    """Draw a rounded rectangle using PIL ImageDraw."""
    from PIL import ImageDraw as _ID
    x0, y0, x1, y1 = xy
    r = max(1, radius)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                            outline=outline, width=outline_width)


def _try_font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = (
        ["C:/Windows/Fonts/LeelawUI.ttf",
         "C:/Windows/Fonts/KhmerUI.ttf",
         "C:/Windows/Fonts/DaunPenh.ttf",
         "arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf"]
        if bold else
        ["C:/Windows/Fonts/LeelawUI.ttf",
         "C:/Windows/Fonts/KhmerUI.ttf",
         "C:/Windows/Fonts/DaunPenh.ttf",
         "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _render_frame_impl(
    active_bar: Optional[int],
    active_left_bar: Optional[int],
    frame_t: float,
    event_t: float,
    event_dur: float,
    *,
    W: int = WIDTH,
    H: int = HEIGHT,
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
    """
    Render one HD video frame.

    Parameters
    ----------
    active_bar  : currently struck bar (1-21), or None for rest
    frame_t     : absolute timestamp of this frame in seconds
    event_t     : start time of the current event
    event_dur   : duration of the current event
    """
    from PIL import Image, ImageDraw, ImageFilter

    # ── Colour palette ─────────────────────────────────────────────────────
    if dark_mode:
        BG          = (10, 12, 18)
        RAIL        = (30, 36, 52)
        BAR_FACE    = (32, 42, 66)
        BAR_SHADE   = (20, 28, 48)
        TUBE        = (24, 32, 52)
        LABEL       = (80, 100, 140)
        LH_FACE     = (28, 72, 140)
        LH_SHADE    = (18, 52, 110)
        STATUS      = (170, 140, 75)
        TITLE_C     = (210, 178, 120)
        GRID_LINE   = (22, 28, 44)
    else:
        BG          = (242, 236, 215)
        RAIL        = (135, 115, 82)
        BAR_FACE    = (192, 172, 130)
        BAR_SHADE   = (155, 135, 95)
        TUBE        = (210, 196, 162)
        LABEL       = (90, 70, 38)
        LH_FACE     = (48, 95, 175)
        LH_SHADE    = (65, 125, 195)
        STATUS      = (108, 78, 22)
        TITLE_C     = (88, 58, 12)
        GRID_LINE   = (220, 210, 185)

    ACCENT = _hex_to_rgb(accent_hex)

    # ── Progress within the current event (0.0 → 1.0) ─────────────────────
    progress = (frame_t - event_t) / max(event_dur, 1e-6)
    progress = max(0.0, min(1.0, progress))

    # Hit flash: sharp spike at the moment of attack, then decay
    hit_flash = math.exp(-progress * 8.0)          # envelope: 1.0 at hit, → 0

    # ── Canvas ────────────────────────────────────────────────────────────
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Song title ────────────────────────────────────────────────────────
    title_h = 0
    if song_title:
        title_h = int(H * 0.1)
        tf_size = int(max(24, int(min(W, H) * 0.077)) * title_scale)
        tf = _try_font(tf_size, True)
        bb = draw.textbbox((0, 0), song_title, font=tf)
        tw = bb[2] - bb[0]
        draw.text(((W - tw) // 2, int(H * 0.033) + int(H * title_y_offset)), song_title,
                  fill=TITLE_C, font=tf)

    # ── Layout constants ──────────────────────────────────────────────────
    pad_x    = max(10, int(W * 0.057))
    gap      = max(2, int(W * 0.0036))
    bar_w    = (W - pad_x * 2 - gap * (N_BARS - 1)) / N_BARS
    rail_top = title_h + int(H * 0.11)
    rail_h   = max(8, int(H * 0.016))
    avail    = H - rail_top - rail_h - int(H * 0.14)
    max_bh_avail = int(avail * 0.80)
    ideal_max_bh = int(W * 0.35)
    max_bh   = min(max_bh_avail, ideal_max_bh)
    min_bh   = int(max_bh * 0.25)
    
    # Push the rail down if there's excess vertical space (portrait mode)
    extra_h = avail - max_bh
    if extra_h > 0:
        rail_top += int(extra_h * 0.4)

    # Rail (horizontal beam the bars hang from)
    draw.rounded_rectangle(
        [pad_x - 20, rail_top, W - pad_x + 20, rail_top + rail_h],
        radius=rail_h // 2,
        fill=RAIL,
    )

    # ── Bars (xylophone slabs) ────────────────────────────────────────────
    for i in range(N_BARS):
        bar_num = N_BARS - i       # 21 → 1 left to right
        t_pos   = i / (N_BARS - 1)
        bh      = int(max_bh - t_pos * (max_bh - min_bh))
        x0      = int(pad_x + i * (bar_w + gap))
        x1      = int(x0 + bar_w)
        y0      = rail_top + rail_h
        y1      = y0 + bh
        cx      = (x0 + x1) // 2
        bw_int  = max(1, x1 - x0)
        max_r   = min(bw_int // 2, bh // 2)
        r_slab  = max(1, min(max_r, int(bar_w * 0.14)))

        is_rh = (active_bar is not None and bar_num == active_bar)
        
        lh_target = active_left_bar if active_left_bar is not None else (active_bar + 7 if active_bar else None)
        is_lh = (two_mallets and lh_target is not None
                 and bar_num == lh_target
                 and bar_num <= N_BARS)

        # ── Slab body ─────────────────────────────────────────────────────
        face  = ACCENT  if is_rh else (LH_FACE  if is_lh else BAR_FACE)
        shade = tuple(max(0, c - 40) for c in ACCENT) if is_rh else (
                LH_SHADE if is_lh else BAR_SHADE)

        stripe_w = max(0, min(bw_int - 1, int(bar_w * 0.15)))
        if stripe_w == 0 and bw_int > 2:
            stripe_w = 1
        
        # Base shadow (covers the left)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=r_slab, fill=shade)
        # Face (shifted right)
        draw.rounded_rectangle([x0 + stripe_w, y0, x1, y1], radius=r_slab, fill=face)

        # Top highlight (metallic shimmer)
        shimmer_h = max(4, int(bh * 0.08)) if not is_rh else max(4, int(bh * 0.15))
        shimmer_t = (0.35 + 0.65 * hit_flash) if is_rh else 0.12
        shimmer_c = _lerp_color(face, (255, 255, 255), shimmer_t)
        margin = max(1, int(bar_w * 0.1))
        
        sx0 = x0 + stripe_w + margin
        sy0 = y0 + margin
        sx1 = x1 - margin
        sy1 = y0 + shimmer_h + margin
        
        sw = max(1, sx1 - sx0)
        sh = max(1, sy1 - sy0)
        s_r = max(1, min(sw // 2, sh // 2, r_slab - margin))
        
        if sx1 > sx0 and sy1 > sy0:
            draw.rounded_rectangle([sx0, sy0, sx1, sy1], radius=s_r, fill=shimmer_c)

        # ── Note label ────────────────────────────────────────────────────
        if show_labels:
            lbl_y  = y1 + max(8, int(H * 0.018)) + int(H * label_y_offset)
            lbl_sz = max(11, min(int(bar_w * 0.44), 22))
            if view_mode in ("Syllabic", "Letters"):
                lbl_sz = int(lbl_sz * 0.78)
            lbl_sz = int(lbl_sz * label_scale)
            lc     = ACCENT if is_rh else (LH_FACE if is_lh else LABEL)
            lf     = _try_font(lbl_sz, True)
    
            from core.rendering.translation import translate_note
            lbl_text = translate_note(bar_num, view_mode)
            bb2      = draw.textbbox((0, 0), lbl_text, font=lf)
            lbl_w    = bb2[2] - bb2[0]
            draw.text((cx - lbl_w // 2, lbl_y), lbl_text, fill=lc, font=lf)

    # ── Bottom status text ────────────────────────────────────────────────
    if show_status and active_bar and 1 <= active_bar <= N_BARS:
        from core.rendering.translation import translate_note
        rh_lbl = translate_note(active_bar, view_mode)
        lh_n   = active_left_bar if active_left_bar is not None else active_bar + 7
        if two_mallets and lh_n <= N_BARS:
            lh_lbl = translate_note(lh_n, view_mode)
            status = f"Right hand: {rh_lbl}     Left hand: {lh_lbl}"
        else:
            status = f"Bar: {rh_lbl}"
        if is_tremolo_hit:
            status += f"     (tremolo {sub_hit + 1}/{total_hits})"
        sf_size = int(max(12, int(min(W, H) * 0.048)) * status_scale)
        sf2 = _try_font(sf_size, True)
        bb3 = draw.textbbox((0, 0), status, font=sf2)
        sw  = bb3[2] - bb3[0]
        y_pos = int(H - H * 0.074) + int(H * status_y_offset)
        draw.text(((W - sw) // 2, y_pos), status, fill=STATUS, font=sf2)

    return np.array(img, dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORCHESTRATION
# ─────────────────────────────────────────────────────────────────────────────

def _export_mp4_impl(
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
    W: int = WIDTH,
    H: int = HEIGHT,
    FPS: int = FPS,
    title_scale: float = 1.0,
    label_scale: float = 1.0,
    status_scale: float = 1.0,
    title_y_offset: float = 0.0,
    label_y_offset: float = 0.0,
    status_y_offset: float = 0.0,
    show_labels: bool = True,
    show_status: bool = True,
) -> None:
    """
    Full MP4 export pipeline.

    Parameters
    ----------
    filepath    : output .mp4 path
    score_text  : raw notation string
    bpm         : beats per minute
    hits_per_sec: tremolo speed
    audio_arr   : pre-rendered audio (float32, mono)
    audio_rate  : audio sample rate in Hz
    progress_cb : optional callable(fraction: float, label: str)
    """
    import imageio
    import soundfile as sf

    # ── 1. Build timeline ─────────────────────────────────────────────────
    events = _build_timeline_impl(score_text, bpm, hits_per_sec, sync_data)
    vid_dur = total_duration(events)

    total_frames = max(1, int(vid_dur * FPS))

    # Build a lookup: frame index → VideoEvent
    # Pre-compute start_frame for each event
    event_frames: list[tuple[int, int, VideoEvent]] = []  # (f_start, f_end, event)
    for ev in events:
        f0 = int(ev.t_start * FPS)
        f1 = max(f0 + 1, int((ev.t_start + ev.duration) * FPS))
        event_frames.append((f0, f1, ev))

    def event_at_frame(fi: int) -> VideoEvent:
        """Find the event active at frame fi."""
        for f0, f1, ev in event_frames:
            if f0 <= fi < f1:
                return ev
        # Past the end — return the last event as rest
        last = events[-1]
        return VideoEvent(last.t_start + last.duration, 0.001, None)

    # ── 2. Write temp WAV ────────────────────────────────────────────────
    tmp_wav = filepath + "_tmp_audio.wav"
    sf.write(tmp_wav, audio_arr, audio_rate)

    # ── 3. Render frames → temp silent video ────────────────────────────
    tmp_video = filepath + "_tmp_video.mp4"
    writer = imageio.get_writer(
        tmp_video, fps=FPS, codec="libx264", macro_block_size=1,
        output_params=["-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p"])

    for fi in range(total_frames):
        ev      = event_at_frame(fi)
        frame_t = fi / FPS
        frame   = _render_frame_impl(
            active_bar=ev.bar,
            active_left_bar=ev.left_bar,
            frame_t=frame_t,
            event_t=ev.t_start,
            event_dur=ev.duration,
            dark_mode=dark_mode,
            song_title=song_title,
            two_mallets=two_mallets,
            accent_hex=accent_hex,
            view_mode=view_mode,
            is_tremolo_hit=ev.is_tremolo_hit,
            sub_hit=ev.sub_hit,
            total_hits=ev.total_hits,
            W=W,
            H=H,
            title_scale=title_scale,
            label_scale=label_scale,
            status_scale=status_scale,
            title_y_offset=title_y_offset,
            label_y_offset=label_y_offset,
            status_y_offset=status_y_offset,
            show_labels=show_labels,
            show_status=show_status,
        )
        writer.append_data(frame)

        if progress_cb and (fi % 30 == 0 or fi == total_frames - 1):
            progress_cb(fi / total_frames,
                        f"Frame {fi + 1}/{total_frames}")

    writer.close()

    # ── 4. Mux audio + video ──────────────────────────────────────────────
    if progress_cb:
        progress_cb(0.98, "Muxing audio + video...")

    cmd = [
        ffmpeg_bin, "-y",
        "-i", tmp_video,
        "-i", tmp_wav,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        filepath,
    ]
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    res = subprocess.run(cmd, capture_output=True, **kwargs)

    # Clean up temp files
    for tmp in (tmp_video, tmp_wav):
        try:
            os.remove(tmp)
        except Exception:
            pass

    if res.returncode != 0:
        err = res.stderr.decode(errors="ignore")[-600:]
        raise RuntimeError(f"ffmpeg failed:\n{err}")

    if progress_cb:
        progress_cb(1.0, "Done!")


# ─── Public API Delegating to C++ Engine / Fallback ──────────────────────────
from core.RoneatVideoCore import RoneatVideoCore
_core = RoneatVideoCore()

def build_timeline(*args, **kwargs):
    return _core.build_timeline(*args, **kwargs)

def render_frame(*args, **kwargs):
    return _core.render_frame(*args, **kwargs)

def export_mp4(*args, **kwargs):
    return _core.export_mp4(*args, **kwargs)
