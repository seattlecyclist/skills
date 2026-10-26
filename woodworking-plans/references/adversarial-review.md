# Adversarial review

The model check proves the pieces occupy the space they should and touch where they should. The
adversarial review proves the design is right: that each change does what was intended, that
everything it moved still fits and still carries load, and that the paperwork (cut list, hardware,
diagrams, steps) followed.

Run it on the first design (scope: everything) and on every change after that (scope: the change,
the parts it touches, and the parts those mate with).

## Procedure

1. **Freeze the inputs.** Run `node scripts/build_plan.js plan.js --check` and keep the output. A
   review of a plan that fails the check is wasted; fix errors first. Then run
   `node scripts/build_plan.js plan.js --review --base plan.prev.js` for the worksheet: steps 3 and
   6 below come pre-filled from it.
2. **List changes.** One id per requested change (`B1`, `B2` …). A first design is one change, `A1`.
3. **Map the blast radius** for each change (the worksheet lists all three, plus every part that
   moved since the base plan, flagging any that no change names):
   - *Touches*: parts whose dimensions, position or joinery the change edits.
   - *Mates*: every part joined to a touched part (from `joints`) or in contact with one (the check's
     contact list). A part that only moved, without changing size, still mates.
   - *Paperwork*: cut list rows, hardware lines, part layouts, details, steps, intro text, and the
     cutting diagram group that mention any of those parts.
4. **Attack.** Assume the change is wrong. For every touched and mating part, work through the
   checklist below and try to produce a failure: a number that doesn't add up, a joint that no
   longer engages, a load with no path, a step that can't be done in that order. Re-derive numbers
   from `PARAMS` by hand; don't trust the generator, that is what is under review.
5. **Fix and loop.** Fix failures in `PARAMS` or the generator, rerun the check, and re-review the
   lines the fix touched. Stop when every line passes, or is a `flag` the user must decide.
6. **Record** (format below). Evidence is numbers and part numbers, never "looks fine".

## Using a fresh reviewer

A reviewer that did not design the piece finds more. When a subagent tool is available, spawn one
with this prompt (fill the brackets), then verify each of its findings yourself before recording:

```
You are reviewing a woodworking plan change as a skeptical shop foreman. Your job is to find the
ways this change breaks the build. Assume it is wrong until you prove otherwise.

Plan source: <path to plan.js>    Model check output: <paste>    Review worksheet: <paste>
Change under review: <id and summary, and the user's words if any>
Previous revision's PARAMS: <paste, or "first design">

For each part the change touches, and each part joined to or touching those parts:
- Re-derive its dimensions by hand from PARAMS and compare with the cut list.
- Walk each joint it is in: does it still engage fully, with sane proportions
  (see references/joinery.md), and can it be cut and assembled in the order of the steps?
- Follow the load from the top surface to the floor through this part.
- Check wood movement, fastener lengths, hardware fit, and clearances to anything that moves
  (drawers, doors, a mattress, a person's legs).
- Check the paperwork: cut list, hardware list, part layouts, details, steps, intro text.

Report each check as: check | evidence (numbers, part numbers) | pass, fail, or flag.
Report failures first. Do not report style preferences. Do not invent problems.
```

## Checklist

Work through every heading for every touched or mating part. Skip a line only when it cannot apply
(no hardware, no moving parts) and say so in the record.

**Dimensions**
- Cut list T × W × L matches the derived numbers (the check confirms it matches the model; you confirm the model matches the intent).
- Overall size and any governing constraint (mattress, opening, appliance) still hold, with stated clearance.
- Stock: each thickness exists as rough lumber (finished + about 1/4"), and long or wide parts fit available boards or are marked as glue-ups.

**Joinery**, for each joint the part is in
- Still engages: tenons seated, laps fully overlap, slots match the thickness of what drops in.
- Proportions from `joinery.md`: tenon thickness, shoulder sizes, mortise walls, tower and cheek sizes, lap depth, dado depth.
- Glue surface is long grain to long grain where glue is the only thing holding it.
- Can be cut with the tools in the intro, and assembled in the step order (nothing has to go in sideways after its neighbour is glued). Check tool limits: a dado stack cuts about 2-1/2" deep at most, a table saw blade about 3", a 1/2" router bit about 1-1/4" per pass.
- Every fastener can be installed: its hole can be bored and its nut, washer and head can be reached once the neighbouring parts are in place. Locate each one against every part around it, not just the part it is in. (The castle bed's head-end barrel nuts first landed inside the corner post.)

**Connections and load path**
- Every load ends in bearing on wood or the floor, not in a screw in end grain or a thin feature.
- Knock-down hardware engages full-height, full-thickness wood (the bed's bolts stay out of the half-height lap).
- Nothing can hinge: two fasteners on one line act as a pivot.
- Racking: something resists it in both directions (aprons, a back, diagonal bracing, a deep joint).

**Movement and clearances**
- Wide solid parts (over about 6") can move across their width: no cross-grain glue, slotted screws or buttons where needed.
- Moving parts (drawers, doors, lids, slides) keep their clearances after the change.
- Anything the user puts in or on it (mattress, saw, books) still fits, and is located where it should be.

**Paperwork**
- Hardware list quantities and sizes (bolt lengths that pass through changed parts).
- Part layouts and authored details show the new numbers.
- Steps still describe a buildable order, and their text names the right parts and sizes. Every hole, bore and fastener in the plan has a step that makes it.
- Counterbores and plugs fit the washer and head and leave room for a socket.
- Intro text and any hard-coded numbers in notes.

## Record format

In the plan object:

```js
revisions: [{ rev: 'B', date: 'Oct 25 2026', summary: 'Stiffer side rails',
  changes: [{ id: 'B1', summary: 'Rails thickened from 1-1/4" to 1-1/2"', parts: ['2', '3'],
              reason: 'Why the change was made, in the user\'s terms.' }] }],
review: [{ rev: 'B', change: 'B1', verdict: 'pass', mates: ['1', '4', '5', '7', '8'],
  checks: [{ check: 'Post slots {#1} follow the rail', result: 'pass',
             evidence: 'Slot width is the rail thickness, so both slots went to 1-1/2". Towers are now 1" square, above the 7/8" minimum.' }] }]
```

- `result` per line: `pass` (checked, holds), `fixed` (failed, fixed in this revision), `flag` (open question for the user), `fail` (still broken).
- `verdict` per change is the worst line: `fail`, then `flag`, then `fixed`, then `pass`. Validation rejects a verdict that disagrees, a line still marked TODO, a change with no review entry, and any `fail` (never ship one).
- The mechanical checks (bores, fastener lengths, tool depths, counterbores) are now in the model check; the review still re-derives the numbers and covers what geometry can't: strength, load path, movement, order of assembly, paperwork.
- `{#id}` in any text renders as a clickable part chip.
- Keep earlier revisions' records. They are the plan's history.

Tell the user in chat what the review found and fixed in a sentence or two, and any `flag` as a
question.
