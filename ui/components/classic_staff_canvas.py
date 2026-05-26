"""
ui/components/classic_staff_canvas.py
======================================
Roneat Studio Pro — Classic Western Staff Notation Canvas

Renders a scrollable, canvas-drawn Western music staff (5-line treble clef staves)
from a parsed Roneat Ek score (bars 1–21). Supports horizontal scrolling and
dynamically re-renders whenever the score changes.

Design rules:
  - NO grid boxes (CTkEntry), NO CTkFrame grid cells.
  - Pure tk.Canvas drawing only: create_line, create_oval, create_text, create_polygon.
  - Horizontally scrollable to accommodate long scores.
  - Bar 1  → C4 (Middle C)  — first ledger line below treble staff.
  - Bar 21 → A6 (top ledger lines above treble staff).

Pitch mapping (Roneat Ek bar index → Western note, diatonic C-major):
  Bar  1 = C4   Bar  2 = D4   Bar  3 = E4   Bar  4 = F4   Bar  5 = G4
  Bar  6 = A4   Bar  7 = B4   Bar  8 = C5   Bar  9 = D5   Bar 10 = E5
  Bar 11 = F5   Bar 12 = G5   Bar 13 = A5   Bar 14 = B5   Bar 15 = C6
  Bar 16 = D6   Bar 17 = E6   Bar 18 = F6   Bar 19 = G6   Bar 20 = A6
  Bar 21 = B6
"""

import tkinter as tk
import customtkinter as ctk
from typing import Optional

# ─── Staff layout constants ────────────────────────────────────────────────────
LINE_SPACING   = 10        # pixels between adjacent staff lines
STAFF_LINES    = 5         # standard 5-line staff
STAFF_HEIGHT   = (STAFF_LINES - 1) * LINE_SPACING   # 40 px from line 1 to line 5
STAFF_TOP_PAD  = 80        # space above each staff system (for high ledger notes)
STAFF_BOT_PAD  = 80        # space below each staff system (for low ledger notes + gap)
SYSTEM_HEIGHT  = STAFF_TOP_PAD + STAFF_HEIGHT + STAFF_BOT_PAD   # full row height

LEFT_MARGIN    = 72        # space for clef symbol
NOTE_SPACING   = 44        # horizontal distance between note positions
NOTEHEAD_RX    = 6         # notehead half-width
NOTEHEAD_RY    = 4         # notehead half-height
STEM_LENGTH    = 32        # stem height in pixels

# ─── Colour palette ────────────────────────────────────────────────────────────
PAGE_BG        = "#FAFAF6"   # parchment-like white
STAFF_LINE_COL = "#222222"   # dark ink
NOTE_COL       = "#1A1A1A"
LEDGER_COL     = "#222222"
CLEF_COL       = "#2A2A2A"
BARLINE_COL    = "#444444"
ACCENT_COL     = "#D4AF37"   # gold for playback highlight
REST_COL       = "#888888"
TEXT_COL       = "#333333"
CANVAS_BG      = "#1A1A1E"   # dark outer background (editor bg)


# ─── Pitch mapping engine ──────────────────────────────────────────────────────

# Each Roneat Ek bar maps to a Western diatonic degree.
# We use "staff step" counting from Middle C (C4).
# Staff step 0 = C4 (first ledger line below treble staff).
# Each step up = one diatonic note.
# Treble staff:
#   E4 = step 2  (bottom line)
#   G4 = step 4  (second line)
#   B4 = step 6  (middle line)
#   D5 = step 8  (fourth line)
#   F5 = step 10 (top line)

# Step → Y offset relative to the TOP of the treble staff (line 5).
# Line 5 (F5, top) is Y=0; each step down adds LINE_SPACING/2 px.
# step_to_y_offset(step) = (10 - step) * (LINE_SPACING / 2)
#   step 10 → 0   (F5, top line)
#   step  8 → 10  (D5, 4th line)
#   step  6 → 20  (B4, middle line)
#   step  4 → 30  (G4, 2nd line)
#   step  2 → 40  (E4, bottom line)
#   step  0 → 50  (C4, first ledger line below)

# Bar 1 = C4 = step 0, Bar 2 = D4 = step 1, … step +1 per bar.
# Bar 21 = B6 = step 20.

_BAR_TO_STEP: dict[int, int] = {bar: bar - 1 for bar in range(1, 22)}

# Note names for step index (for ledger-line logic)
_STEP_NAMES = ["C", "D", "E", "F", "G", "A", "B"]   # 7 diatonic notes

def _step_to_note_name(step: int) -> str:
    return _STEP_NAMES[step % 7]

def _step_to_y(step: int, staff_top_y: float) -> float:
    """
    Convert a staff-step integer to a canvas Y coordinate.

    Args:
        step:        Diatonic step from C4 (0=C4, 1=D4, 2=E4 … 20=B6).
        staff_top_y: Y coordinate of the TOP staff line (line 5 / F5).

    Returns:
        Pixel Y coordinate of the notehead centre.
    """
    # Top line (F5) is at step 10 relative to C4 = step 10 absolute.
    # Staff top_y is the pixel Y of that top line.
    # Each step from there:  y = staff_top_y + (10 - step) * half_spacing
    half = LINE_SPACING / 2
    return staff_top_y + (10 - step) * half


def roneat_bar_to_staff_y(bar_index: int, staff_top_y: float) -> float:
    """
    Public API: map a Roneat Ek bar number (1–21) to a canvas Y coordinate.

    Args:
        bar_index:   Roneat bar number (1–21).
        staff_top_y: Canvas Y of the topmost staff line.

    Returns:
        Canvas Y of the notehead centre.
    """
    step = _BAR_TO_STEP.get(bar_index, 0)
    return _step_to_y(step, staff_top_y)


def _needs_ledger_below(step: int) -> list[int]:
    """Return staff-step values that need ledger lines below the staff (< 2)."""
    lines = []
    s = 0   # C4 = step 0, first ledger below
    while s < 2 and s <= step:
        # Only add ledger at even steps (on the line, not in a space)
        if s % 2 == 0 and s <= step:
            lines.append(s)
        s += 2
    return lines


def _needs_ledger_above(step: int) -> list[int]:
    """Return staff-step values that need ledger lines above the staff (> 10)."""
    lines = []
    s = 12  # C6 = step 14… first ledger above is step 12 (G5 space is 11, A5 line is 12)
    while s <= step:
        if s % 2 == 0:
            lines.append(s)
        s += 2
    return lines


# ─── Duration visual types ─────────────────────────────────────────────────────
# Maps the string duration label from StepEntryController to drawing params.
DURATION_FILL: dict[str, bool] = {
    "Whole":       False,   # open notehead (whole note)
    "Half":        False,   # open notehead with stem (half note)
    "Quarter":     True,    # filled notehead
    "Eighth":      True,    # filled + flag
    "Sixteenth":   True,    # filled + double flag
}
DURATION_STEM: dict[str, bool] = {
    "Whole":       False,
    "Half":        True,
    "Quarter":     True,
    "Eighth":      True,
    "Sixteenth":   True,
}
DURATION_FLAGS: dict[str, int] = {
    "Whole":       0,
    "Half":        0,
    "Quarter":     0,
    "Eighth":      1,
    "Sixteenth":   2,
}


# ─── ClassicStaffCanvas ────────────────────────────────────────────────────────

class ClassicStaffCanvas(ctk.CTkFrame):
    """
    Scrollable Western staff notation canvas for Classic mode.

    Wraps a tk.Canvas inside a CTkFrame with horizontal and vertical scrollbars.
    Draws standard 5-line treble-clef staves with noteheads, stems, flags, and
    ledger lines derived from the current score notation text.

    Public API:
        render(events)      – Redraw the entire score from a list of event dicts.
        set_highlight(idx)  – Highlight the note at position idx (playback cursor).
    """

    def __init__(self, master, color_scheme: Optional[dict] = None, **kwargs):
        super().__init__(master, fg_color=CANVAS_BG, corner_radius=0, **kwargs)

        self._C = color_scheme or {}
        self._events: list[dict] = []
        self._highlight_idx: int = -1

        # Layout: canvas fills, scrollbars on right and bottom
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._hbar = tk.Scrollbar(self, orient="horizontal")
        self._hbar.grid(row=1, column=0, sticky="ew")

        self._vbar = tk.Scrollbar(self, orient="vertical")
        self._vbar.grid(row=0, column=1, sticky="ns")

        self.canvas = tk.Canvas(
            self,
            bg=CANVAS_BG,
            highlightthickness=0,
            xscrollcommand=self._hbar.set,
            yscrollcommand=self._vbar.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self._hbar.config(command=self.canvas.xview)
        self._vbar.config(command=self.canvas.yview)

        # Mouse-wheel scrolling
        self.canvas.bind("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * e.delta / 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>",
            lambda e: self.canvas.xview_scroll(int(-1 * e.delta / 120), "units"))

        # Initial empty render
        self.after(100, lambda: self.render([]))

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def render(self, events: list[dict]) -> None:
        """
        Redraw the entire canvas from a list of score event dicts.

        Args:
            events: List of dicts with keys:
                      bar        (int | None)  – None = rest
                      beats      (float)       – duration in beats
                      is_tremolo (bool)
                      repeat     (int)
                      duration   (str)         – optional: "Quarter", "Half", etc.
        """
        self._events = events
        self._redraw()

    def set_highlight(self, note_idx: int) -> None:
        """
        Highlight the notehead at position note_idx (playback cursor).

        Args:
            note_idx: Zero-based index into self._events; -1 to clear.
        """
        self._highlight_idx = note_idx
        self._redraw()

    # ──────────────────────────────────────────────────────────────────────────
    # Internal drawing
    # ──────────────────────────────────────────────────────────────────────────

    def _redraw(self) -> None:
        """Full canvas redraw from self._events."""
        self.canvas.delete("all")

        cw = self.canvas.winfo_width() or 900
        notes_per_row = max(4, (cw - LEFT_MARGIN * 2) // NOTE_SPACING)

        events = self._events
        total  = len(events)
        rows   = max(1, -(-total // notes_per_row))   # ceiling division

        # Total canvas size
        total_w = max(cw, LEFT_MARGIN + notes_per_row * NOTE_SPACING + 60)
        total_h = max(400, rows * SYSTEM_HEIGHT + 60)
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

        # Page background (parchment)
        page_x0 = 20
        page_x1 = total_w - 20
        page_y0 = 20
        page_y1 = total_h - 20
        self.canvas.create_rectangle(
            page_x0 + 4, page_y0 + 4, page_x1 + 4, page_y1 + 4,
            fill="#111116", outline=""
        )
        self.canvas.create_rectangle(
            page_x0, page_y0, page_x1, page_y1,
            fill=PAGE_BG, outline=STAFF_LINE_COL, width=1
        )

        idx = 0
        for row in range(rows):
            staff_top_y = page_y0 + 40 + row * SYSTEM_HEIGHT + STAFF_TOP_PAD
            staff_x0    = page_x0 + LEFT_MARGIN
            staff_x1    = page_x1 - 20

            self._draw_system(staff_x0, staff_x1, staff_top_y)

            row_events = events[idx: idx + notes_per_row]
            for i, ev in enumerate(row_events):
                note_x = staff_x0 + i * NOTE_SPACING + NOTE_SPACING // 2
                highlighted = (idx + i == self._highlight_idx)
                self._draw_event(ev, note_x, staff_top_y, highlighted)

            idx += notes_per_row

        # Empty-score placeholder
        if not events:
            self.canvas.create_text(
                total_w / 2, total_h / 2 - 60,
                text="♪  Classic Mode  ♪",
                font=("Georgia", 28, "bold"),
                fill=ACCENT_COL
            )
            self.canvas.create_text(
                total_w / 2, total_h / 2 - 20,
                text="Select a duration, then click the Virtual Keyboard to enter notes.",
                font=("Georgia", 13),
                fill=TEXT_COL
            )

    # ─── System (one staff row) ────────────────────────────────────────────────

    def _draw_system(self, x0: float, x1: float, staff_top_y: float) -> None:
        """Draw a complete 5-line staff system with opening barline and treble clef."""
        # 5 horizontal staff lines
        for i in range(STAFF_LINES):
            y = staff_top_y + i * LINE_SPACING
            self.canvas.create_line(x0, y, x1, y, fill=STAFF_LINE_COL, width=1)

        # Opening barline
        bot_y = staff_top_y + STAFF_HEIGHT
        self.canvas.create_line(x0, staff_top_y, x0, bot_y,
                                fill=STAFF_LINE_COL, width=2)

        # Treble clef (drawn as text glyph; Unicode ♩ family works in many fonts)
        clef_x = x0 - 44
        clef_y = staff_top_y + LINE_SPACING * 3   # centre on B4 line
        self.canvas.create_text(
            clef_x, clef_y,
            text="𝄞",          # U+1D11E MUSICAL SYMBOL G CLEF
            font=("Georgia", 52),
            fill=CLEF_COL,
            anchor="center"
        )

    # ─── Single note/rest event ────────────────────────────────────────────────

    def _draw_event(self, ev: dict, x: float, staff_top_y: float,
                    highlighted: bool = False) -> None:
        """Draw a single note or rest at horizontal position x."""
        bar      = ev.get("bar")
        duration = ev.get("duration", "Quarter")
        is_trem  = ev.get("is_tremolo", False)
        repeat   = ev.get("repeat", 1)

        col = ACCENT_COL if highlighted else NOTE_COL

        if bar is None:
            # Rest — draw a simple rest symbol
            self._draw_rest(x, staff_top_y, duration, col)
            return

        step   = _BAR_TO_STEP.get(bar, 0)
        note_y = _step_to_y(step, staff_top_y)

        # Ledger lines (below staff)
        if step < 2:
            for ls in range(0, step + 1, 2):
                if ls % 2 == 0:
                    ly = _step_to_y(ls, staff_top_y)
                    self.canvas.create_line(
                        x - NOTEHEAD_RX - 4, ly,
                        x + NOTEHEAD_RX + 4, ly,
                        fill=LEDGER_COL, width=1
                    )

        # Ledger lines (above staff)
        if step > 10:
            for ls in range(12, step + 1, 2):
                if ls % 2 == 0:
                    ly = _step_to_y(ls, staff_top_y)
                    self.canvas.create_line(
                        x - NOTEHEAD_RX - 4, ly,
                        x + NOTEHEAD_RX + 4, ly,
                        fill=LEDGER_COL, width=1
                    )

        # Stem direction: up if note is on or below middle line (B4, step=6)
        stem_up = step <= 6

        filled = DURATION_FILL.get(duration, True)
        has_stem = DURATION_STEM.get(duration, True)
        flags    = DURATION_FLAGS.get(duration, 0)

        # Notehead
        fill_col  = col if filled else PAGE_BG
        self.canvas.create_oval(
            x - NOTEHEAD_RX, note_y - NOTEHEAD_RY,
            x + NOTEHEAD_RX, note_y + NOTEHEAD_RY,
            fill=fill_col, outline=col, width=1
        )

        # Stem
        if has_stem:
            if stem_up:
                stem_x  = x + NOTEHEAD_RX - 1
                stem_y0 = note_y
                stem_y1 = note_y - STEM_LENGTH
            else:
                stem_x  = x - NOTEHEAD_RX + 1
                stem_y0 = note_y
                stem_y1 = note_y + STEM_LENGTH

            self.canvas.create_line(
                stem_x, stem_y0, stem_x, stem_y1,
                fill=col, width=1
            )

            # Flags (eighth = 1, sixteenth = 2)
            for f in range(flags):
                fy = stem_y1 + f * 8 * (1 if stem_up else -1)
                fx = stem_x + (16 if stem_up else -16)
                self.canvas.create_line(
                    stem_x, fy, fx, fy + 10 * (1 if stem_up else -1),
                    fill=col, width=2, smooth=True
                )

        # Tremolo ticks above notehead
        if is_trem and repeat > 1:
            tick_y = note_y - NOTEHEAD_RY - 6
            for t in range(min(repeat, 3)):
                ty = tick_y - t * 5
                self.canvas.create_line(
                    x - 5, ty, x + 5, ty,
                    fill=ACCENT_COL, width=1
                )

        # Bar index label (small, below)
        label_y = staff_top_y + STAFF_HEIGHT + 22
        self.canvas.create_text(
            x, label_y,
            text=str(bar),
            font=("Segoe UI", 8),
            fill=TEXT_COL,
            anchor="center"
        )

    # ─── Rest drawing ──────────────────────────────────────────────────────────

    def _draw_rest(self, x: float, staff_top_y: float,
                   duration: str, col: str) -> None:
        """Draw a rest symbol at position x."""
        mid_y = staff_top_y + STAFF_HEIGHT / 2

        if duration == "Whole":
            # Whole rest: filled rectangle hanging from 4th line
            ry = staff_top_y + LINE_SPACING   # hang from 2nd line
            self.canvas.create_rectangle(
                x - 8, ry, x + 8, ry + 6,
                fill=REST_COL, outline=""
            )
        elif duration == "Half":
            # Half rest: rectangle sitting on 3rd line
            ry = staff_top_y + LINE_SPACING * 2
            self.canvas.create_rectangle(
                x - 8, ry - 6, x + 8, ry,
                fill=REST_COL, outline=""
            )
        else:
            # Quarter / Eighth / Sixteenth: zigzag line
            pts = [
                x,      mid_y - 12,
                x + 6,  mid_y - 6,
                x - 2,  mid_y,
                x + 6,  mid_y + 6,
                x,      mid_y + 12,
            ]
            self.canvas.create_line(*pts, fill=REST_COL, width=2, smooth=False)
