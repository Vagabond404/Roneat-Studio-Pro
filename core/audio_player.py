"""
core/audio_player.py  v3.5
============================
Roneat Studio Pro — Audio Synthesis Engine

CHANGES in v3.5:
  - Tremolo completely rewritten: `repeat` is the EXACT number of strikes.
  - `hits_per_sec` controls the exact speed of the tremolo roll.
  - Returns actual_dur from _build_tremolo to keep visuals perfectly synced.
"""

import numpy as np
import sounddevice as sd
import time
import os
import logging

from core.file_manager import DATA_DIR

SAMPLES_DIR = os.path.join(DATA_DIR, "samples")


def _parse_token(token):
    """
    Parse a single score token.
    Returns (bar_idx, repeat, is_tremolo) or (None, 1, False).
    """
    if token in ('/', '-', '0', 'x'):
        return None, 1, False

    if '#' in token:
        parts  = token.split('#', 1)
        bar_s  = parts[0]
        rep_s  = parts[1] if len(parts) > 1 else ''
        try:
            repeat = max(1, min(int(rep_s), 32)) if rep_s.isdigit() else 1
        except (ValueError, TypeError):
            repeat = 1
        is_trem = True
    else:
        bar_s   = token
        repeat  = 1
        is_trem = False

    if not bar_s.isdigit():
        return None, 1, False

    bar_idx = int(bar_s)
    if not (1 <= bar_idx <= 21):
        return None, 1, False

    return bar_idx, repeat, is_trem


class RoneatPlayer:
    def __init__(self, roneat_dict, mode="adsr"):
        self.roneat_dict     = roneat_dict
        self.sample_rate     = 44100
        self.is_playing      = False
        self.mode            = mode
        self._samples        = {}
        self._samples_loaded = False

    # ─────────────────────────────────────────────────────────────────────────
    # Sample management
    # ─────────────────────────────────────────────────────────────────────────

    def load_samples(self):
        self._samples = {}
        if not os.path.exists(SAMPLES_DIR):
            self._samples_loaded = True
            return
        try:
            import soundfile as sf
            for bar_num in range(1, 22):
                path = os.path.join(SAMPLES_DIR, f"bar_{bar_num:02d}.wav")
                if os.path.exists(path):
                    data, sr = sf.read(path, dtype='float32', always_2d=False)
                    if data.ndim == 2:
                        data = data.mean(axis=1)
                    if sr != self.sample_rate:
                        try:
                            import librosa
                            data = librosa.resample(data, orig_sr=sr,
                                                    target_sr=self.sample_rate)
                        except Exception as e:
                            logging.warning(f"Error resampling audio: {e}")
                    self._samples[bar_num] = data
            logging.info(f"[Player] Loaded {len(self._samples)} samples")
        except Exception as e:
            logging.error(f"[Player] Sample load error: {e}", exc_info=True)
        self._samples_loaded = True

    def samples_available(self):
        if not self._samples_loaded:
            self.load_samples()
        return len(self._samples) > 0

    # ─────────────────────────────────────────────────────────────────────────
    # Tone generation
    # ─────────────────────────────────────────────────────────────────────────

    def generate_tone(self, frequency, duration, bar_num=None):
        if self.mode == "samples":
            if not self._samples_loaded:
                self.load_samples()
            if bar_num and bar_num in self._samples:
                return self._tone_from_sample(bar_num, duration)
        return self._adsr_tone(frequency, duration)

    def _adsr_tone(self, frequency, duration):
        n     = max(1, int(self.sample_rate * duration))
        t     = np.linspace(0, duration, n, endpoint=False)
        wave  = 1.00 * np.sin(2 * np.pi * frequency         * t)
        wave += 0.40 * np.sin(2 * np.pi * frequency * 2.0   * t)
        wave += 0.18 * np.sin(2 * np.pi * frequency * 2.756 * t)
        wave += 0.08 * np.sin(2 * np.pi * frequency * 4.0   * t)
        click_len = min(int(0.008 * self.sample_rate), n)
        wave[:click_len] += np.random.uniform(-0.15, 0.15, click_len)
        decay_rate = 2.8 + (frequency - 177.0) / (1308.0 - 177.0) * 6.2
        decay_rate = max(2.0, min(decay_rate, 12.0))
        wave      *= np.exp(-decay_rate * t)
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak * 0.35
        return wave.astype(np.float32)

    def _tone_from_sample(self, bar_num, duration):
        data       = self._samples[bar_num].copy()
        target_len = max(1, int(duration * self.sample_rate))
        if len(data) > target_len:
            data = data[:target_len]
        elif len(data) < target_len:
            data = np.pad(data, (0, target_len - len(data)))
        fade_len = max(1, int(target_len * 0.20))
        data[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
        peak = np.max(np.abs(data))
        if peak > 0:
            data = data / peak * 0.35
        return data.astype(np.float32)

    # ─────────────────────────────────────────────────────────────────────────
    # Note builders
    # ─────────────────────────────────────────────────────────────────────────

    def _build_single_note(self, bar_idx, duration, two_mallets):
        n    = max(1, int(self.sample_rate * duration))
        tone = np.zeros(n, dtype=np.float32)
        if bar_idx not in self.roneat_dict:
            return tone
        tone += self.generate_tone(self.roneat_dict[bar_idx], duration, bar_idx)
        if two_mallets:
            lh = bar_idx + 7
            if lh <= 21 and lh in self.roneat_dict:
                tone += self.generate_tone(self.roneat_dict[lh], duration, lh)
        return np.clip(tone, -1.0, 1.0).astype(np.float32)

    def _build_tremolo(self, bar_idx, repeat, two_mallets, hits_per_sec=16.0):
        """
        Builds a tremolo with EXACTLY `repeat` strikes.
        The duration is calculated based on how fast the strikes are played (hits_per_sec).
        Returns the tone array AND the total actual duration.
        """
        lh_idx = bar_idx + 7 if two_mallets else None
        has_lh = (lh_idx is not None and lh_idx <= 21
                  and lh_idx in self.roneat_dict
                  and bar_idx in self.roneat_dict)

        total_hits = repeat
        hit_dur    = 1.0 / max(1.0, hits_per_sec)
        hit_samp   = max(1, int(hit_dur * self.sample_rate))

        total_duration = total_hits * hit_dur
        n = max(1, int(self.sample_rate * total_duration))
        result = np.zeros(n, dtype=np.float32)

        if bar_idx not in self.roneat_dict:
            return result, total_duration

        for h in range(total_hits):
            start = h * hit_samp
            if start >= n:
                break
            seg = min(hit_samp, n - start)

            # Alternate hands
            if has_lh:
                if h % 2 == 0:
                    tone = self.generate_tone(self.roneat_dict[bar_idx], hit_dur, bar_idx)
                else:
                    tone = self.generate_tone(self.roneat_dict[lh_idx], hit_dur, lh_idx)
            else:
                tone = self.generate_tone(self.roneat_dict[bar_idx], hit_dur, bar_idx)

            result[start:start + min(len(tone), seg)] += tone[:seg]

        return np.clip(result, -1.0, 1.0).astype(np.float32), total_duration

    # ─────────────────────────────────────────────────────────────────────────
    # Playback
    # ─────────────────────────────────────────────────────────────────────────

    def _play_note(self, bar_idx, duration, two_mallets,
                   bar_callback=None, tremolo=False, repeat=1, hits_per_sec=16.0):
        if not self.is_playing:
            return 0.0
        if bar_callback:
            try:
                bar_callback(bar_idx)
            except Exception as e:
                logging.warning(f"Error in bar_callback: {e}")

        if tremolo:
            tone, actual_dur = self._build_tremolo(bar_idx, repeat, two_mallets, hits_per_sec)
        else:
            tone = self._build_single_note(bar_idx, duration, two_mallets)
            actual_dur = duration

        sd.play(tone, self.sample_rate)
        sd.wait()
        return actual_dur

    def play_score(self, score_text, bpm=120, two_mallets=False,
                   sync_data=None, bar_callback=None, hits_per_sec=16.0):
        self.is_playing = True
        if not self.roneat_dict:
            self.is_playing = False
            return

        bpm  = max(20, min(int(bpm) if bpm else 120, 400))
        beat = 60.0 / bpm

        if sync_data:
            start = time.time()
            t0    = sync_data[0]['time'] if sync_data else 0.0
            for i, item in enumerate(sync_data):
                if not self.is_playing:
                    break
                target  = item['time'] - t0
                elapsed = time.time() - start
                if target > elapsed:
                    time.sleep(target - elapsed)

                bar_idx, repeat, is_trem = _parse_token(str(item['note']))
                if bar_idx is None:
                    continue

                dur = (min(sync_data[i+1]['time'] - item['time'], 0.9)
                       if i + 1 < len(sync_data) else 0.5)

                self._play_note(bar_idx, max(0.05, dur), two_mallets,
                                bar_callback, tremolo=is_trem, repeat=repeat, hits_per_sec=hits_per_sec)
        else:
            for token in score_text.replace('\n', ' ').split():
                if not self.is_playing:
                    break
                if token == '/':
                    continue
                if token in ('-', '0', 'x'):
                    time.sleep(beat)
                    continue

                bar_idx, repeat, is_trem = _parse_token(token)
                if bar_idx is None:
                    continue

                self._play_note(bar_idx, beat, two_mallets,
                                bar_callback, tremolo=is_trem, repeat=repeat, hits_per_sec=hits_per_sec)

        self.is_playing = False
        if bar_callback:
            try:
                bar_callback(None)
            except Exception as e:
                logging.warning(f"Error in bar_callback (None): {e}")

    def stop(self):
        self.is_playing = False
        sd.stop()

    # ─────────────────────────────────────────────────────────────────────────
    # Offline rendering (MP4 export)
    # ─────────────────────────────────────────────────────────────────────────

    def render_score_to_array(self, notes, durations, two_mallets=False, hits_per_sec=16.0):
        sr     = self.sample_rate
        chunks = []
        for note_raw, dur in zip(notes, durations):
            if isinstance(note_raw, str):
                bar_idx, repeat, is_trem = _parse_token(note_raw)
            else:
                is_trem = int(note_raw) < 0
                bar_idx = abs(int(note_raw))
                repeat  = 1
                if not (1 <= bar_idx <= 21):
                    bar_idx = None

            if bar_idx is None:
                chunks.append(np.zeros(max(1, int(dur * sr)), dtype=np.float32))
                continue

            if is_trem:
                tone, actual_dur = self._build_tremolo(bar_idx, repeat, two_mallets, hits_per_sec)
                chunks.append(tone)
            else:
                tone = self._build_single_note(bar_idx, dur, two_mallets)
                chunks.append(tone)

        if chunks:
            return np.concatenate(chunks)
        return np.zeros(sr, dtype=np.float32)