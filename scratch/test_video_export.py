import sys
import os
sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")

from core.file_manager import load_hz_preset
from core.audio_player import RoneatPlayer
from core.video_exporter import export_mp4, _build_timeline_impl
import numpy as np

# 1. Setup options
score_text = "9 _ / 9#3 - 8"
bpm = 120
hits_per_sec = 12.0
output_file = "scratch/test_export_output.mp4"

if os.path.exists(output_file):
    try:
        os.remove(output_file)
    except Exception as e:
        print(f"Could not remove existing output file: {e}")

# 2. Get tokens and durations for audio rendering
beat_sec = 60.0 / bpm
dt_hit = 1.0 / hits_per_sec

tokens = []
durations = []
# Expand matching the export loop logic in video_export_studio.py
from core.parse_score import expand_score
events = expand_score(score_text)
for ev in events:
    if ev['is_line_rest']:
        continue
    bar = ev['bar']
    left_bar = ev['left_bar']
    has_custom_lh = (left_bar is not None and left_bar != (bar + 7 if bar is not None else None))
    
    if ev['is_tremolo']:
        dur = ev['repeat'] * dt_hit
        if bar is None:
            tok = f"-#{ev['repeat']}"
        else:
            if has_custom_lh:
                tok = f"({left_bar}){bar}#{ev['repeat']}"
            else:
                tok = f"{bar}#{ev['repeat']}"
    else:
        dur = beat_sec * ev['beats']
        if bar is None:
            tok = "-"
        else:
            if has_custom_lh:
                tok = f"({left_bar}){bar}"
            else:
                tok = str(bar)
    tokens.append(tok)
    durations.append(dur)

print("Tokens:", tokens)
print("Durations:", durations)

# 3. Render audio
print("\n--- SYNTHESISING AUDIO ---")
render_player = RoneatPlayer(load_hz_preset(), mode="adsr")
audio_arr = render_player.render_score_to_array(
    tokens, durations, two_mallets=True, hits_per_sec=hits_per_sec)
audio_rate = render_player.sample_rate

print(f"Audio synthesized. Samples: {len(audio_arr)}, rate: {audio_rate}")

# 4. Export MP4
print("\n--- EXPORTING MP4 VIDEO ---")
# Use the compiled C++ backend (which is automatically delegated by export_mp4)
export_mp4(
    filepath=output_file,
    score_text=score_text,
    bpm=bpm,
    hits_per_sec=hits_per_sec,
    audio_arr=audio_arr,
    audio_rate=audio_rate,
    dark_mode=True,
    song_title="សាកល្បងខ្មែរ (Khmer Test Title)",
    two_mallets=True,
    accent_hex="#c8a96e",
    view_mode="Numeric",
    ffmpeg_bin="ffmpeg.exe",
    W=1920,
    H=1080,
    FPS=30,  # 30 fps for faster test run
    title_scale=1.0,
    label_scale=1.0,
    status_scale=1.0,
    title_y_offset=0.0,
    label_y_offset=0.0,
    status_y_offset=0.0,
    show_labels=True,
    show_status=True
)

# 5. Check if output file was created and is not empty
if os.path.exists(output_file):
    sz = os.path.getsize(output_file)
    print(f"\n=== VIDEO EXPORT SUCCESSFUL! Created: {output_file} ({sz} bytes) ===")
    assert sz > 10000, f"Exported file is too small: {sz} bytes"
else:
    print("\n=== VIDEO EXPORT FAILED! Output file not found ===")
    sys.exit(1)
