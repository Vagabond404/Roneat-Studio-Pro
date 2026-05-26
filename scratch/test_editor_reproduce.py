import sys
import os
import logging
sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from core.file_manager import ensure_dirs
from ui.main_window import MainWindow

ensure_dirs()
app = MainWindow()

editor = app.frames.get("editor")
print("EDITOR LOADED:", editor)
print("ACTIVE INSTRUMENT PLUGIN:", editor._get_active_instrument_plugin())
print("JAM PLAYER:", editor._jam_player)
print("JAM PLAYER TYPE:", type(editor._jam_player))

# Let's set the audio mode preference to ADSR to force the fallback synthesis path
# because we want to test the _build_single_note call.
editor._jam_player.mode = "adsr"

print("PLAYING INTERACTIVE NOTE...")
editor._play_interactive_note(1)

import time
time.sleep(2)
print("DONE")
