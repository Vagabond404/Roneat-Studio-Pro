"""
Plugin Architecture Interfaces

Defines abstract base classes that enforce contracts for plugin development.
This ensures third-party plugins follow a consistent interface and prevents
crashes due to missing or incompatible implementations.
"""

from abc import ABC, abstractmethod


class InstrumentPluginBase(ABC):
    """
    Abstract base class for instrument plugins.

    All instrument plugins must inherit from this class and implement the required
    abstract methods. This enforces a contract that ensures compatibility with the
    Roneat Studio core engine.

    Methods:
        get_instrument_name(): Returns the display name of the instrument
        get_note_range(): Returns the minimum and maximum note numbers
        get_note_label(): Returns the label for a specific note
    """

    @abstractmethod
    def get_instrument_name(self) -> str:
        """
        Get the display name of the instrument.

        Returns:
            str: The user-friendly name of the instrument (e.g., "Roneat Ek")
        """
        pass

    @abstractmethod
    def get_note_range(self) -> tuple[int, int]:
        """
        Get the valid note range for this instrument.

        Returns:
            tuple[int, int]: A tuple of (min_note, max_note) where both are inclusive.
                            Example: (1, 21) for a 21-key instrument
        """
        pass

    @abstractmethod
    def get_note_label(self, note_numeric: int, notation_mode: str) -> str:
        """
        Get the label for a specific note.

        This method translates a numeric note index into a human-readable label.
        The label format depends on the notation_mode (e.g., "khmer", "numeric", "solfege").

        Args:
            note_numeric (int): The numeric note index (e.g., 1-21)
            notation_mode (str): The notation mode ("khmer", "numeric", "solfege", etc.)

        Returns:
            str: The label for the note (e.g., "ដូ", "1", "Do")

        Raises:
            ValueError: If note_numeric is outside the valid range or notation_mode is unsupported
        """
        pass

    @abstractmethod
    def get_midi_mapping(self) -> dict[int, int]:
        """
        Get the MIDI mapping for this instrument.

        Returns a dictionary that maps numeric bar/note positions to standard MIDI note numbers.
        This enables proper multisampling routing where each bar on the instrument maps to
        a specific pitch in the MIDI chromatic scale.

        Returns:
            dict[int, int]: A dictionary mapping note positions (e.g., 1-21) to MIDI note numbers.
                           Example for Roneat Ek: {1: 60, 2: 62, 3: 64, ..., 21: 84}
                           MIDI note 60 is Middle C (C4).
        """
        pass

    @abstractmethod
    def get_audio_sample(self, note: int, velocity: int = 100, mallets: int = 1) -> str | None:
        """
        Get the audio sample path for a specific note with optional velocity and mallet layers.

        This method returns the path to a specific .wav or .ogg file for the requested note,
        strike power (velocity), and mallet count. This enables high-fidelity studio multisampling
        with support for velocity layers and mallet variations.

        Args:
            note (int): The numeric note/bar position (e.g., 1-21 for Roneat Ek)
            velocity (int): Strike velocity/power (0-127, default 100). Allows different samples
                           based on how hard the instrument is struck.
            mallets (int): Number of mallets used (default 1). Enables different samples for
                          different mallet counts.

        Returns:
            str | None: The absolute or relative path to the audio sample file (e.g., "assets/audio/roneat_ek/1.wav").
                       Returns None if no sample exists for the given parameters.
                       The path can be relative to the project root or absolute.
        """
        pass

    def render_custom_2d_view(self, canvas, width: int, height: int) -> bool:
        """
        Render a custom 2D view on the canvas.

        This optional method allows instrument plugins to provide custom 2D visualizations.
        The default implementation returns False, meaning the standard flat grid rendering
        should be used. Plugins can override this to provide instrument-specific layouts
        (e.g., circular gong arrangements for Kong Thom).

        Args:
            canvas: The CustomTkinter canvas object where rendering should occur
            width (int): The width of the canvas in pixels
            height (int): The height of the canvas in pixels

        Returns:
            bool: True if custom rendering was performed (bypass default rendering),
                  False to use the standard flat grid rendering
        """
        return False

    def get_note_frequencies(self) -> dict[int, float]:
        """
        Get the frequency mappings for all notes in this instrument.

        This optional method allows instrument plugins to provide custom frequency mappings
        for audio synthesis. The default implementation returns an empty dict, which causes
        playback to use the default Roneat Ek frequencies as fallback.

        Returns:
            dict[int, float]: A dictionary mapping note numbers to frequencies in Hz.
                             Example: {1: 2000.0, 2: 1850.5, ..., 16: 600.0}
                             Return empty dict {} to use default fallback frequencies.
        """
        return {}
