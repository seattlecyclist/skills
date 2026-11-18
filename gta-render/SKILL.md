---
name: gta-render
description: Turn a photo of people (friends, a team, a family, a person and their dog) into bold, hand-painted open-world crime-game loading-screen poster art, the "GTA 6 / Vice City style" look, with a neon Miami sunset or any scene the user describes, keeping every face recognisable. Uses Google's Nano Banana Pro (GEMINI_API_KEY) and falls back to other Gemini image models, then OpenAI's image model (OPENAI_API_KEY). Use whenever the user asks to make a photo "GTA style", "Grand Theft Auto style", "Vice City style", "like a GTA loading screen", crime-game or video-game poster art, or attaches a photo and asks for that look.
---

# GTA render

Repaint a photo as video-game key art: thick outlines, painted cel shading, saturated sunset colour,
the group as the hero of a loading-screen poster. It is a style tribute, not a copy: no game logos,
titles or text, and nothing criminal.

```
photo + scene → pick preset or write scene → render 2 takes → look at them → pick, or adjust and re-run
```

| Path | What it is |
|---|---|
| `scripts/gta_render.py` | Photo + scene → poster art. Model chain, presets, guardrails, `--compare` sheet. |
| `examples/patio-friends/` | A fictional group photo (`photo.jpg`, AI-generated) and two Nano Banana Pro takes. |

**Needs** Python 3 (stdlib only; Pillow for `--compare`, auto aspect and format conversion) and one
key: `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) for Nano Banana, or `OPENAI_API_KEY`. If neither is set,
ask the user for a key or where it is stored, once. Never print a key. If `scripts/` is missing,
the skill is in `gta-render/` of https://github.com/seattlecyclist/skills.

## 1. Brief

From the user, take the **photo** and, if they give one, a **scene**. Infer the rest and say what
you chose:

| Preset | Setting |
|---|---|
| `miami-sunset` (default) | Neon beach city at dusk, palms, pastel art-deco hotels, pink and orange sky. |
| `neon-night` | Rain-slicked downtown, magenta and cyan neon, reflections. |
| `desert-highway` | Two-lane desert road at golden hour, mountains, huge low sun. |
| `beach-day` | Bright boardwalk, turquoise water, deep blue sky. |
| `hills-sunset` | Hillside overlook above a glowing city at sunset. |
| `keep` | The photo's own place, repainted in the same palette with a sunset sky. |

**Hero text** (optional): `--hero "Frame compliance has you covered"` paints the user's own line as
the poster headline, wallpaper style: big slanted brush-script or condensed lettering with a
pink-orange-violet sunset gradient, dark outline and neon glow. `--hero-position bottom` (default),
`top` or `left`. Keep it to the user's words, under about eight words; it is the only text allowed.

`--scene "..."` alone replaces the default setting; with another `--preset` it adds to it ("a
vintage convertible behind them", "their dog in sunglasses"). For a phone wallpaper use
`--aspect 9:16`; otherwise the aspect follows the photo.

## 2. Render

```bash
python3 scripts/gta_render.py photo.jpg out/poster.jpg --takes 2 --compare
python3 scripts/gta_render.py photo.jpg out/poster.jpg --hero "Frame compliance has you covered" --takes 3
python3 scripts/gta_render.py photo.jpg out/poster.jpg --preset neon-night --scene "an empty street in light rain" --aspect 9:16
```

Two takes in parallel, about 30 to 60 seconds and roughly $0.15 to $0.25 each on Nano Banana Pro at
2K. The script prints which model made each file. Model order:
`gemini-3-pro-image` → `gemini-3-pro-image-preview` → `gemini-3.1-flash-image` →
`gemini-3.1-flash-image-preview` → `gemini-2.5-flash-image` → OpenAI `gpt-image-1`. It moves on
when a model is missing (404), rate limited (429), refused, or returns no image. `--model ID` pins one.

## 3. Review before showing anyone

Open every take (and its `-compare.jpg`) and reject a take that:
- changes, adds, drops or merges a person, or makes anyone look older, heavier, thinner, a different
  ethnicity or caricatured, or adds accessories nobody wore (one test take put glasses on all five
  people). Faces are the whole point; this is the most common miss.
- misspells, drops or adds a word in the hero text, or covers a face with it. Read it letter by letter.
  With hero text, render 3 takes: the lettering style varies (brush caps vs script) and one usually misses.
- has readable text or a logo (hat and shirt lettering survives often), or any weapon or gang sign.
- is split into panels or has a border.
- still looks like a photo. The flash fallbacks (`gemini-2.5-flash-image` especially) often only
  swap the background and keep the photo look; if a take came from a fallback model, say so, and
  offer to re-run when Nano Banana Pro is back (a 429 clears in a minute; a spend cap needs the
  user at ai.studio/spend).

Deliver the best one or two, say which you prefer and why in one line, and offer one next step
(another preset, a wallpaper crop, a stronger comic look).

## Guardrails

These are in the prompt in the script and are not options:
- No logos, game titles, wordmarks, lettering or numbers beyond the user's own `--hero` line: a style
  tribute, not a copy of anyone's art or trade dress. Don't add a "GTA" or "VI" title even when asked;
  offer a headline in the user's own words instead.
- No weapons, gang signs or tattoos, drugs, money piles, police chases or crime scenes on real people.
  Decline a scene that asks for them and offer the same mood without them (a parked sports car,
  a rooftop at night, sunglasses and a sunset).
- Only photos the user took or has the people's OK to use. Never put real people's photos in a
  public repo or example; the example here is AI-generated.
