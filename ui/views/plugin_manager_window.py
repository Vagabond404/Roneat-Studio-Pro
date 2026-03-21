import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import logging

class PluginManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent_app, plugin_manager):
        super().__init__(parent_app)
        self.app = parent_app
        self.pm = plugin_manager
        
        self.title("Plugin Manager — Roneat Studio Pro")
        self.geometry("800x600")
        self.minsize(700, 500)
        self.wm_transient(parent_app)
        
        self.C = self.app.C if hasattr(self.app, 'C') else {
            "accent":     "#D4AF37",
            "accent2":    "#e85d4a",
            "success":    "#3ab87a",
            "text":       ("gray10", "gray95"),
            "text_dim":   ("gray45", "#8b949e"),
            "sidebar_bg": ("gray92", "#090a0f"),
            "border":     ("gray80", "#1c2128"),
            "hover":      ("gray85", "#161b22"),
            "main_bg":    ("gray96", "#12151c"),
        }
        self.configure(fg_color=self.C["main_bg"])
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=self.C["sidebar_bg"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkLabel(header, text="🧩 Plugin Manager", 
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=self.C["accent"]).pack(side="left", padx=20, pady=16)
                     
        ctk.CTkButton(header, text="Browse Plugin Store", 
                      fg_color="transparent", text_color=self.C["accent"],
                      hover_color=self.C["hover"], width=0,
                      command=self._open_store).pack(side="right", padx=(0, 20), pady=16)

        ctk.CTkButton(header, text="➕ Install Plugin (.zip)",
                      fg_color=self.C["accent"], text_color="#090a0f",
                      hover_color="#e6c45c",
                      command=self._install_plugin).pack(side="right", padx=10, pady=16)
        
        # ── Plugin List ───────────────────────────────────────────────────────
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", 
            scrollbar_button_color=self.C["border"], scrollbar_button_hover_color=self.C["hover"]
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self._refresh_list()

    def _open_store(self):
        import webbrowser
        webbrowser.open("https://github.com/RoneatStudio/Plugins")

    def _install_plugin(self):
        fp = filedialog.askopenfilename(
            parent=self,
            title="Select Plugin ZIP",
            filetypes=[("ZIP Archives", "*.zip")]
        )
        if fp:
            success = self.pm.install_plugin(fp)
            if success:
                messagebox.showinfo("Success", "Plugin installed and enabled successfully.", parent=self)
                self._refresh_list()
            else:
                messagebox.showerror("Error", "Failed to install plugin. Check logs.", parent=self)

    def _refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        plugins = self.pm.get_installed_plugins()
        if not plugins:
            ctk.CTkLabel(
                self.scroll_frame, text="No plugins installed.\nClick 'Install Plugin' to add one.",
                font=ctk.CTkFont(size=14), text_color=self.C["text_dim"]
            ).pack(pady=40)
            return
            
        for i, info in enumerate(plugins):
            self._create_plugin_card(i, info)

    def _create_plugin_card(self, row: int, info):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=self.C["sidebar_bg"], corner_radius=12)
        card.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        # Left side: Details
        details = ctk.CTkFrame(card, fg_color="transparent")
        details.grid(row=0, column=0, sticky="ew", padx=16, pady=16)
        
        name_lbl = ctk.CTkLabel(details, text=f"{info.name} v{info.version}", 
                                font=ctk.CTkFont(size=16, weight="bold"),
                                text_color=self.C["text"])
        name_lbl.pack(anchor="w")
        
        author_lbl = ctk.CTkLabel(details, text=f"by {info.author}", 
                                  font=ctk.CTkFont(size=12, slant="italic"),
                                  text_color=self.C["text_dim"])
        author_lbl.pack(anchor="w", pady=(2, 8))
        
        desc_lbl = ctk.CTkLabel(details, text=info.description,
                                font=ctk.CTkFont(size=13),
                                text_color=self.C["text"], justify="left", wraplength=450)
        desc_lbl.pack(anchor="w")
        
        if info.error:
            err_lbl = ctk.CTkLabel(details, text=f"Error: {info.error}", 
                                   font=ctk.CTkFont(size=12), text_color=self.C["accent2"])
            err_lbl.pack(anchor="w", pady=(8, 0))

        # Right side: Controls
        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="e", padx=16, pady=16)
        
        # Switch
        switch_var = ctk.BooleanVar(value=info.active)
        sw = ctk.CTkSwitch(
            controls, text="Active" if info.active else "Disabled", variable=switch_var,
            onvalue=True, offvalue=False,
            progress_color=self.C["success"]
        )
        sw.pack(side="top", pady=(0, 10))
        # Keep ref to update text and use properly scoped variables
        sw.configure(command=lambda i=info, v=switch_var, widget=sw: self._toggle_plugin(i, v, widget))
        
        ctk.CTkButton(
            controls, text="Uninstall", width=80,
            fg_color="transparent", text_color=self.C["accent2"],
            hover_color=self.C["hover"], border_width=1, border_color=self.C["border"],
            command=lambda i=info.id: self._uninstall_plugin(i)
        ).pack(side="bottom")

    def _toggle_plugin(self, info, var, switch_widget):
        new_state = var.get()
        if new_state:
            success = self.pm.enable_plugin(info.id)
            if not success:
                var.set(False)
                messagebox.showerror("Error", f"Could not enable {info.name}", parent=self)
            else:
                switch_widget.configure(text="Active")
        else:
            success = self.pm.disable_plugin(info.id)
            if not success:
                var.set(True)
                messagebox.showerror("Error", f"Could not disable {info.name}", parent=self)
            else:
                switch_widget.configure(text="Disabled")

    def _uninstall_plugin(self, plugin_id: str):
        if messagebox.askyesno("Confirm", "Are you sure you want to uninstall this plugin?", parent=self):
            if self.pm.uninstall_plugin(plugin_id):
                self._refresh_list()
            else:
                messagebox.showerror("Error", "Failed to uninstall plugin.", parent=self)
