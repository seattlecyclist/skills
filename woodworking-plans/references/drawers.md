# Drawers: sizing, slides, fronts and hardware

Read this for any plan with a drawer. A drawer is sized from three things, in this order:
**the opening, the slide, the front style.** Choose the slide before any box dimension is final,
because every box width, height and length comes from the slide's spec sheet. Then size the box,
then the front, then the pull. The model check (`drawers` in the plan, below) recomputes every
number here from the model and fails a box that does not fit its slide.

All sizes are inches unless marked; metric values are the maker's. Each slide row cites the
maker's sheet it came from. Retailer listings often misstate clearances: when a builder names a
slide that is not in the catalogue, find the maker's spec sheet and pass its numbers as a custom
slide (see "Custom slides").

## 1. Terms

| Symbol | Meaning |
|---|---|
| `W_o`, `H_o`, `D_o` | The **opening** the box runs in. Width between the faces the slides mount to (case sides, a divider, or blocking flush with the face-frame stiles). Height from the surface below the drawer to the one above it (case bottom, rail, web frame, divider). Depth from the front edge of the case (or the back face of the face frame) to the back. |
| `W_b`, `H_b`, `D_b` | The **box** outside width, height and length (front to back), without the applied front. |
| `t_s`, `t_f`, `t_bk`, `t_bot` | Actual thickness of box sides, box front, box back and bottom. Use the real stock: Baltic birch sold as 1/2" is 12 mm (0.472"), 5/8" is 15 mm (0.591"), 3/4" is 18 mm (0.709"), 1/4" is 6 mm (0.236"); most "1/4" plywood" is 7/32" or 5.2 mm. Caliper it. |
| `c` | Slide clearance per side: the gap between a box side and the opening face, which the slide fills. |
| `L` | Nominal slide length. For undermount slides, Blum and K&V call it NL, the drawer length. |
| `g` | Reveal: the gap between a front and its neighbour or the frame. |

## 2. Box construction

**Stock.** Sides 1/2" for most drawers, 5/8" for drawers over about 24" wide or heavy contents,
3/4" only for very heavy drawers or wood runners. Bottoms 1/4" plywood or tempered hardboard;
1/2" for wide or heavy drawers, and for the undermount bottoms that carry screws.
Solid-wood boxes: secondary woods (poplar, pine, soft maple) at 1/2"–5/8" sides, 3/4" fronts on
traditional inset drawers.

**Corner joints and the front/back length.** The box width `W_b` is fixed by the slide. The front
and back length then depends on the joint:

| Joint | Front / back length | Side length |
|---|---|---|
| Butt, brads/screws/pocket screws (front and back between the sides) | `W_b − 2·t_s` | `D_b` |
| Rabbet in the sides, depth `r` across the side's thickness | `W_b − 2·(t_s − r)` | `D_b` |
| Dado / tongue, front and back tongued into side dadoes `d` deep | `W_b − 2·(t_s − d)` | `D_b` |
| Locking rabbet (drawer lock bit), front tongue `d` into side | `W_b − 2·(t_s − d)` | `D_b` |
| Through dovetails or box joints | `W_b` | `D_b` |
| Half-blind dovetail front (lap `p`), through-dovetail back | front `W_b`, back `W_b` | `D_b − p`, where `p = t_f − socket depth` |
| Sides capture the front and back (pocket screws from outside the sides) | `W_b − 2·t_s` | `D_b` |

Pocket screws go in the outside faces of the box front and back, where the applied front and the
cabinet back hide them: 4 per front/back, no more than 6"–8" apart on wide boxes; 1-1/4" screws
in 1/2" stock, 1-1/2" in 3/4" ([Tom Builds Stuff][tbs]).

**The bottom.** A groove in the sides and front, the back either grooved too (captured bottom) or
ripped to sit on top of the bottom (slide-in bottom, screwed up into the back).

- Groove width = actual bottom thickness (snug, test on scrap). Depth 1/4", never more than half
  the side thickness. Groove at least 1/4" up from the bottom edge; 3/8"–1/2" for heavier boxes
  ([Tom Builds Stuff][tbs]). Undermount slides set it: the groove's lower edge is at the slide's
  bottom recess (Blum Tandem 13 mm, 1/2").
- Bottom panel = inside width `+ 2·(groove depth) − 1/16` by inside length `+ 2·(groove depth) − 1/16`
  (rounded down to 1/32): it drops in without bottoming in the grooves. Inside width = `W_b − 2·t_s`.
  With 1/4" deep grooves this is inside + 7/16"; [Tom Builds Stuff][tbs] uses inside + 3/8".
- Slide-in bottom: back height = `H_b − (groove top above the bottom edge)`.
- Solid-wood bottoms: grain runs **side to side** so the movement is front to back; the bottom
  is not glued, its front edge is bevelled or rabbeted into the groove, and a screw in a slot
  holds it to the back. Leave the bottom 1/8"–1/4" short of the back's outer face for the dry
  season.

**Slide screws must not land in the bottom groove or a dovetail.** Put the slide centreline on
solid side wood, usually the middle of the side or the maker's mounting line.

## 3. Slides

### 3.1 Side-mount ball-bearing slides

The box is narrower than the opening by two clearances. The window is narrow (+1/32", −0 on
every common slide), so the box width must be held to ±1/64":

```
W_b = W_o − 2·c*,  c* = c_min + (c_max − c_min)/2   (aim mid-window)
check: c_min ≤ (W_o − W_b)/2 ≤ c_max on each side
```

| Key | Slide | Clearance per side `c` | Body height | Min box height | Lengths | Load | Notes and source |
|---|---|---|---|---|---|---|---|
| `accuride-3832` | Accuride 3832 / 3832EC full extension | 0.500"–0.531" (12.7 +0.8/−0 mm) | 1.80" (45.7 mm) | 1-7/8" | 14"–28" by 2" (3832 classic from 10") | 100 lb | Box width must not exceed the slide length. Accuride recommends the box 1-1/16" narrower than the opening (17/32" per side, the middle of the window). Inset setback = front thickness + 1/8". #8 pan-head or 6 mm Euro screws, 32 mm system holes only. ([3832EC tech sheet][acc3832]) |
| `kv-8400` | Knape & Vogt 8400 full extension | 0.500"–0.530" (+.03/−0) | 1.79" (45.5 mm) | 2" | 8"–28" by 2" | 100 lb | Max drawer width 24". #7 × 1/2" pan-head screws. 8401/8402 rear brackets, 8404 face-frame bracket. ([K&V 8400 spec][kv8400]) |
| `accuride-3640` | Accuride 3640-A over-travel | 0.890"–0.920" (22.6 +0.8/−0 mm) | 2.09" (53.1 mm) | 2-3/4" | 12"–28" by 2" | 200 lb at 18" | Travel = length + 1" (over-travel, clears a countertop overhang). #10 flat-head or 6 mm Euro screws. ([3640-A quick ref][acc3640]) |
| `accuride-9301` | Accuride 9301 heavy duty | 0.750"–0.781" (19.1 +0.8/−0 mm) | 3.00" (76.2 mm) | 3-1/2" | 10"–36" by 2", 40"–60" | to 500 lb | Tool, file and pantry drawers. 1/4" or #10 screws. ([9301 data sheet][acc9301]) |
| `fulterer-fr5400` | Fulterer FR5400 heavy duty | 0.770"–0.790" (19.5–20 mm) | 3.00" (76.2 mm) | 4" | 12"–60" by 2" | 450 lb | Non-detachable: the box goes in with both slides on it. Screw every cabinet-member hole. ([Fulterer FR5400 spec][fr5400]) |
| `generic-half` | Generic 1/2" ball-bearing (Accuride 3832 class) | 0.500"–0.531" | 1.80" | 1-7/8" | 10"–28" by 2" | 75–100 lb | Use only when the builder has not chosen a slide; tell them to check their slide's sheet. |

**Height.** Side-mount slides need no particular top or bottom clearance, only room to get the
box in and to keep it off the case: at least 1/4" below a box resting over a case bottom or rail,
and 1/4"–3/4" above. Shop rules of thumb: box = opening − 1" when the opening is closed above and
below (1/4" under, 3/4" over, [Tom Builds Stuff][tbs]); 1/2" at floor and ceiling in a bank of
plywood drawers; box 1"–2" shorter than a framed opening ([Woodshop Diaries][wsd]).

**Length.** Pick the longest stock length that fits:

```
L ≤ D_o − s − t_inset − 1/4"     s = slide setback from the case front (1/8" typical; Accuride
                                   and Blum both use 1/8"), t_inset = front thickness on an inset
                                   drawer, else 0; 1/4" keeps the slide off the back
D_b ≥ L                          (the drawer member must lie on the box side; D_b = L usual)
```

Slides come in 2" steps (Accuride 3832, K&V 8400). An overlay drawer in a 24" deep base cabinet
takes a 22" slide; a 19" deep dresser takes 18" ([Woodshop Diaries][wsd]; [Tom Builds Stuff][tbs]).

**Face frames.** The slide mounts to the face of blocking (or a rear bracket) flush with the
inside edge of the stile, so `W_o` is the face-frame opening. Without blocking, a side-mount
slide needs rear brackets (K&V 8401/8402, Accuride rear mounting sockets) and a front bracket or
the stile itself. Accuride requires a 3/4" × 2" vertical mounting strip behind each 3832EC.

### 3.2 Undermount (concealed) slides

The runner sits under the box, inside the side's footprint, and hooks into a notch at the back and
a locking device under the front. The **inside** width is what the maker specifies; the slide
fixes the bottom recess and the box length.

```
inside width   W_in = W_o − k                        (k from the table)
box width      W_b  = W_in + 2·t_s                   (t_s within the slide's side range)
box length     D_b  = NL (Blum Tandem, K&V MuV+, Hettich Quadro);  NL − 10 mm (Blum Movento)
box height     H_b ≤ H_o − h_d                        (h_d from the table)
bottom recess  underside of the bottom ≥ r above the side's bottom edge
rear notch     at least 1-3/8" (35 mm) wide × 1/2" (13 mm) high at each back corner, plus the hook bore
cabinet depth  D_o ≥ D_min(NL)
```

| Key | Slide | `k` (opening − inside width) | Side thickness | Height deduct `h_d` | Bottom recess `r` | Lengths (NL) | Min inside cabinet depth | Load | Source |
|---|---|---|---|---|---|---|---|---|---|
| `blum-tandem-563h` | Blum Tandem plus Blumotion 563H | 42 mm (1-21/32") | 15/32"–5/8" (12–16 mm) | 13/16" (21 mm): 9/16" (14 mm) under the box, at least 9/32" (7 mm) over | 1/2" (13 mm) | 9", 12", 15", 18", 21" (Blum also lists to 30") | NL + 15/16" (557 mm for 21"; read from a hard-to-read table, confirm on the sheet) | 100 lb | [Blum 563H spec][blum563]; [Woodworker Express][wwx]; [Popular Woodworking][pw] |
| `blum-tandem-563f` | Blum Tandem 563F, 3/4" sides | 49 mm (1-15/16") | up to 3/4" (19 mm) | 25/32" (20 mm) | 1/2" (13 mm) | 9"–21" by 3" | as 563H | 100 lb | [Woodworker Express][wwx] |
| `blum-movento-760h` | Blum Movento 760H | 42 mm (1-21/32") | up to 5/8" (16 mm) | 13/16" (21 mm) | recess at least 12 mm high, at most 15 mm deep | check the catalogue | check the catalogue | check the catalogue | [Blum, Building a Movento drawer][blumMov]; box length NL − 10 mm |
| `kv-muv-plus` | Knape & Vogt MuV+ | 42 mm (1-5/8" by K&V's rounding) | 1/2"–5/8" | 13/16" (9/16" under, 1/4" over) | at most 1/2" | 9"–22" | about NL + 2" (K&V's chart pairs a 22" slide with a 24" cabinet) | 75 lb | [K&V MuV+ spec][kvmuv] |
| `kv-muv-plus-34` | Knape & Vogt MuV+34 | 50 mm (1-31/32") | 5/8"–3/4" | 13/16" | at most 1/2" | 9"–22" | about NL + 2" (K&V's chart pairs a 22" slide with a 24" cabinet) | 75 lb | [K&V MuV+ spec][kvmuv] |
| `hettich-quadro-iw21` | Hettich Quadro, installation width 21 | 42 mm (1-21/32") | 13 or 16 mm | 13/16" (20 mm) | 1/2" | 9", 12", 15", 18", 21" | 16-3/4" (15" NL), 19-3/4" (18"), 22-3/4" (21") frameless; about 3/8" more in a face frame | by model (25–40 kg) | [Hettich Quadro FAQ][quadro] |
| `hettich-quadro-iw25` | Hettich Quadro, installation width 25 | 50 mm (1-31/32") | 19 mm | 13/16" (20 mm) | 1/2" | as IW21 | as IW21 | by model (25–40 kg) | [Hettich Quadro FAQ][quadro] |

Outside-width shortcut for Blum Tandem 563H (`W_o − W_b`), from the 563H sheet: 5/8" sides
13/32" (10 mm), 19/32" sides 15/32" (12 mm), 9/16" sides 9/16" (14 mm), 1/2" sides 5/8" (16 mm),
15/32" (12 mm Baltic birch) sides 23/32" (18 mm). Popular Woodworking's shortcut for 1/2" sides:
front/back of a dovetailed box = opening − 5/8" ([Popular Woodworking][pw]).

**Common mistakes.** Undermount boxes are *not* "full opening width" (one popular guide says
so): the inside width is fixed and the sides fill the remaining 42 mm. Sides thicker than the
maximum hit the runner's front lip. A bottom flush with the side's bottom edge leaves nowhere for
the runner. Undermount box length is the slide's NL, not "whatever fits". Front setback on
frameless: 1/8" (3 mm); Hettich face-frame setback 1/32" (1 mm); inset fronts add the front
thickness (+3/32", 2.5 mm, Hettich).

**Width limits.** K&V MuV+: max drawer width = NL + 10", and no more than 28" when the box is
over 6" tall, 24" over 8", 21" over 10" ([K&V MuV+ spec][kvmuv]). Blum's locking devices need an
inside width of at least 6-11/16" (170 mm); Hettich's front clips 6-1/2" (165 mm).

### 3.3 Centre-mount slides

One runner under the middle of the box; the box sides ride on the case or frame.

| Key | Slide | Notes |
|---|---|---|
| `accuride-1029` | Accuride 1029, 3/4 extension, 35 lb | Lengths 13"–27". The box sides must extend 1/4" (6.4 mm) below the bottom; shim the cabinet member to suit (3/8" sides take a 1/8" shim). The back of the box may need a notch so the slide reaches the back. #8 pan-head screws. ([Accuride 1029][acc1029]) |
| `kv-1300` | Knape & Vogt 1300 class, 3/4 extension | Same pattern; light duty. |

Box width with a centre-mount: opening − 1/8" to 1/4" total (the sides guide on the opening, so
keep the play small), and a kicker above each side so the box doesn't tip open.

### 3.4 Wood runners (traditional fitted drawers)

The box slides on its sides on runners (or on a web frame), with kickers above and guides at the
sides. No hardware clearances; the fit is the clearance.

```
W_b = W_o − about 1/32" total, then plane to a sliding fit ("approximately 1/32", plane later
       for seasonal movement", [Fine Woodworking][fww])
H_b = H_o − seasonal allowance (front-to-top gap for the side's cross-grain growth)
       ΔH = H_b × C_T × ΔMC  (USDA Wood Handbook, tangential coefficient C_T per % moisture change)
       e.g. a 6" flat-sawn red oak side (C_T 0.00369) from 6% to 10% MC grows 6 × 0.00369 × 4 = 0.089",
       so fit it in winter with about 3/32" at the top.
D_b = D_o − 1/4" to 1/2" (stops set the closed position)
```

Side and front grain runs the length of the box, so the width barely moves; the height is what
grows. Use quartersawn or low-shrinkage secondary wood for sides; wax the runners. Drawer stops
glued to the runners set inset fronts flush.

## 4. Fronts

Fronts and reveals by cabinet style (`g` reveal, `O` overlay per edge):

| Style | Front width | Front height | Typical numbers |
|---|---|---|---|
| **Inset** (face frame or frameless) | `W_o − 2g` | `H_o − 2g` | g = 1/16"–3/32" commercial, 1/8" common home-shop ([Woodshop Diaries][wsd]); 1/32" on fitted wood-runner drawers. Slide setback = front thickness + 1/8" (Accuride). |
| **Overlay on a face frame** (half / standard) | `W_o + 2·O` | `H_o + O_top + O_bottom` | O = 1/2" typical on 1-1/2" stiles; leaves 1/2" of frame between neighbours. Equal fronts in a stack: split `H_o + O_top + O_bottom − (n−1)g` by n, round down to 1/16" ([Woodshop Diaries][wsd]). |
| **Full overlay, frameless** | `W_case − 2r` (end cabinet) or tile across a run with `g` between | stacked: `Σ F_h = H_case − r_top − r_bottom − (n−1)·g` | 32 mm system: 1.5 mm reveal per edge, 3 mm (1/8") between fronts; base cabinets at least 3 mm at the top ([32 mm full overlay][davelers]). Over a shared divider each front covers half the divider less g/2. |
| **Full overlay on a face frame** | `W_o + 2·O`, O ≈ stile width − g/2 | as above | 1-1/4"–1-3/8" overlay on 1-1/2" stiles. |
| **False front on a box** (overlay drawers) | as the style above | as above | The box has its own front; the applied front screws on from inside, 4 × #8 × 1" washer-head screws through 1/4" holes for ±1/16" adjustment. Screw length ≤ `t_box_front + t_front − 1/8"`. |

**Graduated drawers.** Box heights in a bank usually step by a constant 3/4"–1" or by a
ratio (for example 4:5:6:7 from the top). Fronts follow the boxes; reveals stay equal. Keep the
top drawer at least 3" of inside height.

**Box height inside its front (overlay).** Bottom box `≥ 1/4"` above the case bottom; the front
covers the box with the overlay; the box top sits at least the top clearance under the next rail.
A front taller than its box hides the gap; a box taller than its front's opening cannot close.

## 5. Pulls and handles

- **Placement.** Centre on the front width. Vertically: centred on fronts up to about 8"–10";
  on taller fronts, line them up across the bank (often centred on the top drawer's front) or put
  them in the upper third. Amerock's guide puts door pulls 3"–4" from the corner ([Amerock][amerock]).
  Fronts over about 24" wide take two pulls at 1/4–1/3 of the width from each end, or one long pull
  about 1/3 of the width.
- **Sizes.** Centre-to-centre 3" (the most common), 3-3/4" (96 mm), 5-1/16" (128 mm),
  6-5/16" (160 mm). Knobs one screw.
- **Screws.** 8-32 machine screws (M4 on metric pulls). Length = everything the screw passes
  through + about 1/4": 1" for a 3/4" front; 1-3/4" for a 3/4" false front on a 3/4" box front
  ([Amerock][amerock]). Clearance hole 11/64"–3/16".
- **Finger pulls / no pulls.** A 3/8"–5/8" relief routed under the front, or a 1/2"–3/4" shadow
  gap between rows; push-to-open hardware (Blum Tip-On) needs its own clearance behind the box.

## 6. Worked example (side mount)

A frameless 3/4" case, opening 22" wide, 6" high, 21-1/2" deep, full overlay front, Accuride 3832,
1/2" Baltic birch (0.472") sides, rabbeted 1/4" for the front and back, 1/4" (0.236") bottom.

```
slide length  L ≤ 21.5 − 0.125 − 0 − 0.25 = 21.125   → 20" slide
clearance     c* = 0.500 + 0.031/2 = 0.516"          → W_b = 22 − 2(0.516) = 20.969 = 20-31/32"
height        H_b = 6 − 0.25 − 0.75 = 5"             (≥ 1-7/8" minimum)
length        D_b = 20"
front/back    20.969 − 2(0.472 − 0.25) = 20.525 → 20-17/32"
groove        0.236" wide, 1/4" deep, 1/4" up
bottom        width  20.969 − 0.944 + 0.5 − 0.0625 = 20.462 → 20-7/16"
              length 20 − 0.944 + 0.5 − 0.0625 = 19.493 → 19-15/32"
slide line    centred on the box: 0.25 + 2.5 = 2-3/4" above the case bottom
```

Undermount, same opening, Blum Tandem 563H 21", 5/8" (16 mm, 0.630") sides:
`W_in = 22 − 1.654 = 20.346`, `W_b = 20.346 + 1.26 = 21.606 = 21-19/32"` (the sheet's shortcut:
22 − 13/32 = 21-19/32), `H_b ≤ 6 − 13/16 = 5-3/16"`, `D_b = 21"`, bottom recess 1/2", rear notches
1-3/8" × 1/2", cabinet needs at least 21-15/16" inside depth: this 21-1/2" case is too shallow, so
use the 18" runner.

## 7. Putting it in a plan

Declare every drawer opening in `drawers` (see `plan-schema.md`). The model check finds the box,
slide and front parts inside each opening and fails anything off spec: side clearance outside the
slide's window, an undermount box whose inside width is not `W_o − k`, sides too thick, a box too
tall or too long, a slide longer than the case allows, missing slides. The page prints a
**Drawer Breakout** sheet from the same numbers: each opening with its slide (maker, model,
length, clearances, mounting line and setback), box outside and inside sizes, each box part,
bottom groove and panel, front size with its reveals or overlay, and the pull with its screw.

[acc3832]: https://d1ffabcce73sv0.cloudfront.net/113/55/documents/ac_tech+sheet_3832ec_next-gen_v5_0523+2+2.pdf
[kv8400]: https://www.knapeandvogt.com/sites/default/files/OL2806_8400_Specs-1119.pdf
[acc3640]: https://cdn.shopify.com/s/files/1/0062/7892/files/3640a-quick-ref.pdf
[acc9301]: https://d26s8effnbilat.cloudfront.net/Files/product/18469/tab/11_9301-16-8.pdf
[fr5400]: https://wwhardware.com/media/installation/fr5400-specifications.pdf
[acc1029]: https://pdf.directindustry.com/pdf/accuride/1029/26400-756274.html
[blum563]: https://cdn.shopify.com/s/files/1/0709/8495/8225/files/Blum-Tandem-Plus-563H-Specs.pdf
[blumMov]: https://ea.blum.com/en/building-a-movento-drawer/
[wwx]: https://www.woodworkerexpress.com/blog/2025/03/how-to-install-blum-tandem-drawer-slides/
[pw]: https://popularwoodworking.com/editors-blog/sizing-parts-for-drawers-on-blum-tandem-slides
[kvmuv]: https://cdn.shopify.com/s/files/1/0062/7892/files/muv-spec-sheet.pdf
[quadro]: https://quikdrawers.com/Product_Instructions/Hettich_quadro_faq_install.pdf
[davelers]: https://davelers.com/32mm/Styles/Full_Overlay
[wsd]: https://www.woodshopdiaries.com/how-to-measure-and-size-drawers/
[tbs]: https://www.tombuildsstuff.com/2013/01/how-to-build-drawer-boxes.html
[fww]: https://www.finewoodworking.com/2021/12/10/make-and-fit-a-dovetailed-drawer
[amerock]: https://manualmachine.com/amerock/knobpull/1441920-user-manual
