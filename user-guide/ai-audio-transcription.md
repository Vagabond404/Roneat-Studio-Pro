---
description: Convert audio recordings into editable draft scores and clean the result.
---

# AI Audio Transcription

Roneat Studio Pro can analyze a recording and convert it into an editable draft score.

This feature is best used as a starting point, not as a final result.

### Supported Audio Formats

* WAV
* MP3
* FLAC

{% hint style="info" %}
For the best transcription quality, use a clean solo recording with minimal background noise.
{% endhint %}

### How Transcription Works

The analysis engine detects note onsets and pitch content from your recording.

It then maps those frequencies to the bars of the Roneat Ek and generates a draft score.

Because real performances include overtones and timing variation, some cleanup is usually needed afterward.

### Transcribe a Recording

{% stepper %}
{% step %}
### Open Audio to Score

Click the **Audio to Score** button in the main menu.

![](<../.gitbook/assets/image (8).png>)
{% endstep %}

{% step %}
### Choose your file

Select the recording you want to analyze.

Clear recordings produce better note detection.

![](<../.gitbook/assets/image (9).png>)
{% endstep %}

{% step %}
### Calibrate if needed

If your instrument does not match standard tuning exactly, adjust the calibration settings before analysis.

This helps the detector map notes more accurately.
{% endstep %}

{% step %}
### Run analysis

Click **Analyze** and wait for processing to finish.

A progress bar appears while the file is being analyzed.

![](<../.gitbook/assets/image (10).png>)
{% endstep %}

{% step %}
### Review and clean the result

The generated score is a draft.

Check for ghost notes, missed strikes, and timing offsets, then correct them in the editor.

![](<../.gitbook/assets/image (11).png>)
{% endstep %}
{% endstepper %}

### Best Practices

* Record a single instrument when possible
* Reduce room noise before analysis
* Calibrate first if note mapping looks shifted
* Review every phrase before exporting

Next, see [Settings Overview](settings-overview.md) for calibration details.
