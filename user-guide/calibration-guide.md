---
description: >-
  Calibration is the single most important step for achieving accurate
  transcription.
---

# Calibration Guide

**Teaching the AI Your Instrument**

Calibration is the most important step for reliable note detection.

It teaches the app how **your** Roneat Ek actually sounds.

### Why Calibrate?

Every Roneat Ek is tuned a little differently.

Without calibration, the app falls back to theoretical default frequencies.

With calibration, it compares new recordings against spectral fingerprints captured from your own instrument.

That makes transcription dramatically more accurate.

### What Calibration Does

During calibration, the app:

1. Analyzes a recording of all 21 bars played in sequence.
2. Extracts a spectral fingerprint for each bar.
3. Saves a 1.5-second WAV sample for each bar.

After calibration, two features improve immediately:

* **Fingerprint matching** becomes available for transcription
* **Sample playback** becomes available for more realistic listening

### Recording for Calibration

Before you start:

* Use a quiet room with minimal echo
* Keep the microphone 30–60 cm from the instrument
* Strike each bar clearly
* Leave a 1–2 second gap between notes
* Record from bar 1 to bar 21, high to low
* Choose **Single mallet** or **Two mallets** mode
* For best results, create both recordings

Supported formats:

* WAV
* MP3
* FLAC

{% hint style="warning" %}
Do not include extra sounds between notes.

The engine needs exactly 21 clearly separated onsets.

If it detects more or fewer, calibration will fail.
{% endhint %}

### Running Calibration

1. Go to the **⚙ Settings** panel.
2. Click **Start Calibration**.
3. Select **Single mallet** or **Two mallets**.
4. Choose your calibration recording.
5. Wait for the progress bar to finish.
6. Confirm the success message.

When the process succeeds, the app shows:

`✅ X bars calibrated successfully.`

### After Calibration

After a successful run:

* Transcription uses **Fingerprint Matching Mode** automatically
* Playback can use your recorded samples
* You can recalibrate at any time
* New fingerprints replace the previous set

{% hint style="info" %}
Run calibration again after changing instruments, mallets, or recording setup.

Small timbre changes can affect matching quality.
{% endhint %}

### Troubleshooting

#### "Only X onsets detected, need 21"

Your notes were too close together.

Re-record with longer gaps.

#### Wrong notes still detected after calibration

Check the recording order.

It must be bar 1 through bar 21, high to low.

#### Calibration file location

Fingerprints are stored here:

`%APPDATA%\RoneatStudioPro\roneat_fingerprints.json`

See [Settings Overview](settings-overview.md) for storage details.
