---
description: >-
  Common questions about setup, transcription, exports, licensing, and
  troubleshooting.
---

# FAQ

Start here for quick answers.

If you still need help, use [Support & Contact](../troubleshooting-and-support/support-and-contact.md).

### Frequently Asked Questions

<details>

<summary><strong>What operating systems are supported?</strong></summary>

Roneat Studio Pro v2 supports **Windows 10** and **Windows 11** (64-bit).

macOS and Linux are not officially supported in the current release, though running from source code may work.

</details>

<details>

<summary><strong>Why is the first launch slow?</strong></summary>

On first launch, the app initializes audio drivers and pre-loads the analysis library, `librosa`.

This is a one-time process.

Subsequent launches are faster.

</details>

<details>

<summary><strong>My transcription has many wrong notes. What should I do?</strong></summary>

Complete the calibration step first.

It is the single biggest factor in transcription accuracy.

Also use a clean recording with minimal background noise, little reverb, and one clear instrument.

</details>

<details>

<summary><strong>Can I use Roneat Studio Pro for instruments other than the Roneat Ek?</strong></summary>

The score editor and calibration system can technically be adapted to other 21-note melodic percussion instruments.

However, the interface, notation system, and display are specifically designed for the Roneat Ek.

</details>

<details>

<summary><strong>What does the '#' symbol mean in notation?</strong></summary>

In Roneat Studio Pro, `#` does **not** mean sharp, as in Western notation.

It means **tremolo**.

`9#` means tremolo on bar 9.

`9#3` means 3 rapid strikes on bar 9.

</details>

<details>

<summary><strong>Can I sell scores I create with this software?</strong></summary>

The software is licensed for **non-commercial use**.

You may not use it to generate revenue under the standard license.

For commercial licensing inquiries, contact `contact@angelvisionlabs.com`.

</details>

<details>

<summary><strong>Where are my project files stored?</strong></summary>

You choose the save location when creating a `.roneat` project.

App data, such as settings, calibration data, and logs, is stored in `%APPDATA%\RoneatStudioPro\`.

</details>

<details>

<summary><strong>FFmpeg is missing and MP4 export does not work.</strong></summary>

If you installed the Windows release, FFmpeg is bundled already.

If you are running from source, download `ffmpeg.exe` and place it in the project root next to `main.py`.

</details>

<details>

<summary><strong>Can I undo changes in the Score Editor?</strong></summary>

Yes.

The Score Editor keeps a full undo and redo history.

Use `Ctrl+Z` for undo and `Ctrl+Y` for redo.

</details>
