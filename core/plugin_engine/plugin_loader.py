"""
Plugin Loader Module

Handles plugin discovery, dependency resolution, and dynamic loading.
Provides sandboxed loading with comprehensive error handling to prevent
plugin failures from crashing the main application.
"""

import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginDependencyError(PluginError):
    """Raised when plugin dependencies cannot be satisfied."""
    pass


class PluginLoadError(PluginError):
    """Raised when a plugin fails to load."""
    pass


class PluginLoader:
    """
    Manages plugin discovery, loading, and lifecycle.

    This class provides sandboxed loading of plugins with comprehensive error
    handling. It discovers plugins from a directory, validates dependencies,
    and dynamically loads plugin modules.

    Attributes:
        _loaded_plugins (dict): Cache of loaded plugin modules keyed by plugin ID
        _active_instrument_plugin (Optional[Any]): Currently active instrument plugin
    """

    def __init__(self) -> None:
        """Initialize the plugin loader with empty cache."""
        self._loaded_plugins: dict[str, Any] = {}
        self._active_instrument_plugin: Optional[Any] = None

    def discover_plugins(self, plugins_dir: str) -> list[dict]:
        """
        Discover all available plugins in a directory.

        Scans the plugins directory for subdirectories containing plugin.json files.
        Each valid plugin is returned as a metadata dictionary.

        Args:
            plugins_dir (str): Absolute path to the plugins directory

        Returns:
            list[dict]: List of plugin metadata dictionaries, each containing:
                - id (str): Unique plugin identifier
                - name (str): Display name
                - version (str): Semantic version
                - author (str): Plugin author
                - type (str): Plugin type ("core", "instrument", "utility")
                - depends_on (list[str]): List of plugin IDs this plugin depends on
                - entry_point (str): Path to the main plugin module
                - path (str): Absolute path to the plugin directory
                - instrument_range (dict, optional): For instrument plugins

        Raises:
            OSError: If the plugins directory doesn't exist or isn't readable
        """
        plugins = []
        plugins_path = Path(plugins_dir)

        if not plugins_path.exists():
            logger.warning(f"Plugins directory does not exist: {plugins_dir}")
            return plugins

        if not plugins_path.is_dir():
            logger.error(f"Plugins path is not a directory: {plugins_dir}")
            return plugins

        try:
            for item in plugins_path.iterdir():
                if not item.is_dir() or item.name.startswith("."):
                    continue

                plugin_json_path = item / "plugin.json"
                if not plugin_json_path.exists():
                    continue

                try:
                    with open(plugin_json_path, "r", encoding="utf-8") as f:
                        plugin_meta = json.load(f)

                    # Validate required fields
                    required_fields = ["id", "name", "version", "author", "type", "entry_point"]
                    missing = [field for field in required_fields if field not in plugin_meta]
                    if missing:
                        logger.warning(
                            f"Plugin {item.name} missing required fields: {missing}"
                        )
                        continue

                    # Add plugin directory path
                    plugin_meta["path"] = str(item.absolute())
                    plugin_meta["depends_on"] = plugin_meta.get("depends_on", [])

                    plugins.append(plugin_meta)
                    logger.debug(f"Discovered plugin: {plugin_meta['id']} v{plugin_meta['version']}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in plugin.json for {item.name}: {e}")
                except Exception as e:
                    logger.error(f"Error loading plugin metadata from {item.name}: {e}")

        except Exception as e:
            logger.error(f"Error scanning plugins directory: {e}")

        return plugins

    def resolve_dependencies(self, plugins: list[dict]) -> list[dict]:
        """
        Resolve plugin dependencies and return topologically sorted list.

        Validates that all dependencies are satisfied and that the "core" plugin
        is present. Returns plugins in dependency order (dependencies loaded first).

        Args:
            plugins (list[dict]): List of plugin metadata dictionaries

        Returns:
            list[dict]: Plugins sorted in dependency order

        Raises:
            PluginDependencyError: If core plugin is missing or dependencies cannot be resolved
        """
        # Check for core plugin
        core_plugin = next((p for p in plugins if p["id"] == "core"), None)
        if not core_plugin:
            raise PluginDependencyError(
                "Core plugin (id='core') is required but not installed"
            )

        # Create lookup table
        plugin_map = {p["id"]: p for p in plugins}

        # Validate all dependencies exist
        for plugin in plugins:
            for dep_id in plugin.get("depends_on", []):
                if dep_id not in plugin_map:
                    raise PluginDependencyError(
                        f"Plugin '{plugin['id']}' depends on missing plugin '{dep_id}'"
                    )

        # Topological sort
        resolved = []
        visited = set()
        visiting = set()

        def visit(plugin_id: str) -> None:
            if plugin_id in visited:
                return

            if plugin_id in visiting:
                raise PluginDependencyError(
                    f"Circular dependency detected involving plugin '{plugin_id}'"
                )

            visiting.add(plugin_id)
            plugin = plugin_map[plugin_id]

            for dep_id in plugin.get("depends_on", []):
                visit(dep_id)

            visiting.remove(plugin_id)
            visited.add(plugin_id)
            resolved.append(plugin)

        for plugin in plugins:
            visit(plugin["id"])

        return resolved

    def load_plugin(self, plugin_meta: dict) -> Any:
        """
        Dynamically load a plugin module.

        Loads the plugin's entry point module using importlib. Includes comprehensive
        error handling to prevent malformed plugins from crashing the application.

        Args:
            plugin_meta (dict): Plugin metadata dictionary containing:
                - id (str): Plugin identifier
                - path (str): Plugin directory path
                - entry_point (str): Relative path to entry module (e.g., "main.py")

        Returns:
            Any: The loaded module object

        Raises:
            PluginLoadError: If the plugin fails to load
        """
        plugin_id = plugin_meta.get("id", "unknown")
        plugin_path = plugin_meta.get("path")
        entry_point = plugin_meta.get("entry_point")

        if not plugin_path or not entry_point:
            raise PluginLoadError(
                f"Plugin '{plugin_id}' has invalid path or entry_point"
            )

        try:
            # Construct full path to entry point
            module_path = os.path.join(plugin_path, entry_point)

            if not os.path.exists(module_path):
                raise PluginLoadError(
                    f"Plugin '{plugin_id}' entry point not found: {module_path}"
                )

            # Generate a unique module name to avoid conflicts
            module_name = f"roneat_plugin_{plugin_id}"

            # Load the module dynamically
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(
                    f"Failed to create module spec for plugin '{plugin_id}'"
                )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Cache the loaded plugin
            self._loaded_plugins[plugin_id] = module

            logger.info(f"Successfully loaded plugin: {plugin_id}")
            return module

        except PluginLoadError:
            raise
        except Exception as e:
            logger.error(f"Error loading plugin '{plugin_id}': {e}", exc_info=True)
            raise PluginLoadError(f"Failed to load plugin '{plugin_id}': {e}") from e

    def get_loaded_plugin(self, plugin_id: str) -> Optional[Any]:
        """
        Get a previously loaded plugin by ID.

        Args:
            plugin_id (str): The plugin identifier

        Returns:
            Optional[Any]: The loaded module, or None if not loaded
        """
        return self._loaded_plugins.get(plugin_id)

    def set_active_instrument_plugin(self, plugin: Any) -> None:
        """
        Set the currently active instrument plugin.

        Args:
            plugin (Any): The plugin module/instance
        """
        self._active_instrument_plugin = plugin

    def get_active_instrument_plugin(self) -> Optional[Any]:
        """
        Get the currently active instrument plugin.

        Returns:
            Optional[Any]: The active instrument plugin, or None if not set
        """
        return self._active_instrument_plugin
