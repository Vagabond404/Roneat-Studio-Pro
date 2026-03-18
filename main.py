"""
main.py — Roneat Studio Pro v2.0.1
Entry point. Shows splash screen while heavy modules load,
then launches MainWindow.
"""

import sys
import os
import logging

def _setup_logging():
    if sys.platform == 'win32':
        base_path = os.getenv('APPDATA')
    else:
        base_path = os.path.expanduser('~')
    app_dir = os.path.join(base_path, 'RoneatStudioPro')
    os.makedirs(app_dir, exist_ok=True)
    log_file = os.path.join(app_dir, 'app.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info("--- Roneat Studio Pro Starting ---")

def main():
    _setup_logging()
    # ── 1. Show splash immediately (pure tkinter, no heavy imports) ───────────
    from splash_screen import show_splash, set_progress, close_splash

    splash = show_splash()
    set_progress(0.05, "Initializing…")

    # ── 2. Load heavy modules with progress feedback ───────────────────────────
    set_progress(0.15, "Loading audio engine…")
    import numpy          # noqa – pre-warm numpy
    import sounddevice    # noqa

    set_progress(0.35, "Loading analysis library…")
    import librosa        # noqa – this is the slow one

    set_progress(0.60, "Loading UI…")
    from core.file_manager import ensure_dirs
    from ui.main_window    import MainWindow

    set_progress(0.80, "Preparing workspace…")
    ensure_dirs()

    # Detect file passed via command-line or drag-and-drop onto the .exe
    initial_file = sys.argv[1] if len(sys.argv) > 1 else None

    set_progress(0.95, "Launching…")

    # ── 3. Build main window (hidden until splash closes) ─────────────────────
    app = MainWindow(initial_file=initial_file)

    set_progress(1.0, "Ready")
    splash.update()

    # ── 4. Close splash & hand control to main window ─────────────────────────
    close_splash()

    # Reassign default root so dynamically created fonts/vars don't crash
    import tkinter
    tkinter._default_root = app

    # PyInstaller splash (if used with --splash flag)
    try:
        import pyi_splash
        pyi_splash.close()
    except ImportError:
        pass

    try:
        app.mainloop()
    except Exception as e:
        logging.error("Unhandled exception in main loop", exc_info=True)
        raise


if __name__ == "__main__":
    main()