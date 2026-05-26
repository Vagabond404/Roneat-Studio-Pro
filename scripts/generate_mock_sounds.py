import os
import numpy as np
import soundfile as sf
import math

def generate_mock_sounds():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    legacy_dir = os.path.join(project_root, "assets", "audio", "roneat_ek")
    pro_dir = os.path.join(legacy_dir, "pro")

    os.makedirs(pro_dir, exist_ok=True)

    sample_rate = 44100
    duration = 0.5

    print(f"Generating mock multisampled sounds in: {pro_dir}")

    for note in range(1, 22):
        legacy_file = os.path.join(legacy_dir, f"{note}.wav")
        audio_data = None
        
        # Try to read legacy file if it exists
        if os.path.exists(legacy_file):
            try:
                audio_data, sr = sf.read(legacy_file, dtype='float32')
                if sr != sample_rate:
                    # just keep original sr for legacy read
                    sample_rate = sr
                if audio_data.ndim == 2:
                    audio_data = audio_data.mean(axis=1) # mix to mono
            except Exception as e:
                print(f"Warning: Failed to read {legacy_file}: {e}")
                audio_data = None
                
        # If no legacy file, synthesize a dummy sine wave so we have something to test
        if audio_data is None:
            t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
            freq = 200 + (note * 20) # arbitrary pitch going up
            audio_data = 0.5 * np.sin(2 * np.pi * freq * t)
            # Apply basic fade out to synthesized tone
            fade_len = int(sample_rate * 0.1)
            audio_data[-fade_len:] *= np.linspace(1.0, 0.0, fade_len)
            
            # Save the raw dummy so the legacy path exists too
            sf.write(legacy_file, audio_data.astype(np.float32), sample_rate)
            print(f"Synthesized dummy legacy file: {legacy_file}")

        # Now generate multi-sampled variations
        layers = {
            "soft": 0.5,    # -6dB
            "med": 1.0,     # original
            "hard": 1.2     # increased amplitude
        }
        
        for mallets in [1, 2]:
            for layer_name, multiplier in layers.items():
                dest_filename = f"note{note}_{mallets}m_{layer_name}.wav"
                dest_path = os.path.join(pro_dir, dest_filename)
                
                # Apply amplitude multiplication
                processed_data = audio_data * multiplier
                
                # If mallets == 2, apply a tiny chorus/detune effect to simulate 2 mallets striking 
                if mallets == 2:
                    # Simple delay mix to simulate two mallets
                    delay_samples = int(sample_rate * 0.02) # 20ms delay
                    delayed_data = np.pad(processed_data, (delay_samples, 0))[:-delay_samples]
                    processed_data = (processed_data + delayed_data * 0.8) * 0.6
                
                # Prevent clipping
                processed_data = np.clip(processed_data, -1.0, 1.0)
                
                sf.write(dest_path, processed_data.astype(np.float32), sample_rate)
                
    print("Mock multisampled generation complete!")

if __name__ == "__main__":
    generate_mock_sounds()
