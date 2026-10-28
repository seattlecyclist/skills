# Doors: sizing, hinges, reveals and hardware

Read this for any plan with a hinged door. A door is sized from four things, in this order:
**the cabinet type, the door style, the hinge, then the door.** The cabinet (frameless or face
frame) and the style (full overlay, half overlay, face-frame overlay, inset) set how far the door
covers the case. The hinge has to give exactly that overlay, because a concealed hinge's overlay is
fixed by its crank, the cup's distance from the door edge and the mounting plate, and it adjusts
only about 2 mm after that. So choose the hinge before any door size is final. The model check
(`doors` in the plan, below) measures every door against its hinge's numbers and fails a door the
hinge cannot hang.

All sizes are inches unless marked; hinge makers work in millimetres, and their numbers are given
in mm. Each hinge row cites the sheet it came from. Retailer pages and old catalogues disagree;
when a builder names a hinge that is not in the catalogue, find the maker's planning sheet and pass
its numbers as a custom hinge (see "Custom hinges").

## 1. Terms

| Symbol | Meaning |
|---|---|
| `W_o`, `H_o` | The **opening**: frameless, between the inside faces of the sides and from the underside of the top (or rail) to the top of the bottom; face frame, between the frame's inside edges. |
| `e` | The **case edge** around the opening the door can cover: the side thickness on a frameless case (3/4" ply is really 18–19 mm), or the frame member's width on a face frame. Where the case sides run past a top that is dadoed in, `e` at the top is the side's overhang plus the top's thickness. |
| `O` | **Overlay**: how far the closed door covers `e`, on each edge. |
| `r` | **Reveal** at an exposed edge: `e − O`, the case edge left showing (frameless), or the gap all round an inset door. |
| `g` | **Gap** between two doors (a pair) or a door and a drawer front. |
| `C` | **Cup distance** (boring distance, Blum's B, Salice's K): door edge to the edge of the 35 mm cup. Cup centre = `C + 17.5 mm`. |
| `H` | **Mounting plate height** (Hettich's D): 0, 3, 6, 9 mm. A taller plate moves the door off the case and reduces the overlay. |
| `k` | The hinge's constant: overlay `O = k + C − H` (mm). Each crank has its own `k`. |
| `F_min` | The hinge maker's **minimum reveal** at the hinge edge so the door's back corner clears whatever is next to it while it swings. |

## 2. Reveals and gaps

One rule covers frameless doors and drawer fronts: **about 1/16" (1.5 mm) at every outer edge
and 1/8" (3 mm) between neighbours**, door to door, door to drawer, drawer to drawer. Each front
stops 1/16" short of the edge it covers, so two fronts that meet each give up 1/16" and the gap is
1/8" ([32 mm system: Full Overlay][davelers]; [WOODWEB: Frameless Cabinet Door Dimensions][ww-frameless]).

- AWI's standards (as quoted on WOODWEB) target a 3.2 mm (1/8") gap held to ±0.8 mm at Premium
  grade ([WOODWEB][ww-frameless]). 1/8" is the practical maximum; much tighter than 1/16" a side
  binds unless the hinge and edge profile allow it ([WOODWEB: 1/16" vs 1/8" reveals][ww-reveals]).
- **Solid-wood doors** move across their width with the seasons; shops open the middle gap to
  4 mm (5/32") ([WOODWEB][ww-frameless]).
- Some shops and the Woodshop Diaries guide use 1/8" at each outer edge (case width − 1/4")
  ([Woodshop Diaries][wsd-doors]). Either is right; pick one and keep it even across the cabinet.
- **Inset doors**: 1/16"–3/32" all round in shop practice; Woodshop Diaries uses opening − 1/4"
  (1/8" a side) ([Woodshop Diaries][wsd-doors]). Never less than the hinge's minimum reveal at the
  hinge edge (section 4.4).
- **Face-frame overlay**: the door sits on the frame; the reveal is the frame left showing. Leave
  at least 1/4" of frame between neighbouring doors and at the cabinet edge: a 1-1/2" stile takes up
  to a 1-1/4" overlay ([Woodshop Diaries][wsd-doors]). A common kitchen layout is 1/2" overlay on
  1-1/2" to 1-3/4" frames, leaving about 1-1/4" of frame showing ([WOODWEB: Cabinet Face
  Dimensions][ww-face]).

## 3. Door sizes from the case

| Cabinet and style | Single door | Pair (each leaf) | Height |
|---|---|---|---|
| Frameless, full overlay | `W_o + 2e − 2r` = case width − 2r | `(case width − 2r − g) ÷ 2` | case height − 2r (or `H_o + e_top + e_bot − 2r`) |
| Frameless, half overlay (two doors on one partition) | `W_o + e_outer − r + e_part/2 − g/2` | same per leaf | as full overlay |
| Face frame, overlay `O` | `W_o + 2O` | `(W_o + 2O − g) ÷ 2` (g is usually 1/8") | `H_o + 2O` |
| Inset (frameless or face frame) | `W_o − 2r` | `(W_o − 2r − g) ÷ 2` | `H_o − 2r` |

Round down to the nearest 1/32" and keep the reveals even rather than exact ([Woodshop
Diaries][wsd-doors]). A door with a drawer above it: subtract the drawer front and one more gap
from the height. `doorSize(opening, { style, leaves, frame, reveal, gap, overlay })` in
`plan-core.js` gives these.

**Single or pair.** Doors are happiest taller than wide; Blum's hinge loads assume doors no wider
than 600 mm (23-5/8"), and one more hinge per door up to 650 mm ([Blum: number of hinges][blum-count]).
Past about 24" of opening, use a pair.

## 4. Concealed (European) hinges

All the hinges here are 110° cup hinges in a 35 mm cup with the 45/9.5 screw pattern (Hettich's
Sensys also comes in TH 52/5.5), clipping onto a mounting plate screwed to the case side on the
32 mm system line, **37 mm back from the front edge** of a frameless side ([Blum CLIP top
planning sheet][blum-clip]).

### 4.1 The crank decides the style

| Style | Blum CLIP top BLUMOTION | Salice 200 series | Grass Tiomos 110 | Hettich Sensys 8645i |
|---|---|---|---|---|
| Full overlay | straight arm 71B3550, `k = 11` | "A" crank, `k = 15` | crank 0, `k = 15` (crank 3: `k = 12`) | full overlay, `k = 12.5` |
| Half overlay | half-cranked 71B3650, `k = 1.5` | "G" crank, `k = 6` | crank 9.5, `k = 5.5` | half overlay, `k = 3` |
| Inset (reveal = −O) | full-cranked 71B3750, `k = −7` | "P" crank, `k = −2` | crank 19 (see sheet) | inset, `k = −4` |
| Face frame 1/2" overlay | (use COMPACT 39C, below) | "D" crank, `k = 10` | | |
| Cup distance `C` | 3–7 mm | 3–6 mm | 3–7 mm | 3–7 mm |
| Plates `H` | 0, 3, 6, 9 mm | 0, 1.5, 3, 5 mm (check range) | 0, 2, 3 mm | 0, 1.5, 3, 5 mm |
| Door thickness | to 26 mm | 16–26 mm | to 24 mm | 15–24 mm |
| Source | [Blum][blum-clip], [catalogue][blum-cat] | [Salice USA catalogue][salice] p. 4 | [Grass Tiomos 110][grass] | [Hettich Sensys][hettich] |

```
overlay O (mm) = k + C − H                  inset reveal = −(k + C − H)
cup centre from the door edge = C + 17.5 mm
```

Worked from each sheet: Blum straight arm on a 0 mm plate gives 14, 15, 16, 17, 18 mm at C = 3–7
([Blum][blum-clip]); Hettich writes it as plate D = C + 12.5 − A ([Hettich][hettich]); Salice as
D = (15 + K) − H ([Salice][salice]). The same 5 mm bore on a 0 mm plate gives 16 mm on a Blum, 20 mm
on a Salice or Grass and 17.5 mm on a Hettich: **the hinge make matters**, so name it.

All four adjust about ±2 mm sideways after hanging (Hettich "+2 mm / −2 mm"). Aim the cup and plate
so the door's overlay is in the middle of that range. Where two plates both reach, take the one
that leaves the overlay mid-range ([Hardware Source: choosing a plate][hs-plate]).
`hingeSetup(hinge, overlayMM)` picks the cup distance and plate.

Full overlay on 3/4" (19 mm) sides with 1/16" reveals is 17.5 mm: Blum at C = 6.5 mm on a 0 mm
plate; Hettich at C = 5 mm, 0 plate; Salice at C = 4 mm on a 1.5 mm plate; Grass at C = 4.5 mm on a
2 mm plate. With 1/8" reveals (15.9 mm): Blum C = 5 on a 0 plate, Hettich C = 5 on a 1.5 mm plate, Salice
and Grass C = 4 on a 3 mm plate.

### 4.2 Face-frame hinges

- **Blum COMPACT BLUMOTION 39C**: a one-piece hinge that wraps the frame; the overlay is fixed by
  the model (suffix B16 = 1", B20 = 1-1/4", B21 = 1-5/16", B22 = 1-3/8", B24 = 1-1/2", B25 =
  1-9/16"), 3 mm cup distance, 107° opening, made for 3/4" frames ([cabinetdoor.store: Blum
  Compact][compact]; [cabinetparts: 39C355B24][compact-cp]).
- **Salice "D" crank 1/2" overlay** with its face-frame plate: `O = 10 + K − H` ([Salice][salice]).
- **Inset on a face frame**: an inset (full-crank) hinge on a face-frame plate, or a butt hinge
  mortised into the frame and door (section 6).

### 4.3 Cup bore

35 mm Forstner (+0.1 mm), **Blum 13 mm deep** ([Blum][blum-clip]); Salice 200 series 11.5 mm
(thick-door versions 11 mm, 7/16") ([Salice][salice]); Grass gives a 12.6 mm minimum
([Grass][grass]). Leave at least 2 mm of door behind the cup: a 16 mm door is the thinnest these
hinges are tabled for. The two cup screws (or dowels) sit 45 mm apart on a line 9.5 mm further
from the edge than the cup centre. Bore a test cup in scrap and hang it before boring doors.

### 4.4 Minimum reveal and opening clearance

A thick door's back corner sweeps toward its neighbour as it opens. The maker's **minimum
reveal** is the gap the hinge edge needs to anything beside it: a side panel on an inset door, a
wall, or another door ([Hardware Source: back-to-back reveal][hs-b2b]). Blum (1 mm edge radius):

| Door | C = 3 | 4 | 5 | 6 | 7 mm |
|---|---|---|---|---|---|
| 16 mm | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 |
| 19 mm | 1.0 | 1.0 | 0.9 | 0.9 | 0.9 |
| 22 mm | 1.8 | 1.7 | 1.7 | 1.6 | 1.6 |
| 24 mm | 2.7 | 2.5 | 2.4 | 2.3 | 2.2 |
| 26 mm | 4.3 | 3.8 | 3.4 | 3.2 | 3.0 |

([Blum][blum-clip].) Hettich's are a little smaller for 19 mm doors (0.8 mm at C = 3) and grow
faster past 22 mm (3.9 mm for a 24 mm door at C = 3); add 0.4 mm for a square edge, take 0.6 mm off
for a 3 mm radius ([Hettich][hettich]). Salice tables square edges, so its numbers run higher
(1.2 mm for 19 mm, 5.1 mm for 24 mm at K = 3) ([Salice][salice] p. 70). Grass: 0.9 mm for 19 mm,
2.4 mm for 24 mm ([Grass][grass]).

- **Back-to-back doors** (two doors hinged on one partition) can both be open at once: the gap
  between them must be **twice** the per-door minimum ([Hardware Source][hs-b2b]).
- **Inset doors**: the hinge-edge gap must be at least the minimum reveal; the free edge is not
  limited by the hinge.
- **A pair meeting in the middle** swings apart, so the hinge does not limit the meeting gap; but
  thick inset pairs need a 2°–3° back-bevel on the meeting edges, or an eased edge, so the leading
  corner clears ([WOODWEB: 1/16" vs 1/8" reveals][ww-reveals]).
- **Next to a wall or appliance**: at full opening the door stands proud of the case side by
  its own thickness plus the hinge's door protrusion (Hettich: 8.5 mm full overlay, 18 mm half,
  25 mm inset on a 0 plate, C = 3 [Hettich][hettich]). Leave a filler, or fit the maker's angle
  restriction clip (Blum 70T3553 limits CLIP top to 86° [Blum catalogue][blum-cat]; Grass tables
  minimum reveal at 85° [Grass][grass]).

### 4.5 How many hinges, and where

Salice: **2 hinges** to 36" (900 mm) and 20 lb, **3** to 60" (1600 mm) and 40 lb, **4** to 84"
(2000 mm) and 60 lb, **5** to 96" (2400 mm); hinge spacing must be more than the door's width, and
add one near a limit ([Salice][salice] p. 2). Blum: 2 hinges for 4–6 kg doors, 3 for 6–12 kg, up to
600 mm wide, plus one up to 650 mm; count the handle in the weight ([Blum][blum-count]).

Door weight: plywood about 42 lb/ft³, MDF 48, hardwood about 40, glass 156. A 3/4" plywood door
15" × 30" is about 8 lb.

Hinge centres about 3"–4" from the top and bottom of the door (keep them off fixed shelves and
the case top and bottom inside faces), extra hinges evenly between.

### 4.6 Soft-close, push-to-open and catches

- Blum CLIP top BLUMOTION and Grass Tiomos (damper versions) have soft-close in the cup; Hettich
  Sensys has it in the arm. Nothing else is needed to hold the door shut ([Blum][blum-clip];
  [Grass][grass]; [Hettich][hettich]).
- **Push-to-open**: use the maker's hinge without a spring (Grass Tiomos "without self-closing
  mechanism", or its self-opening version with the Tipmatic pin) and a push latch; leave the door
  no pull ([Grass][grass]).
- Butt-hinged doors need a catch: magnetic or ball catch at the free edge, or a bullet catch in the
  top edge of inset doors.

## 5. Door construction

**Slab doors.** 3/4" plywood or MDF, edge-banded all round (cut 1/32" under each edge for the
banding). Grain runs up. Hinges and pulls screw straight in.

**Frame-and-panel (cope and stick).** 3/4" stiles and rails, typically 2-1/4" wide (WOODWEB
shops: 2-1/4" stiles and 3" bottom rails; Shaker 57 mm, ogee 64 mm) ([WOODWEB: Cabinet Face
Dimensions][ww-face]). Groove 1/4" wide and **3/8" deep**; the cope on the rail ends fills the
same 3/8" ([Woodcraft: raised-panel doors][woodcraft]):

```
stile length = door height
rail length  = door width − 2 × stile width + 2 × groove depth (the cope)
panel width  = door width − 2 × stile width + 2 × groove depth − expansion
panel height = door height − 2 × rail width + 2 × groove depth − 1/16"
```

- **Solid-wood panels float**: no glue in the grooves, rubber spacers in the side grooves. Cut
  wide panels to leave room across the grain: Woodcraft allows about 3/16" for expansion when the
  panel is made in a dry winter shop and about 1/16" when made in a humid summer ([Woodcraft][woodcraft]).
  Plywood or MDF panels can fill the grooves and be glued.
- Raised panels are 5/8"–3/4" thick with a tongue that fits the 1/4" groove (Woodcraft raises
  11/16" panels) ([Woodcraft][woodcraft]). Keep at least 1/4" of panel in each groove when it shrinks.
- Hinge cups go in the stile: a 2-1/4" stile takes a 35 mm cup with the cup centre 22.5 mm from the
  edge. Thinner than 16 mm at the cup (a thin panel at the edge) needs a thin-door hinge.

**Glass doors**: a frame rabbeted 3/8" for 1/8" glass, held with glazing strips; count glass
(156 lb/ft³) in the hinge weight.

## 6. Butt hinges (traditional inset)

Mortise both leaves into the door edge and the frame or case side, each mortise as deep as the leaf
is thick so the leaves close parallel with the door gap. 2-1/2" hinges for up to about 30" doors,
3" above that, at the same 3"–4" spacing (or the rail line on a frame-and-panel door). Set the
hinge knuckle just proud of the face so the door clears the frame. A butt hinge gives no adjustment:
fit the door to the opening with its even gap first.

## 7. Pulls

On the free stile, away from the hinge. **Uppers**: near the bottom corner; **base cabinets**:
near the top corner; 3"–4" in from the corner ([Amerock][amerock]). 8-32 machine screws, length =
door thickness + about 1/4" (1" for a 3/4" door) ([Amerock][amerock]).

## 8. Worked example (frameless pair)

A 30" × 30" frameless wall cabinet, 3/4" sides, top and bottom dadoed 1/2" in from the side ends
(so `e = 1-1/4"` at the top and bottom), 3/4" plywood doors, 1/8" reveals, Blum CLIP top 110° full
overlay:

```
opening       28-1/2" × 27-1/2" (between the sides; under the top to over the bottom)
door width    (30 − 2 × 1/8 − 1/8) ÷ 2 = 14-13/16"
door height   30 − 2 × 1/8 = 29-3/4"
overlay       3/4 − 1/8 = 5/8" = 15.9 mm on each side
hinge         11 + C − H = 15.9  →  C = 5 mm, H = 0 → 16 mm (±2)
cup centre    5 + 17.5 = 22.5 mm (7/8") from the hinge edge, 13 mm deep
hinges        about 8 lb, 29-3/4" tall → 2 per door, 3" from each end
min reveal    19 mm door, C = 5 → 0.9 mm; nothing hinged back to back
```

With 1/16" reveals the doors grow to 14-7/8" × 29-7/8", the overlay to 17.5 mm, and the Blum cup
moves to 6.5 mm.

## 9. Putting it in a plan

Declare every door opening in `doors` (see `plan-schema.md`). The model check finds the door
leaves in front of each opening and the hinges on their hinge edges, and fails what the hinge
cannot do: an overlay no cup distance and plate gives, a cup outside the hinge's range, a door too
thick, an inset hinge on an overlay door, too few hinges for the door's height and weight, an
inset door with less than the minimum reveal at its hinge edge, back-to-back doors closer than
twice it, a cup bore that is not 35 mm. It warns on uneven or oversize reveals, a pair gap outside
1/16"–1/8" (or under 4 mm on solid wood), hinges set too near or far from the ends, a face frame
with less than 1/4" showing, a solid panel with no room to swell, and a pull screw of the wrong
length. The page prints a **Door Breakout** sheet from the same numbers: each opening, each leaf's
size and how it was worked out, the edges, the hinge (maker, model, count, positions), the cup
bore and plate, the overlay check, the swing clearance, the construction and the pull.

### Custom hinges

```js
hinge: { like: 'blum-clip-top-110', name: 'Blum CLIP top 120°', k: 11, angle: 120 }
hinge: { kind: 'overlay', name: '…', k: 13, C: [3, 6], plates: [0, 2, 4], adj: 2, cup: 35, depth: 12, t: [16, 22] }
```

[blum-clip]: https://cdn.shopify.com/s/files/1/0709/8495/8225/files/Blum_110_Degree_Hinge_Placement.pdf
[blum-cat]: https://ahturf.com/content/CLIP%20top%20BLUMOTION.pdf
[blum-count]: https://ea.blum.com/en/number-of-hinges/
[hs-plate]: https://www.hardwaresource.com/mm5/graphics/00000001/moreInfo/701150_f_choosing_plate.pdf
[hs-b2b]: https://cdn.shopify.com/s/files/1/0709/8495/8225/files/701160_back_to_back_overlay_min_reveal.pdf
[salice]: https://res.cloudinary.com/hdi/image/upload/v1625611693/Suppliers/Salice/Documents/Brochures/Salice_CONCEALED_HINGES_FOR_THE_CABINET_usa_Rugby.pdf
[salice-inset]: https://cdn.shopify.com/s/files/1/0709/8495/8225/files/268706_frameless_inset_min_reveal.pdf
[grass]: https://cdn.shopify.com/s/files/1/0616/3624/7751/files/Grass_Tiomos_110.pdf
[hettich]: https://www.specifiedby.com/hettich/perfect-silent-system/hettich_Perfect-Silent-System_Brochures_Sensys-2015-HUK-14987-EN.pdf
[compact]: https://learn.cabinetdoor.store/en/articles/2195136
[compact-cp]: https://www.cabinetparts.com/p/blum-hinges-european-cabinet-hinges-BH39C358B24-p6626
[davelers]: https://davelers.com/32mm/Styles/Full_Overlay
[ww-frameless]: https://woodweb.com/knowledge_base/Frameless_Cabinet_Door_Dimensions.html
[ww-reveals]: https://woodweb.com/knowledge_base/116_Versus_18_Cabinet_Door_Reveals.html
[ww-face]: https://woodweb.com/knowledge_base/Cabinet_Face_Dimensions.html
[wsd-doors]: https://www.woodshopdiaries.com/how-to-determine-cabinet-door-size/
[woodcraft]: https://www.woodcraft.com/blogs/cabinetry-furniture-making/trouble-free-raised-panel-doors
[amerock]: https://manualmachine.com/amerock/knobpull/1441920-user-manual
