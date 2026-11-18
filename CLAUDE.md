# Project rules

- Read `DESIGN.md` before any UI task; its 19 rules are lessons from v1–v4, not preferences.
- Content that repeats or changes lives ONLY in `data/site.json`. Pages are generated: edit the data (or `tools/build.py` for markup), then run `python3 tools/build.py`. Never hand-edit the generated `.html` files.
- Code (identifiers, CSS classes, comments) in English; visible content in Spanish.
- Use only the CSS custom properties defined at the top of `assets/css/site.css`.
- Never invent prices, ages, testimonials, stats or offers. Unknown facts stay out (or as a visible placeholder on legal pages).
- Before shipping a change: axe-core with 0 violations (desktop + mobile, light + dark), no horizontal overflow at 320px, focus never hidden by the fixed bars, works without JS.
