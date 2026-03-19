---
description: >-
  Adjust appearance, playback, calibration, frequency presets, and file
  locations.
---

# Settings Overview

Use **⚙ Settings** to control how Roneat Studio Pro looks, sounds, and stores its data.

This is also where calibration is managed.

### 1. Appearance

#### Theme

Choose one of three appearance modes:

* **Dark**
* **Light**
* **System** — follows the current Windows theme setting

The default is **System**.

### 2. Audio & Playback

#### Playback Mode

Choose how notes are played back:

* **ADSR Synthesis** — The default. The app generates tones mathematically with a realistic xylophone timbre model.
* **Sample Playback** — Available after calibration. The app plays recorded WAV samples from your actual instrument.

Sample Playback gives the most realistic result.

#### BPM

This sets the default tempo for new projects.

#### Hits per second (tremolo)

This controls tremolo playback speed.

The default value is **16 hits/sec**.

### 3. Calibration

Calibration teaches the AI how your specific instrument sounds.

It is the most important step for accurate transcription.

#### How to calibrate

1. Click **Start Calibration** in the Settings panel.
2. Choose **Single mallet** or **Two mallets** mode.
3. Play each bar of the Roneat Ek in order, from bar 1 to bar 21.
4. Leave a clear gap between each note.
5. Let the engine detect 21 onsets and extract the data.

For each bar, the app stores:

* A spectral fingerprint for transcription matching
* A 1.5-second WAV sample for realistic playback

Saved locations:

* Fingerprints: `%APPDATA%\RoneatStudioPro\roneat_fingerprints.json`
* Samples: `%APPDATA%\RoneatStudioPro\samples\bar_XX.wav`

{% hint style="warning" %}
Make sure you record all 21 bars clearly and in order.

If the engine detects more or fewer than 21 onsets, calibration will fail or become inaccurate.
{% endhint %}

{% hint style="info" %}
For the best overall result, calibrate both **Single mallet** and **Two mallets** recordings.
{% endhint %}

### 4. Hz Frequency Presets

Advanced users can adjust the expected frequency for each bar manually.

This is useful when your Roneat follows a non-standard tuning map.

You can save and load these presets as JSON files.

### 5. File Locations

Roneat Studio Pro stores app data in these locations:

* **App data:** `%APPDATA%\RoneatStudioPro\`
* **Fingerprints:** `%APPDATA%\RoneatStudioPro\roneat_fingerprints.json`
* **Samples:** `%APPDATA%\RoneatStudioPro\samples\`
* **Settings:** `%APPDATA%\RoneatStudioPro\app_settings.json`
* **Log file:** `%APPDATA%\RoneatStudioPro\app.log`

Next, see [Calibration Guide](../guides/ai-audio-transcription/calibration-guide.md) or [AI Audio Transcription](../guides/ai-audio-transcription/).
