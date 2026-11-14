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
- Triangles: a triangle leaves no flat for a clamp, so the wide blank is clamped to the fence deck
  and turned over end for end before every pass. The bar comes off base down on the landing deck,
  between a stop strip and the blade, and rides with the sled. Stop when the blank is 1-1/2" wide.
  True the sawn faces in a V block.

The plan's sheet 03 draws the sled from the front for each bar and step 2 draws it from above.

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

## Crosscutting slices

Every log has a marked end and a reference face (the face under the caul), pencilled on the end grain
when it comes out of the block. Crosscut sled with a base no thicker than 1/2", a stop block and a 1"
spacer: slide the log to the spacer, clamp, remove the spacer, cut, so the slice is never trapped.
Triangle logs lie reference face down between two 30 degree strips that stop short of the blade's
path. Hold the slice with a push stick through the cut, push the sled on past the blade and lift the
slice away before pulling back. As each slice comes off, pencil a short line on its sawn face along the
edge that lay on the sled: sheet 05 draws that line in every slice. No crayon or wax on glue faces.
The last 2" of a log is held and never sliced. A 10" saw clears about 3-1/8": a log on a 1/2" sled base
can be 2-5/8" tall. Slices are cut 1/8" over finished thickness.

## Rows, then the board

Triangular slices glue in pairs into diamonds, then pairs into a row in the row jig: a fixed fence, a
cleat, and between them a loose fence sawn into short blocks, one per slice that has its base on that
side, each with its own wedge. One wedge moves one slice. End blocks (a spare slice cut in half) turn
the slanted ends into square faces for the clamp along the row. The faces being glued are the trued
sides of the logs: long grain, one thin coat on one face, moderate pressure. Do not size these faces
as if they were end grain.

Every row is trued: on edge in a carrier under the drum sander, both edges, every row at the same
setting. Never the jointer or planer: the knives meet the fibres end-on.

Rows glue two or three at a time with cauls across both faces near the ends. Register by the slice
corners, which meet corner to corner, and pencil lines drawn across the dry fit.

## Flatten, then trim

Drum sander or router sled; never a thickness planer on end grain. Flatten first, then trim with a
backer and tape on the cut line, so trimming removes any snipe and chipped edges. Sand 80 to 220,
raising the grain before the last grit.

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
