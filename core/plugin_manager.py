import os
import sys
import json
import logging
import traceback
import shutil
from dataclasses import dataclass
from typing import Any, Callable

from core.plugin_loader import _get_plugins_dir, extract_plugin, load_plugin_module, validate_plugin
from core.plugin_api import init_api

@dataclass
class PluginInfo:
    id: str
    name: str
    version: str
    author: str
    description: str
    active: bool
    manifest: dict
    dir_path: str
    module: Any = None
    error: str = None


class PluginManager:
    def __init__(self):
        self.plugins_dir = _get_plugins_dir()
        self.disabled_dir = os.path.join(self.plugins_dir, 'disabled')
        os.makedirs(self.plugins_dir, exist_ok=True)
        os.makedirs(self.disabled_dir, exist_ok=True)
        
        self.plugins: dict[str, PluginInfo] = {}
        self.app = None  # Ref to MainWindow
        
        self.menu_items = []
        self.toolbar_buttons = []
        self.sidebar_panels = []
        self.custom_tabs = []
        
        self.default_theme = {}
        self.default_language = "en"
        self.plugin_state_history = []
        
        self._current_executing_plugin = None

    def initialize(self, app):
        """Called upon MainWindow creation. Initializes API and loads active plugins."""
        self.app = app
        self.default_theme = dict(app.C)
        try:
            import core.i18n as i18n
            self.default_language = i18n.current_lang
        except Exception: pass
        init_api(app, self)
        
        self.scan_and_load_plugins()

    def _read_manifest_from_dir(self, dir_path: str) -> dict | None:
        mf = os.path.join(dir_path, 'plugin.json')
        if os.path.exists(mf):
            try:
                with open(mf, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error reading manifest {mf}: {e}")
        return None

    def scan_and_load_plugins(self):
        """Scans plugin directories and loads active ones."""
        # 1. Scan active plugins
        for item in os.listdir(self.plugins_dir):
            if item == 'disabled':
                continue
            pdir = os.path.join(self.plugins_dir, item)
            if os.path.isdir(pdir):
                manifest = self._read_manifest_from_dir(pdir)
                if manifest:
                    plugin_id = manifest.get('id', item)
                    info = PluginInfo(
                        id=plugin_id,
                        name=manifest.get('name', plugin_id),
                        version=manifest.get('version', '1.0'),
                        author=manifest.get('author', 'Unknown'),
                        description=manifest.get('description', ''),
                        active=True,
                        manifest=manifest,
                        dir_path=item
                    )
                    self.plugins[plugin_id] = info
                    self._load_and_init_plugin(plugin_id)

        # 2. Scan disabled plugins
        for item in os.listdir(self.disabled_dir):
            pdir = os.path.join(self.disabled_dir, item)
            if os.path.isdir(pdir):
                manifest = self._read_manifest_from_dir(pdir)
                if manifest:
                    plugin_id = manifest.get('id', item)
                    info = PluginInfo(
                        id=plugin_id,
                        name=manifest.get('name', plugin_id),
                        version=manifest.get('version', '1.0'),
                        author=manifest.get('author', 'Unknown'),
                        description=manifest.get('description', ''),
                        active=False,
                        manifest=manifest,
                        dir_path=item
                    )
                    self.plugins[plugin_id] = info

    def _load_and_init_plugin(self, plugin_id: str):
        """Loads a single plugin module into memory and calls on_load."""
        info = self.plugins.get(plugin_id)
        if not info or not info.active:
            logging.warning(f"❌ Cannot load plugin {plugin_id}: not found or inactive")
            return

        pdir = os.path.join(self.plugins_dir, info.dir_path)
        logging.info(f"🔧 Loading plugin from: {pdir}")
        
        try:
            mod, _ = load_plugin_module(plugin_id, pdir)
            info.module = mod
            info.error = None
            logging.info(f"✓ Module loaded: {plugin_id}")
            
            # Register UI extensions implicitly if declared
            self._register_ui_extensions(info.manifest)
                
            # Trigger on_load
            logging.info(f"🎯 Calling on_load hook for {plugin_id}...")
            self.trigger_hook_for_plugin(plugin_id, "on_load")
            logging.info(f"✓ on_load hook completed for {plugin_id}")
            
            # Hot-Reload check: If app is already running, initialize immediately
            if getattr(self.app, '_app_is_ready', False):
                logging.info(f"🔥 App is already running. Triggering on_app_start for {plugin_id}...")
                self.trigger_hook_for_plugin(plugin_id, "on_app_start")
                self.app._refresh_plugin_ui()
                logging.info(f"✓ Hot-reload UI integration complete for {plugin_id}")
            
        except Exception as e:
            err_msg = traceback.format_exc()
            logging.error(f"❌ Failed to load plugin {plugin_id}:\n{err_msg}")
            info.error = str(e)
            info.active = False
            self.disable_plugin(plugin_id)

    def _register_ui_extensions(self, manifest: dict):
        # We store these declarations for when UI requests them
        ui_ext = manifest.get("ui_extensions", {})
        if "menu_items" in ui_ext:
            for item in ui_ext["menu_items"]:
                # In actual implementation, we'd bind this via add_menu_item later
                pass

    def get_installed_plugins(self) -> list[PluginInfo]:
        return list(self.plugins.values())

    def install_plugin(self, zip_path: str) -> bool:
        dest_dir = extract_plugin(zip_path)
        if dest_dir:
            manifest = self._read_manifest_from_dir(dest_dir)
            if manifest:
                plugin_id = manifest['id']
                folder_name = os.path.basename(dest_dir)
                # If it was disabled, we must remove it from disabled dir
                old_disabled = os.path.join(self.disabled_dir, folder_name)
                if os.path.exists(old_disabled):
                    shutil.rmtree(old_disabled)
                    
                info = PluginInfo(
                    id=plugin_id,
                    name=manifest.get('name', plugin_id),
                    version=manifest.get('version', '1.0'),
                    author=manifest.get('author', 'Unknown'),
                    description=manifest.get('description', ''),
                    active=True,
                    manifest=manifest,
                    dir_path=folder_name
                )
                self.plugins[plugin_id] = info
                self._load_and_init_plugin(plugin_id)
                return True
        return False

    def check_dependencies(self, plugin_id: str) -> bool:
        info = self.plugins.get(plugin_id)
        if not info:
            return False
        deps = info.manifest.get("dependencies", [])
        for dep in deps:
            dep_info = self.plugins.get(dep)
            if not dep_info or not dep_info.active:
                return False
        return True

    def enable_plugin(self, plugin_id: str) -> bool:
        info = self.plugins.get(plugin_id)
        if not info or info.active:
            return False
            
        disabled_path = os.path.join(self.disabled_dir, info.dir_path)
        active_path = os.path.join(self.plugins_dir, info.dir_path)
        
        if os.path.exists(disabled_path):
            try:
                # Move to active dir
                shutil.move(disabled_path, active_path)
                info.active = True
                self._load_and_init_plugin(plugin_id)
                return True
            except Exception as e:
                logging.error(f"Failed to enable plugin {plugin_id}: {e}")
        return False

    def disable_plugin(self, plugin_id: str, _is_crashing: bool = False) -> bool:
        info = self.plugins.get(plugin_id)
        if not info or not info.active:
            return False
            
        info.active = False
        
        # Call on_unload before moving
        if not _is_crashing:
            self.trigger_hook_for_plugin(plugin_id, "on_unload")
        
        active_path = os.path.join(self.plugins_dir, info.dir_path)
        disabled_path = os.path.join(self.disabled_dir, info.dir_path)
        
        if os.path.exists(active_path):
            try:
                # Unload module from memory
                if info.module:
                    sys.modules.pop(f"roneat_plugins.{plugin_id}", None)
                    info.module = None
                    
                # Remove from UI lists
                self._remove_ui_extensions(plugin_id)
                    
                # Move to disabled dir
                if os.path.exists(disabled_path):
                    shutil.rmtree(disabled_path)
                shutil.move(active_path, disabled_path)
                
                # Undo State
                self.plugin_state_history = [h for h in self.plugin_state_history if h["plugin_id"] != plugin_id]
                self._reapply_state()
                
                return True
            except Exception as e:
                logging.error(f"Failed to disable plugin {plugin_id}: {e}")
        return False

    def uninstall_plugin(self, plugin_id: str) -> bool:
        info = self.plugins.get(plugin_id)
        if not info:
            return False
            
        if info.active:
            self.disable_plugin(plugin_id)
            
        disabled_path = os.path.join(self.disabled_dir, info.dir_path)
        if os.path.exists(disabled_path):
            try:
                shutil.rmtree(disabled_path)
                self.plugins.pop(plugin_id, None)
                return True
            except Exception as e:
                logging.error(f"Failed to uninstall plugin {plugin_id}: {e}")
        return False

    def trigger_hook_for_plugin(self, plugin_id: str, hook_name: str, *args, **kwargs):
        info = self.plugins.get(plugin_id)
        if not info or not info.active or not info.module:
            return
            
        hooks = info.manifest.get("hooks", {})
        if hook_name in hooks:
            func_name = hooks[hook_name]
            func = getattr(info.module, func_name, None)
            if func and callable(func):
                try:
                    self._current_executing_plugin = plugin_id
                    func(*args, **kwargs)
                except Exception as e:
                    logging.error(f"Plugin {plugin_id} crashed during hook {hook_name}: {e}")
                    traceback.print_exc()
                    if hasattr(self.app, 'set_status'):
                        self.app.set_status(f"Plugin Error: {plugin_id}", "error")
                    self.disable_plugin(plugin_id, _is_crashing=True)
                finally:
                    self._current_executing_plugin = None

    def trigger_hook(self, hook_name: str, *args, **kwargs):
        """Triggers a hook on all active plugins."""
        for plugin_id in list(self.plugins.keys()):
            self.trigger_hook_for_plugin(plugin_id, hook_name, *args, **kwargs)

    def _remove_ui_extensions(self, plugin_id: str):
        """Removes all UI items added by a specific plugin."""
        self.menu_items = [item for item in self.menu_items if item.get("plugin_id") != plugin_id]
        self.toolbar_buttons = [item for item in self.toolbar_buttons if item.get("plugin_id") != plugin_id]
        self.sidebar_panels = [item for item in self.sidebar_panels if item.get("plugin_id") != plugin_id]
        self.custom_tabs = [t for t in self.custom_tabs if t.get("plugin_id") != plugin_id]

    def _reapply_state(self):
        if not self.app: return
        self.app.C.update(self.default_theme)
        try:
            import core.i18n as i18n
            i18n.set_lang(self.default_language)
        except: pass
        
        for h in self.plugin_state_history:
            if h["type"] == "theme":
                self.app.C[h["key"]] = h["value"]
            elif h["type"] == "language":
                try:
                    import core.i18n as i18n
                    i18n.set_lang(h["value"])
                except: pass

        ed = self.app.frames.get("editor") if hasattr(self.app, 'frames') else None
        if hasattr(self.app, "_request_update"): self.app._request_update()
        elif ed and hasattr(ed, "_request_update"): ed._request_update()
        
        if hasattr(self.app, '_refresh_nav_translations'):
            self.app._refresh_nav_translations()

    def _wrap_plugin_callback(self, plugin_id, cmd):
        def wrapped(*args, **kwargs):
            try:
                return cmd(*args, **kwargs)
            except Exception as e:
                logging.error(f"Plugin {plugin_id} crashed during callback: {e}")
                self.disable_plugin(plugin_id, _is_crashing=True)
        return wrapped

    # ── UI Injection API for plugins ──────────────────────────────────────────
    def add_custom_tab(self, tab_id: str, label: str, icon: str, widget_class: Any):
        pid = self._current_executing_plugin
        self.custom_tabs.append({
            "plugin_id": pid,
            "tab_id": tab_id,
            "label": label,
            "icon": icon,
            "widget_class": widget_class
        })
        logging.info(f"Registered custom tab: {label}")

    def add_custom_menu_item(self, menu_name: str, label: str, command: Callable):
        pid = self._current_executing_plugin
        self.menu_items.append({"plugin_id": pid, "menu": menu_name, "label": label, 
                                "cmd": self._wrap_plugin_callback(pid, command)})
        logging.info(f"Registered custom menu item: {label} in {menu_name}")

    def add_custom_toolbar_button(self, icon: str, tooltip: str, command: Callable):
        pid = self._current_executing_plugin
        self.toolbar_buttons.append({"plugin_id": pid, "icon": icon, "tooltip": tooltip, 
                                     "cmd": self._wrap_plugin_callback(pid, command)})
        logging.info(f"Registered custom toolbar button: {tooltip}")

    def create_custom_sidebar_panel(self, title: str, content_widget):
        self.sidebar_panels.append({"plugin_id": self._current_executing_plugin, "title": title, "widget": content_widget})
        logging.info(f"Registered custom sidebar panel: {title}")
