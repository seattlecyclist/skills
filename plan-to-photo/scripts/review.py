#!/usr/bin/env python3
"""Make a review sheet from a render: the whole frame plus full-resolution crops of the places that
give a render away, labelled, in one PNG to look at before calling it done.

    python3 review.py render.png --out sheet.png                       (a 3 x 3 grid of crops)
    python3 review.py render.png --crop "pillows:0.3,0.25,0.6,0.5" --crop "under bed:0.55,0.6,0.95,0.95"

Crops are fractions of the frame: x0,y0,x1,y1 from the top left. Read the sheet against
references/realism.md: contact (does everything touch what holds it), shadows (does each shadow
belong to its object, any light leaks), edges, texture scale and repeats, noise, window view.
Needs Pillow.
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument('image'); ap.add_argument('--out', default=None)
ap.add_argument('--crop', action='append', default=[]); ap.add_argument('--cell', type=int, default=640)
a = ap.parse_args()
im = Image.open(a.image).convert('RGB'); W, H = im.size
crops = []
for c in a.crop:
    name, _, box = c.rpartition(':'); crops.append((name or box, tuple(map(float, box.split(',')))))
if not crops:
    for j in range(3):
        for i in range(3):
            crops.append(('r%dc%d' % (j + 1, i + 1), (i / 3, j / 3, (i + 1) / 3, (j + 1) / 3)))
cell = a.cell; cols = 3; rows = (len(crops) + cols - 1) // cols; G = 8
row_h = max(min(cell, int((y1 - y0) * H * min(cell / max(1, (x1 - x0) * W), 1.0))) for _, (x0, y0, x1, y1) in crops)
full_h = int(cell * cols * H / W)
sheet = Image.new('RGB', (cell * cols + G * (cols - 1), full_h + rows * (row_h + 28 + G)), (24, 24, 24))
sheet.paste(im.resize((cell * cols, full_h), Image.LANCZOS), (0, 0))
d = ImageDraw.Draw(sheet)
try: font = ImageFont.truetype('DejaVuSans.ttf', 16)
except Exception: font = ImageFont.load_default()
for k, (name, (x0, y0, x1, y1)) in enumerate(crops):
    box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
    d.rectangle([box[0] * cell * cols / W, box[1] * full_h / H, box[2] * cell * cols / W, box[3] * full_h / H], outline=(255, 80, 60), width=2)
    cr = im.crop(box); s = min(cell / cr.width, cell / cr.height, 1.0)
    cr = cr.resize((max(1, int(cr.width * s)), max(1, int(cr.height * s))), Image.LANCZOS)
    ox = (k % cols) * (cell + G); oy = full_h + G + (k // cols) * (row_h + 28 + G)
    sheet.paste(cr, (ox, oy + 28)); d.text((ox + 6, oy + 5), '%s  (%d%%)' % (name, round(s * 100)), fill=(230, 230, 230), font=font)
out = a.out or a.image.rsplit('.', 1)[0] + '-review.png'
sheet.save(out); print('REVIEW', out)
