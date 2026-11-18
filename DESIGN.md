# DESIGN.md — Nadia Fitness Dance Studio (v5)

v5 takes the **page structure of a classic local activity-centre site** (the reference was blackfrogdivers.com, a dive centre also in Torrox Costa) and builds it on v4's data, generator and rules. Every rule below exists because something went wrong (or right) in v1–v4; the reason is written next to it. Keep this file under two pages.

## What v5 takes from the reference site

| Reference pattern | In v5 |
|---|---|
| Top bar (social icons) + big centred logo + menu bar | Same; only the menu bar is sticky. On mobile the top tiers hide and the bar carries logo, theme and burger |
| Full-width photo hero with a big caps headline | Photo full width, headline on a **solid dark box that overlaps the photo's foot** (no scrim, no faces covered) |
| "Choose your course" image tiles | **¿Para quién es la clase?**: 4 square tiles (Peques, Dance por niveles, Baile para adultos, Fitness) from `groups` in `site.json` |
| Centred caps section titles with a short rule | `.sec-head`, alternating paper / paper-alt sections |
| Team section | **La monitora** (photo in colour, Google rating) |
| Numbers band | Only numbers derived from the data: classes, sessions, groups, Google rating (rule 7) |
| Inner pages with title bar + breadcrumb | `.titlebar` with "Inicio / Página" |
| Dark footer with contact / hours columns | Contacto · Clases de lunes a viernes + horario de llamadas · Páginas |

Left out on purpose: the contact form on the home page (it lives on Contacto), image sliders, shop, weather.

## What the site is for

A parent or an adult in Torrox Costa wants to **find a class that fits who it is for and when they are free, then phone (or WhatsApp) to reserve a place.** Booking is by phone, so the phone number is the main call to action everywhere.

Home order: hero → ¿Para quién es la clase? (tiles) → En el estudio (facts, steps, "Hoy en el estudio") → Horario de la semana → La monitora → numbers → pink phone block. *Why:* practical info first, trust (Nadia, 5,0 ★) right before the decision.

## Direction

**A familiar local-business layout with the brand's energy.** Light pages with dark header/footer bands (the logo is drawn for black), condensed caps headings, the logo's pink used boldly in a few places, photos in colour. Kept from v4: the live **"Hoy en el estudio"** board and the **pink phone block** (the one big pink area per page).

## Tokens

| | Light | Dark | Notes |
|---|---|---|---|
| `--paper` | `#FBF9F6` | `#17130F` | never pure black/white (v1's `#050505` "quemaba los ojos") |
| `--paper-alt` | `#F1EDE8` | `#201A15` | alternating sections, title bars |
| `--ink` | `#1A1512` | `#F3EEE6` | 16:1 |
| `--muted` | `#5B524B` | `#A89E93` | ≥ 6.4:1 on both papers |
| `--rule` | `#D9D1C5` | `#3A322C` | decorative only |
| `--pink` | `#C2006A` | `#FF5AA8` | fills, big type; white on it 6.0:1 / ink on it 6.4:1 |
| `--pink-text` | `#AE005E` | `#FF5AA8` | small pink text 6.2:1 |
| `--band` | `#16120F` | `#16120F` | header, numbers band and footer are always dark: the logo is drawn for black |
| `--edge` | transparent | `#3A322C` | outlines dark blocks (tiles, numbers, footer) on a dark page |

Type: **Barlow Condensed 800** for display (the brand's condensed sport type), italic only for one accent word per heading; **Instrument Sans** for text (17px/1.6, ≤ 65ch).

## Rules (each one learnt the hard way)

1. **No glows, gradients, halos or neon shadows.** v1 felt "busy" and "AI-made" because of them.
2. **One filled pink element per area.** In v1 nobody could tell "qué es botón y qué no". Labels look like text, buttons look like buttons, only real buttons are filled.
3. **No small uppercase labels above headings** and no pill above the hero — an "AI" tell. Section numbers (01–04) are fine: they are the programme's structure.
4. **Display line-height ≥ 1.05** on anything that can wrap. Spanish capitals carry accents (JÓVENES, MIÉRCOLES, ¿) and at 0.9 they collide with the line above.
5. **Photos in colour.** A grayscale portrait next to a big name "da vibes de que ya está con San Pedro".
6. **No minors in photos without written consent.** Crop above the audience; never commit the originals.
7. **Never invent content**: no prices, ages, testimonials, stats, or a "free trial" ("Ven a probar" implied one — use "Contacta").
8. **Grids must fill their rows.** 7 classes = 4 dance + 3 fitness, so they are two lists, not a 4+3 grid with a hole.
9. **Baile vs fitness never by colour alone**: dance = filled dot / solid rule, fitness = ring / dashed rule.
10. **Links inside text are underlined.** Colour alone is not enough (WCAG 1.4.1).
11. **Reserve space for fixed bars**: `scroll-padding` top (sticky header) and bottom (mobile call bar) so focus is never hidden (WCAG 2.4.11).
12. **Grid columns are `minmax(0, 1fr)`**, never bare `1fr`: a no-wrap row inside a `1fr` column made v2 overflow 590px on phones.
13. **Content works without JavaScript.** Pages are static HTML generated from one data file; JS only adds filters, tabs, the "Hoy" board, call status, theme and the burger. Without JS the burger is replaced by plain links.
14. **Animations stop**: the "live" dot pulses twice, then stays still (WCAG 2.2.2); respect `prefers-reduced-motion`.
15. **404 uses absolute site paths** (GitHub Pages serves it at any URL).
16. **Text never sits on a photo without a solid background**, and the box goes below the faces (v5 hero: it overlaps only the photo's foot).
17. **Numbers bands show only facts computed from `site.json`** (v5): no "years of experience" or "happy students" until the client gives real figures. Two equal numbers in a row read as filler (sessions = hours was dropped).
18. **Tiles that link are links on their title**, stretched over the tile, with an underlined title (rule 10) and a visible focus ring around the whole tile.
19. **Focused fields scroll clear of the mobile call bar** (site.js): browsers leave a half-visible field under a fixed bar.

## Single source of truth

`data/site.json` holds everything that repeats or changes: classes, sessions, phone, WhatsApp, address, geo, call hours, rating, social links, season, legal owner data, photos. `tools/build.py` generates every page, the sitemap, the timetable share image, the class placeholders and the group tiles (photo crop, or a generated dark tile when there is no usable photo — no minors, rule 6) from it. Never hand-edit generated HTML.
