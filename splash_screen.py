"""
splash_screen.py  v2.5
======================
Roneat Studio Pro — Animated Splash Screen

Redesigned to match the exact visual identity of the main app:
  - Dynamic Theme Support (Dark & Light modes depending on user settings)
  - Centered golden spinner animation
  - Centered progress bar with glowing highlights
  - Roneat instrument silhouette acting as a subtle backdrop

Usage:
    from splash_screen import show_splash, set_progress, close_splash
    splash = show_splash()
    set_progress(0.5, "Loading libraries...")
    close_splash()
"""

import tkinter as tk
import time
import os
import ctypes

try:
    from core.file_manager import load_app_settings
except ImportError:
    # Fallback if run standalone
    def load_app_settings():
        return {"theme": "Dark"}


# ── Public API ────────────────────────────────────────────────────────────────

_splash_win   = None
_progress_var = None
_stage_var    = None
_anim_job     = None
_angle        = 0

def show_splash():
    """Create and display the splash screen. Call before creating MainWindow."""
    global _splash_win, _progress_var, _stage_var, _anim_job, _angle
    
    if _splash_win is not None:
        return _splash_win

    _splash_win   = tk.Tk()
    _progress_var = tk.DoubleVar(value=0.0)
    _stage_var    = tk.StringVar(value="Starting...")
    _angle        = 0
    _anim_job     = None

    _build(_splash_win)
    _splash_win.update()
    return _splash_win

def set_progress(fraction: float, label: str = ""):
    """Update progress bar (0.0-1.0) and stage label."""
    global _splash_win, _progress_var, _stage_var
    if _splash_win is None:
        return
    try:
        _progress_var.set(max(0.0, min(fraction, 1.0)))
        if label:
            _stage_var.set(label)
        _splash_win.update()
    except Exception:
        pass

def close_splash():
    """Destroy the splash window."""
    global _splash_win, _anim_job
    if _splash_win is None:
        return
    try:
        if _anim_job:
            _splash_win.after_cancel(_anim_job)
        _splash_win.destroy()
    except Exception:
        pass
    _splash_win = None
    _anim_job = None

# ── Dynamic Theme Palettes ───────────────────────────────────────────────────

W, H = 640, 420  # Slightly larger for a more premium, spacious feel

def _get_theme_palette():
    """Determine the correct color palette based on app settings."""
    theme_setting = load_app_settings().get("theme", "Dark").lower()
    
    # If set to system, try to detect windows theme, default to dark if not possible
    if theme_setting == "system":
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            theme_setting = "light" if value == 1 else "dark"
        except Exception:
            theme_setting = "dark"

    is_dark = (theme_setting == "dark")

    return {
        "bg":       "#0d1117" if is_dark else "#f4f5f7",
        "card":     "#161b22" if is_dark else "#ffffff",
        "border":   "#30363d" if is_dark else "#e1e4e8",
        "accent":   "#c8a96e",  # Gold remains the same in both
        "accent2":  "#a07828" if is_dark else "#e8d090",
        "accent3":  "#deba7e" if is_dark else "#b5955a",
        "text":     "#e6edf3" if is_dark else "#24292f",
        "text_dim": "#8b949e" if is_dark else "#6e7781",
        "rail":     "#3a4f68" if is_dark else "#aeb5bd",
        "bar_f":    "#4a6080" if is_dark else "#d1d5da",
        "bar_s":    "#3a4f68" if is_dark else "#babbc0",
        "track":    "#1e2330" if is_dark else "#e1e4e8",
        "glow":     "#161b22" if is_dark else "#f0f2f4",
    }


# ── Internal build ────────────────────────────────────────────────────────────

def _build(root: tk.Tk):
    global _anim_job, _angle

    C = _get_theme_palette()

    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=C["bg"])
    root.resizable(False, False)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw-W)//2}+{(sh-H)//2}")

    # ── Main canvas ───────────────────────────────────────────────────────────
    cv = tk.Canvas(root, width=W, height=H, bg=C["bg"], highlightthickness=0)
    cv.pack(fill="both", expand=True)

    # Card background
    cv.create_rectangle(12, 12, W-12, H-12, fill=C["card"], outline=C["border"], width=1)
    
    # Inner subtle border layout
    cv.create_rectangle(18, 18, W-18, H-18, fill="", outline=C["border"], width=1, dash=(5, 5))

    # Gold top accent stripe (matching main app sidebar)
    cv.create_rectangle(12, 12, W-12, 16, fill=C["accent"], outline="")

    # ── Background Silhouette (Roneat Instrument) ─────────────────────────
    # We draw the Roneat bars as a faint background pattern
    N = 21
    r_x0   = 50
    r_x1   = W - 50
    r_y    = 45
    r_h    = 6
    r_w    = r_x1 - r_x0
    bar_gap = 4
    bar_bw  = (r_w - bar_gap * (N - 1)) / N
    min_bh  = 30
    max_bh  = 90

    # Rail
    cv.create_rectangle(r_x0 - 8, r_y, r_x1 + 8, r_y + r_h, fill=C["rail"], outline="")

    for i in range(N):
        t       = i / (N - 1)
        bh      = max_bh - t * (max_bh - min_bh)
        bx0     = r_x0 + i * (bar_bw + bar_gap)
        bx1     = bx0 + bar_bw
        by0     = r_y + r_h
        by1     = by0 + bh
        bcx     = (bx0 + bx1) / 2

        # Face
        face_color = C["accent"] if i % 7 == 0 else C["bar_f"]
        cv.create_rectangle(bx0, by0, bx1, by1, fill=face_color, outline="", stipple="gray50")
        
        # Strip
        sw2 = max(1, bar_bw * 0.22)
        cv.create_rectangle(bx0, by0, bx0 + sw2, by1, fill=C["bar_s"], outline="")

        # Resonator dot
        tr = max(2, min(bar_bw * 0.35, 4))
        tcy = by1 + tr + 6
        tc  = C["accent"] if i % 7 == 0 else C["rail"]
        cv.create_oval(bcx - tr, tcy - tr, bcx + tr, tcy + tr, fill=tc, outline="", stipple="gray50")

    # ── Foreground Content ───────────────────────────────────────────────────

    # --- Spinner Canvas centered ---
    SPW     = 80
    spin_cx = W // 2
    spin_cy = H // 2 - 30
    spin_cv = tk.Canvas(cv, width=SPW, height=SPW, bg=C["card"], highlightthickness=0)
    cv.create_window(spin_cx, spin_cy, window=spin_cv)

    # --- App Name and Subtitle ---
    cv.create_text(W // 2, spin_cy + 65,
                   text="Roneat Studio",
                   font=("Georgia", 24, "bold"),
                   fill=C["text"], anchor="center")
    
    cv.create_text(W // 2, spin_cy + 95,
                   text="PRO",
                   font=("Courier", 10, "bold"),
                   fill=C["accent"], anchor="center")

    cv.create_text(W // 2, spin_cy + 115,
                   text="Professional Roneat Ek Score Editor",
                   font=("Courier", 10),
                   fill=C["text_dim"], anchor="center")

    # --- Stage label ---
    stage_lbl = tk.Label(cv, textvariable=_stage_var,
                         bg=C["card"], fg=C["text_dim"],
                         font=("Courier", 11, "italic"))
    cv.create_window(W // 2, H - 75, window=stage_lbl)

    # --- Progress bar (Centered at bottom) ---
    BAR_W  = int(W * 0.6)
    BAR_X1 = (W - BAR_W) // 2
    BAR_Y1 = H - 55
    BAR_X2 = BAR_X1 + BAR_W
    BAR_Y2 = BAR_Y1 + 8

    # Track
    cv.create_rectangle(BAR_X1, BAR_Y1, BAR_X2, BAR_Y2, fill=C["track"], outline="")
    # Track glow
    cv.create_rectangle(BAR_X1-2, BAR_Y1-2, BAR_X2+2, BAR_Y2+2, fill="", outline=C["glow"], width=1)

    # Fill rect
    bar_fill = cv.create_rectangle(BAR_X1, BAR_Y1, BAR_X1, BAR_Y2, fill=C["accent"], outline="")
    
    # Shimmer slide
    shimmer = cv.create_rectangle(BAR_X1, BAR_Y1, BAR_X1, BAR_Y2, fill=C["accent3"], outline="")

    # Top highlight line
    bar_hi = cv.create_rectangle(BAR_X1, BAR_Y1, BAR_X1, BAR_Y1 + 2, fill="#ffeebb", outline="")

    # --- Percentage ---
    pct_var = tk.StringVar(value="0%")
    pct_lbl = tk.Label(cv, textvariable=pct_var,
                       bg=C["card"], fg=C["accent"],
                       font=("Courier", 11, "bold"))
    cv.create_window(W // 2 + BAR_W // 2 + 30, H - 51, window=pct_lbl)

    # --- Footer ---
    cv.create_text(W // 2, H - 25,
                   text="v2.5  ·  © 2026 Angel Vision Labs",
                   font=("Courier", 9),
                   fill=C["text_dim"])

    # ── Animation Loop ───────────────────────────────────────────────────────
    def _animate():
        global _angle, _anim_job

        # --- Spinner Arc ---
        spin_cv.delete("all")
        cx_s = SPW // 2
        r_s  = SPW // 2 - 6
        # Background ring
        spin_cv.create_arc(cx_s - r_s, cx_s - r_s, cx_s + r_s, cx_s + r_s,
                           start=0, extent=359, style="arc",
                           outline=C["border"], width=4)
        # Golden moving arc
        spin_cv.create_arc(cx_s - r_s, cx_s - r_s, cx_s + r_s, cx_s + r_s,
                           start=_angle % 360, extent=220,
                           style="arc", outline=C["accent"], width=5)
                           
        # Inner smaller ring spinning opposite way
        r_i = r_s - 10
        spin_cv.create_arc(cx_s - r_i, cx_s - r_i, cx_s + r_i, cx_s + r_i,
                           start=(360 - (_angle * 1.5)) % 360, extent=100,
                           style="arc", outline=C["accent2"], width=2)

        _angle = (_angle + 6) % 360

        # --- Progress Bar Update ---
        pct = _progress_var.get()
        fill_x = BAR_X1 + int(pct * BAR_W)
        cv.coords(bar_fill, BAR_X1, BAR_Y1, max(BAR_X1, fill_x), BAR_Y2)
        cv.coords(bar_hi,   BAR_X1, BAR_Y1, max(BAR_X1, fill_x), BAR_Y1 + 2)

        # --- Shimmer Animation ---
        t_ms = int(time.time() * 1000)
        dur  = 1200
        shim_pos = BAR_X1 + int((t_ms % dur) / dur * max(fill_x - BAR_X1, 1))
        shim_end = min(shim_pos + 50, fill_x)
        if shim_end > shim_pos + 2:
            cv.coords(shimmer, shim_pos, BAR_Y1, shim_end, BAR_Y2)
        else:
            cv.coords(shimmer, BAR_X1, BAR_Y1, BAR_X1, BAR_Y2)

        pct_var.set(f"{int(pct * 100)}%")

        try:
            _anim_job = root.after(30, _animate)
        except Exception:
            pass

    _animate()


if __name__ == "__main__":
    # Test block to preview the splash screen standalone
    # Set Windows DPI awareness if testing standalone
    try:
         ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
         pass

    splash = show_splash()
    
    # Simulate loading process
    import time as t
    
    stages = [
        "Loading audio engines...", 
        "Loading Roneat presets...", 
        "Initializing Score Editor...", 
        "Preparing AI modules...", 
        "Ready."
    ]
    
    for i in range(101):
        idx = min(i // 20, len(stages) - 1)
        set_progress(i / 100.0, stages[idx])
        t.sleep(0.04)
        
    t.sleep(0.5)
    close_splash()