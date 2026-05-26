import sys
import os
import logging
import time
import customtkinter as ctk

sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")

logging.basicConfig(level=logging.INFO)

from ui.views.score_editor import ScoreEditor
from core.file_manager import ensure_dirs

ensure_dirs()

root = ctk.CTk()
# Mock get_project_data_callback
def get_data():
    return {}

editor = ScoreEditor(root, get_data)
# Force adsr mode to test the fallback synthesis path
editor._jam_player.mode = "adsr"

print("Triggering interactive note...")
editor._play_interactive_note(1)

# Wait a moment for the daemon thread to run
time.sleep(1.5)

root.destroy()
print("Test completed.")
