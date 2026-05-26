import re
import sys

filename = "c:/Users/ange-/PycharmProjects/Roneat_Studio/ui/views/score_editor.py"
with open(filename, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add Glow Intensity slider after font_size_slider
glow_slider_code = """        self.font_size_slider.pack(fill="x", padx=18, pady=(2, 8))
        self._row_label(card, "Glow Intensity")
        self.glow_slider = ctk.CTkSlider(
            card, from_=0.0, to=1.0, number_of_steps=20,
            command=self._request_update,
            progress_color = self.C["accent"],
            button_color = self.C["accent"], height=18)
        self.glow_slider.set(0.6)
        self.glow_slider.pack(fill="x", padx=18, pady=(2, 8))"""
content = content.replace('        self.font_size_slider.pack(fill="x", padx=18, pady=(2, 8))', glow_slider_code)

# 2. Replace roneat_canvas with roneat_label
canvas_setup = """        self.roneat_canvas = tk.Canvas(f, highlightthickness=0)
        self.roneat_canvas.grid(row=3, column=0, sticky="nsew")

        self.roneat_canvas.bind("<Configure>",
            lambda e: self._draw_roneat2d(self._playing_bar))
        self.roneat_canvas.bind("<ButtonPress-1>",   self._on_bar_press)
        self.roneat_canvas.bind("<ButtonRelease-1>", self._on_bar_release)
        self.roneat_canvas.bind("<ButtonPress-3>",   self._on_bar_right_click)
        self.roneat_canvas.bind("<Motion>",          self._on_canvas_motion)
        self.roneat_canvas.bind("<Leave>",           self._on_canvas_leave)"""

label_setup = """        self.roneat_label = ctk.CTkLabel(f, text="")
        self.roneat_label.grid(row=3, column=0, sticky="nsew")

        self.roneat_label.bind("<Configure>",
            lambda e: self._draw_roneat2d(self._playing_bar))
        self.roneat_label.bind("<ButtonPress-1>",   self._on_bar_press)
        self.roneat_label.bind("<ButtonRelease-1>", self._on_bar_release)
        self.roneat_label.bind("<ButtonPress-3>",   self._on_bar_right_click)
        self.roneat_label.bind("<Motion>",          self._on_canvas_motion)
        self.roneat_label.bind("<Leave>",           self._on_canvas_leave)"""
content = content.replace(canvas_setup, label_setup)

# 3. Replace W = self.roneat_canvas.winfo_width() in _bar_at_xy
content = content.replace("W = self.roneat_canvas.winfo_width()", "W = self.roneat_label.winfo_width()")
content = content.replace("H = self.roneat_canvas.winfo_height()", "H = self.roneat_label.winfo_height()")

# 4. Replace _draw_roneat2d completely
# We'll use regex to find _draw_roneat2d to the end of the method
draw_method_start = content.find("    def _draw_roneat2d(self")
if draw_method_start == -1:
    print("Could not find _draw_roneat2d")
    sys.exit(1)

draw_method_end = content.find("    # =========================================================================", draw_method_start)

draw_code = """    def generate_preview_frame(self, W, H, active_bar, hover_bar, press_bar, trem_repeat, active_hand):
        from PIL import Image, ImageDraw, ImageFilter
        from core.rendering.translation import translate_note
        
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_col = (18, 18, 18) if is_dark else (240, 240, 240)
        
        # Base image
        img = Image.new("RGBA", (W, H), bg_col + (255,))
        draw = ImageDraw.Draw(img)
        
        # Glow layer
        glow_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_img)
        
        bars, rail_y, rail_h, bar_w = self._bar_geometry(W, H)
        min_note, max_note = self._get_active_note_range()
        mode = self._roneat_mode
        use_2m = (self._2d_two_mallet_var.get() if mode in ("edit", "jam") else self.left_hand_var.get())
        
        # Draw Rail
        rail_col = (62, 62, 66) if is_dark else (166, 124, 82)
        if bars:
            draw.rectangle([bars[0][1] - 6, rail_y, bars[-1][2] + 6, rail_y + rail_h], fill=rail_col)

        # Draw Notes
        bar_face = (42, 45, 46) if is_dark else (210, 180, 140)
        bar_edge = (21, 23, 24) if is_dark else (139, 69, 19)
        glow_intensity = getattr(self, "glow_slider", None)
        glow_val = glow_intensity.get() if glow_intensity else 0.6

        accent_hex = self.C["accent"]
        # Convert hex to RGB
        accent_rgb = tuple(int(accent_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        for (bar_num, xl, xr, yt, yb, cx) in bars:
            is_rh = active_bar is not None and bar_num == active_bar and active_hand in ("both", "right")
            is_lh = active_bar is not None and use_2m and bar_num == active_bar + 7 and bar_num <= max_note and active_hand in ("both", "left")
            is_press = press_bar is not None and bar_num == press_bar
            is_press_lh = press_bar is not None and use_2m and bar_num == press_bar + 7 and bar_num <= max_note
            is_hov = hover_bar is not None and bar_num == hover_bar and not (is_rh or is_press)
            is_hov_lh = hover_bar is not None and use_2m and bar_num == hover_bar + 7 and bar_num <= max_note and not (is_lh or is_press_lh)

            fc = bar_face
            sc = bar_edge
            glow_c = None

            if is_rh or is_press:
                fc = accent_rgb
                glow_c = accent_rgb
            elif is_lh or is_press_lh:
                fc = (28, 78, 128) if is_dark else (255, 179, 0)
                glow_c = fc
            elif is_hov:
                fc = (212, 175, 55)
            elif is_hov_lh:
                fc = (184, 134, 11)

            # Draw Glow
            if glow_c and glow_val > 0.05:
                # expand rect for glow
                gx1, gy1 = xl - 4, yt - 4
                gx2, gy2 = xr + 4, yb + 6
                g_alpha = int(255 * glow_val)
                glow_draw.rounded_rectangle([gx1, gy1, gx2, gy2], radius=4, fill=glow_c + (g_alpha,))

            # Base shadow/edge
            draw.rounded_rectangle([xl, yt, xr, yb], radius=2, fill=bar_edge)
            # Inner face
            draw.rounded_rectangle([xl + 1, yt, xr - 1, yb - 2], radius=2, fill=fc)

            # Draw string (playhead representation)
            i_idx = max_note - bar_num
            tube_r = max(3, min(bar_w * 0.36, 10))
            tube_cy = yb + tube_r + 5 + (tube_r * 0.5 if i_idx % 2 == 0 else 0)
            
            draw.line([(cx, yb), (cx, tube_cy - tube_r)], fill=(68, 68, 68), width=1)
            
            # Strike point / Playhead (Neon ring effect)
            tc = glow_c if glow_c else ((37, 37, 38) if is_dark else (245, 245, 245))
            draw.ellipse([cx - tube_r, tube_cy - tube_r, cx + tube_r, tube_cy + tube_r], fill=tc)

        # Apply blur to glow and composite
        if glow_val > 0.05:
            blur_rad = 5.0 + (glow_val * 15.0)
            glow_blurred = glow_img.filter(ImageFilter.GaussianBlur(radius=blur_rad))
            img = Image.alpha_composite(img, glow_blurred)

        return img

    def _draw_roneat2d(self, active_bar=None, hover_bar=None, press_bar=None, trem_repeat=0, active_hand="both"):
        import customtkinter as ctk
        
        lbl = getattr(self, 'roneat_label', None)
        if not lbl:
            return
            
        lbl.update_idletasks()
        W = lbl.winfo_width()
        H = lbl.winfo_height()
        if W < 50 or H < 50:
            return
            
        pil_img = self.generate_preview_frame(W, H, active_bar, hover_bar, press_bar, trem_repeat, active_hand)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(W, H))
        
        lbl.configure(image=ctk_img, text="")
        lbl.image = ctk_img  # Prevent garbage collection

"""

content = content[:draw_method_start] + draw_code + content[draw_method_end:]

with open(filename, "w", encoding="utf-8") as f:
    f.write(content)

print("Patching complete.")
