"""
core/rendering/translation.py
================================
NotationTranslator — bidirectional mapping between Roneat bar indices (1-21)
and their visual string representations in the three notation modes.

Design contract
---------------
- The data model (ScoreManager / notes_box) ALWAYS stores raw integers 1-21.
- The UI and export layers call index_to_string() for display only.
- Cell editors call string_to_index() to convert user input back to an integer
  before writing to the model.
- Duplicate-note ambiguity (e.g. "Sol" appears 3×) is resolved by returning the
  middle-octave index, unless the caller provides an explicit octave qualifier.
"""

from __future__ import annotations

# ── Canonical mappings (index 1-21 → display string) ──────────────────────
SYLLABIC_MAP: dict[int, str] = {
    1: "Sol", 2: "La",  3: "Si",  4: "Do",  5: "Re",  6: "Mi",  7: "Fa",
    8: "Sol", 9: "La", 10: "Si", 11: "Do", 12: "Re", 13: "Mi", 14: "Fa",
    15: "Sol", 16: "La", 17: "Si", 18: "Do", 19: "Re", 20: "Mi", 21: "Fa",
}

LETTERS_MAP: dict[int, str] = {
    1: "G",  2: "A",  3: "B",  4: "C",  5: "D",  6: "E",  7: "F",
    8: "G",  9: "A", 10: "B", 11: "C", 12: "D", 13: "E", 14: "F",
    15: "G", 16: "A", 17: "B", 18: "C", 19: "D", 20: "E", 21: "F",
}

# ── Reverse maps: normalised string → list[int] (ascending) ───────────────
def _build_reverse(fwd: dict[int, str]) -> dict[str, list[int]]:
    rev: dict[str, list[int]] = {}
    for idx, label in fwd.items():
        rev.setdefault(label.lower(), []).append(idx)
    for lst in rev.values():
        lst.sort()
    return rev

_SYLLABIC_REV = _build_reverse(SYLLABIC_MAP)
_LETTERS_REV  = _build_reverse(LETTERS_MAP)

# Accepted syllable spellings (aliases → canonical)
_SYLLABIC_ALIASES: dict[str, str] = {
    "do": "do", "ré": "re", "re": "re", "mi": "mi",
    "fa": "fa", "sol": "sol", "la": "la", "si": "si", "ti": "si",
}


class NotationTranslator:
    """
    Stateless utility class for converting between bar indices and notation strings.

    All methods are class-methods so the class never needs to be instantiated.

    Octave suffixes
    ---------------
    Because all 7 note names repeat 3 times across the 21-bar range, the
    forward conversion appends a digit suffix (1, 2, or 3) so every label is
    unique and round-trips are lossless:

        Bar  1 → G1 / Sol1     Bar  8 → G2 / Sol2     Bar 15 → G3 / Sol3
        Bar  7 → F1 / Fa1      Bar 14 → F2 / Fa2      Bar 21 → F3 / Fa3

    The reverse parser accepts with OR without the suffix.  When the suffix is
    absent it falls back to *prefer_octave* (default: middle octave 2).
    """

    # ── Forward translation ────────────────────────────────────────────────

    @classmethod
    def index_to_string(cls, index: int, mode: str) -> str:
        """
        Convert a bar index (1-21) to its display string for *mode*.

        For Letters and Syllabic the result includes a numeric octave suffix
        (e.g. ``G2``, ``Sol2``) so the mapping is injective (no ambiguity).

        Parameters
        ----------
        index : int  — Roneat bar number [1, 21]
        mode  : str  — "Numeric", "Letters", or "Syllabic"

        Returns
        -------
        str — formatted label; falls back to str(index) for unknown modes.
        """
        if not isinstance(index, int) or not (1 <= index <= 21):
            return str(index) if index is not None else ""

        if mode == "Numeric":
            return str(index)

        octave = ((index - 1) // 7) + 1   # 1, 2, or 3

        if mode == "Letters":
            return f"{LETTERS_MAP[index]}{octave}"
        if mode == "Syllabic":
            return f"{SYLLABIC_MAP[index]}{octave}"
        return str(index)

    # ── Reverse translation ────────────────────────────────────────────────

    @classmethod
    def string_to_index(cls, value: str, mode: str,
                        prefer_octave: int | None = None) -> int | None:
        """
        Convert a user-typed string back to a bar index (1-21).

        For *Numeric* mode the string must be a plain integer in [1, 21].

        For *Letters* / *Syllabic* mode the optional trailing digit suffix
        ``1`` / ``2`` / ``3`` disambiguates the octave.  Without a suffix,
        *prefer_octave* is used (default: middle octave 2).

        Parameters
        ----------
        value        : str           — raw user input (case-insensitive).
        mode         : str           — active notation mode.
        prefer_octave: int | None    — 1, 2, or 3 to force a specific octave.

        Returns
        -------
        int | None — bar index 1-21, or *None* if the value cannot be parsed.
        """
        v = value.strip()
        if not v:
            return None

        # ── Numeric ──────────────────────────────────────────────────────
        if mode == "Numeric":
            if v.isdigit() and 1 <= int(v) <= 21:
                return int(v)
            return None

        # ── Strip optional trailing octave digit ─────────────────────────
        import re as _re
        oct_m = _re.match(r'^(.+?)([123])$', v)
        if oct_m:
            note_str = oct_m.group(1)
            prefer_octave = int(oct_m.group(2))
        else:
            note_str = v

        # ── Letters ──────────────────────────────────────────────────────
        if mode == "Letters":
            candidates = _LETTERS_REV.get(note_str.lower(), [])
            return cls._pick_octave(candidates, prefer_octave)

        # ── Syllabic ─────────────────────────────────────────────────────
        if mode == "Syllabic":
            normalised = _SYLLABIC_ALIASES.get(note_str.lower())
            if normalised is None:
                return None
            candidates = _SYLLABIC_REV.get(normalised, [])
            return cls._pick_octave(candidates, prefer_octave)

        return None

    # ── Validation helpers ─────────────────────────────────────────────────

    @classmethod
    def is_valid_input(cls, value: str, mode: str) -> bool:
        """Return True if *value* is a recognised notation string for *mode*."""
        return cls.string_to_index(value, mode) is not None

    @classmethod
    def valid_hints(cls, mode: str) -> str:
        """Return a short human-readable hint of valid inputs for *mode*."""
        if mode == "Numeric":
            return "1 – 21"
        if mode == "Letters":
            return "G1 A1 B1 C1 D1 E1 F1  (octave 1/2/3 suffix)"
        if mode == "Syllabic":
            return "Sol1 La1 Si1 Do1 Re1 Mi1 Fa1  (octave 1/2/3 suffix)"
        return ""

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _pick_octave(candidates: list[int], prefer_octave: int | None) -> int | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        if prefer_octave is not None:
            idx = prefer_octave - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        # Default: middle candidate
        return candidates[len(candidates) // 2]


# ── Legacy compatibility shim ─────────────────────────────────────────────────
# Old call-sites use:  translate_note(note_val, active_mode)

def translate_note(note_val: int, active_mode: str) -> str:
    """Thin wrapper kept for backward-compat. Prefer NotationTranslator.index_to_string()."""
    return NotationTranslator.index_to_string(note_val, active_mode)
