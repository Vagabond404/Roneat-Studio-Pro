"""
core/calibration.py  v2.0
==========================
Roneat Studio Pro — Fingerprint Calibration Engine

NEW IN v2:
  - Saves trimmed WAV samples for each bar alongside fingerprints
    → enables sample-based playback in audio_player ("samples" mode)
  - Sample duration: 1.5 s per bar (captures full natural resonance)
  - Samples stored in DATA_DIR/samples/bar_NN.wav
"""

import numpy as np
import librosa
import librosa.effects
import librosa.onset
import json
import os
from scipy.signal import butter, sosfilt

from core.file_manager import DATA_DIR

FINGERPRINT_FILE = os.path.join(DATA_DIR, "roneat_fingerprints.json")
SAMPLES_DIR      = os.path.join(DATA_DIR, "samples")

N_MELS          = 128
N_FFT           = 4096
HOP_LENGTH      = 512
ONSET_SKIP_MS   = 18     # skip mallet clack
ANALYSIS_WIN_MS = 120    # fingerprint window (short, for AI matching)
SAMPLE_WIN_MS   = 1500   # sample window (long, for playback quality)


def _extract_fingerprint(window, sr):
    mel = librosa.feature.melspectrogram(
        y=window, sr=sr,
        n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH,
        fmin=80, fmax=min(sr // 2, 1600)
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    return np.mean(log_mel, axis=1)


def _cosine_similarity(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _save_sample(audio, sr, bar_num):
    """Save a bar's audio window as a WAV sample for playback."""
    try:
        import soundfile as sf
        os.makedirs(SAMPLES_DIR, exist_ok=True)
        path = os.path.join(SAMPLES_DIR, f"bar_{bar_num:02d}.wav")
        # Normalise before saving
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.90
        sf.write(path, audio.astype(np.float32), sr)
    except Exception as e:
        print(f"  [WARN] Could not save sample for bar {bar_num}: {e}")


def samples_available():
    """Return True if at least one sample WAV exists."""
    if not os.path.exists(SAMPLES_DIR):
        return False
    return any(
        f.startswith("bar_") and f.endswith(".wav")
        for f in os.listdir(SAMPLES_DIR)
    )


def calibrate_from_audio(audio_path, num_bars, progress_callback=None):
    """
    Slice audio → fingerprints + WAV samples per bar.

    Returns:
        dict {bar_number: fingerprint_list} or None on failure
    """
    print(f"\n{'='*60}")
    print(f"  CALIBRATION v2 - {num_bars} bars from {audio_path}")
    print(f"{'='*60}")

    if progress_callback:
        progress_callback(2, "Loading audio file...")

    y, sr    = librosa.load(audio_path, sr=None, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)
    print(f"  SR={sr} Hz  Duration={duration:.2f}s")

    if progress_callback:
        progress_callback(15, "Running HPSS separation...")

    _, y_perc = librosa.effects.hpss(y, margin=3.0)

    if progress_callback:
        progress_callback(30, "Detecting note onsets...")

    onset_frames = librosa.onset.onset_detect(
        y=y_perc, sr=sr, units='frames', hop_length=HOP_LENGTH,
        backtrack=True,
        pre_max=3, post_max=3, pre_avg=5, post_avg=5,
        delta=0.05, wait=12
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=HOP_LENGTH)
    print(f"  Detected {len(onset_frames)} onsets (need {num_bars})")

    if len(onset_frames) < num_bars:
        msg = (f"Only {len(onset_frames)} onsets detected, need {num_bars}. "
               f"Please re-record with clearer note separation.")
        print(f"  [ERROR] {msg}")
        if progress_callback:
            progress_callback(100, f"ERROR: {msg}")
        return None

    if len(onset_frames) > num_bars:
        print(f"  [WARN] More onsets ({len(onset_frames)}) than bars ({num_bars}). "
              f"Using first {num_bars}.")
        onset_frames = onset_frames[:num_bars]
        onset_times  = onset_times[:num_bars]

    skip_s    = int((ONSET_SKIP_MS   / 1000.0) * sr)
    fp_win_s  = int((ANALYSIS_WIN_MS / 1000.0) * sr)
    smp_win_s = int((SAMPLE_WIN_MS   / 1000.0) * sr)

    fingerprints = {}

    for i, (frame, t) in enumerate(zip(onset_frames, onset_times)):
        pct     = 35 + int((i / num_bars) * 55)
        bar_num = i + 1

        onset_sample = librosa.frames_to_samples(frame, hop_length=HOP_LENGTH)
        w_start      = onset_sample + skip_s

        if w_start >= len(y):
            print(f"  [WARN] Bar {bar_num}: window past EOF, skipping")
            continue

        # --- Fingerprint window (short) ---
        fp_end = min(w_start + fp_win_s, len(y))
        fp_win = y[w_start:fp_end]
        rms    = float(np.sqrt(np.mean(fp_win ** 2)))
        fp     = _extract_fingerprint(fp_win, sr)
        fingerprints[bar_num] = fp.tolist()

        # --- Sample window (long — for playback) ---
        smp_end = min(w_start + smp_win_s, len(y))
        smp_win = y[w_start:smp_end]
        _save_sample(smp_win, sr, bar_num)

        print(f"  Bar {bar_num:2d}  t={t:.3f}s  rms={rms:.5f}  "
              f"fp_mean={fp.mean():.3f}  sample={len(smp_win)/sr:.2f}s")

        if progress_callback:
            progress_callback(
                pct,
                f"Bar {bar_num}/{num_bars} - fingerprinted + sample saved (t={t:.2f}s)"
            )

    if progress_callback:
        progress_callback(100, f"Done — {len(fingerprints)} bars calibrated.")

    print(f"  Calibrated {len(fingerprints)} bars successfully.")
    return fingerprints


def save_fingerprints(single_fps, two_fps):
    data = {}
    if single_fps:
        data["single"] = {str(k): v for k, v in single_fps.items()}
    if two_fps:
        data["two"]    = {str(k): v for k, v in two_fps.items()}
    with open(FINGERPRINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"  Fingerprints saved -> {FINGERPRINT_FILE}")


def load_fingerprints():
    if not os.path.exists(FINGERPRINT_FILE):
        return None, None
    try:
        with open(FINGERPRINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        single = {int(k): np.array(v) for k, v in data.get("single", {}).items()}
        two    = {int(k): np.array(v) for k, v in data.get("two",    {}).items()}
        return (single or None), (two or None)
    except Exception as e:
        print(f"  [WARN] Could not load fingerprints: {e}")
        return None, None


def match_window_to_bar(window, sr, fingerprints):
    fp     = _extract_fingerprint(window, sr)
    scores = {bar: _cosine_similarity(fp, np.array(ref))
              for bar, ref in fingerprints.items()}
    best_bar   = max(scores, key=scores.get)
    best_score = scores[best_bar]
    return best_bar, best_score, scores