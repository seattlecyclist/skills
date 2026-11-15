# Rules and repeat math

Two things live here: the rules that make the skill give the same plan every time, and the math that
finds what repeats in a board, so a part is made once and turned, never made again. The code is
`scripts/planks.py` (grouping rows into planks) and `scripts/repeats.py` (the analysis, the size
candidates and the variants page).

```bash
python3 scripts/repeats.py design.json                      # what repeats, then nearby sizes ranked
python3 scripts/repeats.py design.json --no-candidates      # the analysis only
python3 scripts/repeats.py --variants out.html a.json b.json   # every face one plank can make
```

## The rules (fixed, in this order)

1. **No chance anywhere.** No random numbers, no clock, no dependence on set or dictionary order.
   The same `design.json` gives a byte-identical `plan.json` and `plan.html`; `selftest.py` builds a
   board under two hash seeds and compares. If a change breaks that, the change is wrong.
2. **Parts are compared by shape and wood, never by name.** Two bars, logs or rows are the same part
   when their outlines and the area of each wood inside them match to 0.01 in. How a pattern
   generator happened to cut a shape into pieces does not matter.
3. **Names follow first use.** Bars, logs and planks are lettered and numbered in the order the board
   first needs them, taking the rows in order (R1 first) and each row from its left end. P1 is always
   the plank of row 1.
4. **A row joins the first plank it fits, trying the moves in a fixed order:** as cut, turned end for
   end, turned over like a page, rolled over. Within one move, an exact match beats a slide. The
   order prefers moves that keep the same face up, because a pencil arrow then reads the same on
   every row.
5. **A slide may widen a plank only up to `shop.max_crosscut`** (24 in). Past that the rows stay on
   separate planks and the plan says the limit kept them apart.
6. **A plank is worth making when it gives two or more rows.** Sheet 05 answers "Worth a plank?" for
   each one; a board where more than half the planks give a single row gets a warning.
7. **One spare row per plank** is added to the plank's length, plus the kerfs.
8. **A size change is chosen by a fixed ranking:** buildable first, then fewest one-off planks,
   fewest plank types, fewest log types, fewest log lengths to glue, then the size nearest the one
   asked for. `repeats.py` prints the ranking; take the top line unless the user's size matters more.
9. **Thresholds are numbers, not judgment:** bevel 45 degrees or less, four parts or fewer in a
   glue-up, six log types before a warning, 1/8 in of trim on every edge, Janka 900 or more.
10. **When two answers tie, the earlier row, the lower letter and the smaller turn win.**
11. **Rectangles first.** A 60 degree pattern is built from sandwich bars when a layout passes; logs
    are used only when `"build": "logs"` asks or no layout passes, and then the plan warns and says why.
12. **A bar layout passes by numbers:** every bar on the board a slice of one flat sandwich; bar at
    least 0.4 in on its narrow side (`min_sandwich_bar`); sandwich no thicker than
    `max_cut_height` x cos(tilt) less 1/32 in; at least two slabs from a sandwich as wide as the
    planer takes. **Among layouts that pass:** fewest sandwiches, then fewest bar kinds, then the
    largest bar, the taller row, the fewest bars, rows across before rows along.
13. **A sandwich is as wide as its slabs need and no wider,** in quarter inches, one board if that
    still gives three slabs, two boards edge-glued when one board wide would take more than four sandwiches of a kind. One spare slab in ten, at least one, per sandwich type.

## The moves and what each does

A row is one crosscut slice of a plank. It can go into the board four ways, and it can slide.

| Move | In the hand | On the face | Keeps the same face up |
|---|---|---|---|
| As cut | nothing | the row as drawn | yes |
| Slide | shift along its length | figure shifts sideways; half a repeat staggers like bricks, a third or quarter makes diagonals | yes |
| Turn end for end | half turn flat on the bench | rotated 180 degrees: leans reverse, top and bottom swap | yes |
| Roll over | underside up, top edge to bottom edge | mirrored top to bottom, so shapes meet their reflection at the seam | no |
| Turn over like a page | underside up, left end to right end | mirrored left to right | no |

Rolling and paging show the other face of the slice. On an end-grain board both faces are end grain,
so nothing is lost, but the pencil arrow is on the underside (drawn dashed). The four moves form a
closed set: any two done in a row equal one of the four, so no other orientation exists to try.

The same moves apply one level down. A log turned end for end in a plank shows its mirrored section;
a log rolled a third or a half turn shows its section rotated. A plan should say which, with a prime
on the letter only when the log is actually turned.

## The math

**Row period.** Write each row as the sequence of its logs, left to right, each log reduced to a key
(outline plus area of each wood). The period is the smallest k where every row j equals row j+k slid
along, tested up to half the row count. Period 1 means one plank makes the whole board (chevrons,
gems, notched cubes). No period means the rows never repeat as cut.

**Turns.** For each of the three turns, find the rows that become another row under it. If row i
turned is row j, the board has that symmetry about the line at (i+j)/2. A line that falls between two
rows (4.5) pairs every row; a line on a row (3) leaves the middle row without a partner, which is
where one-off planks come from.

**Plank types = orbits.** Join every pair of rows related by a slide or a turn. The groups that
result are the plank types, and their count is the least number of different glue-ups the board
needs. `planks` in the plan can be larger than `orbits` only when rule 5 kept rows apart.

**What to change when the count is high.**
- An odd row count with a symmetry line on a row: add or drop one row so the line falls between rows.
  Star Field at 7 rows needed 6 planks, 5 of them for one row each; at 6 rows it needs 3 planks, each
  used twice.
- A crop that starts off a symmetry line: move the size so the trim lands on one.
- Rows that never pair: turn the board a quarter turn and test again, the rows then run the other
  way through the lattice. `repeats.py` tries this for you.
- A colouring with no mirror: re-shade so one half mirrors the other (Ziggurat: 12 one-off planks
  became 6 planks used twice each).
- Still high: say so, and offer a pattern that repeats.

**Counts to report.** Rows per plank type (higher is better), planks cut for one row (should be 0),
log lengths glued (the real labour), widest plank (must fit the sled).

### The proof that a bar build makes the face

For a bar with glue lines at angle θ to its width, layers are intervals along the normal
n = (−sin θ, cos θ) measured from the bar's centre. `bars.layers_of` takes the pattern's pieces inside
the bar's rectangle, projects their corners on n, and requires exactly one wood in every interval
between consecutive projections; if two woods share an interval the stripes are not parallel and the
bar fails. φ = min(θ, 180 − θ). When φ < 45 the tilted rips are the bar's sides: blade tilt φ, slab
thickness the bar's width B, squared to the row height H. Otherwise tilt 90 − φ, slab H, squared to B.
A glue line at normal distance a meets the two sawn faces at (a ∓ (B/2) sin θ) / cos θ + H/2 from the
first squared edge (sides case), which is what the plan prints as the squaring marks.

`bars.verify` then forgets the pattern: it redraws every bar on the board from its type's layers
alone, turned as the plank and row turn it, clips each redrawn piece to the trim, and measures the
area where the pattern under it is a different wood. The check passes when that area is under
2/100,000 of the board plus 2/100,000 sq in per bar (rounding hairs). `selftest.py` swaps the woods of
one bar and requires the proof to fail.

## Finding new faces from one plank

`repeats.py --variants` takes each plank and draws every board it can make when all rows are that one
crosscut: the second row as cut or one of the three turns, and each row slid by 0, 1/2, 1/3 or 1/4 of
the plank's repeat. That is 16 recipes; faces that come out the same, also as seen from the other
side or end, are shown once. Each is scored by **colour carry**: the share of every row seam where
the same wood sits on both sides. High carry means figures run through seams into larger shapes
(rolling every other row always scores 100%: each row meets its own reflection). Low carry gives a
busier, broken face. The page is sorted by carry and each caption is the recipe in bench words.

Use it when the user wants something new from a pattern they like, or to offer an easier build: every
face on the page costs one plank. Rows slid by a third or quarter stop triangles meeting point to
point across the seam; that is sound to build, the seams are straight, but say it is a different look.

Not covered yet: turning individual logs inside the plank, and boards of two alternating planks.
The plank steps and this variants tool are a worked-out method, not yet checked by a builder.
