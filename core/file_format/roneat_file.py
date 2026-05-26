"""Universal .roneat file format handler for Roneat Ek scores.

This module provides data structures and file management for the notation-agnostic
.roneat JSON format, enabling seamless interchange between numeric, syllabic, and
classic notation modes without data loss.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Lazy import - jsonschema is only loaded when validation is actually needed
jsonschema = None


@dataclass
class RoneatNote:
    """Represents a single note in a Roneat Ek score.

    Attributes:
        id: Unique note identifier (auto-assigned if not provided).
        bar: Measure number (1-indexed).
        beat: Beat position as float (e.g., 1.0, 1.5, 2.0).
        duration: Duration in beats (4.0=whole, 2.0=half, 1.0=quarter, 0.5=eighth, 0.25=sixteenth).
        pitch_numeric: Numeric pitch (1-21 for Roneat Ek bar number).
        pitch_midi: MIDI note number (0-127).
        velocity: MIDI velocity (0-127).
        hand: Playing hand ("left" or "right").
        repetition_count: Number of repetitions (default 1, e.g., 7#6 means repeat 6 times).
    """

    id: int
    bar: int
    beat: float
    duration: float
    pitch_numeric: int
    pitch_midi: int
    velocity: int
    hand: str
    repetition_count: int = 1

    def to_dict(self) -> dict:
        """Convert note to dictionary representation.

        Returns:
            Dictionary with all note attributes.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RoneatNote":
        """Create note from dictionary representation.

        Args:
            data: Dictionary containing note attributes.

        Returns:
            RoneatNote instance.
        """
        return cls(**data)


@dataclass
class RoneatScore:
    """Represents a complete Roneat Ek score with metadata and notes.

    Attributes:
        title: Score title.
        author: Composer or arranger name.
        tempo_bpm: Tempo in beats per minute.
        time_signature: Time signature as string (e.g., "4/4").
        notes: List of RoneatNote objects.
        notation_mode: Display notation mode ("numeric", "syllabic", or "classic").
        theme: UI theme preference ("dark" or "light").
        instrument_id: Active instrument plugin ID (default: "roneat_ek").
        software_version: Version of software that created the score.
        created_at: ISO 8601 datetime string.
    """

    title: str
    author: str
    tempo_bpm: int
    time_signature: str
    notes: list[RoneatNote] = field(default_factory=list)
    notation_mode: str = "numeric"
    theme: str = "dark"
    instrument_id: str = "roneat_ek"
    software_version: str = "2.3.0"
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize created_at timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        """Convert score to dictionary representation for JSON serialization.

        Returns:
            Dictionary with file_metadata, score_metadata, notes, and display_settings.
        """
        return {
            "file_metadata": {
                "version": "2.3.0",
                "created_at": self.created_at,
                "software_version": self.software_version,
                "instrument": "roneat_ek",
                "instrument_id": self.instrument_id,
            },
            "score_metadata": {
                "title": self.title,
                "author": self.author,
                "tempo_bpm": self.tempo_bpm,
                "time_signature": self.time_signature,
            },
            "notes": [note.to_dict() for note in self.notes],
            "display_settings": {
                "notation_mode": self.notation_mode,
                "theme": self.theme,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RoneatScore":
        """Create score from dictionary representation.

        Args:
            data: Dictionary with file_metadata, score_metadata, notes, and display_settings keys.

        Returns:
            RoneatScore instance.

        Raises:
            KeyError: If required keys are missing.
        """
        score_meta = data["score_metadata"]
        file_meta = data["file_metadata"]
        display = data["display_settings"]

        notes = [RoneatNote.from_dict(note_dict) for note_dict in data.get("notes", [])]

        return cls(
            title=score_meta["title"],
            author=score_meta["author"],
            tempo_bpm=score_meta["tempo_bpm"],
            time_signature=score_meta["time_signature"],
            notes=notes,
            notation_mode=display.get("notation_mode", "numeric"),
            theme=display.get("theme", "dark"),
            instrument_id=file_meta.get("instrument_id", "roneat_ek"),
            software_version=file_meta.get("software_version", "2.3.0"),
            created_at=file_meta.get("created_at"),
        )


class RoneatFileManager:
    """Manager for saving and loading .roneat files with validation."""

    _schema: Optional[dict] = None
    _schema_path = Path(__file__).parent / "roneat_schema.json"

    @classmethod
    def _load_schema(cls) -> dict:
        """Load JSON schema from file.

        Returns:
            JSON schema as dictionary.

        Raises:
            FileNotFoundError: If schema file not found.
            json.JSONDecodeError: If schema is invalid JSON.
        """
        if cls._schema is None:
            with open(cls._schema_path, "r", encoding="utf-8") as f:
                cls._schema = json.load(f)
        return cls._schema

    @staticmethod
    def validate(data: dict) -> bool:
        """Validate data against the .roneat schema.

        Args:
            data: Dictionary to validate.

        Returns:
            True if data is valid.

        Raises:
            jsonschema.ValidationError: If validation fails.
            ImportError: If jsonschema package not installed.
        """
        # Lazy import jsonschema only when validation is needed
        try:
            import jsonschema as jschema
        except ImportError:
            raise ImportError(
                "jsonschema package required for validation. Install with: pip install jsonschema"
            )
        
        schema = RoneatFileManager._load_schema()
        jschema.validate(instance=data, schema=schema)
        return True

    @staticmethod
    def save(score: RoneatScore, filepath: str) -> None:
        """Save score to .roneat file with validation.

        Args:
            score: RoneatScore instance to save.
            filepath: Path to save file (should end with .roneat).

        Raises:
            ValueError: If score data fails validation.
            IOError: If file write fails.
        """
        data = score.to_dict()

        try:
            RoneatFileManager.validate(data)
        except Exception as e:
            raise ValueError(f"Score validation failed: {e}") from e

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(filepath: str) -> RoneatScore:
        """Load score from .roneat file with validation.

        Args:
            filepath: Path to .roneat file.

        Returns:
            RoneatScore instance.

        Raises:
            FileNotFoundError: If file does not exist.
            json.JSONDecodeError: If file is not valid JSON.
            ValueError: If file data fails schema validation.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        try:
            RoneatFileManager.validate(data)
        except Exception as e:
            raise ValueError(f"File validation failed: {e}") from e

        return RoneatScore.from_dict(data)
