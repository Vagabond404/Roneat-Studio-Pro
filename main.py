"""
 ██████╗  ██████╗ ███╗   ██╗███████╗ █████╗ ████████╗
 ██╔══██╗██╔═══██╗████╗  ██║██╔════╝██╔══██╗╚══██╔══╝
 ██████╔╝██║   ██║██╔██╗ ██║█████╗  ███████║   ██║   
 ██╔══██╗██║   ██║██║╚██╗██║██╔══╝  ██╔══██║   ██║   
 ██║  ██║╚██████╔╝██║ ╚████║███████╗██║  ██║   ██║   
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝   ╚═╝   
                                                     
 ███████╗████████╗██╗   ██╗██████╗ ██╗ ██████╗ 
 ██╔════╝╚══██╔══╝██║   ██║██╔══██╗██║██╔═══██╗
 ███████╗   ██║   ██║   ██║██║  ██║██║██║   ██║
 ╚════██║   ██║   ██║   ██║██║  ██║██║██║   ██║
 ███████║   ██║   ╚██████╔╝██████╔╝██║╚██████╔╝
 ╚══════╝   ╚═╝    ╚═════╝ ╚═════╝ ╚═╝ ╚═════╝ 

 Welcome to the Core Engine of Roneat Studio Pro.
 Traditional Cambodian Heritage meets Modern Engineering.
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
    
    # Detect file passed via command-line or drag-and-drop onto the .exe
    initial_file = None
    dev_mode = False
    
    for arg in sys.argv[1:]:
        if arg == '--dev':
            dev_mode = True
        elif os.path.exists(arg) and arg.lower().endswith('.roneat'):
            initial_file = arg

    # ── 1. Show splash immediately (pure tkinter, no heavy imports) ───────────
    from splash_screen import show_splash, set_progress, close_splash

    splash = show_splash()
    set_progress(0.05, "Initializing…")

    # ── 2. Load heavy modules with progress feedback ───────────────────────────
    set_progress(0.35, "Loading UI Engine…")
    from core.file_manager import ensure_dirs
    import core.eel_bridge as eel_bridge
    import eel

    set_progress(0.70, "Preparing workspace…")
    ensure_dirs()
    
    # Initialize Eel bridge (scans plugins and loads active ones)
    eel_bridge.init_bridge()
    
    # If a file was passed on startup, load it now
    if initial_file:
        try:
            eel_bridge.load_project_file(initial_file)
        except Exception as e:
            logging.error(f"Failed to load initial file {initial_file}: {e}")

    set_progress(1.0, "Ready")
    splash.update()
    
    # ── 3. Hand control to Eel ────────────────────────────────────────────────
    close_splash()

    # Launch Eel Window
    # Point Eel to the Vite dev server in dev mode, or serve built assets in production
    exposed_js_funcs = [
        'js_show_toast',
        'js_transcribe_progress',
        'js_active_beat_highlight',
        'js_video_export_progress',
        'js_load_project_data',
        'js_calibration_progress'
    ]

    if dev_mode:
        logging.info("Starting Eel in DEVELOPMENT mode (proxying Vite)...")
        eel.init('web', allowed_extensions=['.html'])
        eel._js_functions.extend(exposed_js_funcs)
        for func in exposed_js_funcs:
            eel._mock_js_function(func)
        eel.start(
            'http://localhost:5173',
            mode='chrome',
            size=(1380, 860),
            port=8000
        )
    else:
        logging.info("Starting Eel in PRODUCTION mode (serving web/)...")
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
        os.makedirs(web_dir, exist_ok=True)
        eel.init(web_dir, allowed_extensions=['.html'])
        eel._js_functions.extend(exposed_js_funcs)
        for func in exposed_js_funcs:
            eel._mock_js_function(func)
        eel.start(
            'index.html',
            mode='chrome',
            size=(1380, 860),
            port=8000
        )


if __name__ == "__main__":
    main()