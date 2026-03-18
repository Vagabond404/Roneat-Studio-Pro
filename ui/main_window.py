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
            "accent":     "#c8a96e",
            "accent2":    "#e85d4a",
            "success":    "#3ab87a",
            "text":       ("gray10", "gray92"),
            "text_dim":   ("gray45", "gray60"),
            "sidebar_bg": ("gray92", "#0f1117"),
            "border":     ("gray80", "#1e2330"),
            "hover":      ("gray85", "#1a1f2e"),
        }

        icon_path = resource_path(os.path.join("assets", "logo.ico"))
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception as e:
                logging.warning(f"Could not load icon: {e}")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=230, corner_radius=0,
                                    fg_color=self.C["sidebar_bg"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(6, weight=1)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.grid(row=0, column=0, pady=(32, 6), padx=20, sticky="ew")
        ctk.CTkLabel(logo, text="ᨠ",
                     font=ctk.CTkFont(size=44),
                     text_color=self.C["accent"]).pack(anchor="center")
        ctk.CTkLabel(logo, text="Roneat Studio",
                     font=ctk.CTkFont(family="Georgia", size=17, weight="bold"),
                     text_color=self.C["accent"]).pack(anchor="center", pady=(4, 0))
        ctk.CTkLabel(logo, text="PRO",
                     font=ctk.CTkFont(family="Courier", size=9, weight="bold"),
                     text_color=self.C["text_dim"]).pack(anchor="center")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.C["border"]
                     ).grid(row=1, column=0, padx=18, pady=(8, 16), sticky="ew")

        nav_items = [
            ("editor",   "Score Editor", "🎼"),
            ("audio",    "Audio AI",     "🎤"),
            ("settings", "Settings",     "⚙"),
        ]
        self._nav_btns = {}
        for idx, (key, label, icon) in enumerate(nav_items):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"  {icon}   {label}",
                command=lambda k=key: self.show_frame(k),
                fg_color="transparent",
                text_color=self.C["text"],
                hover_color=self.C["hover"],
                anchor="w", height=44, corner_radius=10,
                font=ctk.CTkFont(size=13)
            )
            btn.grid(row=2 + idx, column=0, pady=2, padx=10, sticky="ew")
            self._nav_btns[key] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=self.C["border"]
                     ).grid(row=5, column=0, padx=18, pady=(8, 12), sticky="ew")

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.grid(row=7, column=0, sticky="ew", padx=14, pady=4)

        ctk.CTkButton(
            bottom, text="💾  Save Project",
            command=self.save_proj,
            fg_color=self.C["accent"], text_color="#0f1117",
            hover_color="#deba7e", height=40, corner_radius=10,
            font=ctk.CTkFont(family="Georgia", size=12, weight="bold")
        ).pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            bottom, text="📂  Load Project",
            command=self.load_proj_dialog,
            fg_color="transparent", text_color=self.C["text"],
            border_width=1, border_color=self.C["border"],
            hover_color=self.C["hover"], height=38, corner_radius=10,
            font=ctk.CTkFont(size=12)
        ).pack(fill="x")

        status_f = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_f.grid(row=9, column=0, sticky="ew", padx=14, pady=(0, 16))
        self.status_lbl = ctk.CTkLabel(
            status_f, text="● Ready",
            font=ctk.CTkFont(size=11),
            text_color=self.C["success"]
        )
        self.status_lbl.pack(anchor="w", padx=6)

        # ── Main content ──────────────────────────────────────────────────────
        self.main_cont = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_cont.grid(row=0, column=1, sticky="nsew")
        self.main_cont.grid_rowconfigure(0, weight=1)
        self.main_cont.grid_columnconfigure(0, weight=1)

        self.frames = {
            "editor":   ScoreEditor(self.main_cont, self.get_project_data),
            "audio":    AudioToScore(self.main_cont, self.import_from_audio),
            "settings": SettingsPage(self.main_cont),
        }

        self.show_frame("editor")

        # ── Drag & drop .roneat files ─────────────────────────────────────────
        self._setup_drag_drop()

        if initial_file:
            self.load_proj(initial_file)

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

    def _set_nav_active(self, key):
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.configure(fg_color=self.C["hover"], text_color=self.C["accent"])
            else:
                btn.configure(fg_color="transparent", text_color=self.C["text"])

    def show_frame(self, name):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)
        self._set_nav_active(name)
        self.set_status(f"● {name.replace('_', ' ').title()}", "ready")

    def set_status(self, text, level="ready"):
        colors = {"ready":   self.C["success"],
                  "working": self.C["accent"],
                  "error":   self.C["accent2"]}
        self.status_lbl.configure(
            text=text, text_color=colors.get(level, self.C["success"]))

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