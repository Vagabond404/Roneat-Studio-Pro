"""
Kong Thom Instrument Plugin

Implements the Kong Thom (Cambodian circular gong chime) with 16 bossed gongs.
Provides custom circular 2D visualization with semicircular gong arrangement.
"""

import logging
import math
from typing import Optional

try:
    from core.plugin_engine import InstrumentPluginBase
except ImportError:
    class InstrumentPluginBase:
        """Minimal interface fallback for plugin isolation."""
        pass

logger = logging.getLogger(__name__)


class KongThomPlugin(InstrumentPluginBase):
    """
    Kong Thom Instrument Plugin

    Implements the 16-key Kong Thom (Cambodian circular gong chime).
    Features a custom circular 2D visualization with gongs arranged
    in a semicircular arc, with dynamic scaling to fit the canvas.

    Attributes:
        NOTES (list[str]): Numeric labels for each of the 16 gongs
        MIN_NOTE (int): Minimum note number (1)
        MAX_NOTE (int): Maximum note number (16)
    """

    # Gong labels (numeric 1-16)
    NOTES_NUMERIC = [str(i) for i in range(1, 17)]

    # Solfege names
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
    ]

    MIN_NOTE = 1
    MAX_NOTE = 16

    def __init__(self) -> None:
        """Initialize the Kong Thom plugin."""
        self.plugin_id = "kong_thom"
        self.plugin_name = "Kong Thom"
        self.instrument_name = "Kong Thom"
        logger.info(f"Initializing {self.plugin_name}")

    def get_instrument_name(self) -> str:
        """
        Get the display name of the instrument.

        Returns:
            str: "Kong Thom"
        """
        return self.instrument_name

    def get_note_range(self) -> tuple[int, int]:
        """
        Get the valid note range for Kong Thom.

        Returns:
            tuple[int, int]: (1, 16)
        """
        return (self.MIN_NOTE, self.MAX_NOTE)

    def get_note_label(self, note_numeric: int, notation_mode: str = "numeric") -> str:
        """
        Get the label for a specific gong.

        Args:
            note_numeric (int): The gong number (1-16)
            notation_mode (str): The notation mode ("numeric" or "solfege")

        Returns:
            str: The label for the gong

        Raises:
            ValueError: If note_numeric is outside the valid range
        """
        if note_numeric < self.MIN_NOTE or note_numeric > self.MAX_NOTE:
            raise ValueError(f"Note {note_numeric} is outside valid range ({self.MIN_NOTE}-{self.MAX_NOTE})")

        idx = note_numeric - 1

        if notation_mode == "solfege":
            return self.NOTES_SOLFEGE[idx]
        elif notation_mode == "numeric":
            return self.NOTES_NUMERIC[idx]
        else:
            # Default to numeric for unknown modes
            return self.NOTES_NUMERIC[idx]

    def get_midi_mapping(self) -> dict[int, int]:
        """
        Get the MIDI mapping for Kong Thom gongs.

        Maps the 16 gongs to MIDI notes spanning from MIDI 81 (A5, highest)
        to MIDI 57 (A3, lowest), covering approximately 2 octaves suitable for
        a circular gong chime with higher metallic pitches.

        Returns:
            dict[int, int]: Mapping of gong numbers (1-16) to MIDI note numbers
        """
        # MIDI mapping for 16 gongs with higher metallic pitches
        # Gongs 1-8: lower left arc (lower pitches)
        # Gongs 9-16: upper right arc (higher pitches)
        return {
            1: 57, 2: 59, 3: 60, 4: 62, 5: 64, 6: 65, 7: 67, 8: 69,
            9: 71, 10: 72, 11: 74, 12: 76, 13: 77, 14: 79, 15: 81, 16: 83
        }

    def get_audio_sample(self, note: int, velocity: int = 100, mallets: int = 1) -> str | None:
        """
        Get the audio sample path for a Kong Thom gong.

        Returns the path to a .wav file for the requested gong note. Currently ignores
        velocity and mallet parameters as a basic implementation. These will be
        leveraged in future versions for high-fidelity multisampling support.

        Args:
            note (int): The gong number (1-16)
            velocity (int): Strike velocity (0-127, default 100). Currently ignored.
            mallets (int): Number of mallets (default 1). Currently ignored.

        Returns:
            str | None: Path to the audio sample (e.g., "assets/audio/kong_thom/1.wav").
                       Returns None if note is outside valid range.
        """
        # Validate note range
        if not (self.MIN_NOTE <= note <= self.MAX_NOTE):
            return None

        # Return legacy path format
        # Velocity and mallets are ignored for now but can be extended later
        return f"assets/audio/kong_thom/{note}.wav"

    def get_note_at_xy(self, x: int, y: int, width: int, height: int) -> int | None:
        """
        Detect which gong was clicked at the given canvas coordinates.

        Uses circular hit detection for the gongs arranged in the semicircular arc layout.

        Args:
            x (int): Canvas x coordinate of the click
            y (int): Canvas y coordinate of the click
            width (int): Canvas width in pixels
            height (int): Canvas height in pixels

        Returns:
            int | None: The gong number (1-16) if a gong was clicked, None otherwise
        """
        try:
            # Layout parameters match render_custom_2d_view()
            center_x = width / 2
            center_y = height * 0.65

            # Calculate the radius
            usable_width = width * 0.85
            usable_height = height * 0.65
            radius = min(usable_width / 2, usable_height) * 0.9

            # Gong radius for hit detection (same as in render_custom_2d_view)
            gong_radius = max(8, radius / 20)

            # Angular range
            start_angle_deg = 20
            end_angle_deg = 160
            total_arc_deg = end_angle_deg - start_angle_deg
            angle_per_gong = total_arc_deg / (self.MAX_NOTE - 1)

            # Check each gong for hit detection
            for gong_num in range(self.MIN_NOTE, self.MAX_NOTE + 1):
                angle_deg = start_angle_deg + ((gong_num - 1) * angle_per_gong)
                angle_rad = math.radians(angle_deg)

                # Position of gong center
                gong_x = center_x + radius * math.cos(angle_rad)
                gong_y = center_y - radius * math.sin(angle_rad)

                # Calculate distance from click to gong center
                dx = x - gong_x
                dy = y - gong_y
                dist = math.sqrt(dx * dx + dy * dy)

                # Check if click is within gong radius (with 2px tolerance)
                if dist <= gong_radius + 2:
                    return gong_num

            return None

        except Exception as e:
            logger.error(f"Error in get_note_at_xy: {e}")
            return None

    def get_note_frequencies(self) -> dict[int, float]:
        """
        Get the frequency mappings for Kong Thom gongs.
        
        Kong Thom uses higher-pitched metallic bell frequencies compared to the
        wooden bars of Roneat Ek. The gongs are arranged with lower notes on
        the left arc and higher notes on the right arc.
        
        Returns:
            dict[int, float]: Mapping of gong numbers (1-16) to frequencies in Hz
        """
        # Higher-pitched metallic bell frequencies for Kong Thom
        # Gongs 1-8: left arc (lower pitches)
        # Gongs 9-16: right arc (higher pitches)
        return {
            1:  880.0,    # 880 Hz (A5 - higher than Roneat's lowest)
            2:  932.3,    # 932 Hz
            3:  987.8,    # 987 Hz
            4:  1046.5,   # 1046 Hz (C6)
            5:  1108.7,   # 1108 Hz
            6:  1174.7,   # 1174 Hz
            7:  1244.5,   # 1244 Hz
            8:  1318.5,   # 1318 Hz
            9:  1396.9,   # 1396 Hz
            10: 1479.98,  # 1479 Hz (B5)
            11: 1567.98,  # 1567 Hz
            12: 1661.2,   # 1661 Hz
            13: 1760.0,   # 1760 Hz (A6 - double of gong 1)
            14: 1864.7,   # 1864 Hz
            15: 1975.5,   # 1975 Hz
            16: 2093.0,   # 2093 Hz (C7 - bright metallic)
        }

    def render_custom_2d_view(self, canvas, width: int, height: int) -> bool:
        """
        Render a custom circular 2D view of Kong Thom on the canvas.

        Draws 16 gongs arranged in a U-shaped semicircle, with gongs 1-8 on the
        left arc and gongs 9-16 on the right arc. The layout scales dynamically
        to fit the canvas dimensions.

        Args:
            canvas: The CustomTkinter canvas object
            width (int): Canvas width in pixels
            height (int): Canvas height in pixels

        Returns:
            bool: Always returns True (custom rendering handled)
        """
        try:
            # Determine color scheme based on current theme
            try:
                import customtkinter as ctk
                is_dark = ctk.get_appearance_mode() == "Dark"
            except Exception:
                is_dark = True

            # Color palette
            bg_col = "#121212" if is_dark else "#F5F5F5"
            gong_face = "#D2B48C" if is_dark else "#E8D4B8"
            gong_shadow = "#8B4513" if is_dark else "#A0826D"
            gong_highlight = "#F5F5F5" if is_dark else "#FEFEFE"
            active_gong = "#C8A96E" if is_dark else "#D4A574"
            text_color = "#C8A96E" if is_dark else "#8B4513"
            cord_color = "#444444" if is_dark else "#777777"

            # Clear canvas and set background
            canvas.delete("all")
            canvas.create_rectangle(0, 0, width, height, fill=bg_col, outline="")

            # Layout parameters: semicircle arc from left to right
            # The gongs will be arranged in a U-shape
            center_x = width / 2
            center_y = height * 0.65  # Position center lower for better spacing

            # Calculate the radius to fit within canvas
            # Leave padding for labels and spacing
            usable_width = width * 0.85
            usable_height = height * 0.65
            radius = min(usable_width / 2, usable_height) * 0.9

            # Angular range: 20° to 160° (140° arc) to create semicircle
            start_angle_deg = 20
            end_angle_deg = 160
            total_arc_deg = end_angle_deg - start_angle_deg
            angle_per_gong = total_arc_deg / (self.MAX_NOTE - 1)

            # Draw the mounting rail (curved arc)
            rail_width = 4
            rail_radius_outer = radius + 8
            rail_radius_inner = radius - 8
            rail_points = []

            # Outer arc of rail
            for i in range(self.MAX_NOTE):
                angle_deg = start_angle_deg + (i * angle_per_gong)
                angle_rad = math.radians(angle_deg)
                x = center_x + rail_radius_outer * math.cos(angle_rad)
                y = center_y - rail_radius_outer * math.sin(angle_rad)
                rail_points.append((x, y))

            # Inner arc of rail (reversed)
            for i in range(self.MAX_NOTE - 1, -1, -1):
                angle_deg = start_angle_deg + (i * angle_per_gong)
                angle_rad = math.radians(angle_deg)
                x = center_x + rail_radius_inner * math.cos(angle_rad)
                y = center_y - rail_radius_inner * math.sin(angle_rad)
                rail_points.append((x, y))

            # Draw rail as polygon
            if len(rail_points) >= 3:
                rail_color = "#5A4A3A" if is_dark else "#8B7355"
                canvas.create_polygon(rail_points, fill=rail_color, outline="")

            # Draw each gong
            gong_radius = max(8, radius / 20)  # Dynamic gong size

            for gong_num in range(self.MIN_NOTE, self.MAX_NOTE + 1):
                angle_deg = start_angle_deg + ((gong_num - 1) * angle_per_gong)
                angle_rad = math.radians(angle_deg)

                # Position of gong center
                gong_x = center_x + radius * math.cos(angle_rad)
                gong_y = center_y - radius * math.sin(angle_rad)

                # Draw gong base (circle)
                canvas.create_oval(
                    gong_x - gong_radius,
                    gong_y - gong_radius,
                    gong_x + gong_radius,
                    gong_y + gong_radius,
                    fill=gong_face,
                    outline=""
                )

                # Draw gong shadow (darker edge)
                shadow_offset = gong_radius * 0.3
                canvas.create_arc(
                    gong_x - gong_radius,
                    gong_y - gong_radius,
                    gong_x + gong_radius,
                    gong_y + gong_radius,
                    start=180,
                    extent=180,
                    fill=gong_shadow,
                    outline=""
                )

                # Draw gong highlight
                highlight_radius = gong_radius * 0.6
                canvas.create_oval(
                    gong_x - highlight_radius * 0.4,
                    gong_y - highlight_radius * 0.6,
                    gong_x + highlight_radius * 0.4,
                    gong_y - highlight_radius * 0.2,
                    fill=gong_highlight,
                    outline=""
                )

                # Draw suspension cord
                cord_top_y = gong_y - gong_radius - 8
                canvas.create_line(
                    gong_x,
                    cord_top_y,
                    gong_x,
                    gong_y - gong_radius,
                    fill=cord_color,
                    width=1
                )

                # Draw gong label
                label_dist = gong_radius + 20
                label_x = gong_x
                label_y = gong_y + label_dist
                label_font_size = max(7, int(gong_radius * 1.2))

                try:
                    import customtkinter as ctk
                    label_font = ("Courier", label_font_size, "bold")
                except Exception:
                    label_font = ("Courier", 10, "bold")

                canvas.create_text(
                    label_x,
                    label_y,
                    text=str(gong_num),
                    font=label_font,
                    fill=text_color
                )

            # Draw title/status message
            title_text = "Kong Thom - 16 Gong Circle"
            title_y = height * 0.08
            try:
                import customtkinter as ctk
                title_font = ("Segoe UI", 14, "bold")
            except Exception:
                title_font = ("Arial", 14, "bold")

            canvas.create_text(
                width / 2,
                title_y,
                text=title_text,
                font=title_font,
                fill=text_color
            )

            return True

        except Exception as e:
            logger.error(f"Error rendering custom Kong Thom view: {e}")
            return False


# Singleton instance
_plugin_instance: Optional[KongThomPlugin] = None


def get_plugin() -> KongThomPlugin:
    """
    Get or create the singleton Kong Thom plugin instance.

    Returns:
        KongThomPlugin: The plugin instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = KongThomPlugin()
    return _plugin_instance
