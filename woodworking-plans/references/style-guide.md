# Style guide: the magazine plan

The reference is a classic woodworking-magazine plan PDF for a miter saw station: a seven-page
drawings supplement to a magazine article. It is dense, quiet, and entirely
in service of building the thing. The template reproduces its structure and conventions and adds
interactivity where paper falls short.

## What the reference does, page by page

1. **Introduction**: wordmark, red title, issue line, a full-width photo of the finished piece,
   then two columns of serif text on stock (plywood and lumber needed), species options and an
   unusual material (galvanized steel door facings, with where to source a sheet).
2. **Layout drawings for the parts with joinery**: the uprights' notch layout (side view), and the
   dado positions for each upright in face views, lettered A, B, C in red circles.
3. **Carcass exploded view + MATERIAL LIST** (green box, two columns, parts 1 to 39).
4. **Supporting views and hardware**: upright locations (front view), drawer divider notch layout
   (side view), web frame (top view), and the Hard-to-Find Hardware box: casters, T-track, slides,
   hinges, catches, pulls, grommets, dust fittings, each with quantity, catalog number and price.
5. **Drawers, doors and tray**: two more exploded views, each with its own material list box, plus
   details: tray side (inside view), door frame groove and tenon (front and end views).
6. and 7. **Cutting diagrams**: one per plywood thickness (3/4", 1/2", 1/4"), parts numbered in
   balloons on white sheets.

Conventions throughout:

- Parts numbered **continuously across sections** (1 to 55), in roughly build order; the same
  number in the list, the exploded view and the cutting diagram.
- Rows read `12  Top Edging, Long (2)  1/4" x 3/4" x 64-3/4"`: number, name, quantity in
  parentheses, then **T x W x L**, with stacked fractions and inch marks.
- An **asterisk** marks a dimension that depends on something outside the plan ("width will vary,
  depending on miter saw").
- Hardware that is a modeled part (casters, slides, pulls, T-track) is numbered in the material list
  like wood, with a description instead of dimensions.
- Drawings are **named by view**: Exploded View, Front View, Side View, Top View, Inside View, End
  View. Detail callouts note depth and placement in words ("1/4" deep").
- Every page has the same running line (publisher, copyright) and a page number.
- No build steps in the drawings supplement; the article carries them. Our page includes short steps
  because it stands alone.

## How the template maps it

| Reference | Template |
|---|---|
| White letter page, running footer: publication and issue (italic) left, copyright centre, folio right, mirrored on even pages | `.sheet` on a light ground; footer shows `meta.series` + `meta.date`, title + rev, and the page number, mirrored on even sheets |
| Page 1: wordmark top left, red title, bold issue line, italic deck, lead photo, two-column serif text with a red drop cap | Masthead: `meta.series` as a two-line condensed wordmark, title in red, date, subtitle; the 3D exploded view is the lead illustration; intro in two columns with a drop cap; What You'll Need in a green box in the column |
| Exploded view: hand-coloured parts with pen grain lines, black outlines, white numbered balloons, red lettered circles under the balloon for copies that differ (2 / A), "Carcass Exploded View" in bold italic | three.js exploded view: flat lit faces (tops paler, faces turned away lean amber), grain lines drawn in the shader along each part's grain, ink outlines, white balloons with plain numbers, red letters for `instances[].label`; explode slider, presets, hover, select, isolate, assembly steps |
| Each assembly's page: its full exploded view, with the MATERIAL LIST box for just that assembly below it, the art just overlapping the box | One Material List sheet per `section`: a still exploded view of that section (rendered from the same model, framed on it, balloons clickable), captioned "Bed Frame Exploded View", over its green box |
| MATERIAL LIST in a green-ruled box, two columns, `1 Bottom (1)  3/4" x 23-3/4" x 62-3/4"` with a black rule under every row | Same: green box, section and T x W x L heads, two columns (one on phones), material and the builder's note in light italic under the name |
| Hard-to-Find Hardware in a solid blue box, white bold italic, dotted leaders to the price | Same box; dotted leader runs to `source`; notes in light italic under the line |
| Part layouts: peach fill, thin outline, horizontal dimension text in a gap in the line, stacked fractions, balloon on the part, red "All 4 Uprights" | Auto part layouts with the same look: balloon on the face view, red "All n", (Face) and (Edge) views, chain dimensions |
| Front / side / top views titled in bold italic with "(Front View)" under it in light italic | "Overall Dimensions (Front View)" etc.; every figure title is set that way, with no frame around the drawing |
| Groove and tenon details | Authored `details` drawings (rect, poly, line, dim, text, callout) |
| Cutting diagrams per thickness: white sheets, peach parts, numbers in balloons, no hatching | Same, packed per thickness and material, plus a board-foot table |
| (in the article) steps | Building It: numbered run-in heads in two-column body text, each with "Show in 3D" |
| Letter pages, printed | "Printable PDF of these plans" link in the masthead: builds a letter-size PDF in the browser, each sheet on its own pages, breaking between drawings and boxes, controls hidden |
| Plywood cutting diagram with a red "First cut" line (another plan in the same style) | Every sheet numbers its breakdown in red: rips first (cut 1 heavy, labelled "First cut"), then crosscuts, then trims, as dashed red lines; face-grain arrows on sheet parts |
| Lettered section details | `view.sections`: Section A–A drawings with 45° ink hatching on the cut faces, and a heavy chain cutting-plane line with arrows and letters on the elevation |
| Taper jig layout drawn beside the parts | Shop Aids sheet: each jig's drawing beside its own small parts table, purpose and use |
| (full-size pattern sheets) | Full-Size Patterns sheet: patterns, part faces and story sticks at real size with a 1" check square; the PDF tiles them at 100% on letter pages with corner marks |
| (flat-pack instructions: hardware at 1:1, crossed-out wrong way) | Fasteners, Actual Size after the hardware box; red-ruled "Don't" panels with a ✕ under the step |
| — | Shop Cut List sheet: green Shopping List box, then every part sorted for the saw with rough and finished sizes and R / F tick boxes |
| — | Finishing Schedule box at the end of Building It; in / mm toggle beside the PDF link |
| — | Joinery sheet: every joint, what holds it, Show isolates it in 3D |
| — | Revisions & Review: adversarial review record and the live model check |

## Visual rules

Measured from the reference PDF (colours sampled from the pages, fonts from its font list).

- **Page.** White, in both themes; only the ground around the pages darkens. No title bands. A
  page with its own boxed heading (the material list) has no other heading; drawing pages have
  none at all, each figure carries its own title.
- **Type.** The reference uses Univers Condensed (bold, light, oblique) for every label, list
  and drawing title, Helvetica for balloon numbers and Century Old Style for running text. The
  template uses Roboto Condensed, Helvetica/Arial and Gelasio (Century as a local fallback). Figure
  titles are bold italic; the view name under them is light italic in parentheses.
- **Colour.** Ink `#231f20`. Part fill in 2D `#feecda`. Material list box: border `#00553c`, fill
  `#e9f2ec`. Hardware box `#185578` with white text. Title red `#9b282d`; part notes in red
  `#c42d3b`. Steel `#c5c2be`. In 3D, maple-like yellow `#f2e38a` (per-material colours in
  `materials`) shaded toward amber `#c98a3e`. Selection uses the hardware blue; review results
  use green, amber and red.
- **Balloons.** White circle, thin black ring, plain (not bold) number. Leaders are hairlines.
- **Leaders don't cross.** Lay balloons out so no two leader lines cross each other, on every
  drawing: the 3D view, the section plates, part layouts and authored details. It is a strong
  preference, not a hard rule: when a crowded view has no clean layout, one crossing is better than
  a balloon far from its part or on top of another. Automatic placement scores crossings as the
  worst thing after overlapping balloons, then swaps the balloons of any two leaders still crossing;
  render_check and `--validate` warn about what is left, and never fail on it.
- **Dimensions.** Thin lines, small filled arrowheads, extension lines. Text always reads
  horizontally, in a white gap in the line, with stacked fractions. All drawings are set at one
  text size on screen (about 13px), so a short slat and a long rail read the same.
- **Lists.** `x` between dimensions (`3/4" x 23-3/4" x 62-3/4"`), quantity in parentheses after
  the name, the part number in bold before it.

## Writing voice

Write like the magazine's technical editor: plain, specific, shop-tested.

- Intro: what the piece is, the one idea that makes it look the way it does, and how it goes
  together, in two short paragraphs.
- Steps: imperative, one operation each, with the reason when it isn't obvious ("Lay out the
  half-laps from the assembled post positions, not from the cut list"). Name parts with `{#id}`.
- Notes in the cut list: the one fact a builder needs at the saw ("Face-glue two 8/4 blanks").
- Joint notes: the sizes that matter (slot width, notch depth, tenon size).
- Never pad. No "beautiful", "stunning", "timeless".
- **New paperwork keeps the same voice.** Red stays reserved for identifying marks: cut numbers,
  section letters, "Don't". Hatching appears only on section cut faces, never on cutting diagrams.
  Grain arrows are thin ink-2 lines labelled *grain*, so they read as notes, not parts.
