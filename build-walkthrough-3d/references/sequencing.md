# Choosing a build order

The walkthrough is only useful if it is the order the builder will really work in. Decide the order
as a woodworker would, then model it; never pick an order because it is easy to animate.

## Rules of thumb

1. **Sub-assemblies flat first.** Frames, face frames, drawer boxes, doors and laminated panels are
   glued up flat on the assembly table, then stood up or carried to the case. Show the first one
   piece by piece and the rest arriving whole ("Make three more frames the same way").
2. **Hold it before you join it.** Things that cannot stand on their own get a fixture: build stands
   or blocks at finished height, cheeks to keep a frame upright, a temporary brace across the tops.
   Model fixtures as `temp` bodies, and take them off in their own step once the piece holds itself.
3. **Square before it is locked.** Mention squaring at the step after which it can no longer be
   corrected (before the back goes on, before the glue sets on the rails).
4. **Inside before outside.** Anything that has to get in past something else goes in first: blocks
   inside a bay before the top, slides before drawer boxes, boxes before faces, the platform before
   the saw.
5. **Bottom up, back to front.** Rails and dividers stack up from the floor, each sitting on the one
   below; fillers that set a drawer opening go in before the divider above them.
6. **Machines and hardware last.** Tracks, tapes, stops and the machine itself go on once the
   surfaces they need are flat and finished.
7. **Every step is one action.** If the text needs "then" twice, it is two steps. Repeated identical
   parts (eight drawer boxes) are one step.

## Paths a person could do

- A part comes in from the side that is open at that moment: a rail between two frames slides in from
  the front or back, not down through a top rail that is already there.
- Long parts slide along their length into a channel; panels drop into a ledge from above.
- Turning something over or standing it up is a path of poses: lift clear of the table, turn,
  move over, lower. Give the legs `seg` weights so the turn is not rushed.
- Fixtures come off upward or outward through a gap that exists at that step; the check will say
  when they cannot.

When `verify.js` reports a collision, ask what the builder would do: change the direction, move the
step earlier or later, or split it. That is the point of the check: it finds the order problems that a
written plan hides ("the castor block cannot go in once the top is on").

## Step text

- Title: imperative, specific, under about 40 characters ("Set the 9″ fillers and the first divider").
- Text: one or two sentences with the numbers that matter at that step and the reason when it is not
  obvious. Use the plan's part names so the label in 3D matches the cut list.
- `sheet`: the drawing sheet the step comes from, so the builder can cross-check.
