"""
core/pdf_exporter.py  v3.0
============================
Roneat Studio Pro — PDF Export

NEW IN v3:
  - Optional cover page (title, composer, date, decorative border)
  - Row numbers at left of each grid row
  - Title centred, no leading dash artefact
  - accent_hex and font_size_override respected
  - Tremolo displayed as "7~3" (bar 7 repeated 3 times)
"""

import os
import sys
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


def _register_fonts():
    """Try to register a Khmer-capable font. Returns (title_font, body_font)."""
    local = resource_path(os.path.join("assets", "KhmerFont.ttf"))
    if os.path.exists(local):
        try:
            pdfmetrics.registerFont(TTFont('KhmerFont', local))
            return 'KhmerFont', 'Helvetica'
        except Exception:
            pass
    if sys.platform == 'win32':
        windir = os.environ.get('WINDIR', 'C:\\Windows')
        for name in ('LeelawUI.ttf', 'DaunPenh.ttf', 'KhmerUI.ttf', 'Nirmala.ttf'):
            p = os.path.join(windir, 'Fonts', name)
            if os.path.exists(p):
                try:
                    pdfmetrics.registerFont(TTFont('KhmerFont', p))
                    return 'KhmerFont', 'Helvetica'
                except Exception:
                    continue
    return 'Helvetica-Bold', 'Helvetica'


def _hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def export_to_pdf(filepath, title, notes_text, measure_mode,
                  show_left_hand, cols=16,
                  accent_hex="#c8a96e", font_size_override=None,
                  show_cover=False, composer="", show_row_numbers=True):
    """
    Export score to PDF.

    Parameters
    ----------
    filepath           : output .pdf path
    title              : song title
    notes_text         : raw notation string
    measure_mode       : "4", "8", or "manual"
    show_left_hand     : bool — show left hand bar numbers below right hand
    cols               : columns per grid row
    accent_hex         : right-hand note colour
    font_size_override : override auto cell font size
    show_cover         : prepend a cover page
    composer           : composer name shown on cover
    show_row_numbers   : show row index at left margin
    """
    import re
    title_font, body_font = _register_fonts()
    ar, ag, ab = _hex_rgb(accent_hex)

    # ── Parse notation ────────────────────────────────────────────────────────
    _TOKEN_RE = re.compile(r'^(\d+)(#(\d+))?$')
    beats = []
    for raw in notes_text.replace('\n', ' ').split():
        if raw == '/':
            if beats:
                beats[-1]['barline'] = True
            continue
        if raw in ('-', '0', 'x'):
            beats.append({'text': '-', 'barline': False,
                          'is_trem': False, 'bar': None, 'repeat': 1})
            continue
        m = _TOKEN_RE.match(raw)
        if m:
            bar    = int(m.group(1))
            is_t   = bool(m.group(2))
            repeat = int(m.group(3)) if m.group(3) else 1
            label  = f"{bar}~{repeat}" if is_t else str(bar)
            beats.append({'text': label, 'bar': bar, 'barline': False,
                          'is_trem': is_t, 'repeat': repeat})

    # ── Layout maths ──────────────────────────────────────────────────────────
    c = canvas.Canvas(filepath, pagesize=A4)
    w, h = A4

    margin_x  = 36
    row_num_w = 24 if show_row_numbers else 0
    usable_w  = w - margin_x * 2 - row_num_w
    cell_w    = usable_w / cols
    cell_h    = min(48, max(26, cell_w * 1.15))
    row_gap   = 16
    fs        = font_size_override or min(14, cell_w * 0.42)

    total_rows  = math.ceil(len(beats) / cols) if beats else 1
    rows_per_pg = max(1, math.floor((h - 180) / (cell_h + row_gap)))
    num_pages   = max(1, math.ceil(total_rows / rows_per_pg))

    # ── Cover page ────────────────────────────────────────────────────────────
    if show_cover:
        clean_title = title.strip().lstrip('- ').strip()
        c.setStrokeColorRGB(ar, ag, ab)
        c.setLineWidth(3)
        c.rect(28, 28, w - 56, h - 56)
        c.setLineWidth(1)
        c.rect(36, 36, w - 72, h - 72)

        c.setFillColorRGB(ar * 0.5, ag * 0.5, ab * 0.5)
        c.setFont(body_font, 9)
        c.drawCentredString(w / 2, h - 80, "— RONEAT EK —")

        c.setFont(title_font, 34)
        c.setFillColorRGB(ar, ag, ab)
        c.drawCentredString(w / 2, h / 2 + 50, clean_title)
        tw = c.stringWidth(clean_title, title_font, 34)
        c.setStrokeColorRGB(ar, ag, ab)
        c.setLineWidth(1.5)
        c.line(w / 2 - tw / 2, h / 2 + 42, w / 2 + tw / 2, h / 2 + 42)

        c.setFont(body_font, 14)
        c.setFillColorRGB(0.40, 0.45, 0.54)
        c.drawCentredString(w / 2, h / 2, "Roneat Ek Score")
        if composer:
            c.setFont(body_font, 12)
            c.drawCentredString(w / 2, h / 2 - 28, f"Composed by  {composer}")

        from datetime import date
        c.setFont(body_font, 10)
        c.setFillColorRGB(0.60, 0.60, 0.60)
        c.drawCentredString(w / 2, 58, date.today().strftime("%B %Y"))
        c.showPage()

    # ── Score pages ───────────────────────────────────────────────────────────
    beat_idx = 0
    row_num  = 1

    for page_num in range(num_pages):
        if page_num == 0:
            clean_title = title.strip().lstrip('- ').strip()
            c.setFont(title_font, 22)
            c.setFillColorRGB(ar, ag, ab)
            c.drawCentredString(w / 2, h - 64, clean_title)
            tw = c.stringWidth(clean_title, title_font, 22)
            c.setStrokeColorRGB(ar, ag, ab)
            c.setLineWidth(1)
            c.line(w / 2 - tw / 2, h - 72, w / 2 + tw / 2, h - 72)
            c.setFont(body_font, 11)
            c.setFillColorRGB(0.40, 0.45, 0.54)
            c.drawCentredString(w / 2, h - 88, "Roneat Ek Score")
            start_y = h - 148
        else:
            start_y = h - 64

        row_i = 0
        while beat_idx < len(beats) and row_i < rows_per_pg:
            cy_top = start_y - row_i * (cell_h + row_gap)

            if show_row_numbers:
                c.setFont(body_font, 8)
                c.setFillColorRGB(0.6, 0.6, 0.6)
                c.drawRightString(margin_x + row_num_w - 4,
                                  cy_top - cell_h / 2 + 3,
                                  str(row_num))
            x = margin_x + row_num_w

            for col_i in range(cols):
                if (row_i + col_i) % 2 == 0:
                    c.setFillColorRGB(0.97, 0.98, 0.99)
                else:
                    c.setFillColorRGB(1.0, 1.0, 1.0)
                c.setStrokeColorRGB(0.78, 0.82, 0.88)
                c.setLineWidth(0.5)
                c.rect(x, cy_top - cell_h, cell_w, cell_h, fill=1, stroke=1)

                if beat_idx < len(beats):
                    bd     = beats[beat_idx]
                    txt    = bd['text']
                    cx     = x + cell_w / 2
                    cy_mid = cy_top - cell_h / 2

                    if txt == '-':
                        c.setFillColorRGB(0.70, 0.75, 0.80)
                        c.setFont(body_font, fs)
                        c.drawCentredString(cx, cy_mid - fs / 4, "-")
                    else:
                        bar   = bd.get('bar', 0) or 0
                        is_t  = bd.get('is_trem', False)
                        rep   = bd.get('repeat', 1)

                        if show_left_hand:
                            c.setFillColorRGB(ar, ag, ab)
                            c.setFont(body_font, fs * 0.88)
                            lbl_rh = f"{bar}~{rep}" if is_t else str(bar)
                            c.drawCentredString(cx, cy_mid + fs * 0.22, lbl_rh)
                            lh = bar + 7
                            if lh <= 21:
                                c.setFillColorRGB(0.15, 0.39, 0.92)
                                c.setFont(body_font, fs * 0.62)
                                lbl_lh = f"{lh}~{rep}" if is_t else str(lh)
                                c.drawCentredString(cx, cy_mid - fs * 0.52, lbl_lh)
                        else:
                            c.setFillColorRGB(ar, ag, ab)
                            c.setFont(body_font, fs)
                            lbl = f"{bar}~{rep}" if is_t else str(bar)
                            c.drawCentredString(cx, cy_mid - fs / 4, lbl)

                    # Bar line
                    draw_bl = False
                    if "Manual" not in str(measure_mode):
                        grp = 4 if "4" in str(measure_mode) else 8
                        if (col_i + 1) % grp == 0 and col_i < cols - 1:
                            draw_bl = True
                    elif bd.get('barline'):
                        draw_bl = True
                    if draw_bl:
                        c.setStrokeColorRGB(0.10, 0.10, 0.20)
                        c.setLineWidth(2.5)
                        c.line(x + cell_w, cy_top, x + cell_w, cy_top - cell_h)

                    beat_idx += 1
                x += cell_w
            row_i  += 1
            row_num += 1

        c.setFont(body_font, 9)
        c.setFillColorRGB(0.50, 0.50, 0.50)
        c.drawCentredString(w / 2, 26, f"Page {page_num + 1} / {num_pages}")
        c.showPage()

    c.save()