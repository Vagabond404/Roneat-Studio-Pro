"""
Roneat Ek Instrument Plugin

Implements the standard Roneat Ek (Cambodian bamboo xylophone) with 21 keys.
Provides note mapping, labels, and instrument-specific functionality.
"""

import logging
from typing import Optional

# Import the abstract base class - this will be available from the core plugin_engine
# In a real scenario, we'd do: from core.plugin_engine import InstrumentPluginBase
# For plugin isolation, we define the interface here
try:
    from core.plugin_engine import InstrumentPluginBase
except ImportError:
    # Fallback: define a minimal interface if the import fails
    class InstrumentPluginBase:
        """Minimal interface fallback for plugin isolation."""
        pass

logger = logging.getLogger(__name__)


class RoneatEkPlugin(InstrumentPluginBase):
    """
    Roneat Ek Instrument Plugin

    Implements the standard 21-key Roneat Ek (Cambodian bamboo xylophone).
    This plugin provides note mapping, labels in multiple notation modes,
    and instrument-specific metadata.

    Attributes:
        NOTES (list[str]): Khmer names for each of the 21 keys
        MIN_NOTE (int): Minimum note number (1)
        MAX_NOTE (int): Maximum note number (21)
    """

    # Khmer note names (ដើម, ឌ, ឌ៉ា, ណ, ណ៉ា, ត, ត៉ា, ដូ, ដូ៉ា, ត, ត៉ា, ទ, ទ៉ា, ទ់, ធ, ធ៉ា, ន, ន៉ា, ប, ប៉ា, ផ)
    NOTES_KHMER = [
        "ដើម",  # 1
        "ឌ",    # 2
        "ឌ៉ា",   # 3
        "ណ",    # 4
        "ណ៉ា",   # 5
        "ត",    # 6
        "ត៉ា",   # 7
        "ដូ",   # 8
        "ដូ៉ា",  # 9
        "ត",    # 10
        "ត៉ា",   # 11
        "ទ",    # 12
        "ទ៉ា",   # 13
        "ទ់",    # 14
        "ធ",    # 15
        "ធ៉ា",   # 16
        "ន",    # 17
        "ន៉ា",   # 18
        "ប",    # 19
        "ប៉ា",   # 20
        "ផ",    # 21
    ]

    # Solfege names (Do, Re, Mi, Fa, Sol, La, Si, Do, ...)
    NOTES_SOLFEGE = [
        "Do",    # 1
        "Re",    # 2
        "Mi",    # 3
        "Fa",    # 4
        "Sol",   # 5
        "La",    # 6
        "Si",    # 7
        "Do",    # 8
        "Re",    # 9
        "Mi",    # 10
        "Fa",    # 11
        "Sol",   # 12
        "La",    # 13
        "Si",    # 14
        "Do",    # 15
        "Re",    # 16
        "Mi",    # 17
        "Fa",    # 18
        "Sol",   # 19
        "La",    # 20
        "Si",    # 21
    ]

    MIN_NOTE = 1
    MAX_NOTE = 21

    def __init__(self) -> None:
        """Initialize the Roneat Ek plugin."""
        self.plugin_id = "roneat_ek_standard"
        self.plugin_name = "Roneat Ek (Standard)"
        self.instrument_name = "Roneat Ek"
        logger.info(f"Initializing {self.plugin_name}")

    def get_instrument_name(self) -> str:
        """
        Get the display name of the instrument.

        Returns:
            str: "Roneat Ek"
        """
        return self.instrument_name

    def get_note_range(self) -> tuple[int, int]:
        """
        Get the valid note range for Roneat Ek.

        Returns:
            tuple[int, int]: (1, 21) representing the 21-key range
        """
        return (self.MIN_NOTE, self.MAX_NOTE)

    def get_note_label(self, note_numeric: int, notation_mode: str) -> str:
        """
        Get the label for a specific note.

        Translates a numeric note index into a human-readable label based on the
        notation mode. Supports multiple notation systems: Khmer, numeric, and solfege.

        Args:
            note_numeric (int): The note index (1-21)
            notation_mode (str): The notation mode to use:
                - "khmer": Khmer script labels (ដើម, ឌ, etc.)
                - "numeric": Simple numeric labels (1, 2, 3, ...)
                - "solfege": Musical solfege (Do, Re, Mi, ...)

        Returns:
            str: The label for the note

        Raises:
            ValueError: If note_numeric is outside the range 1-21 or notation_mode
                       is not recognized
        """
        # Validate note range
        if not (self.MIN_NOTE <= note_numeric <= self.MAX_NOTE):
            raise ValueError(
                f"Note {note_numeric} is outside valid range "
                f"({self.MIN_NOTE}-{self.MAX_NOTE})"
            )

        # Convert to 0-based index
        index = note_numeric - 1

        # Return label based on notation mode
        if notation_mode.lower() == "khmer":
            return self.NOTES_KHMER[index]
        elif notation_mode.lower() == "numeric":
            return str(note_numeric)
        elif notation_mode.lower() == "solfege":
            return self.NOTES_SOLFEGE[index]
        else:
            raise ValueError(
                f"Notation mode '{notation_mode}' not supported. "
                f"Valid modes: khmer, numeric, solfege"
            )

    def get_midi_mapping(self) -> dict[int, int]:
        """
        Get the MIDI mapping for Roneat Ek bars.

        Maps the 21 bars to MIDI notes spanning from MIDI 84 (C6, highest)
        to MIDI 50 (D3, lowest), covering approximately 3 octaves suitable for
        a bamboo xylophone.

        Returns:
            dict[int, int]: Mapping of bar numbers (1-21) to MIDI note numbers
        """
        # Hardcoded MIDI mapping for 21 bars, roughly 1.6-2 semitones apart
        # This provides a natural spread across the instrument's pitch range
        return {
            1: 84, 2: 82, 3: 81, 4: 79, 5: 77, 6: 76, 7: 74, 8: 72, 9: 71, 10: 69,
            11: 67, 12: 66, 13: 64, 14: 62, 15: 61, 16: 59, 17: 57, 18: 56, 19: 54, 20: 52,
            21: 50
        }

    def get_audio_sample(self, note: int, velocity: int = 100, mallets: int = 1) -> str | None:
        """
        Get the audio sample path for a Roneat Ek bar.

        Always uses the 'med' (medium) velocity layer for consistent,
        natural-sounding playback without hard or soft intensity switching.

        Args:
            note (int): The bar number (1-21)
            velocity (int): Ignored — always uses medium layer.
            mallets (int): Number of mallets (1 or 2).

        Returns:
            str | None: Path to the audio sample. Returns None if note is outside range.
        """
        import os

        if not (self.MIN_NOTE <= note <= self.MAX_NOTE):
            return None

        # Always use 'med' layer — one consistent intensity
        pro_path_rel = f"assets/audio/roneat_ek/pro/note{note}_{mallets}m_med.wav"

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        pro_path_abs = os.path.join(project_root, pro_path_rel)

        if os.path.exists(pro_path_abs):
            return pro_path_rel

        # Fallback to legacy path format
        return f"assets/audio/roneat_ek/{note}.wav"

    def initialize(self) -> bool:
        """
        Initialize the plugin and validate its state.

        Returns:
            bool: True if initialization succeeds, False otherwise
        """
        try:
            logger.info(
                f"{self.plugin_name} initialized successfully with "
                f"{self.MAX_NOTE} keys"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def shutdown(self) -> None:
        """Perform cleanup when the plugin is being unloaded."""
        logger.info(f"{self.plugin_name} shutting down")


# Module-level plugin instance
_plugin_instance: Optional[RoneatEkPlugin] = None


def get_plugin() -> RoneatEkPlugin:
    """
    Get or create the singleton Roneat Ek plugin instance.

    Returns:
        RoneatEkPlugin: The Roneat Ek plugin instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = RoneatEkPlugin()
    return _plugin_instance
