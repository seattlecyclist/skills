#!/usr/bin/env python3
"""Download CC0 scanned textures and HDRIs into assets/<id>/ (Poly Haven and ambientCG).

    python3 fetch_assets.py assets polyhaven:walnut_veneer_02 polyhaven:borghese_gardens ambientcg:Carpet016
    python3 fetch_assets.py assets --res 4k --list bedroom        (print a starter set for a setting)

Poly Haven textures come as <id>_diff/_rough/_disp/_nor_gl_<res>.jpg|png, HDRIs as <id>_<res>.exr|hdr
(put in assets/hdri/). ambientCG sets come as a zip of <id>_<res>-JPG_Color/Roughness/... files.
Both name schemes are read by p2p.find_maps. Everything here is CC0: free to use, no attribution
required (crediting them is still nice).

Needs network access to api.polyhaven.com, dl.polyhaven.org and ambientcg.com. In a sandbox that
blocks them, run this on the machine that renders, or download by hand from polyhaven.com and
ambientcg.com into the same folders.
"""
import sys, os, json, zipfile, io, argparse, urllib.request

UA = {'User-Agent': 'plan-to-photo-skill'}
STARTERS = {
    'bedroom': ['polyhaven:walnut_veneer_02', 'polyhaven:white_oak_veneer', 'polyhaven:rough_linen', 'polyhaven:knitted_fleece',
                'polyhaven:wool_boucle', 'ambientcg:Carpet016', 'polyhaven:borghese_gardens'],
    'kitchen': ['polyhaven:white_oak_veneer', 'polyhaven:marble_01', 'polyhaven:painted_plaster_wall', 'polyhaven:brushed_concrete',
                'ambientcg:Tiles101', 'polyhaven:rough_linen', 'polyhaven:kloofendal_48d_partly_cloudy_puresky'],
    'living': ['polyhaven:walnut_veneer_02', 'polyhaven:oak_veneer_01', 'polyhaven:wool_boucle', 'polyhaven:leather_red_02',
               'ambientcg:Carpet016', 'polyhaven:rough_linen', 'polyhaven:borghese_gardens'],
    'dining': ['polyhaven:oak_veneer_01', 'polyhaven:white_oak_veneer', 'polyhaven:rough_linen', 'polyhaven:painted_plaster_wall',
               'polyhaven:kloofendal_48d_partly_cloudy_puresky'],
    'office': ['polyhaven:walnut_veneer_02', 'polyhaven:white_oak_veneer', 'polyhaven:fabric_pattern_07', 'ambientcg:Carpet016',
               'polyhaven:painted_plaster_wall', 'polyhaven:borghese_gardens'],
    'patio': ['polyhaven:wood_planks_grey', 'polyhaven:brushed_concrete', 'polyhaven:aerial_grass_rock', 'polyhaven:kloofendal_48d_partly_cloudy_puresky'],
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def polyhaven(aid, res, root):
    info = json.loads(get('https://api.polyhaven.com/info/' + aid))
    files = json.loads(get('https://api.polyhaven.com/files/' + aid))
    if info.get('type') == 0 or 'hdri' in files:
        out = os.path.join(root, 'hdri'); os.makedirs(out, exist_ok=True)
        r = files['hdri'].get(res) or files['hdri'][sorted(files['hdri'])[-1]]
        f = r.get('exr') or r.get('hdr'); url = f['url']
        dst = os.path.join(out, os.path.basename(url))
        if not os.path.exists(dst): open(dst, 'wb').write(get(url))
        print('HDRI', dst); return
    out = os.path.join(root, aid); os.makedirs(out, exist_ok=True)
    want = {'Diffuse': 'jpg', 'Rough': 'jpg', 'Displacement': 'png', 'nor_gl': 'jpg', 'AO': 'jpg'}
    for key, fmt in want.items():
        if key not in files: continue
        r = files[key].get(res) or files[key][sorted(files[key])[-1]]
        f = r.get(fmt) or next(iter(r.values())); url = f['url']
        dst = os.path.join(out, os.path.basename(url))
        if not os.path.exists(dst): open(dst, 'wb').write(get(url))
        print('  ', dst)
    print('SET', out)


def ambientcg(aid, res, root):
    out = os.path.join(root, aid); os.makedirs(out, exist_ok=True)
    data = get('https://ambientcg.com/get?file=%s_%s-JPG.zip' % (aid, res))
    zipfile.ZipFile(io.BytesIO(data)).extractall(out)
    print('SET', out)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('ids', nargs='*')
    ap.add_argument('--res', default='4k'); ap.add_argument('--list', default=None)
    a = ap.parse_args()
    if a.list:
        print(' '.join(STARTERS[a.list])); sys.exit(0)
    os.makedirs(a.root, exist_ok=True); bad = 0
    for i in a.ids:
        src, _, aid = i.partition(':')
        try:
            (polyhaven if src == 'polyhaven' else ambientcg)(aid, a.res if src == 'polyhaven' else a.res.upper(), a.root)
        except Exception as e:
            bad += 1; print('FAILED', i, e, file=sys.stderr)
    sys.exit(1 if bad else 0)
