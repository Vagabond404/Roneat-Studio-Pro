---
description: Export scores as PDF or MP4 and choose the right output settings.
---

# Exporting (PDF & Video)

Roneat Studio Pro supports two export formats:

* **PDF** for print-ready notation
* **MP4** for synchronized scrolling score videos

### Before You Export

Check these items first:

1. Confirm the score text is final.
2. Review the live preview for errors.
3. Set the correct title.
4. Confirm whether playback should use synthesized or synced audio.

### PDF Export

The PDF export dialog includes these options:

* **Title** — Pulled automatically from the Score Editor title field
* **Composer name** — Optional. Shown on the cover page
* **Show Cover Page** — Adds a decorative cover page with title, composer, and date
* **Columns per row** — Number of note cells per row. Default: `16`
* **Measure mode** — Draw bar lines every 4 beats, every 8 beats, or use **Manual** mode with `/`
* **Show left-hand notation** — Displays the computed left-hand bar number below each right-hand note in smaller blue text
* **Show row numbers** — Adds a row index on the left of each grid row
* **Accent color** — Sets the note number color. Default: gold `#c8a96e`
* **Font size override** — Lets you set the note number size manually

{% hint style="info" %}
Tremolo tokens such as `9#3` are shown as `9~3` in the PDF grid.
{% endhint %}

### MP4 Video Export

MP4 export creates a scrolling score video synchronized to audio.

Key points:

* The video shows the score grid scrolling in time
* The audio track is either synthesized from the score or taken from the original embedded recording
* The output file is a standard **H.264 MP4**
* Rendering uses **FFmpeg**, which is bundled with the Windows installer
* Typical uses include YouTube uploads, teaching material, and social clips

{% hint style="info" %}
FFmpeg is required for MP4 export. It is included in the Windows installer. If you are running from source code, place `ffmpeg.exe` in the root project folder.
{% endhint %}

{% hint style="warning" %}
Video export can take time.

It is CPU-intensive, especially on long scores.

Do not close the app while rendering is in progress.
{% endhint %}

### Which Export Should You Use?

* Use **PDF** for printing, archiving, and score review
* Use **MP4** for guided playback, lessons, and online sharing

If your score started from a recording, review [AI Audio Transcription](ai-audio-transcription/) and [Working with Projects](working-with-projects.md) first.
