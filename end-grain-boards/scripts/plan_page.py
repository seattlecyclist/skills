"""The shop plan page: a set of numbered sheets, each with a title block, its drawing beside its data,
and notes underneath, closing with the checks. Warm paper, Archivo headings, Source Serif body text and
IBM Plex Mono labels and numbers, walnut-brown accent; light and dark.

page(plan, svgs, photo) -> one self-contained HTML string (fonts from Google Fonts, nothing else external).
"""
import base64, html, os, re
from collections import OrderedDict


def _fr(s):
    """Escape. Fractions stay as typed (1-1/2") so the page, the tables and the drawings all show them one way."""
    return html.escape(str(s))


CSS = """
:root{--paper:#f1efe9;--sheet:#fafaf8;--ink:#1e2327;--graphite:#5b6167;--rule:#d6d3cb;--plate:#ffffff;
 --accent:#6b4630;--accent-ink:#6b4630;--good:#2f6b4a;--mid:#2b5c8c;--weak:#c23b2e;--warn:#9a6a12;--hl:rgba(242,211,188,.6);
 --shadow:0 1px 0 rgba(30,35,39,.06),0 8px 24px -16px rgba(30,35,39,.35);
 --f-display:"Archivo","Arial",system-ui,sans-serif;--f-body:"Source Serif 4",Georgia,serif;--f-mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--paper:#15181b;--sheet:#1d2126;--ink:#ebe8e2;--graphite:#a5a9ad;--rule:#33383e;--plate:#f4f5f2;
 --accent:#d9a37f;--accent-ink:#e8bf9f;--good:#6fb08a;--mid:#7fa9d6;--weak:#e2786b;--warn:#d9b45a;--hl:rgba(217,163,127,.2);
 --shadow:0 1px 0 rgba(0,0,0,.3),0 10px 28px -18px rgba(0,0,0,.8);color-scheme:dark}}
:root[data-theme="dark"]{--paper:#15181b;--sheet:#1d2126;--ink:#ebe8e2;--graphite:#a5a9ad;--rule:#33383e;--plate:#f4f5f2;
 --accent:#d9a37f;--accent-ink:#e8bf9f;--good:#6fb08a;--mid:#7fa9d6;--weak:#e2786b;--warn:#d9b45a;--hl:rgba(217,163,127,.2);
 --shadow:0 1px 0 rgba(0,0,0,.3),0 10px 28px -18px rgba(0,0,0,.8);color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-body);font-size:15px;line-height:1.55;padding:0 16px 64px}
.wrap{max-width:1180px;margin:0 auto}
a{color:var(--accent-ink);text-underline-offset:3px}
.mono{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.fr{white-space:nowrap}.fr sup,.fr sub{font-size:.68em;line-height:0}.fr sup{vertical-align:.45em}.fr sub{vertical-align:0}
h1,h2,.tb .no,.stat b,.sn,.jn{font-stretch:112%}
header.hero{padding-block:40px 28px;display:grid;gap:18px;border-bottom:1px solid var(--rule)}
.eyebrow{font-family:var(--f-mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--graphite)}
h1{font-family:var(--f-display);font-weight:700;font-size:clamp(38px,7vw,68px);line-height:.98;margin:0;letter-spacing:-.01em;text-wrap:balance}
h1 em{font-style:normal;color:var(--accent)}
.lede{max-width:68ch;margin:0;color:var(--graphite);font-size:16.5px}
.chain{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-family:var(--f-mono);font-size:12.5px}
.chain span{border:1px solid var(--rule);background:var(--sheet);padding:4px 9px;border-radius:3px}
.chain span b{color:var(--accent-ink);font-weight:500;margin-right:6px}.chain i{font-style:normal;color:var(--accent)}
.stats{display:flex;flex-wrap:wrap;gap:16px 28px;margin-top:6px}
.stat b{display:block;font-family:var(--f-display);font-size:30px;line-height:1;font-weight:600}
.stat small{font-size:12.5px;color:var(--graphite)}
nav.index{padding-block:22px;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:4px 18px;border-bottom:1px solid var(--rule)}
nav.index a{display:flex;gap:10px;align-items:baseline;text-decoration:none;color:var(--ink);padding:6px 0;border-bottom:1px dashed transparent}
nav.index a:hover{border-bottom-color:var(--rule)}
nav.index .n{font-family:var(--f-mono);font-size:12px;color:var(--accent-ink)}nav.index .t{flex:1;min-width:0;font-weight:600;font-size:14px}
nav.index .s{font-family:var(--f-mono);font-size:12px;color:var(--graphite)}
.sheet{margin-top:40px;background:var(--sheet);border:1px solid var(--rule);box-shadow:var(--shadow);border-radius:4px;overflow:hidden;scroll-margin-top:16px}
.tb{display:grid;grid-template-columns:auto 1fr auto;border-bottom:1px solid var(--rule)}
.tb>div{padding:14px 18px;min-width:0}
.tb .no{font-family:var(--f-display);font-size:44px;font-weight:700;line-height:1;color:var(--accent);border-right:1px solid var(--rule);display:flex;align-items:center}
.tb h2{font-family:var(--f-display);font-weight:600;font-size:28px;line-height:1.05;margin:0 0 4px;text-wrap:balance}
.tb .by{font-size:13.5px;color:var(--graphite)}
.tb .meta{border-left:1px solid var(--rule);display:grid;gap:6px;align-content:center;justify-items:end;text-align:right}
.dims{font-family:var(--f-mono);font-size:12.5px;color:var(--graphite)}
.stamp{font-family:var(--f-mono);font-size:12px;color:var(--good);display:flex;gap:6px;align-items:center}.stamp.bad{color:var(--weak)}
.main,.lower{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(0,1fr);gap:1px;background:var(--rule)}
.lower{border-top:1px solid var(--rule)}.full{grid-template-columns:1fr}
.main>figure,.lower>figure,.notes>figure{margin:0;background:var(--sheet);padding:14px;display:grid;gap:8px;align-content:start;min-width:0}
.ph{background:var(--plate);border-radius:2px;overflow:auto;display:block}
.ph svg,.ph img{display:block;max-width:100%;height:auto;margin:0 auto}
figcaption{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;font-size:12.5px;color:var(--graphite)}
.lbl{font-family:var(--f-mono);font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;color:var(--ink)}
.notes,.panel{background:var(--sheet);padding:16px 18px;display:grid;gap:12px;align-content:start;min-width:0}
.notes h3,.panel h3{font-family:var(--f-mono);font-size:11.5px;letter-spacing:.07em;text-transform:uppercase;margin:0;font-weight:500;color:var(--graphite)}
.notes ul,.panel ul{margin:0;padding-left:18px;display:grid;gap:5px}
.notes p,.panel p{margin:0}.small{font-size:13.5px;color:var(--graphite)}
.sw{display:inline-block;width:12px;height:12px;border:1px solid rgba(0,0,0,.35);border-radius:2px;vertical-align:-1px;margin-right:6px}
.tbl{overflow-x:auto}
table.d{border-collapse:collapse;width:100%;font-size:13.5px}
table.d th,table.d td{text-align:left;padding:7px 8px 7px 0;border-bottom:1px solid var(--rule);vertical-align:top}
table.d th{font:500 11px var(--f-mono);letter-spacing:.07em;text-transform:uppercase;color:var(--graphite)}
table.d td.m{font-family:var(--f-mono);font-size:12.5px;font-variant-numeric:tabular-nums}
table.d td.q{font-family:var(--f-mono);text-align:right;padding-right:12px}
table.d .sub{display:block;font-size:12.5px;color:var(--graphite);margin-top:2px}
table.d tr.grp td{font:500 11px var(--f-mono);letter-spacing:.07em;text-transform:uppercase;color:var(--accent-ink);padding-top:16px}
.chip{font:500 11.5px var(--f-mono);display:inline-grid;place-items:center;min-width:22px;height:22px;padding:0 5px;border:1.2px solid var(--ink);border-radius:11px;background:var(--sheet);color:var(--ink);vertical-align:1px;margin:0 1px}
.jgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:0;background:var(--sheet)}
.joint{background:var(--sheet);border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:14px;display:grid;gap:10px;align-content:start;min-width:0}
.joint .jh{display:flex;gap:10px;align-items:baseline}
.joint .jn{font-family:var(--f-display);font-weight:700;font-size:22px;color:var(--accent);line-height:1}
.joint h4{margin:0;font-size:15px;font-weight:600;line-height:1.25}.joint .jsub{font-size:12.5px;color:var(--graphite)}
.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:13px;margin:0}
.kv dt{font:500 11px var(--f-mono);letter-spacing:.06em;text-transform:uppercase;color:var(--graphite);padding-top:2px}
.kv dd{margin:0;min-width:0}.kv dd.m{font-family:var(--f-mono);font-size:12.5px}
ol.steps{list-style:none;margin:0;padding:0}
ol.steps>li{display:grid;grid-template-columns:44px 1fr;gap:4px 12px;padding:14px 0;border-bottom:1px solid var(--rule)}
ol.steps>li:last-child{border-bottom:0}
ol.steps .sn{font-family:var(--f-display);font-weight:700;font-size:26px;color:var(--accent);line-height:1}
ol.steps h4{margin:0 0 4px;font-size:15.5px;font-weight:600}
ol.steps ul{margin:0;padding-left:18px;columns:2 40ch;column-gap:36px}
ol.steps ul li{break-inside:avoid;margin-bottom:5px}
ol.steps .see{font-family:var(--f-mono);font-size:12px;color:var(--graphite);margin-top:6px}
.kick{display:inline-block;font-family:var(--f-display);font-weight:800;font-size:12px;letter-spacing:.09em;color:#fff;background:var(--accent);padding:2px 8px;border-radius:2px;margin-bottom:6px}
.stepgrid{display:grid;gap:12px}
.asm{display:flex;flex-wrap:wrap;gap:10px;margin:0;align-items:stretch;justify-content:center}
.asm figure{margin:0;border:1px solid var(--rule);background:#fff;border-radius:2px;overflow:hidden;flex:1 1 300px;max-width:620px;display:grid;align-items:center}
.asm svg{display:block;max-width:100%;height:auto;margin:0 auto}
.asm figure.wide{flex-basis:100%;max-width:820px}.rip{columns:2 320px;column-gap:36px}.rip p{margin:0 0 8px;break-inside:avoid}
.logpair{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:12px;align-items:center}.logpair .ph svg{max-height:380px;width:auto}
@media (max-width:760px){.logpair{grid-template-columns:1fr}}
.dont{grid-column:2;margin-top:8px;border-left:3px solid var(--weak);padding:6px 10px;font-size:14px;background:color-mix(in srgb,var(--weak) 8%,transparent)}
.dont b{font-family:var(--f-mono);font-size:11.5px;letter-spacing:.07em;color:var(--weak);margin-right:6px}
.stepbox{background:var(--sheet);padding:4px 18px}
section.find{margin-top:56px;display:grid;gap:18px}
section.find h2{font-family:var(--f-display);font-size:36px;margin:0;font-weight:700;line-height:1;font-stretch:112%}
table.cost{border-collapse:collapse;font-size:14px;width:100%}
table.cost td{padding:7px 0;border-bottom:1px solid var(--rule);vertical-align:top}
table.cost td:last-child{text-align:right;font-family:var(--f-mono);padding-left:14px;white-space:nowrap}
table.cost .pass{color:var(--good)}table.cost .warn{color:var(--warn)}table.cost .fail{color:var(--weak)}
table.cost .sub{display:block;font-size:12.5px;color:var(--graphite)}
footer{margin-top:48px;font-size:12.5px;color:var(--graphite);max-width:80ch}
.jgrid.logs{grid-template-columns:repeat(2,minmax(0,1fr))}
.jgrid.logs .ph svg{width:100%;height:auto;max-height:340px}
@media (max-width:760px){.jgrid.logs{grid-template-columns:1fr}}
.setups{grid-template-columns:repeat(var(--n),minmax(0,1fr))}
@media (max-width:860px){.setups{grid-template-columns:1fr}.main,.lower{grid-template-columns:1fr}.tb{grid-template-columns:auto 1fr}
 .tb .meta{grid-column:1/-1;border-left:0;border-top:1px solid var(--rule);justify-items:start;text-align:left}}
@media (max-width:520px){.tb .no{font-size:34px}.tb h2{font-size:23px}.jgrid{grid-template-columns:1fr}}
"""

TICK = ('<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="1" y="1" width="12" height="12" rx="2" '
        'fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4 7.2l2 2 4-4.4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')


def _runs(xs):
    """A row's slices in order; a repeating single or pair is written once with its count."""
    for k in (1, 2):
        if len(xs) >= 3 * k and all(xs[i] == xs[i % k] for i in range(len(xs))):
            n, rem = divmod(len(xs), k)
            return f"{' '.join(xs[:k])} × {n}" + (f", then {' '.join(xs[:rem])}" if rem else "")
    return " ".join(xs)


ORD = {1: "1ST", 2: "2ND", 3: "3RD", 4: "4TH", 5: "5TH"}


def page(plan, svgs, photo, guide=None):
    from cbplan import dim, short, plan_name, RIP_POINTS
    e = html.escape; fr = _fr
    W, L, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    sh = plan["shop"]; logs = plan["logs"]; bars = plan["bars"]; rows = plan["rows"]
    nbars = sum(b["total_bars"] for b in bars); nlogs = sum(l["count"] for l in logs); nsl = plan["n_slices"]
    bf = sum(s["bf_buy"] for s in plan["stock"])
    nglued = sum(l["count"] for l in logs if sum(len(s_["parts"]) for s_ in l["stages"]) > 1)
    errors = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    warns = [c for c in plan["checks"] if not c["ok"] and c["level"] == "warn"]
    size = f'{short(W)} × {short(L)} × {short(T)}'
    stamp = (f'<div class="stamp bad">✗ {len(errors)} check{"s" if len(errors) > 1 else ""} fail</div>' if errors else
             f'<div class="stamp">{TICK}{len(plan["checks"]) - len(warns)} of {len(plan["checks"])} checks pass</div>')
    wname = lambda k: plan_name(plan, k)
    pl = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")

    def tb(no, title, by, meta):
        return (f'<div class="tb"><div class="no mono">{no}</div><div><h2>{e(title)}</h2><div class="by">{by}</div></div>'
                f'<div class="meta">{meta}</div></div>')

    def fig(svg_or_img, label, extra=""):
        return f'<figure><div class="ph">{svg_or_img}</div><figcaption><span class="lbl">{e(label)}</span>{extra}</figcaption></figure>'

    words = plan["name"].split()
    h1 = (e(" ".join(words[:-2])) + " <em>" + e(" ".join(words[-2:])) + "</em>") if len(words) > 2 else f"<em>{e(plan['name'])}</em>"
    desc = plan.get("description") or ""
    lede = fr((desc[0].upper() + desc[1:] + ". ") if desc else "")
    chain = "".join(f'<span><b>{n}</b>{e(s["title"].replace("the ", ""))}</span>' for n, s in enumerate(plan["steps"], 1))
    stats = "".join(f'<div class="stat"><b class="mono">{b}</b><small>{e(s)}</small></div>' for b, s in (
        (fr(f'{size.replace(chr(34), "")}"'), "W × L × T, finished"),
        (str(nbars), f'bars in {pl(len(plan["bar_types"]), "shape")}'),
        (str(nglued), f'logs glued, {pl(len(logs), "kind")}' + (f' ({nlogs - nglued} more are solid bars)' if nlogs > nglued else "")),
        (str(nsl), f"slices in {pl(len(rows), 'row')}"),
        (f"{bf:g}", "board feet to buy")))

    sheets = [("overview", "Overview", short(W) + " × " + short(L)), ("materials", "Material list", f"{bf:g} bd ft"),
              ("bars", "Bars & rip setups", pl(len(plan["bar_types"]), "shape")), ("logs", "Logs", pl(len(logs), "kind")),
              ("layout", "Slice layout", f"{nsl} slices"), ("build", "Building it", f'{len(plan["steps"])} steps')]
    index = "".join(f'<a href="#{i}"><span class="n">{n:02d}</span><span class="t">{e(t)}</span><span class="s">{fr(s)}</span></a>'
                    for n, (i, t, s) in enumerate(sheets, 1))
    index += (f'<a href="#checks"><span class="n">R</span><span class="t">Checks</span><span class="s" style="color:var(--{"weak" if errors else "good"})">'
              f'{"✗ " + str(len(errors)) + " fail" if errors else ("all pass ✓" if not warns else str(len(plan["checks"]) - len(warns)) + " pass · " + str(len(warns)) + " note")}</span></a>')
    sheet_no = {i: f"{n:02d}" for n, (i, _, _) in enumerate(sheets, 1)}

    H = []
    # 01 overview
    if photo and os.path.exists(photo):
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        hero = fig(f'<img src="data:{mime};base64,{base64.b64encode(open(photo, "rb").read()).decode()}" alt="Render of the finished board">',
                   "Render", '<span>made from the exact face with plan-to-photo</span>')
        second = fig(svgs["face"], "Top face · finished size")
    else:
        hero = fig(svgs["face"], "Top face · finished size")
        top = max((l for l in logs if l["crosscut"]), key=lambda l: l["slices"])
        second = fig(svgs[f'log_{top["id"]}'], f'The building block · log {top["id"]}, end view',
                     f'<span>{len(top["cells"])} pieces, {top["slices"]} slices of it in the board</span>')
    woods = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span>{e(w["name"])}: '
                    f'{next((s["bf_buy"] for s in plan["stock"] if s["species"] == w["name"]), 0):g} bd ft</li>' for w in plan["woods"])
    tilts = sorted({round(b["tilt"], 1) for b in plan["bar_types"] if b["tilt"]})
    kind = plan["info"]["kind"]
    tools = ["Table saw" + (f", digital angle gauge (blade at {', '.join(f'{t:g}°' for t in tilts)})" if tilts else "") + ", rip sled with three toggle clamps",
             "Jointer and planer for the blanks and bars",
             {"tri": "Drum sander or thickness planer (helical head is best) to true bars and logs in the V blocks", "blocks": "Jointer and planer to true the logs",
              "panel": "Planer to true the panels", "hex": "Sanding board: 120 grit on a flat base, for the faces of the pucks"}[kind],
             "Crosscut sled with a stop block, spacer and hold-down", "Band saw (to halve one spare slice for end blocks)" if kind == "tri" else "Band saw or hand saw to halve the edge pucks, calipers" if kind == "hex" else "Calipers and a straightedge",
             {"tri": "Shop-made V blocks, row jig and sled cradle (step 2)", "blocks": "Shop-made band cradle, corner cauls and row jig (step 2)", "panel": "Flat cauls", "hex": "Flat glue-up base with a clamped frame of four straight boards (step 2), blue tape"}[kind],
             "Bar clamps, taped cauls, Titebond III", "Router sled or drum sander to flatten the board; never a planer on the finished end grain",
             "Random-orbit sander, mineral oil and board butter"]
    how = {"tri": "Bars are glued two to four at a time into small triangular logs in a V block. Every face of every log is sanded flat, the logs are sliced, "
                  "the triangular slices are glued into straight rows, and the rows are glued into the board. No glue-up ever has a face that cannot be machined.",
           "blocks": "Each star block is built as a square log: two bars make a band, two bands and a square bar make a quarter log, two quarters make a half and two halves the block. "
                     "The faces of each glue-up that are glued next are machined flat first, then the block logs are sliced and the slices glued in rows.",
           "hex": "Each cube is three diamond bars taped and glued into one hexagon log. The logs are sliced into hexagon pucks, the pucks are sanded and test-fitted, "
                  "and all of them are glued at once inside a clamped frame, starting from the centre. This is how Tom Silva builds the board at This Old House. "
                  "Expect a few hairline gaps; they are filled with glue and sanding dust before the last sanding.",
           "panel": "Square-edged strips are glued into flat panels, the panels are planed and crosscut, and the slices are stood on end and glued into the board."}[kind]
    notes = [how] + list(plan["notes"])
    glance = "".join(f'<dt>{e(k)}</dt><dd class="m">{fr(v)}</dd>' for k, v in (
        ("Bars", f'{nbars} + spares, {pl(len(plan["bar_types"]), "shape")}'), ("Logs", ", ".join(f'{l["count"]} × {l["id"]}' for l in logs)),
        ("Slices", f'{nsl}, cut {short(plan["slice_cut"])} thick'), ("Rows", f'{len(rows)}, each about {short(max(r["height"] for r in rows))} wide') if kind != "hex" else ("Pucks", f'{sum(1 for r in rows for pk in r["pucks"] if not pk.get("half"))} whole, {sum(1 for r in rows for pk in r["pucks"] if pk.get("half"))} half, in {len(rows)} rows'),
        ("Glue-ups", f'{sum(1 for s in plan["steps"] if s.get("glue"))} stages, never more than four parts in a log' if kind != "hex" else "the logs, then every puck in one session")))
    side = (f'<div class="notes" style="padding:0;display:grid;gap:0;align-content:start">{second}'
            f'<div class="notes"><h3>How it goes together</h3><ul>{"".join(f"<li>{fr(n)}</li>" for n in notes)}</ul><h3>At a glance</h3><dl class="kv">{glance}</dl></div></div>')
    H.append(f'<article class="sheet" id="overview">{tb("01", "Overview", fr(desc[0].upper() + desc[1:]) if desc else "", f"<div class=dims>{fr(size)}</div>{stamp}")}'
             f'<div class="main">{hero}{side}</div>'
             f'<div class="lower" style="grid-template-columns:1fr 1.65fr"><div class="notes"><h3>Wood to buy</h3><ul>{woods}</ul></div>'
             f'<div class="notes"><h3>Tools</h3><ul style="display:block;columns:2 30ch;column-gap:32px">{"".join(f"<li>{fr(t)}</li>" for t in tools)}</ul></div></div></article>')

    # 02 materials
    trs = ""
    for st in plan["stock"]:
        col = next(w["end"] for w in plan["woods"] if w["name"] == st["species"])
        trs += f'<tr class="grp"><td colspan="5"><span class="sw" style="background:{col}"></span>{e(st["species"])} · buy {st["bf_buy"]:g} bd ft</td></tr>'
        for it in st["items"]:
            for bl in it["blanks"]:
                trs += (f'<tr><td><span class="chip">{it["bar"]}</span></td><td class="m">{e(it["rough"])}</td><td class="q">{bl["n"]}</td>'
                        f'<td class="m">{fr(bl["size"])}</td><td class="m">{e(bl["yield"])} · {it["per_blank"]} per blank</td></tr>')
    wl = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span><b>{e(w["name"])}</b>'
                 + (f' · Janka {w["janka"]} · shrinkage {w["tan"]}%' if w["janka"] else "") + f'. {fr(w["note"])}</li>' for w in plan["woods"])
    H.append(f'<article class="sheet" id="materials">{tb("02", "Material list", "Blanks for each bar, by species, milled to the bar\'s thickness", "<div class=dims>T × W × L</div>")}'
             f'<div class="lower full" style="border-top:0"><div class="panel"><div class="tbl"><table class="d"><tr><th>Bar</th><th>Rough stock</th>'
             f'<th style="text-align:right;padding-right:12px">Blanks</th><th>Milled blank</th><th>Bars it must yield</th></tr>{trs}</table></div>'
             f'<p class="small">Board feet include 25% for defects and milling. Blanks are {fr(short(sh["stock_width"]))} wide after jointing and the last {fr(short(sh["blank_remainder"]))} of each is not ripped, '
             f'so the bars per blank shown are what the blank really gives. Wider stock gives more.</p></div></div>'
             f'<div class="lower full"><div class="notes"><h3>The woods</h3><ul>{wl}</ul></div></div></article>')

    # 03 bars
    cl = "".join(f'<tr><td><span class="chip">{b["bar"]}</span></td><td>{fr(b["label"])}<span class="sub">{e(wname(b["species"]))}</span></td>'
                 f'<td class="q">{b["total_bars"]} + {b["total_spares"]}</td><td class="m">' + "<br>".join(f'{l["bars"]} + {l["spares"]} @ {fr(short(l["bar_length"]))}' for l in b["lengths"])
                 + f'</td><td class="m">{fr(short(b["stock"]))}</td></tr>' for b in bars)
    setups = "".join(f'<div class="joint"><div class="jh"><span class="jn">{bt["id"]}</span><div><h4>{fr(bt["label"])}</h4>'
                     f'<div class="jsub">{"blade " + format(bt["tilt"], ".1f") + "° from vertical" if bt["tilt"] else "blade square"}</div></div></div>'
                     f'<div class="ph">{svgs["bar_" + bt["id"]]}</div>'
                     f'<ol class="small" style="margin:0;padding-left:18px;display:grid;gap:4px">{"".join(f"<li>{fr(s)}</li>" for s in bt["steps"])}</ol></div>'
                     for bt in plan["bar_types"])
    H.append(f'<article class="sheet" id="bars">{tb("03", "Bars & rip setups", "Every piece of the face is the end of one of these bars. Each drawing shows the section, then the table saw from the front for that rip", f"<div class=dims>{nbars} bars + spares · kerf {fr(short(sh["kerf"]))}</div>")}'
             f'<div class="lower full" style="border-top:0;border-bottom:1px solid var(--rule)"><div class="panel"><h3>The bevel rip</h3><div class="rip">{"".join(f"<p><b>{e(h_)}.</b> {fr(t_)}</p>" for h_, t_ in RIP_POINTS if h_ != "Triangles" or any("triangle" in bt.get("kind", "") for bt in plan["bar_types"]))}<p><b>The cards below.</b> Each gives what differs for that bar: the strip to start from, how it is turned for the second bevel, and the figure to set the sled to.</p></div></div></div>'
             f'<div class="jgrid setups" style="--n:{2 if len(plan["bar_types"]) in (2, 4) else min(3, len(plan["bar_types"]))}">{setups}</div>'
             f'<div class="lower full"><div class="panel"><h3>Cut list</h3><div class="tbl"><table class="d">'
             f'<tr><th>Bar</th><th>Section</th><th style="text-align:right;padding-right:12px">Qty + spare</th><th>Lengths</th><th>Blank thickness</th></tr>{cl}</table></div>'
             f'<p class="small">Bars are cut {fr(short(sh["glue_extra"]))} longer than the log they go into.</p></div></div></article>')

    # 04 logs
    cards = ""
    for l in logs:
        made = " + ".join(f'{k} × {fr(short(ln))}' for ln, k in l["make"])
        parts = OrderedDict()
        for st in l["stages"]:
            for p in st["parts"]:
                key = ("log " + p["log"]) if "log" in p else ("bar " + p["bar"] + " " + wname(p["wood"]).split()[-1].lower())
                parts[key] = parts.get(key, 0) + 1
        ptxt = ", ".join(f"{c} × {k}" for k, c in parts.items())
        use = f'{l["slices"]} slices + {l["spares"]} spare, {fr(short(plan["slice_cut"]))} thick' if l["crosscut"] else "goes into " + ", ".join(
            sorted({"log " + o["id"] for o in logs for st in o["stages"] for p in st["parts"] if p.get("log") == l["id"]}))
        asm = svgs.get(f'asm_log_{l["id"]}') if l["level"] == 1 else None
        wide = ' style="grid-column:1/-1"' if len(l["stages"]) > 1 else ""
        cards += (f'<div class="joint"{wide}><div class="jh"><span class="jn">{e(l["id"])}</span>'
                  f'<div><h4>{e(l["name"])}: {fr(short(l["w"]))} {e(l["what"])}{(", finishes about " + fr(dim(l["trued"]))) if l["kind"] == "tri" else ""}</h4><div class="jsub">{"one solid bar, trued like the other logs" if sum(len(s_["parts"]) for s_ in l["stages"]) == 1 else pl(len(l["stages"]), "glue-up") + " · " + e(l["stages"][0]["jig"])}</div></div></div>'
                  + f'<div class="ph">{svgs[f"log_{l["id"]}"]}</div>'
                  + f'<dl class="kv"><dt>Parts</dt><dd class="m">{e(ptxt)}</dd><dt>Make</dt><dd class="m">{made} long</dd><dt>Use</dt><dd class="m">{use}</dd></dl></div>')
    H.append(f'<article class="sheet" id="logs">{tb("04", "Logs", "End views, as the parts sit in the jig: blue is glue, orange is clamp pressure, numbers are bars from sheet 03, faded parts are already glued", f"<div class=dims>{pl(len(logs), "log type")}</div>")}'
             f'<div class="jgrid logs">{cards}</div></article>')

    # 05 layout
    per_log = "".join(f'<dt>Log {e(l["id"])}</dt><dd class="m">{l["slices"]} slices</dd>' for l in logs if l["crosscut"])
    rowtab = "".join(f'<tr><td class="m" style="color:var(--accent-ink)">R{r["n"]}</td><td class="m">' + _runs([pk["log"] + ("′" if pk["flip"] else "") + ("½" if pk.get("half") else "") for pk in r["pucks"]]) + '</td></tr>' for r in rows)
    marks = ("<li>The letter is the log the slice comes from.</li><li>The short heavy line is the pencil line you drew on the slice at the saw: it marks the log's reference face.</li>"
             "<li>A prime (A′) means the slice is turned over, pencil line underneath, on the edge shown.</li><li>R1, R2 … are the rows, glued in that order.</li>"
             "<li>Dashed red is the trim line; the paler area is cut off.</li>") if kind not in ("panel", "hex") else (
             "<li>Every hexagon is one puck, a slice of log A, set with its pale lid diamond toward the top of the drawing.</li>"
             "<li>½ is a half puck: a puck sawn in two from point to point (step 7), sawn edge to the outside.</li>"
             "<li>R1, R2 … are the rows. They are not glued one at a time: every puck goes into the frame in one session.</li>"
             "<li>Dashed red is the trim line: the two ragged ends are sawn off, and each long side gets a light clean-up cut.</li>") if kind == "hex" else (
             "<li>Each row is one slice of the panel named by its letter.</li><li>A prime (A′) means the slice is turned end for end.</li><li>Dashed red is the trim line.</li>")
    H.append(f'<article class="sheet" id="layout">{tb("05", "Slice layout", "Top view before trimming: which slice goes where, and which way round", f"<div class=dims>{nsl} slices · {pl(len(rows), "row")}</div>")}'
             f'<div class="main">{fig(svgs["layout"], "Slices before trimming")}<div class="panel"><h3>Reading the drawing</h3><ul>{marks}</ul>'
             f'<h3>Slices needed</h3><dl class="kv">{per_log}</dl>'
             f'<h3>Row by row, starting at the end with the R label</h3><div class="tbl"><table class="d">{rowtab}</table></div></div></div></article>')

    # 06 build
    import re as _re
    def runin(t):          # "Row jig: a flat base..." gets its name in bold
        m = _re.match(r"^([A-Z][A-Za-z′' -]{2,26}): ", t)
        return f"<b>{e(m.group(1))}.</b> {fr(t[m.end():].strip()[:1].upper() + t[m.end():].strip()[1:])}" if m else fr(t)
    st = ""
    nglue = 0
    for n, s in enumerate(plan["steps"], 1):
        refs = [sheet_no[d] for d in s.get("see", []) if d in sheet_no]
        see = f'<div class="see">See sheet {", ".join(refs)}</div>' if refs else ""
        dont = f'<div class="dont"><b>DON\'T</b>{fr(s["dont"])}</div>' if s.get("dont") else ""
        kick = ""
        if s.get("glue"):
            nglue += 1; kick = f'<span class="kick">GLUE-UP {nglue}</span><br>'
        figs = list(dict.fromkeys(f for f in s.get("figs", []) if f in svgs))
        body = f'{kick}<h4>{e(s["title"])}</h4><ul>{"".join(f"<li>{runin(t)}</li>" for t in s["text"])}</ul>{see}'
        if figs:
            body = f'<div class="stepgrid"><div>{body}</div><div class="asm">{"".join(f"<figure{' class=wide' if f == 'ripsled' else ''}>{svgs[f]}</figure>" for f in figs)}</div></div>'
        st += f'<li><span class="sn">{n}</span><div>{body}</div>{dont}</li>'
    H.append(f'<article class="sheet" id="build">{tb("06", "Building it", "In order, with the reason where it isn\'t obvious", f"<div class=dims>{len(plan["steps"])} steps</div>")}'
             f'<div class="stepbox"><ol class="steps">{st}</ol></div></article>')

    chk = "".join(f'<tr><td>{e(c["what"])}' + (f'<span class="sub">{fr(c["detail"])}</span>' if c["detail"] else "") + '</td>'
                  f'<td class="{"pass" if c["ok"] else c["level"] if c["level"] == "warn" else "fail"}">{"PASS" if c["ok"] else ("WARN" if c["level"] == "warn" else "FAIL")}</td></tr>'
                  for c in plan["checks"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan["name"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,600;112,700&family=IBM+Plex+Mono:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">End-grain cutting board · shop plan</div>
<h1>{h1}</h1><p class="lede">{lede}</p><div class="chain" aria-label="Build order">{chain}</div><div class="stats">{stats}</div></header>
<nav class="index" aria-label="Sheets">{index}</nav>
<main>{"".join(H)}</main>
<article class="sheet" id="checks">{tb("R", "Checks", "Recomputed from the board's geometry every time the plan is built", stamp)}
<div class="lower full" style="border-top:0"><div class="panel"><table class="cost">{chk}</table></div></div></article>
<footer>Kerf {fr(short(sh["kerf"]))}; slices cut {fr(short(plan["slice_cut"]))}; {fr(short(sh["end_trim"]))} to square the first end of a log and {fr(short(sh["hold_end"]))} held at the other; sliced logs at most {sh["max_log_length"]:g}" long; bars ripped {fr(short(sh["rip_oversize"]))} over and machined to size; {sh["true_skim"]:.2f}" allowed for each truing pass. Change these under "shop" in design.json and rebuild.</footer>
</div></body></html>"""
