# FloraGuard design notes

## Colour token rationale and contrast check

Green communicates plant health and primary actions; rose pink is a secondary accent. Risk colours identify low, medium, and high conditions, but risk is also conveyed with an icon and visible label. Ratios below are calculated from the token values in `src/index.css`; WCAG AA requires 4.5:1 for normal text and 3:1 for large text and meaningful non-text controls.

| Foreground | Background | Contrast | Notes |
| --- | --- | ---: | --- |
| `#1F2933` | `#FAF8F5` | 13.92:1 | Light body text |
| `#5B6770` | `#FFFFFF` | 5.80:1 | Light muted text |
| `#FFFFFF` | `#1F6F4A` | 6.12:1 | Primary button label |
| `#1F6F4A` | `#E6F2EC` | 5.33:1 | Primary tint text |
| `#C2185B` | `#FCE7F0` | 4.99:1 | Light accent tint text |
| `#2E7D32` | `#E8F5E9` | 4.56:1 | Light low-risk badge |
| `#805000` | `#FFF8E1` | 6.45:1 | Medium-risk label and warning icon |
| `#C62828` | `#FFEBEE` | 4.92:1 | High-risk label |
| `#EAF1EC` | `#101714` | 15.84:1 | Dark body text |
| `#8FA89A` | `#18231E` | 6.34:1 | Dark muted text |
| `#2E9C6A` | `#18231E` | 4.68:1 | Dark primary |
| `#FFB300` | `#2B1E00` | 9.08:1 | Dark medium-risk label |
| `#07140D` | `#2E9C6A` | 5.45:1 | Dark primary button label |
| `#1B0505` | `#EF5350` | 5.63:1 | Dark danger button label |
| `#FF6BAD` | `#3B0D22` | 6.28:1 | Dark accent text |
| `#4CAF50` | `#0A2B0A` | 5.54:1 | Dark low-risk badge |
| `#EF5350` | `#2B0A0A` | 5.24:1 | Dark high-risk badge |

The map uses the original brighter medium-risk fill (`--risk-medium`) for polygon visibility; its text/icon uses the darker `--risk-medium-text`. Always re-check the actual text/background pair if token values, component states, or theme colors change.

## Typography

| Use | Typeface | Size |
| --- | --- | --- |
| Page and section headings | Plus Jakarta Sans, 700 | 1.5–2.5rem, responsive |
| Body copy | Inter, 400 | 1rem |
| Controls and labels | Inter, 500–600 | 0.875–1rem |
| Secondary metadata | Inter, 400–500 | 0.75–0.875rem |

## Spacing

Layouts use an 8px spacing rhythm where practical (8, 16, 24, 32, 48, 64px). Cards have 16px corners, controls use 12px corners, and touch targets are at least 44px where interaction requires it.

## Motion

Transitions are brief and restrained. Loading, toast, pulse, and page effects respect `prefers-reduced-motion` in the global stylesheet. Motion is supplementary feedback and never carries the only indication of state.

## Risk is never communicated by colour alone

`RiskBadge` includes a shield icon and a visible translated label in addition to colour. Map legends pair each risk swatch with an icon and label. Keep these cues together when changing or reusing risk displays.

## Low-confidence results

Photo results below 60% confidence show a warning and request agronomist review instead of presenting the possible problem as certain. The threshold is defined by `LOW_CONFIDENCE_THRESHOLD` in `src/config.js`.

## Map privacy

Grower and manager maps show only broad zone polygons and aggregates. Do not add farm names, exact farm coordinates, report-owner identities, or other identifying location details.

## Role-based navigation

The welcome screen stores the selected role (`grower` or `manager`) in `fg_role` and routes users to `/grower` or `/dashboard`. Grower screens use a compact bottom navigation; dashboard screens provide a desktop sidebar and mobile tab bar. Settings can clear the role and return to the role chooser.
