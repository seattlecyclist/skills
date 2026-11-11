# Setting recipes

Starting points for the room around the piece. Pick the closest, then adapt to what the user
described (style, colours, time of day, where the piece stands). Sizes in meters. Every recipe
assumes one window wall with a portal, scanned floor, and the hero piece at about 40 to 60% of the
frame width.

Fetch a starter asset set with `fetch_assets.py assets --list <setting>`.

## Bedroom (worked example: examples/walnut-bed)
- Room 4.4 x 5.6, ceiling 2.7. Bed headboard against the back wall, 2 to 5 cm off it.
- Floor: white oak planks; wool rug under the bed's lower two thirds (8 x 10 ft for a queen).
- Walls: warm white (0.70, 0.67, 0.62); an accent behind the bed in limewash or a deeper neutral.
- Dressing: `dress/bed.py` (mattress, duvet folded back, pillows, lumbar, throw). Nightstands with
  lamps on, a book stack, a vase; one large artwork centred over the bed.
- Light: low morning or late afternoon sun through a side window, sun elevation 20 to 30 degrees,
  bedside lamps on at 15 to 20 W.
- Camera: three-quarter view from the foot corner, eye height 0.95, 28 mm, f/5.6.

## Kitchen
- Room 4 x 5, ceiling 2.6 to 2.8. Cabinets and island are usually the plan itself.
- Counters: stone or quartz (`surface` with a marble or terrazzo scan, roughness 0.15 to 0.3, coat
  0.3), or butcher block (`planks` along the run, plank_w 0.04). Backsplash tile with grout (a tile
  scan at its real tile size).
- Hardware: brass, stainless or blackened steel (`metal`). Under-cabinet strip lights as thin
  emissive boxes, 3000 K.
- Dressing: a bowl of fruit or lemons, a cutting board, a stack of plates, a bottle of oil, a plant
  or cut branches in a jar, a linen towel on a bar. Not too many; three groups.
- Light: bright overcast or high sun from a window over the sink; a pendant pair over the island.
- Camera: from the end of the island at 1.2 to 1.4 eye height, 24 to 28 mm; or a straight-on
  elevation at 35 mm for cabinetry.

## Living room
- Room 5 x 6. Sofa or the hero piece facing the window light, a rug that both front legs sit on.
- Dressing: throw on the sofa arm, two or three cushions (`pillow` + `creases`), coffee-table books,
  a plant, a floor lamp.
- Light: soft side light, golden hour (sun elevation 10 to 20 degrees) for warmth.
- Camera: eye height 1.0 to 1.2, 28 mm, from a corner.

## Dining room
- Table centred under a pendant (emissive shade, 2700 K), chairs pulled out unevenly.
- Dressing: a runner (cloth sim), a bowl or vase, two place settings at most.
- Light: window behind or beside the table for rim light on the top's edge.
- Camera: eye height 1.2 to 1.4 looking slightly down at the top, 35 mm.

## Home office / study
- Desk against a window or a wall with shelving. Rug under the chair.
- Dressing: a laptop (a thin box with a dark screen), a lamp, a mug, a notebook, a plant.
- Light: daylight from the side, desk lamp on.

## Bathroom (vanities, cabinets)
- Small room, 2.4 x 3. Tile floor and wainscot, mirror over the vanity (glossy, roughness 0).
- Dressing: folded towels, a soap dish, a small plant. Light: overhead plus a window.

## Patio / outdoor
- No room: set `room` to null, put a floor plane of pavers or decking, and let the HDRI be the whole
  background (the camera sees it directly). A low fence or planters to close the view.
- Light: the HDRI's own sun, mid-afternoon. Camera at 1.4 to 1.6.

## Workshop
- Concrete floor (`surface`, brushed concrete), plywood or pegboard walls, a bench, sawdust is a
  bump-only noise on horizontal surfaces. Overhead fluorescent strips (emissive, 4000 K) plus a
  roll-up door as the window.
