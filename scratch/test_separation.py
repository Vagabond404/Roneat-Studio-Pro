import sys
import os
sys.path.append(r"c:\Users\ange-\PycharmProjects\Roneat_Studio")

from core.video_exporter import _build_timeline_impl
from core.RoneatVideoCore import RoneatVideoCore

score_text = "9 _ / 9#3 - 8"
bpm = 60
hits_per_sec = 10.0

print("--- TESTING PYTHON TIMELINE ---")
py_events = _build_timeline_impl(score_text, bpm, hits_per_sec, sync_data=None)
for idx, ev in enumerate(py_events):
    print(f"[{idx}] t_start={ev.t_start:.3f}, duration={ev.duration:.3f}, bar={ev.bar}, left_bar={ev.left_bar}, is_tremolo={ev.is_tremolo_hit}, sub_hit={ev.sub_hit}/{ev.total_hits}")

print("\n--- TESTING C++ TIMELINE ---")
core = RoneatVideoCore()
cpp_events = core.build_timeline(score_text, bpm, hits_per_sec, sync_data=None)
for idx, ev in enumerate(cpp_events):
    # Since C++ returns custom VideoEvent objects wrapped by pybind11, they should have similar attributes:
    # t_start, duration, bar (None/std::nullopt), left_bar (None/std::nullopt), is_tremolo_hit, sub_hit, total_hits
    # (Note: std::nullopt is converted to None in python by pybind11)
    print(f"[{idx}] t_start={ev.t_start:.3f}, duration={ev.duration:.3f}, bar={ev.bar}, left_bar={ev.left_bar}, is_tremolo={ev.is_tremolo_hit}, sub_hit={ev.sub_hit}/{ev.total_hits}")

# Verify that they match in count and timing
assert len(py_events) == len(cpp_events), f"Event count mismatch: {len(py_events)} != {len(cpp_events)}"
for idx in range(len(py_events)):
    pe = py_events[idx]
    ce = cpp_events[idx]
    assert abs(pe.t_start - ce.t_start) < 1e-5, f"t_start mismatch at {idx}: {pe.t_start} != {ce.t_start}"
    assert abs(pe.duration - ce.duration) < 1e-5, f"duration mismatch at {idx}: {pe.duration} != {ce.duration}"
    assert pe.bar == ce.bar, f"bar mismatch at {idx}: {pe.bar} != {ce.bar}"
    assert pe.left_bar == ce.left_bar, f"left_bar mismatch at {idx}: {pe.left_bar} != {ce.left_bar}"
    assert pe.is_tremolo_hit == ce.is_tremolo_hit, f"is_tremolo_hit mismatch at {idx}: {pe.is_tremolo_hit} != {ce.is_tremolo_hit}"

print("\n=== TIMELINE VERIFICATION PASSED: PYTHON AND C++ LOGIC ARE IN PERFECT SYNC! ===")
