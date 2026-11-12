#!/usr/bin/env python3
"""Turn a plan you were given as a PDF or as images (scans, phone photos, screenshots) into pages
you can read: one PNG per page, the PDF's text layer when it has one, a contact sheet, and an index
that says what each page probably is.

    python3 read_drawings.py plan.pdf drawings/                 # every page at 150 dpi
    python3 read_drawings.py plan.pdf drawings/ --pages 1-16    # skip the full-size pattern tiles
    python3 read_drawings.py IMG_2041.jpg IMG_2042.jpg drawings/
    python3 read_drawings.py plan.pdf drawings/ --pages 6 --dpi 300 --tile 2   # small dimension text

Writes into the output folder:
    page-01.png ...     the pages (images are EXIF-rotated and copied as PNG)
    page-01-t1.png ...  with --tile N: an N x N grid of overlapping tiles per page, for small text
    page-01.txt ...     the PDF's text layer for that page, when it has one
    contact.png         every page small, numbered: look at this first to find the pages that matter
    pages.md            the index: size, ink, kind (title, list, drawing, full-size tile, blank), text

Then read the pages (references/drawings.md says in what order and what to take from each) and
write the takeoff and the plan.json. Needs Pillow; PDFs need poppler (pdftoppm, pdftotext) or the
PyMuPDF package.
"""
import argparse, os, re, shutil, subprocess, sys

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    sys.exit('needs Pillow: pip install pillow')

IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp', '.tif', '.tiff', '.bmp', '.gif', '.heic', '.heif')


def page_range(spec, n):
    if not spec:
        return list(range(1, n + 1))
    out = []
    for part in spec.split(','):
        a, _, b = part.partition('-')
        a = int(a); b = int(b) if b else a
        out += [p for p in range(a, b + 1) if 1 <= p <= n]
    return out


def pdf_pages(pdf, out, dpi, pages):
    """Render the pages and pull the text layer. Returns [(png, text)]."""
    res = []
    if shutil.which('pdftoppm'):
        info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
        n = int(re.search(r'Pages:\s+(\d+)', info).group(1))
        for p in page_range(pages, n):
            stem = os.path.join(out, 'page-%02d' % p)
            subprocess.run(['pdftoppm', '-r', str(dpi), '-png', '-singlefile', '-f', str(p), '-l', str(p), pdf, stem], check=True)
            txt = ''
            if shutil.which('pdftotext'):
                txt = subprocess.run(['pdftotext', '-layout', '-f', str(p), '-l', str(p), pdf, '-'], capture_output=True, text=True).stdout
            res.append((stem + '.png', txt))
        return res
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit('PDF input needs poppler (brew install poppler / apt install poppler-utils) or PyMuPDF (pip install pymupdf)')
    doc = fitz.open(pdf)
    for p in page_range(pages, doc.page_count):
        pg = doc[p - 1]
        png = os.path.join(out, 'page-%02d.png' % p)
        pg.get_pixmap(dpi=dpi).save(png)
        res.append((png, pg.get_text()))
    return res


def image_page(src, out, i, max_side):
    try:
        im = Image.open(src)
    except Exception as e:  # HEIC without pillow-heif, a corrupt file
        sys.exit('cannot open %s (%s); convert it to PNG or JPEG first' % (src, e))
    im = ImageOps.exif_transpose(im).convert('RGB')
    if max(im.size) > max_side:  # phone photos: keep enough to read 1/16" fractions, not 48 MP
        s = max_side / max(im.size)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    png = os.path.join(out, 'page-%02d.png' % i)
    im.save(png)
    return png


def ink(im):
    """Fraction of the page that is not paper: tells blank pages and dense drawings apart."""
    h = im.convert('L').resize((300, round(300 * im.height / im.width))).histogram()
    return sum(h[:240]) / sum(h)   # light fills (section hatching on a peach ground) count as ink


def kind(text, ink_frac):
    t = text.lower()
    if re.search(r'full size|actual size|print at 100%|check square', t):
        return 'full-size tile (patterns; measure curves here, skip for reading)'
    if ink_frac < 0.002:
        return 'blank'
    if re.search(r'material list|cut ?list|bill of materials|cutting list|parts list', t):
        return 'parts list'
    if re.search(r'overall|front view|side view|top view|elevation|section', t):
        return 'drawing'
    if not text.strip():
        return 'image only (no text layer): read it'
    return 'text'


def tiles(png, n, overlap=0.12):
    im = Image.open(png); W, H = im.size; out = []
    tw, th = W / n, H / n
    for j in range(n):
        for i in range(n):
            box = (max(0, round(i * tw - overlap * tw)), max(0, round(j * th - overlap * th)),
                   min(W, round((i + 1) * tw + overlap * tw)), min(H, round((j + 1) * th + overlap * th)))
            p = png[:-4] + '-t%d.png' % (j * n + i + 1)
            im.crop(box).save(p); out.append(p)
    return out


def contact(pngs, path, cols=8, w=300):
    ims = [Image.open(p).convert('RGB') for p in pngs]
    h = max(round(w * im.height / im.width) for im in ims)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w, rows * (h + 22)), 'white')
    d = ImageDraw.Draw(sheet)
    for k, (im, p) in enumerate(zip(ims, pngs)):
        x, y = (k % cols) * w, (k // cols) * (h + 22)
        sheet.paste(im.resize((w, round(w * im.height / im.width))), (x, y + 22))
        d.rectangle([x, y + 22, x + w - 1, y + 22 + h - 1], outline=(200, 200, 200))
        d.text((x + 6, y + 4), os.path.basename(p)[:-4], fill=(160, 20, 20))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inputs', nargs='+', help='a PDF and/or images, then the output folder')
    ap.add_argument('--dpi', type=int, default=150, help='PDF render resolution (150 reads list text; 300 for small dimensions)')
    ap.add_argument('--pages', help='PDF pages to render, e.g. 1-16,22')
    ap.add_argument('--tile', type=int, default=0, help='also cut each page into an N x N grid of overlapping tiles')
    ap.add_argument('--max-side', type=int, default=4000, help='downscale images whose long side is larger')
    a = ap.parse_args()
    *srcs, out = a.inputs
    if not srcs:
        ap.error('give at least one input and an output folder')
    os.makedirs(out, exist_ok=True)

    pages = []  # (png, text, source)
    for src in srcs:
        if src.lower().endswith('.pdf'):
            pages += [(png, txt, src) for png, txt in pdf_pages(src, out, a.dpi, a.pages)]
        elif src.lower().endswith(IMG_EXT):
            pages.append((image_page(src, out, len(pages) + 1, a.max_side), '', src))
        else:
            sys.exit('not a PDF or image: ' + src)

    lines = ['# Pages', '', 'Source: ' + ', '.join(os.path.basename(s) for s in srcs), '',
             '| Page | Size px | Ink | Kind | First text |', '|---|---|---|---|---|']
    for png, txt, src in pages:
        im = Image.open(png); f = ink(im)
        if txt.strip():
            with open(png[:-4] + '.txt', 'w') as fh:
                fh.write(txt)
        first = next((l.strip() for l in txt.splitlines() if l.strip()), '')[:70].replace('|', '/')
        lines.append('| %s | %dx%d | %.1f%% | %s | %s |' % (os.path.basename(png)[:-4], im.width, im.height, 100 * f, kind(txt, f), first))
        if a.tile > 1:
            tiles(png, a.tile)
    contact([p for p, _, _ in pages], os.path.join(out, 'contact.png'))
    has_text = any(t.strip() for _, t, _ in pages)
    lines += ['', 'Text layer: ' + ('yes, on some pages (page-NN.txt); still check numbers against the drawing' if has_text
                                    else 'none: every number has to be read from the images'),
              '', 'Next: open contact.png, then read the pages in the order references/drawings.md gives.']
    with open(os.path.join(out, 'pages.md'), 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
