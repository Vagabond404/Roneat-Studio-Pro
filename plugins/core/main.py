"""
Core Plugin for Roneat Studio

Provides essential core functionality and UI components for managing instruments
and coordinating with other plugins.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CorePlugin:
    """
    Core plugin providing fundamental Roneat Studio functionality.

    This plugin is always loaded first and required by all other plugins.
    It provides UI components and core services.
    """

    def __init__(self) -> None:
        """Initialize the core plugin."""
        self.plugin_id = "core"
        self.plugin_name = "Roneat Studio Core"
        logger.info(f"Initializing {self.plugin_name}")

    def get_instrument_selector_ui(self, parent_frame: Any) -> Optional[Any]:
        """
        Create and return an instrument selector UI component.

        This method generates a UI widget that allows users to select from available
        instrument plugins. The widget is placed on the provided parent frame.

        Args:
            parent_frame (Any): The parent CustomTkinter frame or widget where the
                               instrument selector should be placed

        Returns:
            Optional[Any]: The created UI component, or None if UI creation fails

        Note:
            This is a placeholder for the actual UI implementation. The real
            implementation will be integrated with the UI layer (CustomTkinter).
        """
        try:
            # This method returns a UI component that will be populated by the main UI layer
            logger.debug("Creating instrument selector UI")
            return {
                "type": "instrument_selector",
                "parent_frame": parent_frame,
            }
        except Exception as e:
            logger.error(f"Error creating instrument selector UI: {e}")
            return None

    def initialize(self) -> bool:
        """
        Initialize the core plugin and validate its state.

        Returns:
            bool: True if initialization succeeds, False otherwise
        """
        try:
            logger.info(f"{self.plugin_name} initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize {self.plugin_name}: {e}")
            return False

    def shutdown(self) -> None:
        """Perform cleanup when the plugin is being unloaded."""
        logger.info(f"{self.plugin_name} shutting down")


# Module-level plugin instance
_plugin_instance: Optional[CorePlugin] = None


def get_plugin() -> CorePlugin:
    """
    Get or create the singleton core plugin instance.

    Returns:
        CorePlugin: The core plugin instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = CorePlugin()
    return _plugin_instance
