---
description: A complete reference for the Roneat Studio Pro text notation system.
---

# Score Notation Reference

Roneat Studio Pro uses a simple text-based notation system.

Scores are written as space-separated tokens in the **Notes** text box.

Each token represents one event: a note, a rest, a tremolo, or a bar line.

### Overview

Use this page as the quick reference for writing and reading scores.

If you are new to the editor, start with [Interface Overview](interface-overview.md).

### Token Types

| Token | Meaning                                                | Example |
| ----- | ------------------------------------------------------ | ------- |
| `9`   | Play bar 9 for 1 beat                                  | `9`     |
| `9#`  | Play bar 9 as tremolo with the default repeat behavior | `9#`    |
| `9#3` | Play bar 9 as tremolo with 3 rapid strikes             | `9#3`   |
| `-`   | Rest for 1 beat                                        | `-`     |
| `0`   | Rest alias                                             | `0`     |
| `x`   | Rest alias                                             | `x`     |
| `/`   | Visual bar line only                                   | `/`     |

{% hint style="info" %}
Tokens are separated by spaces.

`9 8 7 / 6 - 5` is valid.

`987/6-5` is not.
{% endhint %}

### Bar Numbers

The Roneat Ek has **21 bars**.

Bar **1** is the highest pitch.

Bar **21** is the lowest pitch.

Valid note numbers are **1** through **21**.

Any numeric note token outside this range is flagged as invalid.

| Bar | Default Frequency (Hz) |
| --- | ---------------------: |
| 1   |                   1308 |
| 2   |                   1174 |
| 3   |                   1064 |
| 4   |                    977 |
| 5   |                    884 |
| 6   |                    791 |
| 7   |                    720 |
| 8   |                    655 |
| 9   |                    589 |
| 10  |                    536 |
| 11  |                    490 |
| 12  |                    444 |
| 13  |                    399 |
| 14  |                    359 |
| 15  |                    328 |
| 16  |                    295 |
| 17  |                    266 |
| 18  |                    243 |
| 19  |                    221 |
| 20  |                    198 |
| 21  |                    177 |

### Two-Mallet (Left Hand) Notation

When **Left Hand** mode is enabled in the Score Editor, the app computes the second hand automatically.

You do **not** write the left hand manually.

The app adds **bar +7** during playback and preview.

Example:

* Right hand `9`
* Left hand `16`

This is useful for fast review and teaching playback.

### Tremolo Notation

Use `#` to mark tremolo.

Examples:

* `9#` — Tremolo on bar 9
* `9#3` — Tremolo on bar 9 with 3 rapid strikes
* `9#8` — Tremolo on bar 9 with 8 rapid strikes

The number after `#` controls the strike count.

If no number is given, the default repeat behavior is used.

Playback speed is controlled by **Hits per second** in [Settings Overview](settings-overview.md).

### Rests and Silence

Use `-`, `0`, or `x` for silence.

Each rest token occupies **1 beat**.

Choose one style and stay consistent within a score.

### Bar Lines

Use `/` to insert a visual divider.

This helps readability in the live preview and exported PDF.

`/` does **not** add time or affect playback.

In PDF export, you can place bar lines manually with `/` or let the app group beats automatically.

### Example Score

```
9 8 7 6 / 5 4 3 2 / 1 - - - /
9# 8 7 6#3 / 5 4 - 3 /
```

In this example:

* `9 8 7 6` plays four descending bars
* `/` inserts a visual divider
* `1 - - -` plays bar 1, then three beats of silence
* `9#` plays a tremolo on bar 9
* `6#3` plays bar 6 with 3 rapid strikes
* `-` inserts a one-beat rest

### Validation

The Score Editor validates notation in real time.

Invalid tokens are shown in the validation panel.

Common issues:

* Bar number out of range, such as `25`
* Invalid tremolo repeat count outside `1` to `32`
* Unrecognized tokens, such as `9a`
* Missing spaces between tokens

{% hint style="warning" %}
`0` is valid only as a standalone rest token.

Use numbers `1` through `21` for notes.
{% endhint %}

Next, see [Working with Projects](working-with-projects.md) to learn how scores and embedded audio are saved together.
