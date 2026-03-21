"""
ui/main_window.py  v3.0
========================
Roneat Studio Pro — Main Application Window

Changes in v3.0:
  - save_proj uses song title as default filename
  - Drag & drop support for .roneat project files on the main window
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import sys
import logging

from ui.views.score_editor   import ScoreEditor
from ui.views.audio_to_score import AudioToScore
from ui.views.settings_page  import SettingsPage
from core.file_manager       import (
    save_roneat_project, load_roneat_project, load_app_settings
)
from core.plugin_manager     import PluginManager
from ui.views.plugin_manager_tab   import PluginManagerTab
from core.i18n               import tr


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


class MainWindow(ctk.CTk):
    def __init__(self, initial_file=None):
        super().__init__()

        self.title("Roneat Studio Pro")
        self.geometry("1380x860")
        self.minsize(1100, 700)

        ctk.set_appearance_mode(load_app_settings().get("theme", "Dark"))

        self.C = {
            "accent":     "#D4AF37",
            "accent2":    "#e85d4a",
            "success":    "#3ab87a",
            "text":       ("gray10", "gray95"),
            "text_dim":   ("gray45", "#8b949e"),
            "sidebar_bg": ("gray92", "#090a0f"),
            "border":     ("gray80", "#1c2128"),
            "hover":      ("gray85", "#161b22"),
            "main_bg":    ("gray96", "#12151c"),
            "card":       ("white",  "#161b22"),
        }
        self.configure(fg_color=self.C["sidebar_bg"])

        icon_path = resource_path(os.path.join("assets", "logo.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                logging.warning(f"Could not load icon: {e}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0,
                                    fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(6, weight=1)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.grid(row=0, column=0, pady=(40, 10), padx=20, sticky="ew")
        ctk.CTkLabel(logo, text="ᨠ",
                     font=ctk.CTkFont(size=46),
                     text_color=self.C["accent"]).pack(anchor="center")
        ctk.CTkLabel(logo, text="Roneat Studio",
                     font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                     text_color=self.C["accent"]).pack(anchor="center", pady=(6, 0))
        ctk.CTkLabel(logo, text="PRO",
                     font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold", slant="italic"),
                     text_color=self.C["text_dim"]).pack(anchor="center")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.C["border"]
                     ).grid(row=1, column=0, padx=22, pady=(12, 20), sticky="ew")

        self.base_nav_items = [
            ("editor",   "Score Editor", "🎼"),
            ("audio",    "Audio AI",     "🎤"),
            ("settings", "Settings",     "⚙"),
            ("plugins",  "Plugins",      "🧩"),
        ]
        self._nav_btns = {}
        
        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=4)
        # Using grid inside nav_frame or pack, pack is easier for dynamic inserts
        
        # Build base nav
        self._build_nav_buttons()

        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.C["border"]
                     ).grid(row=3, column=0, padx=22, pady=(12, 16), sticky="ew")

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=16, pady=4)

        self.save_btn = ctk.CTkButton(
            bottom, text=f"💾  {tr('Save Project')}",
            command=self.save_proj,
            fg_color=self.C["accent"], text_color="#090a0f",
            hover_color="#e6c45c", height=44, corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.save_btn.pack(fill="x", pady=(0, 8))

        self.load_btn = ctk.CTkButton(
            bottom, text=f"📂  {tr('Load Project')}",
            command=self.load_proj_dialog,
            fg_color="transparent", text_color=self.C["text"],
            border_width=1, border_color=self.C["border"],
            hover_color=self.C["hover"], height=42, corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.load_btn.pack(fill="x")
        
        # Give remaining vertical space to row 5 so status stays pinned at the bottom
        self.sidebar.grid_rowconfigure(5, weight=1)
        
        status_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_f.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 20))
        self.status_lbl = ctk.CTkLabel(
            status_f, text=f"● {tr('Ready')}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.C["success"]
        )
        self.status_lbl.pack(anchor="w", padx=8)

        # ── Main content ──────────────────────────────────────────────────────
        self.main_cont = ctk.CTkFrame(self, corner_radius=16, fg_color=self.C["main_bg"],
                                      border_width=1, border_color=self.C["border"])
        self.main_cont.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        self.main_cont.grid_rowconfigure(0, weight=1)
        self.main_cont.grid_columnconfigure(0, weight=1)

        # ── Initialize Plugin System ──────────────────────────────────────────
        self.plugin_manager_instance = PluginManager()

        self.frames = {
            "editor":   ScoreEditor(self.main_cont, self.get_project_data),
            "audio":    AudioToScore(self.main_cont, self.import_from_audio),
            "settings": SettingsPage(self.main_cont),
            "plugins":  PluginManagerTab(self.main_cont, self.plugin_manager_instance),
        }

        self.show_frame("editor")

        self.plugin_manager_instance.initialize(self)

        # ── Drag & drop .roneat files ─────────────────────────────────────────
        self._setup_drag_drop()

        if initial_file:
            self.load_proj(initial_file)
            
        # Hook on_app_start fired ONLY AFTER all UI is fully built
        self._app_is_ready = True
        self.plugin_manager_instance.trigger_hook("on_app_start")
        self._refresh_plugin_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Drag & drop
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_drag_drop(self):
        """
        Enable drag-and-drop for .roneat project files onto the main window.
        Uses tkinterdnd2 if available; gracefully skipped if not installed.
        """
        try:
            self.drop_target_register('DND_Files')
            self.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            logging.info("tkinterdnd2 not available, drag and drop disabled.")

    def _on_drop(self, event):
        raw = event.data.strip()
        # Strip curly braces that tkinterdnd2 adds for paths with spaces
        if raw.startswith('{') and raw.endswith('}'):
            raw = raw[1:-1]
        fp = raw.strip('"')
        if os.path.isfile(fp):
            if fp.lower().endswith('.roneat'):
                self.load_proj(fp)
            else:
                # Forward audio file drop to Audio AI page
                try:
                    self.frames["audio"]._drop_file(fp)
                    self.show_frame("audio")
                except Exception as e:
                    logging.error(f"Error handling dropped audio file: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Failed to load dropped file:\n{e}")

    # ─────────────────────────────────────────────────────────────────────────

    def _build_nav_buttons(self, plugin_tabs=None):
        """Rebuilds the navigation frame buttons."""
        for widget in self.nav_frame.winfo_children():
            widget.destroy()
            
        self._nav_btns.clear()
        
        # Base Items
        all_items = list(self.base_nav_items)
        
        # Plugin Tab Items
        if plugin_tabs:
            all_items.extend(plugin_tabs)
            
        for key, label, icon in all_items:
            btn = ctk.CTkButton(
                self.nav_frame,
                text=f"  {icon}   {tr(label)}",
                command=lambda k=key: self.show_frame(k),
                fg_color="transparent",
                text_color=self.C["text"],
                hover_color=self.C["hover"],
                anchor="w", height=48, corner_radius=12,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
            )
            btn.pack(fill="x", pady=4)
            self._nav_btns[key] = btn

        # Restore active state visually
        active_tab = getattr(self, "_current_active_tab", "editor")
        self._set_nav_active(active_tab)

    def _set_nav_active(self, key):
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=self.C["hover"], text_color=self.C["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=self.C["text"])

    def _refresh_plugin_ui(self):
        """Clears and redraws the plugin tools based on registered hooks."""
        tabs = []
        if hasattr(self, 'plugin_manager_instance'):
            tabs = self.plugin_manager_instance.custom_tabs
            
        # 1. Update Navigation Tabs ──────────
        nav_tabs = [(t["tab_id"], t["label"], t["icon"]) for t in tabs]
        self._build_nav_buttons(nav_tabs)
        
        # Unpack previously injected tab frames if removed
        active_plugin_tab_ids = [t["tab_id"] for t in tabs]
        keys_to_remove = []
        for frame_name, frame_obj in self.frames.items():
            if frame_name not in [base[0] for base in self.base_nav_items]:
                if frame_name not in active_plugin_tab_ids:
                    frame_obj.destroy()
                    keys_to_remove.append(frame_name)
                    
        for k in keys_to_remove:
            self.frames.pop(k, None)
            
        # Instantiate newly registered tab frames if not exist
        for t in tabs:
            if t["tab_id"] not in self.frames:
                widget_class = t["widget_class"]
                try:
                    # widget_class must accept (master)
                    frame_instance = widget_class(self.main_cont)
                    self.frames[t["tab_id"]] = frame_instance
                except Exception as e:
                    logging.error(f"Failed to instantiate plugin tab {t['tab_id']}: {e}")

        # If current frame was deleted, switch back to editor
        if getattr(self, "_current_active_tab", "editor") not in self.frames:
            self.show_frame("editor")
            
        if "plugins" in self.frames and hasattr(self.frames["plugins"], "_refresh_list"):
            self.frames["plugins"]._refresh_list()

    def show_frame(self, name):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        if name == "plugins" and hasattr(self.frames["plugins"], "_refresh_list"):
            self.frames["plugins"]._refresh_list()
            
        self._set_nav_active(name)
        
        display_name = name.replace('_', ' ').title()
        if name == "editor": display_name = "Score Editor"
        elif name == "audio": display_name = "Audio AI"
        elif name == "settings": display_name = "Settings"
        elif name == "plugins": display_name = "Plugins"
            
        self.set_status(f"● {tr(display_name)}", "ready")
        
    def _refresh_nav_translations(self):
        self._refresh_plugin_ui()
        self.save_btn.configure(text=f"💾  {tr('Save Project')}")
        self.load_btn.configure(text=f"📂  {tr('Load Project')}")
        active_tab = getattr(self, "_current_active_tab", "editor")
        self.show_frame(active_tab)

    def set_status(self, text, level="ready"):
        colors = {"ready":   self.C["success"],
                  "working": self.C["accent"],
                  "error":   self.C["accent2"]}
        self.status_lbl.configure(
            text=text, text_color=colors.get(level, self.C["success"]))

    def show_toast(self, message: str, level: str = "info", duration: int = 3000):
        toast = ctk.CTkLabel(
            self, text=f"  {message}  ", corner_radius=8,
            fg_color=self.C.get("card", "gray20"),
            text_color=self.C.get("success", "white") if level == "info" else self.C.get("accent2", "red"),
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        toast.place(relx=0.5, rely=0.9, anchor="center")
        self.after(duration, toast.destroy)

    def get_project_data(self):
        ed = self.frames["editor"]
        return {
            "title":           ed.title_entry.get(),
            "notes":           ed.notes_box.get("0.0", "end"),
            "sync_data":       ed.current_sync_data,
            "last_audio_path": ed._last_audio_path,
        }

    def save_proj(self):
        # Default filename = song title (sanitised)
        raw_title = self.frames["editor"].title_entry.get().strip()
        safe_name = "".join(
            ch for ch in raw_title
            if ch.isalpha() or ch.isdigit() or ch in " _-"
        ).strip() or "roneat_project"

        fp = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            initialfile=f"{safe_name}.roneat",
            defaultextension=".roneat",
            filetypes=[("Roneat Projects", "*.roneat")]
        )
        if not fp:
            return
        data = self.get_project_data()
        
        # Trigger on_project_save hook
        if hasattr(self, 'plugin_manager_instance'):
            self.plugin_manager_instance.trigger_hook("on_project_save", data)
            
        save_roneat_project(fp, data)
        self.frames["editor"]._last_zip_path = fp
        self.set_status(f"● Saved: {os.path.basename(fp)}", "ready")

    def load_proj_dialog(self):
        fp = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            filetypes=[("Roneat Projects", "*.roneat")])
        if fp:
            self.load_proj(fp)

    def load_proj(self, fp):
        data = load_roneat_project(fp)
        if data:
            ed = self.frames["editor"]
            ed.title_entry.delete(0, "end")
            ed.title_entry.insert(0, data.get("title", ""))
            ed.notes_box.delete("0.0", "end")
            ed.notes_box.insert("0.0", data.get("notes", ""))
            if ed._undo:
                ed._undo.snapshot()
            ed.current_sync_data = data.get("sync_data", None)
            ed._last_audio_path  = data.get("last_audio_path", None)
            ed._last_zip_path    = fp

            if ed.current_sync_data:
                ed.bpm_entry.configure(state="disabled")
                ed.sync_lbl.configure(text="⏱ Synced playback loaded")
            else:
                ed.bpm_entry.configure(state="normal")
                ed.sync_lbl.configure(text="")

            ed.update_preview()
            ed._run_validation()
            self.show_frame("editor")
            self.set_status(f"● Loaded: {os.path.basename(fp)}", "ready")
            
            # Trigger hook
            if hasattr(self, 'plugin_manager_instance'):
                self.plugin_manager_instance.trigger_hook("on_project_open", data)


    def import_from_audio(self, notes_str, is_two_mallets,
                          sync_data=None, audio_path=None):
        """Called by AudioToScore when user clicks 'Import to Score Editor'."""
        ed = self.frames["editor"]
        ed.notes_box.delete("0.0", "end")
        ed.notes_box.insert("0.0", notes_str)
        if ed._undo:
            ed._undo.snapshot()
        ed.left_hand_var.set(is_two_mallets)
        ed._last_audio_path = audio_path

        if sync_data:
            ed.current_sync_data = sync_data
            ed.bpm_entry.configure(state="disabled")
            ed.sync_lbl.configure(text="⏱ Playing at original recorded tempo")
        else:
            ed.current_sync_data = None
            ed.bpm_entry.configure(state="normal")
            ed.sync_lbl.configure(text="")

        ed.update_preview()
        ed._run_validation()
        self.show_frame("editor")
        self.set_status("● Score imported from audio", "ready")