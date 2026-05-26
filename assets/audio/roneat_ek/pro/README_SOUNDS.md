# Roneat Studio Pro - Studio Audio Guide

Dear Audio Engineer,

This directory (`assets/audio/roneat_ek/pro/`) is configured to process the high-fidelity, multisampled Roneat Ek sounds. Roneat Studio Pro v3.0.0 uses a dynamic velocity-layered architecture to achieve realistic performances.

Presently, this folder contains **mock/dummy files** synthesized for testing the engine logic. Once the final studio recordings are prepared, you must replace these mock files. 

## Naming Convention

To ensure the engine can route the audio paths flawlessly, every file must follow this exact naming format:

**Format:** `note{note_number}_{mallets}m_{layer}.wav`

### Parameters

1. **`{note_number}`**: The bar number spanning the instrument (1 through 21). Note 1 is the lowest pitch (left), and Note 21 is the highest pitch (right).
2. **`{mallets}m`**: Specifies how many mallets are striking simultaneously.
   - `1m`: Single mallet strike.
   - `2m`: Dual mallet strike (used for standard octave harmonies).
3. **`{layer}`**: The strike velocity dynamic layer.
   - `soft`: Target velocity 0-40. Played gently.
   - `med`: Target velocity 41-90. Standard strike.
   - `hard`: Target velocity 91-127. High power strike.

### Example File Names

* `note1_1m_soft.wav`
* `note5_2m_hard.wav`
* `note21_1m_med.wav`

If the application cannot locate a specific pro sample, it will fallback to using the legacy singular sound files located in the parent directory (`assets/audio/roneat_ek/{note}.wav`).

Please ensure all `.wav` files are mixed consistently and cleanly mapped to these layers.
