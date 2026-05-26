"""
splash_screen.py  v4.2
======================
Roneat Studio Pro — Premium Splash Screen
  - Shows the Roneat Studio Pro logo (PNG)
  - Reads the saved theme (Dark / Light / System) and matches the main app
  - Gold gradient progress bar at the bottom
  - Zero heavy dependencies (pure tkinter; PIL optional for logo)
"""

import tkinter as tk
import time
import ctypes
import os
from typing import Optional

try:
    from core.file_manager import load_app_settings
except ImportError:
    def load_app_settings():
        return {"theme": "Dark"}


# ── Public API ────────────────────────────────────────────────────────────────

_root        : Optional[tk.Tk]        = None
_progress_var: Optional[tk.DoubleVar] = None
_stage_var   : Optional[tk.StringVar] = None
_anim_job    : Optional[str]          = None


def show_splash() -> tk.Tk:
    """Create and display the splash screen. Call before any heavy imports."""
    global _root, _progress_var, _stage_var, _anim_job

    if _root is not None:
        return _root

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    _root         = tk.Tk()
    _progress_var = tk.DoubleVar(master=_root, value=0.0)
    _stage_var    = tk.StringVar(master=_root, value="")
    _anim_job     = None

    _build(_root)
    _root.update()
    return _root


def set_progress(fraction: float, label: str = "") -> None:
    """Update progress bar (0.0–1.0) and status label."""
    global _root, _progress_var, _stage_var
    if _root is None:
        return
    try:
        _progress_var.set(max(0.0, min(fraction, 1.0)))
        if label:
            _stage_var.set(label)
        _root.update()
    except Exception:
        pass


def close_splash() -> None:
    """Destroy the splash window."""
    global _root, _anim_job
    if _root is None:
        return
    try:
        if _anim_job:
            _root.after_cancel(_anim_job)
        _root.destroy()
    except Exception:
        pass
    _root     = None
    _anim_job = None

    import tkinter
    if getattr(tkinter, '_default_root', None) is not None:
        tkinter._default_root = None


# ── Theme resolution ──────────────────────────────────────────────────────────

def _resolve_theme() -> str:
    """Return 'dark' or 'light' based on saved app settings."""
    theme = load_app_settings().get("theme", "Dark").lower()

    if theme == "system":
        try:
            import winreg
            reg = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(
                reg,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "light" if val == 1 else "dark"
        except Exception:
            return "dark"

    return "dark" if theme == "dark" else "light"


# ── Palette ───────────────────────────────────────────────────────────────────

W, H = 520, 300


def _palette(dark: bool) -> dict:
    return {
        "bg":       "#0c0f14" if dark else "#f4f5f7",
        "text":     "#e8edf5" if dark else "#1a1a2e",
        "sub":      "#4a5568" if dark else "#888888",
        "gold":     "#D4AF37",
        "gold_dim": "#3a2c05" if dark else "#e8d080",
        "border":   "#1e2535" if dark else "#d0d4dc",
        "card_bg":  "#141820" if dark else "#ffffff",
    }


# ── Load Logo Image ───────────────────────────────────────────────────────────

def _load_logo_image(target_size: int = 80):
    """
    Try to load the Roneat Studio Icon PNG using PIL, scale it to target_size.
    Returns a PhotoImage compatible with tkinter, or None on failure.
    """
    # Find the logo
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_candidates = [
        os.path.join(script_dir, "assets", "Roneat Studio Icon.png"),
        os.path.join(script_dir, "frontend", "src", "assets", "logo.png"),
    ]

    logo_path = None
    for candidate in logo_candidates:
        if os.path.exists(candidate):
            logo_path = candidate
            break

    if logo_path is None:
        return None

    # Try PIL first
    try:
        from PIL import Image, ImageTk
        img = Image.open(logo_path).convert("RGBA")
        img.thumbnail((target_size, target_size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except ImportError:
        pass

    # Fallback: tkinter's built-in PNG loader (no scaling)
    try:
        return tk.PhotoImage(file=logo_path)
    except Exception:
        return None


# ── Build ─────────────────────────────────────────────────────────────────────

def _build(root: tk.Tk) -> None:
    global _anim_job

    dark = (_resolve_theme() == "dark")
    C    = _palette(dark)

    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg=C["bg"])
    root.resizable(False, False)

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")

    cv = tk.Canvas(root, width=W, height=H, bg=C["bg"], highlightthickness=0)
    cv.pack(fill="both", expand=True)

    # Outer border
    cv.create_rectangle(0, 0, W - 1, H - 1, outline=C["border"], fill="")

    # Inner card
    CARD_X1, CARD_Y1 = 20, 18
    CARD_X2, CARD_Y2 = W - 20, H - 18
    cv.create_rectangle(CARD_X1, CARD_Y1, CARD_X2, CARD_Y2,
                        fill=C["card_bg"], outline=C["border"])

    # Try to load and display the logo
    logo_img = _load_logo_image(target_size=70)
    logo_y_offset = 0  # offset for title/sub if logo present

    if logo_img:
        # Keep a reference to prevent garbage collection
        root._logo_img = logo_img
        logo_cx = W // 2
        logo_cy = 88
        cv.create_image(logo_cx, logo_cy, image=logo_img, anchor="center")
        logo_y_offset = 60  # shift text down

    # App name
    title_y = (logo_y_offset + 100) if logo_img else (H // 2 - 24)
    cv.create_text(W // 2, title_y,
                   text="Roneat Studio",
                   font=("Georgia", 22, "bold"),
                   fill=C["text"], anchor="center")

    # PRO badge
    pro_y = title_y + 28
    cv.create_text(W // 2, pro_y,
                   text="P  R  O",
                   font=("Courier", 8, "bold"),
                   fill=C["gold"], anchor="center")

    # Stage label
    stage_lbl = tk.Label(root, textvariable=_stage_var,
                         bg=C["card_bg"], fg=C["sub"],
                         font=("Courier", 9), bd=0)
    cv.create_window(W // 2, H - 32, window=stage_lbl, anchor="center")

    # Progress track (full width, 4px at very bottom)
    BAR_Y = H - 6
    cv.create_rectangle(0, BAR_Y, W, H, fill=C["gold_dim"], outline="")
    bar_fill = cv.create_rectangle(0, BAR_Y, 0, H, fill=C["gold"], outline="")
    bar_shim = cv.create_rectangle(0, BAR_Y, 0, H,
                                   fill="#f0d060" if dark else "#ffe87a", outline="")

    # Spinner (small arc, top-right corner of card)
    SPW = 22
    spin = tk.Canvas(root, width=SPW, height=SPW, bg=C["card_bg"], highlightthickness=0)
    cv.create_window(W - 30, 30, window=spin)

    angle = [0.0]

    def _animate():
        global _anim_job

        # Spinner
        spin.delete("all")
        cx = SPW // 2
        r  = cx - 3
        spin.create_arc(cx - r, cx - r, cx + r, cx + r,
                        start=angle[0] % 360, extent=255,
                        style="arc", outline=C["gold"], width=2)
        angle[0] = (angle[0] + 8) % 360

        # Progress bar fill
        pct    = _progress_var.get()
        fill_x = int(pct * W)
        cv.coords(bar_fill, 0, BAR_Y, max(1, fill_x), H)

        if fill_x > 20:
            t_ms     = int(time.time() * 1000)
            dur      = 700
            shim_pos = int((t_ms % dur) / dur * fill_x)
            shim_end = min(shim_pos + 55, fill_x)
            cv.coords(bar_shim, shim_pos, BAR_Y, shim_end, H)
        else:
            cv.coords(bar_shim, 0, BAR_Y, 0, H)

        try:
            _anim_job = root.after(25, _animate)
        except Exception:
            pass

    _animate()


# ── Standalone preview ────────────────────────────────────────────────────────

if __name__ == "__main__":
    splash = show_splash()

    stages = [
        "Loading audio engine…",
        "Loading presets…",
        "Initializing editor…",
        "Preparing workspace…",
        "Ready.",
    ]

    import time as _t
    for i in range(101):
        idx = min(i // 20, len(stages) - 1)
        set_progress(i / 100.0, stages[idx])
        _t.sleep(0.025)

    _t.sleep(0.4)
    close_splash()