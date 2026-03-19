---
description: Solutions to the most common problems users encounter.
---

# Troubleshooting

Use this page when something does not behave as expected.

{% hint style="info" %}
Start with the log file: `%APPDATA%\RoneatStudioPro\app.log`

It often shows the exact failing component.
{% endhint %}

### The App Won't Launch

**Symptom:** Double-clicking the `exe` does nothing, or an error appears immediately.

#### Solutions

1. Make sure you are on Windows `10` or `11`, `64-bit`.
2. Right-click the `exe` and choose **Run as administrator** once.
3. Check the log file at `%APPDATA%\RoneatStudioPro\app.log` for error details.
4. If Windows SmartScreen blocks the app, click **More info** and then **Run anyway**. This is normal for newly released software.

{% hint style="warning" %}
A SmartScreen warning does not mean the app is malicious.

It is common for new Windows software.
{% endhint %}

### The App Is Stuck on the Splash Screen

**Symptom:** The splash screen appears but never closes.

**Cause:** The app loads `librosa`, a large audio analysis library, during startup. On slower machines, this can take `10–30` seconds on the first launch.

#### Solution

1. Wait.
2. Do not close the app.
3. Let the first launch finish.

Subsequent launches are faster because Python caches the compiled modules.

{% hint style="warning" %}
If the splash screen stays for more than `2` minutes, check `app.log` for a Python import error.

This usually means the installation is corrupted.

Reinstall the app.
{% endhint %}

### No Sound During Playback

**Symptom:** `Play` is pressed but nothing is heard.

#### Solutions

1. Check that your system audio is not muted and the correct output device is selected in Windows.
2. Make sure no other app has exclusive control of the audio device.
3. Try switching `Playback Mode` from `Sample Playback` to `ADSR Synthesis` in `Settings`. `Sample Playback` requires calibration data. If samples are missing, it produces silence.
4. Check `app.log` for `sounddevice` errors.

### Transcription Gives Mostly Wrong Notes

**Symptom:** After running Audio AI, most of the detected bars are incorrect.

#### Solutions

1. **Complete calibration first.** This is the most common cause. Without calibration, the app uses generic pitch detection which is sensitive to tuning variations.
2. **Use a cleaner recording.** Background noise, reverb, and room echo all confuse onset detection. Record as close to the instrument as practical.
3. **Check recording levels.** If the audio is too quiet, below `-20 dB` peak, or too loud and clipping, onset detection becomes unreliable.
4. **Match the `Two mallets` setting to the recording.** Using the wrong mode degrades fingerprint matching accuracy.

{% hint style="info" %}
Calibration has the biggest impact on accuracy.

Do it before spending time cleaning up a bad draft.
{% endhint %}

### Calibration Fails — `Only X onsets detected, need 21`

**Symptom:** Calibration stops and shows this error message.

**Cause:** The audio contained fewer clearly separated onsets than expected.

#### Solutions

1. Re-record the calibration sequence with a longer pause, `2–3` seconds, between each bar.
2. Avoid letting the resonance of one bar overlap into the next.
3. Do not add any extra sounds between bars, including coughs, string buzz, or accidental hits.
4. Make sure you play exactly `21` bars, in order from bar `1` highest to bar `21` lowest.

### PDF Export Is Blank or Cuts Off Early

**Symptom:** The exported PDF has no notes or stops partway through.

#### Solutions

1. Make sure the Notes text box actually contains notation text before exporting.
2. Check for validation errors in the editor. Invalid tokens may cause the parser to stop early.
3. Try reducing the `Columns per row` setting if notes are overflowing the page margins.

### MP4 Export Fails or Produces No File

**Symptom:** The MP4 export dialog completes but no file appears, or an error is shown.

**Most likely cause:** `FFmpeg` is missing or not found.

#### Solutions

1. If you are using the Windows installer, verify the installation was not corrupted by reinstalling.
2. If you are running from source, download `ffmpeg.exe` and place it in the root project folder next to `main.py`.
3. Check `app.log` for a `FileNotFoundError` mentioning `ffmpeg`.

{% hint style="warning" %}
`FFmpeg` is required for MP4 export.

Without it, the export cannot produce a video file.
{% endhint %}

### The `.roneat` File Won't Open

**Symptom:** Double-clicking a `.roneat` file does nothing, or the app opens but the project does not load.

#### Solutions

1. Try using **📂 Load Project** inside the app instead of double-clicking.
2. Make sure the `.roneat` file is not corrupted. Try opening it with a ZIP tool such as `7-Zip`. It should contain `data.json`.
3. If the file was created with an older version of the app, `v1` plain JSON format, it is still compatible. Try loading it manually through the Load dialog.
4. Check `app.log` for a JSON or ZIP read error.

### Playback Tempo Is Wrong After Importing from Audio

**Symptom:** After importing a transcribed score, playback is too fast or too slow.

**Explanation:** When a score is imported from audio analysis, sync data, the exact timing of each note, is attached. Playback follows the original recording's tempo, not the `BPM` field. The `BPM` field will be grayed out and you will see `⏱ Synced playback loaded`.

#### Solution

1. Clear the Notes box.
2. Re-paste the notation text manually.
3. Confirm that the sync data is detached.
4. Edit the `BPM` field again.

{% hint style="info" %}
Use synced playback when you want the original performance timing.

Detach sync only when you want fixed-tempo playback.
{% endhint %}

### Still Having Issues?

1. Check the log file at `%APPDATA%\RoneatStudioPro\app.log`.
2. Gather the exact error message, if one appears.
3. Visit [Support & Contact](support-and-contact.md).
