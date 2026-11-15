# Technique

How patterned end-grain boards are built, and why the plan says what it says. Read before writing
advice the plan does not already give.

## The rules everything follows

1. **Machine every glue-up flat before the next one.** A face that goes into a joint has been planed,
   jointed or sanded since the last time glue touched it. This is why the board is built from small
   closed logs (triangles and rectangles): every face of them can be machined. Never design a
   glue-up whose outside is a zigzag or a V-groove; it cannot be cleaned and the next joint gaps.
2. **Few parts per glue-up.** Three or four bars into a log, two slices into a pair, pairs into a
   row, two or three rows at a time. Only square-edged strips (a checkerboard panel) go together
   many at once.
3. **One setting per dimension.** Every bar of a thickness through the planer in one session; every
   log through the sander at one setting. Parts that match each other matter more than parts that
   match the drawing.
4. **Rip over, machine to size.** The saw gets a bar within 1/32"; the planer or sanding sled makes
   it right.
5. **Test on scrap.** Three short bars dry-fitted in the cradle show a wrong tilt before good wood
   is cut.

## Milling

Acclimate a week. Joint a face and an edge, plane to the thickness in the material list. Straight
grain, quartersawn or rift where possible.

## Ripping bars

Blade tilt set with a digital angle gauge. Every bevel is cut with the work clamped to a **rip sled**,
the sliding rip jig with toggle clamps that the makers in the practice guide use. The sled is a
plywood base with a tall bridge across each end; the tilted blade saws the base into two decks and
the bridges hold them together. It runs against the rip fence, which stays on the side the blade
leans away from. The fence deck (between fence and blade) carries a locating fence in slotted holes
and three toggle clamps that close on a caul laid on the work. The landing deck (beyond the blade,
under its lean) catches what comes off. Nothing is ever loose on the saw table, and a bar is never
ripped between a tilted blade and the fence.

- Diamonds and parallelograms: rip square-edged strips first, blade square. On the sled bevel one
  edge, roll the strip over (same end leading) and bevel the other. One locating fence setting, found
  by test strips. The sawn faces are parallel: pack the bars side by side on a carrier and plane or
  sand to thickness.
- Trapezoids: square-edged strips again; bevel one edge, turn the strip end for end with the same
  face up, bevel the other. The bar sits wide face up under the caul. True the sawn faces in a V block.
- Triangles: a triangle leaves no flat for a clamp, so it is never the piece that is held. The cut
  is Vaughn McMillan's (Woodcraft Magazine, quilt-pattern board): bevel the edge of a wide board, turn
  it over, rip again, and the triangle comes away as the offcut on the open side of the blade. He runs
  a board at least 5" wide along the rip fence with a push block. The plan clamps the same wide blank
  to the fence deck and turns it end for end before every pass; the bar lands base down on the landing
  deck against a stop strip and rides out with the sled. The stop strip is the plan's own addition, so
  the plan says to prove it on scrap. Stop when the blank is 1-1/2" wide. True the sawn faces in a V block.
- Where a pattern can avoid triangle bars, avoid them. Tumbling blocks are built from hexagon logs of
  three diamond bars for that reason (see Hexagon logs).

The plan's sheet 03 draws the sled from the front for each bar and step 2 draws it from above.

## Hexagon logs (tumbling blocks)

How makers build the cube board (Tom Silva at This Old House; Degoose and lanwater on LumberJocks).
Three 60 degree diamond bars, one of each wood, are glued into a hexagon log held by painter's tape
wrapped round it every few inches. The log is not machined: scrape the glue and check it across the
flats. It is crosscut into pucks, the puck sides get a few strokes on 120 grit, and all the pucks are
glued in one session on a taped base, from the centre out, inside a frame of four straight boards
clamped both ways, with cauls over the top. Half pucks, sawn point to point, fill the ends of every
other row. Because nothing is machined after the bars, cut every bar at one saw and planer setting
(lanwater's second batch did not match his first), expect hairline gaps, and fill them with glue and
sanding dust before the last flattening pass, as Silva does.

## Triangle logs (60 degree patterns)

Glue and true in V blocks: two side pieces with 30 degree edges on a flat base, the V lined with
packing tape. The sides stop 3/16" under the top of the part, so they bear on nearly all of it and
the top stands proud for the caul or the sander; each size and height of part gets its own block
(`vblocks` in cbplan works them out). One side is glued and screwed down; the other is held by screws
in slotted holes, slack for gluing so a clamp across the block closes it on the parts, tight for
truing. Bars stack in flat layers, tip down; a taped caul on the flat top and clamps every 4 to 5
inches. A log that needs a second layer gets its first glue-up made and trued in its own smaller
block, then the upper bars are dry-stacked on it and eased until the stack closes.

True all three faces through a drum sander (or with a jack plane) in rounds: every log first face up,
then second, then third, the drum lowered a hair each round. About 0.01" a face. The block plus log
must pass the sander; a tall block gets a 1/4" base.

Four trued logs glue into a log of twice the side the same way (`levels` 2): fewer, larger slices.

Sizes after truing: a log of side L finishes L - 2*sqrt(3)*skim, a row loses 2*skim more across its
width. The plan scales the layout to those sizes and reports them, because the trim margins and the
finished size depend on them.

## Square logs (45 degree patterns)

Bands are glued in a band cradle (a base with a 45 degree undercut stop) and planed nested in pairs,
bevel to bevel, so no feather edge leads into the knives. Quarter logs are glued in corner cauls (two
L-shaped cauls) so clamps work from two directions. Two joints at right angles are never glued at
once: quarters into halves, halves into blocks, each jointed and planed square in between.

## Planks, rows, then the board

Rows are never assembled from loose slices. The trued logs, still long, are glued side by side into a
plank whose end is one row of the board; every crosscut of the plank is then a whole row. This is how
makers build repeating end-grain patterns, and it replaced this skill's earlier slice-by-slice rows,
which meant hundreds of small glue-ups.

`scripts/planks.py` groups the rows. Two rows share a plank when one is the other as cut, turned end
for end, turned over, or slid along by a few logs (the plank is then made a log or two wider, up to
`shop.max_crosscut`). A lattice that repeats every row or two needs one or two planks. A pattern with
no repeat from row to row needs a plank per row; the plan warns, and a different pattern or a
symmetric colouring is the fix. Decide plank by plank: a plank earns its glue-up only when its row
comes up again, as cut or as its mirror by turning. Sheet 05 states that count for each plank.

Gluing a plank: on a flat taped base, in sections of three or four logs, then sections to each other.
Triangle logs lie point down and point up in turn; a strip with a 30 degree bevel lies against the
leaning log at each side so the clamps bear square. Taped cauls are clamped down across the top. Every
log has a marked end and a reference face; sheet 05 draws the plank from the marked ends.

Truing a plank: both wide faces through the planer or drum sander, all planks at one setting. A plank
is long grain, so the planer is safe. A plank wider than the machine is built as two halves, each
trued, and joined last. This replaces truing the edges of end-grain rows.

Crosscutting: plank flat on the sled (edge strip between a leaning edge and the fence), hold-down,
stop block and a 1" spacer so the row is never trapped. Rows are cut 1/8" over finished thickness and
numbered on the sawn face as they come off. The last 2" of a plank is held and never cut.

Rows glue two or three at a time with cauls across both faces near the ends. Register by the log
corners, which meet corner to corner, and pencil lines drawn across the dry fit. The faces being glued
are the machined faces of the planks: long grain, one thin coat, moderate pressure.

The plank steps are this skill's own write-up of that practice and have not been built or read by a
critic yet. Tumbling blocks from hexagon logs is the exception: pucks cannot be made as planks.

## Flatten, then trim

Drum sander or router sled; never a thickness planer on end grain. Flatten first, then trim with a
backer and tape on the cut line, so trimming removes any snipe and chipped edges. Sand 80 to 220,
raising the grain before the last grit.

## Without a drum sander

The practice guide's rule is "planer while long grain; drum sander after". So:

- Bars and logs (long grain): a thickness planer can do what the drum sander does (the guide planes long-grain stock, but its makers sand triangle logs, so the V block in a planer is an adaptation to prove on a spare log), in the same V
  blocks and carriers, at 1/64" a pass. A helical head is the best tool for it.
- Rows on edge (cut across the grain): outside the guide's planer rule. First choice is the flat
  sanding board by hand. A helical-head planer is an adaptation with a known risk (the last slice
  breaks out): row in its carrier, scrap block taped behind the trailing end, 1/64" passes, test row first.
- The glued board (end grain): router sled, then random-orbit sander. Makers who put end grain through
  a planer add rails or a support block and still report tear-out and thrown boards; the plan never asks for it.

## Frame

A frame is end grain too. Plane a board to the frame width, crosscut blocks from it at the slice
length, stand them on end and glue them edge to edge into four strips. Glue the long strips to the
trimmed field, saw their ends flush, glue the end strips, saw flush, and flatten once more so frame
and field are in one plane. A long-grain frame splits the board.

## Finish and options

Ease edges (1/8" chamfer or round-over). Food-grade mineral oil to refusal, then oil-and-beeswax
board butter. Feet let the underside dry. Juice grooves in two light passes with a core-box bit.

## Wood movement

End-grain boards move across both face directions. Keep shrinkage figures within about 4 points
across the species, borders in end grain only (never a long-grain frame), and tell the owner to oil
both faces.
