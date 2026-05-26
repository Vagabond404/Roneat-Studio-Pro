"""
ui/main_window.py  v4.0
========================
Roneat Studio Pro — Main Application Window

Changes in v4.0:
  - Premium DAW aesthetic: Deep Charcoal (#121212) + Matte Gold (#D4AF37)
  - Sidebar restructured: logo top, main nav middle, settings isolated at bottom
  - corner_radius=4 on all nav buttons for a clean, professional look
  - Main content frame: 1px #333333 border, corner_radius=0 (rectangular DAW panels)
  - ctk.set_appearance_mode("Dark") enforced globally
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
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


# ── Premium DAW Color Palette ────────────────────────────────────────────────
# All values are hardcoded for Dark mode — the entire design is dark-first.
# -- Premium DAW Color Palette: (light, dark) tuples for full theme support --
THEME = {
    "bg_deep":      ("#F2F2F2", "#121212"),
    "bg_panel":     ("#E8E8E8", "#1E1E1E"),
    "bg_card":      ("#FFFFFF", "#252526"),
    "bg_card2":     ("#F0F0F0", "#2A2D2E"),
    "border":       ("#CCCCCC", "#3E3E42"),
    "accent":       "#D4AF37",
    "accent2":      "#8E7611",
    "accent_err":   "#e85d4a",
    "success":      "#3ab87a",
    "blue":         "#3d8ec9",
    "warn":         "#f59e0b",
    "text":         ("#1A1A1A", "#E0E0E0"),
    "text_dim":     ("#666666", "#888888"),
    "hover_bg":     ("#DCDCDC", "#2A2A2A"),
}


class MainWindow(ctk.CTk):
    def __init__(self, initial_file=None):
        super().__init__()

        # Load saved theme (respect user preference — defaults to Dark)
        _saved_theme = load_app_settings().get("theme", "Dark")
        ctk.set_appearance_mode(_saved_theme)

        self.title("Roneat Studio Pro")
        self.geometry("1380x860")
        self.minsize(1100, 700)
        self.configure(fg_color=THEME["bg_deep"])

        # Expose color dict for child views that reference master.C
        self.C = {
            "accent":     THEME["accent"],
            "accent2":    THEME["accent_err"],
            "success":    THEME["success"],
            "text":       THEME["text"],
            "text_dim":   THEME["text_dim"],
            "sidebar_bg": THEME["bg_panel"],
            "border":     THEME["border"],
            "hover":      THEME["hover_bg"],
            "main_bg":    THEME["bg_deep"],
            "card":       THEME["bg_card"],
        }

        icon_path = resource_path(os.path.join("assets", "Roneat Studio Icon.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                logging.warning(f"Could not load icon: {e}")

        # ── Root grid: sidebar | main content ────────────────────────────────
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_content()

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
        
        # ── Set plugin manager reference in ScoreEditor for dynamic instruments ──
        self.frames["editor"].set_plugin_manager(self.plugin_manager_instance)
        
        # ── Set default instrument to Roneat Ek if available and active ──────
        try:
            all_plugins = self.plugin_manager_instance.get_installed_plugins()
            roneat_ek = next((p for p in all_plugins if p.id == "roneat_ek_standard" and p.active), None)
            if roneat_ek:
                self.plugin_manager_instance.set_active_instrument_plugin_id("roneat_ek_standard")
                logging.info("Default instrument set to Roneat Ek")
        except Exception as e:
            logging.warning(f"Could not set default instrument: {e}")
        
        # ── Populate instrument selector after plugin manager is ready ────────
        self._update_instrument_selector()

        # ── Drag & drop .roneat files ─────────────────────────────────────────
        self._setup_drag_drop()

        if initial_file:
            self.load_proj(initial_file)

        # Hook on_app_start fired ONLY AFTER all UI is fully built
        self._app_is_ready = True
        self.plugin_manager_instance.trigger_hook("on_app_start")
        self._refresh_plugin_ui()

    # ─────────────────────────────────────────────────────────────────────────
    # Sidebar construction
    # ─────────────────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        """Build the sidebar: logo top, main nav middle, settings isolated at bottom."""
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=THEME["bg_panel"],
            border_width=0
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Row layout:
        #   0: logo block
        #   1: thin separator
        #   2: main nav frame (Score Editor, Audio AI, Plugins)
        #   3: spacer — pushes settings to the bottom
        #   4: gold separator line before settings
        #   5: settings button
        #   6: thin separator
        #   7: save/load/status footer
        self.sidebar.grid_rowconfigure(3, weight=1)   # spacer expands
        self.sidebar.grid_columnconfigure(0, weight=1)

        # ── Logo ─────────────────────────────────────────────────────────────
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(32, 0))

        # Load high-quality banners (Gold for Light mode, White for Dark mode)
        try:
            # We use resource_path to ensure it works when packaged as EXE
            banner_gold_path = resource_path(os.path.join("assets", "icons", "Roneat Banner - Gold.png"))
            banner_white_path = resource_path(os.path.join("assets", "icons", "Roneat Banner - White.png"))
            
            logo_img = ctk.CTkImage(
                light_image=Image.open(banner_gold_path),
                dark_image=Image.open(banner_white_path),
                size=(180, 90)
            )
            logo_lbl = ctk.CTkLabel(logo_frame, image=logo_img, text="")
            logo_lbl.pack(pady=(10, 5))
        except Exception as e:
            import logging
            logging.warning(f"Could not load banner images: {e}")
            # Fallback to emoji if images are missing
            ctk.CTkLabel(
                logo_frame,
                text="🎼",
                font=ctk.CTkFont(size=48)
            ).pack(pady=(10, 5))

        ctk.CTkLabel(
            logo_frame,
            text="RONEAT STUDIO PRO",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=THEME["accent"]
        ).pack(anchor="center", pady=(4, 0))

        ctk.CTkLabel(
            logo_frame,
            text="v3.0.0",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=THEME["text_dim"]
        ).pack(anchor="center", pady=(2, 0))

        # Separator under logo
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=THEME["border"]
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(18, 0))

        # ── Main Navigation ──────────────────────────────────────────────────
        # Items: Score Editor, Audio AI, Plugins (Settings is separate at bottom)
        self.base_nav_items = [
            ("editor",  "Score Editor", "🎼"),
            ("audio",   "Audio AI",     "🎤"),
        ]
        self._nav_btns = {}

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(16, 0))

        self._build_nav_buttons()

        # ── Spacer (row 3 has weight=1, pushes everything below to bottom) ───
        # (implicit via grid_rowconfigure above)

        # ── Gold separator above bottom utilities ────────────────────────────
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=THEME["accent2"]
        ).grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 8))

        # ── Instrument Selector Label ────────────────────────────────────────
        ctk.CTkLabel(
            self.sidebar,
            text="🎸  Instrument",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=THEME["text_dim"]
        ).grid(row=5, column=0, sticky="w", padx=16, pady=(0, 4))

        # ── Instrument Selector ──────────────────────────────────────────────
        # Initially empty, will be populated when a project loads
        self._instrument_selector = ctk.CTkOptionMenu(
            self.sidebar,
            values=["No project loaded"],
            command=self._on_instrument_changed,
            fg_color=THEME["bg_card"],
            button_color=THEME["accent"],
            button_hover_color=THEME["accent2"],
            text_color=THEME["text"],
            dropdown_fg_color=THEME["bg_card"],
            dropdown_text_color=THEME["text"],
            anchor="w",
            height=36,
            corner_radius=4,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self._instrument_selector.grid(row=6, column=0, sticky="ew", padx=12, pady=(0, 8))
        self._instrument_selector.configure(state="disabled")
        self._instrument_selector_enabled = False
        self._instrument_id_to_name_map = {}  # For reverse lookup

        # ── Plugins button ───────────────────────────────────────────────────
        self._plugins_btn = ctk.CTkButton(
            self.sidebar,
            text=f"  🧩   {tr('Plugins')}",
            command=lambda: self.show_frame("plugins"),
            fg_color="transparent",
            text_color=THEME["text"],
            hover_color=THEME["hover_bg"],
            anchor="w",
            height=42,
            corner_radius=4,
            border_width=0,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self._plugins_btn.grid(row=7, column=0, sticky="ew", padx=12, pady=(0, 4))

        # ── Settings button ──────────────────────────────────────────────────
        self._settings_btn = ctk.CTkButton(
            self.sidebar,
            text=f"  ⚙   {tr('Settings')}",
            command=lambda: self.show_frame("settings"),
            fg_color="transparent",
            text_color=THEME["text"],
            hover_color=THEME["hover_bg"],
            anchor="w",
            height=42,
            corner_radius=4,
            border_width=0,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self._settings_btn.grid(row=8, column=0, sticky="ew", padx=12, pady=(0, 8))

        # ── Separator above footer ────────────────────────────────────────────
        ctk.CTkFrame(
            self.sidebar, height=1, fg_color=THEME["border"]
        ).grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 0))

        # ── Footer: Save / Load / Status ──────────────────────────────────────
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=10, column=0, sticky="ew", padx=12, pady=(8, 16))
        footer.grid_columnconfigure(0, weight=1)

        self.save_btn = ctk.CTkButton(
            footer,
            text=f"💾  {tr('Save Project')}",
            command=self.save_proj,
            fg_color=THEME["accent"],
            text_color="#0d0d0d",
            hover_color=THEME["accent2"],
            height=38,
            corner_radius=4,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.save_btn.pack(fill="x", pady=(0, 6))

        self.load_btn = ctk.CTkButton(
            footer,
            text=f"📂  {tr('Load Project')}",
            command=self.load_proj_dialog,
            fg_color="transparent",
            text_color=THEME["text"],
            border_width=1,
            border_color=THEME["border"],
            hover_color=THEME["hover_bg"],
            height=36,
            corner_radius=4,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.load_btn.pack(fill="x", pady=(0, 10))

        self.status_lbl = ctk.CTkLabel(
            footer,
            text=f"●  {tr('Ready')}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["success"]
        )
        self.status_lbl.pack(anchor="w", padx=4)

    def _build_main_content(self):
        """Build the main content frame — rectangular, 1px charcoal border."""
        self.main_cont = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=THEME["bg_deep"],
            border_width=1,
            border_color=THEME["border"]
        )
        self.main_cont.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        self.main_cont.grid_rowconfigure(0, weight=1)
        self.main_cont.grid_columnconfigure(0, weight=1)

    # ─────────────────────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────────────────────

    def _build_nav_buttons(self, plugin_tabs=None):
        """Rebuild the main navigation frame buttons (excludes Settings)."""
        for widget in self.nav_frame.winfo_children():
            widget.destroy()

        self._nav_btns.clear()

        all_items = list(self.base_nav_items)

        if plugin_tabs:
            all_items.extend(plugin_tabs)

        for key, label, icon in all_items:
            btn = ctk.CTkButton(
                self.nav_frame,
                text=f"  {icon}   {tr(label)}",
                command=lambda k=key: self.show_frame(k),
                fg_color="transparent",
                text_color=THEME["text"],
                hover_color=THEME["hover_bg"],
                anchor="w",
                height=42,
                corner_radius=4,
                border_width=0,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
            )
            btn.pack(fill="x", pady=3)
            self._nav_btns[key] = btn

        active_tab = getattr(self, "_current_active_tab", "editor")
        self._set_nav_active(active_tab)

    def _set_nav_active(self, key):
        """Highlight the active nav button in Gold; reset others to transparent."""
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(
                    fg_color=THEME["hover_bg"],
                    text_color=THEME["accent"]
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=THEME["text"]
                )

        # Handle isolated buttons (Settings, Plugins) highlight
        if hasattr(self, '_settings_btn'):
            is_settings = (key == "settings")
            self._settings_btn.configure(
                fg_color=THEME["hover_bg"] if is_settings else "transparent",
                text_color=THEME["accent"] if is_settings else THEME["text"]
            )
        
        if hasattr(self, '_plugins_btn'):
            is_plugins = (key == "plugins")
            self._plugins_btn.configure(
                fg_color=THEME["hover_bg"] if is_plugins else "transparent",
                text_color=THEME["accent"] if is_plugins else THEME["text"]
            )

    def _refresh_plugin_ui(self):
        """Clears and redraws the plugin tools based on registered hooks."""
        tabs = []
        if hasattr(self, 'plugin_manager_instance'):
            tabs = self.plugin_manager_instance.custom_tabs

        # 1. Update Navigation Tabs
        nav_tabs = [(t["tab_id"], t["label"], t["icon"]) for t in tabs]
        self._build_nav_buttons(nav_tabs)

        # Remove previously injected tab frames if no longer registered
        active_plugin_tab_ids = [t["tab_id"] for t in tabs]
        keys_to_remove = []
        for frame_name, frame_obj in self.frames.items():
            if frame_name not in [base[0] for base in self.base_nav_items] and frame_name not in ["settings", "plugins"]:
                if frame_name not in active_plugin_tab_ids:
                    frame_obj.destroy()
                    keys_to_remove.append(frame_name)

        for k in keys_to_remove:
            self.frames.pop(k, None)

        # Instantiate newly registered tab frames
        for t in tabs:
            if t["tab_id"] not in self.frames:
                widget_class = t["widget_class"]
                try:
                    frame_instance = widget_class(self.main_cont)
                    self.frames[t["tab_id"]] = frame_instance
                except Exception as e:
                    logging.error(f"Failed to instantiate plugin tab {t['tab_id']}: {e}")

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

        self._current_active_tab = name
        self._set_nav_active(name)

        display_name = name.replace('_', ' ').title()
        if name == "editor":   display_name = "Score Editor"
        elif name == "audio":  display_name = "Audio AI"
        elif name == "settings": display_name = "Settings"
        elif name == "plugins": display_name = "Plugins"

        self.set_status(f"●  {tr(display_name)}", "ready")

    def _refresh_nav_translations(self):
        self._refresh_plugin_ui()
        self.save_btn.configure(text=f"💾  {tr('Save Project')}")
        self.load_btn.configure(text=f"📂  {tr('Load Project')}")
        active_tab = getattr(self, "_current_active_tab", "editor")
        self.show_frame(active_tab)

    # ─────────────────────────────────────────────────────────────────────────
    # Status / Toast
    # ─────────────────────────────────────────────────────────────────────────

    def set_status(self, text, level="ready"):
        colors = {
            "ready":   THEME["success"],
            "working": THEME["accent"],
            "error":   THEME["accent_err"]
        }
        self.status_lbl.configure(
            text=text,
            text_color=colors.get(level, THEME["success"])
        )

    def show_toast(self, message: str, level: str = "info", duration: int = 3000):
        toast = ctk.CTkLabel(
            self,
            text=f"  {message}  ",
            corner_radius=4,
            fg_color=THEME["bg_card"],
            text_color=THEME["success"] if level == "info" else THEME["accent_err"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        toast.place(relx=0.5, rely=0.92, anchor="center")
        self.after(duration, toast.destroy)

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
        if raw.startswith('{') and raw.endswith('}'):
            raw = raw[1:-1]
        fp = raw.strip('"')
        if os.path.isfile(fp):
            if fp.lower().endswith('.roneat'):
                self.load_proj(fp)
            else:
                try:
                    self.frames["audio"]._drop_file(fp)
                    self.show_frame("audio")
                except Exception as e:
                    logging.error(f"Error handling dropped audio file: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Failed to load dropped file:\n{e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Project data
    # ─────────────────────────────────────────────────────────────────────────

    def get_project_data(self):
        ed = self.frames["editor"]
        project_data = {
            "title":           ed.title_entry.get(),
            "author":          ed.author_entry.get() if hasattr(ed, "author_entry") else "Anonymous",
            "notes":           ed._get_numeric_score_text(),  # always numeric for storage
            "sync_data":       ed.current_sync_data,
            "last_audio_path": ed._last_audio_path,
            "measure":         ed.measure_combo.get(),
            "grid":            ed.grid_combo.get(),
            "font_size":       int(ed.font_size_slider.get()),
            "accent":          ed.C.get("accent", "#c8a96e"),
            "left_hand":       ed.left_hand_var.get(),
            "show_nums":       ed.show_numbers_var.get(),
            "bpm":             ed.bpm_entry.get(),
            "hits_sec":        ed.trem_speed_entry.get()
        }
        
        # Include active instrument plugin ID
        if hasattr(self, 'plugin_manager_instance'):
            project_data["instrument_id"] = self.plugin_manager_instance.get_active_instrument_plugin_id()
        
        return project_data

    def save_proj(self):
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
        
        # Save using save_roneat_project
        if save_roneat_project(fp, data):
            if hasattr(self, 'plugin_manager_instance'):
                self.plugin_manager_instance.trigger_hook("on_project_save", data)

            self.frames["editor"]._last_zip_path = fp
            self.set_status(f"●  Saved: {os.path.basename(fp)}", "ready")
        else:
            self.set_status("Error saving project", "error")

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
            
            # ── Load and set active instrument plugin ──────────────────────────
            instrument_id = data.get("instrument_id", "roneat_ek")
            if hasattr(self, 'plugin_manager_instance'):
                if not self.plugin_manager_instance.set_active_instrument_plugin_id(instrument_id):
                    # Plugin not found or inactive, fall back to roneat_ek
                    from tkinter import messagebox
                    messagebox.showwarning(
                        title="Instrument Plugin Not Found",
                        message=f"The instrument plugin '{instrument_id}' is not available.\n"
                                f"Falling back to 'roneat_ek'."
                    )
                    self.plugin_manager_instance.set_active_instrument_plugin_id("roneat_ek")
            
            ed.title_entry.delete(0, "end")
            ed.title_entry.insert(0, data.get("title", ""))
            
            if hasattr(ed, "author_entry"):
                ed.author_entry.delete(0, "end")
                ed.author_entry.insert(0, data.get("author", ""))
                
            ed.notes_box.delete("0.0", "end")
            ed.notes_box.insert("0.0", data.get("notes", ""))
            # Loaded text is always numeric — reset the decode-mode tracker
            ed._prev_mode = "Numeric"
            # If the UI is currently in a non-numeric mode, re-encode now
            current_mode = ed.get_active_view_mode()
            if current_mode != "Numeric":
                new_text = ed._numeric_to_mode(data.get("notes", ""), current_mode)
                ed._syncing_text = True
                try:
                    ed.notes_box.delete("0.0", "end")
                    ed.notes_box.insert("0.0", new_text)
                finally:
                    ed._syncing_text = False
                ed._prev_mode = current_mode
            
            # Restore display parameters
            if "measure" in data:
                ed.measure_combo.set(data["measure"])
            if "grid_columns" in data and data["grid_columns"]:
                gc = data["grid_columns"]
                for val in ed.grid_combo._values:
                    if val.startswith(str(gc)):
                        ed.grid_combo.set(val)
                        break
            if "font_size" in data:
                ed.font_size_slider.set(data["font_size"])
            if "accent" in data:
                ed.C["accent"] = data["accent"]
            if "left_hand" in data:
                ed.left_hand_var.set(data["left_hand"])
            if "show_nums" in data:
                ed.show_numbers_var.set(data["show_nums"])
            if "bpm" in data:
                # Force-enable before inserting — entry may be disabled from previous sync project
                ed.bpm_entry.configure(state="normal")
                ed.bpm_entry.delete(0, "end")
                # Sanitize to plain integer string (handles "170.0" saved as float)
                try:
                    bpm_val = str(int(float(str(data["bpm"]))))
                except (ValueError, TypeError):
                    bpm_val = "120"
                ed.bpm_entry.insert(0, bpm_val)
            if "hits_sec" in data:
                ed.trem_speed_entry.configure(state="normal")
                ed.trem_speed_entry.delete(0, "end")
                ed.trem_speed_entry.insert(0, data["hits_sec"])
            
            # Sync loaded data
            ed._update_metadata_from_ui()
            
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
            self.set_status(f"●  Loaded: {os.path.basename(fp)}", "ready")

            if hasattr(self, 'plugin_manager_instance'):
                self.plugin_manager_instance.trigger_hook("on_project_open", data)
            
            # ── Update instrument selector after loading ──────────────────────
            self._update_instrument_selector()

    def _update_instrument_selector(self):
        """Populate the instrument selector dropdown with available instruments.
        
        Only shows the dropdown if there are 2 or more active instrument plugins.
        """
        if not hasattr(self, 'plugin_manager_instance'):
            return
        
        available = self.plugin_manager_instance.get_available_instruments()
        
        # Hide selector if less than 2 instruments available
        if not available or len(available) < 2:
            self._instrument_selector.grid_remove()  # Hide the dropdown
            self._instrument_selector_enabled = False
            self._instrument_id_to_name_map = {}
            
            # Still set active instrument to first available (if any)
            if available:
                first_plugin_id = available[0][0]
                self.plugin_manager_instance.set_active_instrument_plugin_id(first_plugin_id)
            
            return
        
        # Show the selector
        self._instrument_selector.grid()
        
        # Build mapping: plugin_id -> plugin_name
        self._instrument_id_to_name_map = {plugin_id: name for plugin_id, name in available}
        
        # Create list of names for dropdown (sorted)
        instrument_names = [name for _, name in available]
        self._instrument_selector.configure(values=instrument_names, state="normal")
        
        # Set dropdown to current active instrument
        current_id = self.plugin_manager_instance.get_active_instrument_plugin_id()
        if current_id in self._instrument_id_to_name_map:
            display_name = self._instrument_id_to_name_map[current_id]
            self._instrument_selector.set(display_name)
        else:
            # Fallback to first available
            first_name = instrument_names[0] if instrument_names else "Unknown"
            self._instrument_selector.set(first_name)
        
        self._instrument_selector_enabled = True

    def refresh_instrument_ui(self):
        """Refresh the entire instrument UI after plugin changes.
        
        This method is called automatically when plugins are enabled/disabled
        to update the dropdown and all related UI elements.
        """
        # Update instrument selector dropdown
        self._update_instrument_selector()
        
        # Refresh the score editor grid with new instrument settings
        ed = self.frames.get("editor")
        if ed:
            ed.update_preview()
        
        logging.info("Instrument UI refreshed")

    def _on_instrument_changed(self, selected_display_name):
        """Handle user selecting a different instrument from the dropdown."""
        if not self._instrument_selector_enabled:
            return
        
        # Reverse lookup: display_name -> plugin_id
        plugin_id = None
        for pid, pname in self._instrument_id_to_name_map.items():
            if pname == selected_display_name:
                plugin_id = pid
                break
        
        if not plugin_id:
            return
        
        # Set active instrument
        if not self.plugin_manager_instance.set_active_instrument_plugin_id(plugin_id):
            messagebox.showerror(
                title="Instrument Error",
                message=f"Failed to switch to instrument '{selected_display_name}'."
            )
            return
        
        # Update current score's instrument_id if project is open
        ed = self.frames.get("editor")
        if ed and hasattr(ed, 'current_score') and ed.current_score:
            ed.current_score.instrument_id = plugin_id
        
        # Refresh the score editor grid with new instrument's note range
        if ed:
            ed.update_preview()
            self.set_status(f"●  Switched to: {selected_display_name}", "ready")

    def import_from_audio(self, notes_str, is_two_mallets,
                          sync_data=None, audio_path=None):
        """Called by AudioToScore when user clicks 'Import to Score Editor'."""
        ed = self.frames["editor"]
        ed.notes_box.delete("0.0", "end")
        ed.notes_box.insert("0.0", notes_str)
        # notes_str from audio pipeline is always numeric
        ed._prev_mode = "Numeric"
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
        self.set_status("●  Score imported from audio", "ready")