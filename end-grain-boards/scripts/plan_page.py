"""The shop plan page: a set of numbered sheets, each with a title block, its drawing beside its data,
and notes underneath, closing with the checks. Warm paper, Archivo headings, Source Serif body text and
IBM Plex Mono labels and numbers, walnut-brown accent; light and dark.

page(plan, svgs, photo) -> one self-contained HTML string (fonts from Google Fonts, nothing else external).
"""
import base64, html, os, re


def _fr(s):
    """Escape, then set fractions as small stacked numerals: 1-5/16 -> 1 5/16 with sup/sub."""
    s = html.escape(str(s))
    s = re.sub(r"(\d+)-(\d+)/(\d+)", lambda m: f'{m[1]}<span class="fr"><sup>{m[2]}</sup>⁄<sub>{m[3]}</sub></span>', s)
    s = re.sub(r"(^|[^\d/#>])(\d+)/(\d+)(?![\d.])", lambda m: f'{m[1]}<span class="fr"><sup>{m[2]}</sup>⁄<sub>{m[3]}</sub></span>', s)
    return s


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
.main>figure,.lower>figure{margin:0;background:var(--sheet);padding:14px;display:grid;gap:8px;align-content:start;min-width:0}
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
ol.steps ul{margin:0;padding-left:18px;display:grid;gap:5px;max-width:76ch}
ol.steps .see{font-family:var(--f-mono);font-size:12px;color:var(--graphite);margin-top:6px}
.dont{grid-column:2;margin-top:8px;border-left:3px solid var(--weak);padding:6px 10px;font-size:14px;background:color-mix(in srgb,var(--weak) 8%,transparent)}
.dont b{font-family:var(--f-mono);font-size:11.5px;letter-spacing:.07em;color:var(--weak);margin-right:6px}
.stepbox{background:var(--sheet);padding:4px 18px}
section.find{margin-top:56px;display:grid;gap:18px}
section.find h2{font-family:var(--f-display);font-size:36px;margin:0;font-weight:700;line-height:1;font-stretch:112%}
table.cost{border-collapse:collapse;font-size:14px;width:100%;max-width:760px}
table.cost td{padding:7px 0;border-bottom:1px solid var(--rule);vertical-align:top}
table.cost td:last-child{text-align:right;font-family:var(--f-mono);padding-left:14px;white-space:nowrap}
table.cost .pass{color:var(--good)}table.cost .warn{color:var(--warn)}table.cost .fail{color:var(--weak)}
table.cost .sub{display:block;font-size:12.5px;color:var(--graphite)}
footer{margin-top:48px;font-size:12.5px;color:var(--graphite);max-width:80ch}
.setups{grid-template-columns:repeat(var(--n),minmax(0,1fr))}
@media (max-width:860px){.setups{grid-template-columns:1fr}.main,.lower{grid-template-columns:1fr}.tb{grid-template-columns:auto 1fr}
 .tb .meta{grid-column:1/-1;border-left:0;border-top:1px solid var(--rule);justify-items:start;text-align:left}}
@media (max-width:520px){.tb .no{font-size:34px}.tb h2{font-size:23px}.jgrid{grid-template-columns:1fr}}
"""

TICK = ('<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><rect x="1" y="1" width="12" height="12" rx="2" '
        'fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M4 7.2l2 2 4-4.4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>')


def page(plan, svgs, photo, guide=None):
    from cbplan import dim, short, XF_MARK, XF_TEXT, plan_name
    e = html.escape; fr = _fr
    W, L, T = plan["board"]["width"], plan["board"]["length"], plan["board"]["thickness"]
    sh = plan["shop"]; logs = plan["logs"]; bars = plan["bars"]
    nbars = sum(b["total_bars"] for b in bars); nlogs = sum(l["count"] for l in logs); nsl = len(plan["slices"])
    bf = sum(s["bf_buy"] for s in plan["stock"])
    errors = [c for c in plan["checks"] if not c["ok"] and c["level"] != "warn"]
    warns = [c for c in plan["checks"] if not c["ok"] and c["level"] == "warn"]
    size = f'{short(W)} × {short(L)} × {short(T)}'
    stamp = (f'<div class="stamp bad">✗ {len(errors)} check{"s" if len(errors) > 1 else ""} fail</div>' if errors else
             f'<div class="stamp">{TICK}{len(plan["checks"]) - len(warns)} of {len(plan["checks"])} checks pass</div>')

    def tb(no, title, by, meta):
        return (f'<div class="tb"><div class="no mono">{no}</div><div><h2>{e(title)}</h2><div class="by">{by}</div></div>'
                f'<div class="meta">{meta}</div></div>')

    def fig(svg_or_img, label, extra=""):
        return f'<figure><div class="ph">{svg_or_img}</div><figcaption><span class="lbl">{e(label)}</span>{extra}</figcaption></figure>'

    # title: last two words in the accent
    words = plan["name"].split()
    h1 = (e(" ".join(words[:-2])) + " <em>" + e(" ".join(words[-2:])) + "</em>") if len(words) > 2 else f"<em>{e(plan['name'])}</em>"
    desc = plan.get("description") or ""
    lede = fr((desc[0].upper() + desc[1:] + ". ") if desc else "") + fr(plan["notes"][0] if plan["notes"] else "")
    chain = "<i>→</i>".join(f'<span><b>{n}</b>{e(s["title"].replace("the ", ""))}</span>' for n, s in enumerate(plan["steps"], 1))
    stats = "".join(f'<div class="stat"><b class="mono">{b}</b><small>{e(s)}</small></div>' for b, s in (
        (fr(f'{size.replace(chr(34), "")}"'), "W × L × T, finished"),
        (str(nbars), f'bars, {len(plan["bar_types"])} shape{"s" if len(plan["bar_types"]) > 1 else ""}'),
        (str(nlogs), f'log{"s" if nlogs > 1 else ""} glued, {len(logs)} kind{"s" if len(logs) > 1 else ""}'),
        (str(nsl), "slices in the final glue-up"),
        (f"{bf:g}", "board feet to buy, " + ", ".join(w["name"].split()[-1].lower() for w in plan["woods"]))))

    sheets = [("overview", "Overview", short(W) + " × " + short(L)), ("materials", "Material list", f"{bf:g} bd ft"),
              ("bars", "Bars & rip setups", f'{len(plan["bar_types"])} shape{"s" if len(plan["bar_types"]) > 1 else ""}'),
              ("logs", "Units & logs", (f'{len(plan["units"])} unit{"" if len(plan["units"]) == 1 else "s"} · ' if plan["units"] else "") + f'{len(logs)} log{"" if len(logs) == 1 else "s"}'),
              ("layout", "Slice layout", f"{nsl} slices"), ("build", "Building it", f'{len(plan["steps"])} steps')]
    index = "".join(f'<a href="#{i}"><span class="n">{n:02d}</span><span class="t">{e(t)}</span><span class="s">{fr(s)}</span></a>'
                    for n, (i, t, s) in enumerate(sheets, 1))
    index += (f'<a href="#checks"><span class="n">R</span><span class="t">Checks</span><span class="s" style="color:var(--{"weak" if errors else "good"})">'
              f'{"✗ " + str(len(errors)) + " fail" if errors else "all pass ✓"}</span></a>')

    H = []
    # 01 overview
    if photo and os.path.exists(photo):
        mime = "image/png" if photo.lower().endswith(".png") else "image/jpeg"
        hero = fig(f'<img src="data:{mime};base64,{base64.b64encode(open(photo, "rb").read()).decode()}" alt="Render of the finished board">',
                   "Render", '<span>made from the exact face with plan-to-photo</span>')
    else:
        hero = fig(svgs["face"], "Finished face")
    if photo and os.path.exists(photo):
        second = fig(svgs["face"], "Top face · finished size")
    elif guide and os.path.exists(guide):
        second = fig(f'<img src="data:image/png;base64,{base64.b64encode(open(guide, "rb").read()).decode()}" alt="Colour-coded view of the board">',
                     "Colour-coded view")
    else:
        second = '<div class="notes"></div>'
    woods = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span>{e(w["name"])}: '
                    f'{next((s["bf_buy"] for s in plan["stock"] if s["species"] == w["name"]), 0):g} bd ft</li>' for w in plan["woods"])
    tilts = sorted({round(b["tilt"], 1) for b in plan["bar_types"] if b["tilt"]})
    tools = ["Table saw" + (f" with a digital angle gauge (blade at {', '.join(f'{t:g}°' for t in tilts)})" if tilts else ""),
             "Thin-rip jig, zero-clearance insert, push block", "Crosscut sled with a stop block",
             "Bar clamps, cauls, packing tape for the bevelled units", "Router sled or drum sander (not a planer)",
             "Random-orbit sander, mineral oil and board butter"]
    H.append(f'<article class="sheet" id="overview">{tb("01", "Overview", fr(desc[0].upper() + desc[1:]) if desc else "", f"<div class=dims>{fr(size)}</div>{stamp}")}'
             f'<div class="main">{hero}{second}</div>'
             f'<div class="lower"><div class="notes"><h3>About the pattern</h3><ul>{"".join(f"<li>{fr(n)}</li>" for n in plan["notes"])}</ul></div>'
             f'<div class="notes"><h3>What you\'ll need</h3><ul>{woods}</ul><h3>Tools</h3><ul>{"".join(f"<li>{fr(t)}</li>" for t in tools)}</ul></div></div></article>')

    # 02 materials
    rows = ""
    for st in plan["stock"]:
        col = next(w["end"] for w in plan["woods"] if w["name"] == st["species"])
        rows += f'<tr class="grp"><td colspan="4"><span class="sw" style="background:{col}"></span>{e(st["species"])} · buy {st["bf_buy"]:g} bd ft</td></tr>'
        for it in st["items"]:
            rows += (f'<tr><td><span class="chip">{it["bar"]}</span></td><td class="m">{e(it["rough"])}</td><td class="q">{it["blanks"]}</td>'
                     f'<td class="m">{fr(it["blank"])}</td></tr>')
    wl = "".join(f'<li><span class="sw" style="background:{w["end"]}"></span><b>{e(w["name"])}</b>'
                 + (f' · Janka {w["janka"]} · shrinkage {w["tan"]}%' if w["janka"] else "") + f'. {fr(w["note"])}</li>' for w in plan["woods"])
    H.append(f'<article class="sheet" id="materials">{tb("02", "Material list", "Blanks per species, milled to the bar thickness", "<div class=dims>T × W × L</div>")}'
             f'<div class="lower full" style="border-top:0"><div class="panel"><div class="tbl"><table class="d"><tr><th>Bar</th><th>Rough</th>'
             f'<th style="text-align:right;padding-right:12px">Blanks</th><th>Milled blank</th></tr>{rows}</table></div>'
             f'<p class="small">Board feet include 25% for defects and milling. Blanks are {fr(short(sh["stock_width"]))} wide after jointing; wider stock gives more bars per blank.</p></div></div>'
             f'<div class="lower full"><div class="notes"><h3>The woods</h3><ul>{wl}</ul></div></div></article>')

    # 03 bars
    cl = "".join(f'<tr><td><span class="chip">{b["bar"]}</span></td><td>{fr(b["label"])}<span class="sub">{e(plan_name(plan, b["species"]))} · {e(", ".join(b["roles"]))}</span></td>'
                 f'<td class="q">{b["total_bars"]}</td><td class="m">' + "<br>".join(f'<span class="fr">{l["bars"]} @ {fr(short(l["bar_length"]))}</span>' for l in b["lengths"])
                 + f'</td><td class="m">{fr(short(b["stock"]))}</td></tr>' for b in bars)
    setups = "".join(f'<div class="joint"><div class="jh"><span class="jn">{bt["id"]}</span><div><h4>{fr(bt["label"])}</h4>'
                     f'<div class="jsub">{"blade " + format(bt["tilt"], ".1f") + "° from vertical" if bt["tilt"] else "blade square"}</div></div></div>'
                     f'<ul class="small" style="margin:0;padding-left:18px;display:grid;gap:4px">{"".join(f"<li>{fr(s)}</li>" for s in bt["steps"])}</ul></div>'
                     for bt in plan["bar_types"])
    H.append(f'<article class="sheet" id="bars">{tb("03", "Bars & rip setups", "Every piece of the face is the end of one of these bars", f"<div class=dims>{nbars} bars · kerf {fr(short(sh["kerf"]))}</div>")}'
             f'<div class="main">{fig(svgs["bars"], "Cross-sections and the blank, end view")}<div class="panel"><h3>Cut list</h3><div class="tbl"><table class="d">'
             f'<tr><th>Bar</th><th>Section</th><th style="text-align:right;padding-right:12px">Qty</th><th>Lengths</th><th>Blank</th></tr>{cl}</table></div></div></div>'
             f'<div class="jgrid setups" style="border-top:1px solid var(--rule);--n:{min(3, len(plan["bar_types"]))}">{setups}</div></article>')

    # 04 units and logs
    cards = ""
    for u in plan["units"]:
        pcs = "<br>".join(f'{p["count"]} × {fr(short(p["length"]))} for {e(p["log"])}' for p in u["pieces"])
        cards += (f'<div class="joint"><div class="ph">{svgs.get(f"unit{u["type"] + 1}", "")}</div><div class="jh"><span class="jn">U{u["type"] + 1}</span>'
                  f'<div><h4>{len(u["bars"])} bars glued as drawn</h4><div class="jsub">tape glue-up</div></div></div>'
                  f'<dl class="kv"><dt>Make</dt><dd class="m">{pcs}</dd></dl></div>')
    for l in logs:
        what = ", ".join(x for x in ((f'{len(l["units"])} units' if l["units"] else ""), (f'{len(l["loose_bars"])} bars' if l["loose_bars"] else "")) if x)
        cards += (f'<div class="joint" style="grid-column:1/-1"><div class="ph">{svgs[f"log{l["type"]}"]}</div><div class="jh"><span class="jn">{e(l["name"][-1])}</span>'
                  f'<div><h4>{e(l["name"])}: {e(what)} side by side</h4><div class="jsub">{"needs a plywood carrier on the sled" if l.get("carrier") else "sits flat on the sled"}</div></div></div>'
                  f'<dl class="kv"><dt>Make</dt><dd class="m">{l["count"]} × {fr(short(l["length"]))} long</dd><dt>Slices</dt><dd class="m">{l["slices"]} + {l["spares"]} spare, '
                  f'{fr(short(T + sh["flatten_allowance"]))} thick</dd></dl></div>')
    H.append(f'<article class="sheet" id="logs">{tb("04", "Units & logs", "Bars glue into units, units glue side by side into logs; labels show any unit turned or flipped", f"<div class=dims>{len(plan["units"])} unit type{"" if len(plan["units"]) == 1 else "s"} · {len(logs)} log type{"" if len(logs) == 1 else "s"}</div>")}'
             f'<div class="jgrid">{cards}</div></article>')

    # 05 layout
    turns = sorted({s["xf"] for s in plan["slices"]} - {"id"})
    per_log = "".join(f'<dt>{e(l["name"])}</dt><dd class="m">slices ' + ", ".join(str(s["n"]) for s in plan["slices"] if s["log"] == l["name"]) + "</dd>" for l in logs)
    H.append(f'<article class="sheet" id="layout">{tb("05", "Slice layout", "Number, log letter and any turn, glued bottom to top; trim on the red dashed line", f"<div class=dims>{nsl} slices</div>")}'
             f'<div class="main">{fig(svgs["layout"], "Slices before trimming")}<div class="panel"><h3>Where each slice comes from</h3><dl class="kv">{per_log}</dl>'
             f'<h3>Marks</h3><ul>' + ("".join(f"<li><b class=mono>{XF_MARK[t]}</b> {e(XF_TEXT[t])}</li>" for t in turns) or "<li>Every slice goes down as cut.</li>")
             + '</ul><p class="small">The pencil V drawn across each log before crosscutting tells you which face is up and keeps the slices in order.</p></div></div></article>')

    # 06 build
    where = {"bars": "03", "layout": "05", "face": "01"}
    st = ""
    for n, s in enumerate(plan["steps"], 1):
        refs = sorted({where.get(d, "04") for d in s["diagrams"]})
        see = f'<div class="see">See sheet {", ".join(refs)}</div>' if refs else ""
        dont = f'<div class="dont"><b>DON\'T</b>{fr(s["dont"])}</div>' if s.get("dont") else ""
        st += f'<li><span class="sn">{n}</span><div><h4>{e(s["title"])}</h4><ul>{"".join(f"<li>{fr(t)}</li>" for t in s["text"])}</ul>{see}</div>{dont}</li>'
    H.append(f'<article class="sheet" id="build">{tb("06", "Building it", "In order, with the reason where it isn\'t obvious", f"<div class=dims>{len(plan["steps"])} steps</div>")}'
             f'<div class="stepbox"><ol class="steps">{st}</ol></div></article>')

    chk = "".join(f'<tr><td>{e(c["what"])}' + (f'<span class="sub">{fr(c["detail"])}</span>' if c["detail"] else "") + '</td>'
                  f'<td class="{"pass" if c["ok"] else c["level"] if c["level"] == "warn" else "fail"}">{"PASS" if c["ok"] else ("WARN" if c["level"] == "warn" else "FAIL")}</td></tr>'
                  for c in plan["checks"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(plan["name"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@112,600;112,700&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap">
<style>{CSS}</style></head><body><div class="wrap">
<header class="hero"><div class="eyebrow">End-grain cutting board · shop plan · {e(plan["pattern"])}</div>
<h1>{h1}</h1><p class="lede">{lede}</p><div class="chain" aria-label="Build order">{chain}</div><div class="stats">{stats}</div></header>
<nav class="index" aria-label="Sheets">{index}</nav>
<main>{"".join(H)}</main>
<section class="find" id="checks"><div class="eyebrow">Checks</div><h2>What the model proves</h2>
<p class="lede">Recomputed from the board's geometry every time the plan is built: the pieces must cover the board exactly and every bar must be one a table saw can rip.</p>
<table class="cost">{chk}</table></section>
<footer>Kerf {fr(short(sh["kerf"]))}, slices cut {fr(short(T + sh["flatten_allowance"]))} ({fr(short(sh["flatten_allowance"]))} to flatten), {fr(short(sh["end_trim"]))} trimmed from each log end, logs at most {sh["max_log_length"]:g}" long, one spare slice per log. Change these under "shop" in design.json and rebuild.</footer>
</div></body></html>"""
