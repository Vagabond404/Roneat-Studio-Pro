"""
Python wrapper for the C++ Roneat Audio Engine (pybind11 module).
Handles graceful fallback if the C++ module is not yet compiled.

FALLBACK MODE: If C++ module unavailable, uses Python sounddevice for playback.
"""

import sys
import numpy as np
import sounddevice as sd
import threading
import queue

try:
    try:
        from core import roneat_audio_core
    except ImportError:
        import roneat_audio_core
    _cpp_module_available = True
except ImportError as e:
    _cpp_module_available = False
    print(f"[Warning] Could not import C++ audio engine 'roneat_audio_core': {e}", file=sys.stderr)
    print("[Warning] Ensure you have compiled the C++ extension in src/audio_engine_cpp and placed the .pyd/.so file in the 'core' folder.", file=sys.stderr)
    print("[Warning] Falling back to Python sounddevice backend for audio playback.", file=sys.stderr)


class PythonAudioPlayback:
    """Python fallback for audio playback using sounddevice when C++ unavailable."""
    def __init__(self, sample_rate=44100, buffer_size=256):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.stream = None
        self._playing_queue = queue.Queue(maxsize=8)
        self._stream_lock = threading.Lock()
        self._start_stream()
    
    def _start_stream(self):
        """Start the sounddevice output stream."""
        try:
            def callback(outdata, frames, time_info, status):
                if status:
                    pass  # Ignore underrun warnings
                try:
                    audio_data = self._playing_queue.get_nowait()
                    if len(audio_data) < frames:
                        # Pad with zeros if not enough data
                        audio_data = np.concatenate([
                            audio_data,
                            np.zeros(frames - len(audio_data), dtype=np.float32)
                        ])
                    outdata[:, 0] = audio_data[:frames]
                except queue.Empty:
                    outdata.fill(0)
            
            with self._stream_lock:
                if self.stream is None:
                    self.stream = sd.OutputStream(
                        samplerate=self.sample_rate,
                        channels=1,
                        dtype='float32',
                        callback=callback,
                        blocksize=self.buffer_size
                    )
                    self.stream.start()
        except Exception as e:
            print(f"[Warning] Failed to start audio stream: {e}", file=sys.stderr)
    
    def play_buffer(self, audio_data: np.ndarray):
        """Queue audio data for playback."""
        try:
            data = np.ascontiguousarray(audio_data, dtype=np.float32)
            self._playing_queue.put(data, block=False)
        except queue.Full:
            # Drop audio if queue is full (better than blocking)
            pass
    
    def shutdown(self):
        """Stop the audio stream."""
        with self._stream_lock:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None


class RoneatAudioCore:
    def __init__(self):
        if _cpp_module_available:
            self._engine = roneat_audio_core.RoneatAudioEngine()
        else:
            # Use Python fallback
            self._engine = None
            self._python_fallback = PythonAudioPlayback()
            self._fallback_samples = {}

    def initialize(self, sample_rate: int = 44100, buffer_size: int = 256) -> None:
        if self._engine:
            self._engine.initialize(sample_rate, buffer_size)
        else:
            # Python fallback: store sample rate for later use
            pass

    def load_sample_from_buffer(self, bar_number: int, audio_data: np.ndarray) -> None:
        if self._engine:
            # Ensure the numpy array is contiguous float32
            data = np.ascontiguousarray(audio_data, dtype=np.float32)
            self._engine.loadSampleFromBuffer(bar_number, data)
        else:
            # Python fallback: store sample for trigger_note fallback
            self._fallback_samples[bar_number] = audio_data

    def play_buffer(self, audio_data: np.ndarray) -> None:
        if self._engine:
            data = np.ascontiguousarray(audio_data, dtype=np.float32)
            self._engine.playBuffer(data)
        else:
            # Python fallback: play via sounddevice
            self._python_fallback.play_buffer(audio_data)

    def trigger_note(self, bar_number: int, velocity: float = 1.0) -> None:
        if self._engine:
            self._engine.triggerNote(bar_number)
        else:
            # Python fallback: trigger via sounddevice from stored samples
            if bar_number in self._fallback_samples:
                self._python_fallback.play_buffer(self._fallback_samples[bar_number])

    def stop_all(self) -> None:
        if self._engine:
            self._engine.stopAll()
        else:
            # Python fallback: clear the queue
            try:
                while True:
                    self._python_fallback._playing_queue.get_nowait()
            except:
                pass

    def shutdown(self) -> None:
        if self._engine:
            self._engine.shutdown()
        else:
            # Python fallback: cleanup
            if hasattr(self, '_python_fallback'):
                self._python_fallback.shutdown()

