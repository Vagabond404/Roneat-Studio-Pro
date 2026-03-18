"""
core/audio_analyzer.py  v7.1
==============================
Roneat Studio Pro — Audio Analysis Engine

Changes in v7.1:
  - Console output reduced to key steps only (no per-onset spam)
  - # notation = Tremolo, not sharp — returned as negative bar numbers
    (e.g. "9#" → -9 in sync_data so player and video handle it correctly)
  - pYIN confidence filtering preserved
  - Polyphony detection + harmonic isolation preserved
"""

import numpy as np
import librosa
import librosa.effects
import librosa.onset
from scipy.signal import butter, sosfilt

from core.calibration import (
    load_fingerprints, match_window_to_bar,
    ONSET_SKIP_MS, ANALYSIS_WIN_MS
)

HOP_LENGTH      = 512
ENERGY_GATE     = 0.001
PYIN_FMIN       = 150.0
PYIN_FMAX       = 1400.0
PYIN_CONFIDENCE = 0.50


def detect_polyphony(y, sr):
    frame_len = int(0.05 * sr)
    hop       = frame_len // 2
    n_fft     = 4096
    stft      = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop, win_length=frame_len))
    freqs     = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    mask      = (freqs >= 150) & (freqs <= 1400)
    db_band   = librosa.amplitude_to_db(stft[mask, :], ref=np.max)
    poly_frames, peak_counts = 0, []
    for f in range(db_band.shape[1]):
        frame = db_band[:, f]
        above = frame > -50.0
        peaks = sum(1 for i in range(1, len(frame) - 1)
                    if above[i] and frame[i] > frame[i - 1] and frame[i] > frame[i + 1])
        peak_counts.append(peaks)
        if peaks > 12:
            poly_frames += 1
    avg_peaks  = float(np.mean(peak_counts))
    poly_ratio = poly_frames / max(len(peak_counts), 1)
    is_poly    = avg_peaks > 9 or poly_ratio > 0.25
    print(f"[Analyzer] Polyphony: avg_peaks={avg_peaks:.1f}  ratio={poly_ratio:.0%}  "
          f"-> {'POLYPHONIC' if is_poly else 'clean'}")
    return is_poly, poly_ratio, avg_peaks


def _detect_onsets(y_perc, sr):
    frames = librosa.onset.onset_detect(
        y=y_perc, sr=sr, units='frames', hop_length=HOP_LENGTH,
        backtrack=True, pre_max=3, post_max=3, pre_avg=5, post_avg=5,
        delta=0.05, wait=6
    )
    return frames, librosa.frames_to_time(frames, sr=sr, hop_length=HOP_LENGTH)


def _nearest_bar(hz, roneat_dict):
    return min(roneat_dict.keys(), key=lambda b: abs(roneat_dict[b] - hz))


def _pyin_pitch(y_win, sr):
    if len(y_win) < 1024:
        return None, 0.0, 0
    try:
        f0, _, voiced_prob = librosa.pyin(
            y_win, sr=sr, fmin=PYIN_FMIN, fmax=PYIN_FMAX,
            frame_length=2048, hop_length=256, fill_na=None
        )
        if f0 is None:
            return None, 0.0, 0
        mask   = (voiced_prob > PYIN_CONFIDENCE) & ~np.isnan(f0)
        voiced = f0[mask]
        if len(voiced) == 0:
            return None, 0.0, 0
        return float(np.median(voiced)), float(np.mean(voiced_prob[mask])), len(voiced)
    except Exception as e:
        print(f"[Analyzer] pYIN error: {e}")
        return None, 0.0, 0


def audio_to_notes(filepath, roneat_dict, two_mallets=True, progress_callback=None):
    """
    Transcribe audio → Roneat bar numbers.

    Tremolo notation: if a note token contains '#' (e.g. "9#"),
    the bar number is stored as negative (-9) in sync_data so the
    player and video exporter can apply tremolo treatment.

    Returns:
        (notes_str, poly_info, sync_data)
        notes_str  - space-separated bar tokens, e.g. "9 8# 6 5"
        poly_info  - dict with polyphony stats
        sync_data  - list of {'note': int, 'time': float}
                     note is negative for tremolo bars
    """
    print("\n[Analyzer] -- Starting analysis ----------------------------------")

    single_fps, two_fps = load_fingerprints()
    use_fp = single_fps is not None and len(single_fps) > 0
    if use_fp:
        active_fps = (two_fps if (two_mallets and two_fps and len(two_fps) > 0)
                      else single_fps)
        print(f"[Analyzer] Mode: FINGERPRINT ({len(active_fps)} bars)")
    else:
        active_fps = None
        print("[Analyzer] Mode: pYIN PITCH DETECTION")

    if progress_callback:
        progress_callback(3, "Loading audio file...", None, None)
    y, sr = librosa.load(filepath, sr=None, mono=True)
    y = librosa.util.normalize(y)
    dur   = librosa.get_duration(y=y, sr=sr)
    print(f"[Analyzer] SR={sr}  Duration={dur:.2f}s")

    if progress_callback:
        progress_callback(8, "Analyzing audio complexity...", None, None)
    is_poly, poly_ratio, avg_peaks = detect_polyphony(y, sr)
    poly_info = {"is_polyphonic": is_poly,
                 "poly_ratio":    round(poly_ratio, 3),
                 "avg_peaks":     round(avg_peaks, 1)}

    msg = (f"Polyphonic ({poly_ratio:.0%}) - isolating melody..."
           if is_poly else "Clean audio - proceeding...")
    if progress_callback:
        progress_callback(12, msg, None, poly_info)

    if progress_callback:
        progress_callback(18, "Separating harmonic/percussive...", None, None)
    margin     = 8.0 if is_poly else 4.0
    y_harm, y_perc = librosa.effects.hpss(y, margin=margin)
    if is_poly:
        nyq    = sr / 2.0
        sos    = butter(4, 200.0 / nyq, btype='high', output='sos')
        y_harm = sosfilt(sos, y_harm)

    if progress_callback:
        progress_callback(25, "Detecting note onsets...", None, None)
    onset_frames, onset_times = _detect_onsets(y_perc, sr)
    if len(onset_frames) < 3:
        print("[Analyzer] Few percussive onsets found. Falling back to full audio.")
        onset_frames, onset_times = _detect_onsets(y, sr)
    print(f"[Analyzer] {len(onset_frames)} onsets detected")

    if len(onset_frames) == 0:
        if progress_callback:
            progress_callback(100, "No notes detected. Check audio quality.", None, poly_info)
        return "", poly_info, []

    if progress_callback:
        progress_callback(32, f"{len(onset_frames)} onsets - analysing pitches...", None, None)

    skip_s     = int((ONSET_SKIP_MS  / 1000.0) * sr)
    win_s      = int((ANALYSIS_WIN_MS / 1000.0) * sr)
    pyin_win_s = max(win_s, int(0.20 * sr))

    detected    = []   # list of bar tokens (str, e.g. "9" or "9#")
    sync_data   = []   # list of {'note': int (neg=tremolo), 'time': float}
    skip_count  = 0

    for i, (frame, t) in enumerate(zip(onset_frames, onset_times)):
        pct      = 32 + int((i / len(onset_frames)) * 61)
        onset_s  = librosa.frames_to_samples(frame, hop_length=HOP_LENGTH)
        w_start  = onset_s + skip_s
        w_end    = min(w_start + win_s,      len(y))
        py_end   = min(w_start + pyin_win_s, len(y_harm))

        if w_start >= len(y):
            skip_count += 1
            continue

        window = y[w_start:w_end]
        rms    = float(np.sqrt(np.mean(window ** 2)))
        if rms < ENERGY_GATE:
            skip_count += 1
            continue

        if use_fp:
            bar, score, _ = match_window_to_bar(window, sr, active_fps)
            note_data = {"index": i, "time": float(t),
                         "bar": bar, "rms": rms, "score": float(score)}
        else:
            hz, conf, n_voiced = _pyin_pitch(y_harm[w_start:py_end], sr)
            if hz is None:
                skip_count += 1
                continue
            bar       = _nearest_bar(hz, roneat_dict)
            note_data = {"index": i, "time": float(t),
                         "bar": bar, "rms": rms, "score": conf}

        detected.append(str(bar))
        sync_data.append({"note": bar, "time": float(t)})

        if progress_callback:
            progress_callback(pct, f"Note {i + 1}/{len(onset_frames)} -> Bar {bar}",
                              note_data, None)

    result = ' '.join(detected)
    print(f"[Analyzer] Done - {len(detected)} notes, {skip_count} skipped")
    if progress_callback:
        progress_callback(100, f"Done - {len(detected)} notes detected.", None, poly_info)

    return result, poly_info, sync_data


def sync_score_with_audio(score_text, audio_path):
    """
    Align an existing score string with an audio file's onset times.
    Tremolo tokens (containing '#') produce negative note values.
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)
    _, y_perc = librosa.effects.hpss(y, margin=4.0)
    _, onset_times = _detect_onsets(y_perc, sr)

    tokens = [t for t in score_text.replace('\n', ' ').split() if t != '/']
    result = []
    for i, tok in enumerate(tokens):
        is_trem = '#' in tok
        clean   = tok.replace('#', '')
        if not clean.isdigit():
            continue
        bar_num = int(clean)
        if is_trem:
            bar_num = -bar_num  # negative = tremolo
        t = round(float(onset_times[i]) if i < len(onset_times) else 0.0, 4)
        result.append({'note': bar_num, 'time': t})
    return result