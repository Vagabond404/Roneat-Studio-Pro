import sys
import time
import numpy as np

sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")
from core.RoneatAudioCore import RoneatAudioCore

core = RoneatAudioCore()
core.initialize(44100, 256)

print("Playing tone using play_buffer (ADSR)...")
# Generate a simple 1 second 440Hz sine wave
sr = 44100
t = np.linspace(0, 1.0, sr, False)
tone = 0.5 * np.sin(2 * np.pi * 440.0 * t)
core.play_buffer(tone)

time.sleep(1.5)

print("Loading sample...")
core.load_sample_from_buffer(1, tone)
print("Triggering note...")
core.trigger_note(1)

time.sleep(1.5)
print("Finished!")
