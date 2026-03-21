import os
import sys
import json
import zipfile
import shutil
import logging
import importlib.util
import builtins

def _get_plugins_dir():
    """Returns the local 'plugins' directory at the root of the project."""
    # Assuming this file is core/plugin_loader.py, project root is folder above core/
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(root, "plugins")

def validate_plugin(zip_path: str) -> tuple[bool, str]:
    """Validates a plugin ZIP file before installation."""
    if not os.path.exists(zip_path):
        return False, "File does not exist"
    if not zip_path.endswith('.zip'):
        return False, "Not a ZIP file"
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.namelist()
            if 'plugin.json' not in file_list:
                # Some zips have a root folder inside (e.g. plugin_folder/plugin.json)
                # Let's search for plugin.json
                possible_jsons = [f for f in file_list if f.endswith('plugin.json')]
                if not possible_jsons:
                    return False, "Missing plugin.json manifest"
                manifest_path = possible_jsons[0]
            else:
                manifest_path = 'plugin.json'
            
            with zf.open(manifest_path) as f:
                manifest = json.load(f)
            
            required_keys = ['id', 'name', 'version', 'author', 'entry_point']
            for k in required_keys:
                if k not in manifest:
                    return False, f"Missing '{k}' in plugin.json"
                    
            entry_point = manifest['entry_point']
            
            # Check if entry point exists in zip
            root_dir = os.path.dirname(manifest_path)
            entry_point_path = entry_point if not root_dir else f"{root_dir}/{entry_point}"
            
            if entry_point_path not in file_list:
                return False, f"Entry point {entry_point} not found in zip"
                
            return True, "Valid plugin"
            
    except zipfile.BadZipFile:
        return False, "Corrupted ZIP file"
    except json.JSONDecodeError:
        return False, "Invalid JSON format in plugin.json"
    except Exception as e:
        return False, f"Error validating plugin: {e}"

def extract_plugin(zip_path: str) -> str | None:
    """Extracts a valid plugin to the plugins directory and returns its folder path. Returns None on failure."""
    valid, msg = validate_plugin(zip_path)
    if not valid:
        logging.error(f"Plugin validation failed: {msg}")
        return None
        
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Get manifest to determine the ID
            file_list = zf.namelist()
            manifest_path = [f for f in file_list if f.endswith('plugin.json')][0]
            root_dir_in_zip = os.path.dirname(manifest_path)
            
            with zf.open(manifest_path) as f:
                manifest = json.load(f)
            
            plugin_id = manifest['id']
            dest_dir = os.path.join(_get_plugins_dir(), plugin_id)
            
            # Remove old version if it exists
            if os.path.exists(dest_dir):
                shutil.rmtree(dest_dir)
            os.makedirs(dest_dir, exist_ok=True)
            
            # Extract only the files belonging to the plugin (avoid path traversal attacks)
            for file_info in zf.infolist():
                if file_info.filename.startswith(root_dir_in_zip) and not file_info.is_dir():
                    # Preserve relative path structure
                    rel_path = os.path.relpath(file_info.filename, root_dir_in_zip) if root_dir_in_zip else file_info.filename
                    target_path = os.path.join(dest_dir, rel_path)
                    
                    # Ensure safety
                    if os.path.abspath(target_path).startswith(os.path.abspath(dest_dir)):
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with zf.open(file_info) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                            
        return dest_dir
    except Exception as e:
        logging.error(f"Error extracting plugin: {e}")
        return None

def load_plugin_module(plugin_id: str, plugin_dir: str):
    """Dynamically loads the plugin python code and returns the module."""
    manifest_path = os.path.join(plugin_dir, 'plugin.json')
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Missing plugin.json in {plugin_dir}")
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    entry_point = manifest.get('entry_point', '__init__.py')
    entry_point_path = os.path.join(plugin_dir, entry_point)
    
    if not os.path.exists(entry_point_path):
        raise FileNotFoundError(f"Entry point {entry_point} not found in {plugin_dir}")
        
    # Inject plugin_dir into sys.path temporarily to allow the plugin to import its own submodules
    original_sys_path = sys.path.copy()
    sys.path.insert(0, plugin_dir)
    
    try:
        module_name = f"roneat_plugins.{plugin_id}"
        spec = importlib.util.spec_from_file_location(module_name, entry_point_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            
            # --- Lightweight Sandboxing / Permissions Enforcement ---
            permissions = manifest.get("permissions", [])
            original_import = builtins.__import__
            
            def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                if name in ['os', 'shutil', 'subprocess', 'pathlib', 'io']:
                    if "file_system" not in permissions and "system" not in permissions:
                        raise ImportError(f"⚠️ SECURITY: Plugin '{plugin_id}' lacks 'file_system' permission to import '{name}'.")
                
                if name in ['socket', 'urllib', 'requests', 'http']:
                    if "network" not in permissions:
                        raise ImportError(f"⚠️ SECURITY: Plugin '{plugin_id}' lacks 'network' permission to import '{name}'.")
                        
                return original_import(name, globals, locals, fromlist, level)
            
            # Inject our restricted dictionary to avoid globally overriding
            safe_builtins = builtins.__dict__.copy()
            safe_builtins['__import__'] = _restricted_import
            module.__builtins__ = safe_builtins
            # --------------------------------------------------------
            
            spec.loader.exec_module(module)
            return module, manifest
        else:
            raise ImportError(f"Could not load spec for {plugin_id}")
    finally:
        sys.path = original_sys_path
