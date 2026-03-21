import customtkinter as ctk
import os
import shutil
import importlib
import logging
from tkinter import filedialog, messagebox

class PluginManagerTab(ctk.CTkFrame):
    def __init__(self, master, plugin_manager):
        super().__init__(master, fg_color="transparent")
        self.pm = plugin_manager
        
        # Access theme colors from MainWindow
        self.C = master.master.C if hasattr(master.master, 'C') else {
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
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 10))
        
        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(fill="x")
        
        ctk.CTkLabel(title_row, text="🧩 Plugin Manager", 
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=self.C["text"][1] if ctk.get_appearance_mode() == "Dark" else self.C["text"][0]).pack(side="left")
                     
        ctk.CTkButton(title_row, text="➕ Install Plugin (.zip)",
                      fg_color=self.C["accent"], text_color="#090a0f",
                      hover_color="#deba7e", height=36, corner_radius=8,
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=self._install_plugin).pack(side="right")
                      
        ctk.CTkLabel(header, text="Extend the capabilities of Roneat Studio Pro with third-party tools and effects.",
                     font=ctk.CTkFont(family="Segoe UI", size=13),
                     text_color=self.C["text_dim"]).pack(anchor="w", pady=(4, 0))
        
        ctk.CTkFrame(header, height=1, fg_color=self.C["border"]).pack(fill="x", pady=(20, 0))
        
        # ── Plugin List ───────────────────────────────────────────────────────
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color="transparent", 
            scrollbar_button_color=self.C["accent"]
        )
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        self._refresh_list()

    def _install_plugin(self):
        fp = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Select Plugin ZIP",
            filetypes=[("ZIP Archives", "*.zip")]
        )
        if fp:
            success = self.pm.install_plugin(fp)
            if success:
                messagebox.showinfo("Success", "Plugin installed and enabled successfully. Custom UI menus have been added to the sidebar.", parent=self.winfo_toplevel())
                self._refresh_list()
                self._update_main_ui()
            else:
                messagebox.showerror("Error", "Failed to install plugin. Please check the logs.", parent=self.winfo_toplevel())

    def _refresh_list(self):
        if not self.pm:
            return
            
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        plugins = self.pm.get_installed_plugins()
        if not plugins:
            ctk.CTkLabel(
                self.scroll_frame, text="No plugins installed.\nClick 'Install Plugin' to add one.",
                font=ctk.CTkFont(family="Segoe UI", size=14), text_color=self.C["text_dim"]
            ).pack(pady=40)
            return
            
        for i, info in enumerate(plugins):
            self._create_plugin_card(i, info)

    def _create_plugin_card(self, row: int, info):
        # Card matching app theme instead of hardcoded dark
        card_color = self.C.get("card", ("white", "#161b22"))
        card = ctk.CTkFrame(self.scroll_frame, fg_color=card_color, corner_radius=12,
                            border_width=1, border_color=self.C["accent"] if info.active else self.C["border"])
        card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        # Left side: Details
        details = ctk.CTkFrame(card, fg_color="transparent")
        details.grid(row=0, column=0, sticky="ew", padx=20, pady=16)
        
        name_lbl = ctk.CTkLabel(details, text=f"{info.name}", 
                                font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                text_color=self.C["text"])
        name_lbl.pack(side="left", anchor="w")
        
        status_color = self.C["success"] if info.active else self.C["text_dim"]
        ctk.CTkLabel(details, text="●" if info.active else "○", 
                     font=ctk.CTkFont(size=14), text_color=status_color).pack(side="left", padx=8)
        
        meta = ctk.CTkFrame(card, fg_color="transparent")
        meta.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 4))
        
        desc_lbl = ctk.CTkLabel(meta, text=info.description,
                                font=ctk.CTkFont(family="Segoe UI", size=13, slant="italic"),
                                text_color=self.C["text_dim"], justify="left", wraplength=500)
        desc_lbl.pack(anchor="w")
        
        v_lbl = ctk.CTkLabel(meta, text=f"v{info.version} • {info.author}", 
                             font=ctk.CTkFont(family="Courier", size=11),
                             text_color=self.C.get("text_dim", "#6e7781"))
        v_lbl.pack(anchor="w", pady=(8, 16))
        
        if info.error:
            err_lbl = ctk.CTkLabel(meta, text=f"Error: {info.error}", 
                                   font=ctk.CTkFont(size=12), text_color=self.C["accent2"])
            err_lbl.pack(anchor="w", pady=(0, 16))

        # Right side: Controls
        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.grid(row=0, column=1, rowspan=2, sticky="ne", padx=20, pady=20)
        
        # Switch
        switch_var = ctk.BooleanVar(value=info.active)
        sw = ctk.CTkSwitch(
            controls, text="Active" if info.active else "Disabled", variable=switch_var,
            onvalue=True, offvalue=False,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            progress_color=self.C["accent"]
        )
        sw.pack(side="top", pady=(0, 12))
        sw.configure(command=lambda i=info, v=switch_var, widget=sw: self._toggle_plugin(i, v, widget))
        
        ctk.CTkButton(
            controls, text="↻ Reload", width=80, height=28, corner_radius=6,
            fg_color="transparent", text_color=self.C["accent"],
            hover_color=self.C["hover"], border_width=1, border_color=self.C["accent"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=lambda i=info.id: self._reload_plugin(i)
        ).pack(side="top", pady=(0, 6))

        ctk.CTkButton(
            controls, text="Uninstall", width=80, height=28, corner_radius=6,
            fg_color="transparent", text_color=self.C["accent2"],
            hover_color=self.C["hover"], border_width=1, border_color=self.C["border"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=lambda i=info.id: self._uninstall_plugin(i)
        ).pack(side="top")

        # Plugin Specific Tools
        plugin_cmds = [item for item in self.pm.menu_items if item.get("plugin_id") == info.id]
        plugin_btns = [item for item in self.pm.toolbar_buttons if item.get("plugin_id") == info.id]
        all_tools = plugin_cmds + plugin_btns
        
        if info.active and all_tools:
            tools_frame = ctk.CTkFrame(card, fg_color="transparent")
            tools_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 16))
            
            ctk.CTkLabel(tools_frame, text="Tools:", 
                         font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), 
                         text_color=self.C["text_dim"]).pack(side="left", padx=(0, 10))
                         
            for tool in all_tools:
                lbl = tool.get("label", tool.get("tooltip", "Tool"))
                icon = tool.get("icon", "🔧")
                ctk.CTkButton(
                    tools_frame, text=f"{icon} {lbl}", command=tool.get("cmd"),
                    height=28, fg_color=self.C["card"], text_color=self.C["text"],
                    border_width=1, border_color=self.C["border"], hover_color=self.C["hover"],
                ).pack(side="left", padx=4)

    def _update_main_ui(self):
        """Forces the MainWindow to refresh plugin injected UI components."""
        app = self.pm.app
        if app and hasattr(app, '_refresh_plugin_ui'):
            app._refresh_plugin_ui()

    def _toggle_plugin(self, info, var, switch_widget):
        new_state = var.get()
        if new_state:
            success = self.pm.enable_plugin(info.id)
            if not success:
                var.set(False)
                messagebox.showerror("Error", f"Could not enable {info.name}", parent=self.winfo_toplevel())
            else:
                switch_widget.configure(text="Active")
        else:
            success = self.pm.disable_plugin(info.id)
            if not success:
                var.set(True)
                messagebox.showerror("Error", f"Could not disable {info.name}", parent=self.winfo_toplevel())
            else:
                switch_widget.configure(text="Disabled")
        self._refresh_list()
        self._update_main_ui()

    def _reload_plugin(self, plugin_id: str):
        info = self.pm.plugins.get(plugin_id)
        if not info: return
        
        logging.info(f"Reloading plugin: {plugin_id}")
        self.pm.disable_plugin(plugin_id)
        
        # force module reload if previously imported
        mod_name = f"roneat_plugins.{plugin_id}"
        if mod_name in importlib.sys.modules:
            try:
                importlib.reload(importlib.sys.modules[mod_name])
            except Exception as e:
                logging.error(f"Failed to reload module {mod_name}: {e}")
                
        self.pm.enable_plugin(plugin_id)
        messagebox.showinfo("Reload complete", f"Plugin {info.name} has been reloaded.", parent=self.winfo_toplevel())
        self._refresh_list()
        self._update_main_ui()

    def _uninstall_plugin(self, plugin_id: str):
        if messagebox.askyesno("Confirm", "Are you sure you want to uninstall this plugin?", parent=self.winfo_toplevel()):
            if self.pm.uninstall_plugin(plugin_id):
                self._refresh_list()
                self._update_main_ui()
            else:
                messagebox.showerror("Error", "Failed to uninstall plugin.", parent=self.winfo_toplevel())
