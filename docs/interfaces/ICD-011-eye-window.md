# ICD-011 — Eye pod in the window

> **Status:** Skeleton · **Updated:** 2026-11-15 · **Requirements:** EYE-021 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

How each eye pod fits a bedroom window and the floor behind it, without changing the
house, and keeps light out of the room (SYS-035, SYS-044, SYS-045).

```yaml
id: ICD-011
title: Eye pod in the window
status: skeleton
ends:
  - {component: eye-screen}
  - {component: eye-mask}
  - {component: eye-shroud}
  - {component: eye-stand}
  - {external: house}
medium: Mechanical, optical
```

## Measured (owner, 2026-11-15, approximate)

Both windows have permanent blinds that cover the top 6 in (0.15 m) of the glass, so the
usable glass is 48 in tall, not 54 in.

| | Left (small) | Right (large) |
|---|---|---|
| Glass, width × height | 27 × 54 in | 36 × 54 in |
| **Usable glass, below the blinds** | **27 × 48 in (0.686 × 1.219 m)**, exactly 9:16 | **36 × 48 in (0.914 × 1.219 m)**, 3:4 |
| Fixed divider | None reported | Large vertical divider about in the middle; width TBD-006 |
| Sill height above the floor | about 2 ft (0.6 m) | about 2 ft (0.6 m) |
| Floor space behind | TBD-006 | about 10 ft (3 m), a bedroom with a bed |

What follows from these numbers (AAXA P400 class, 0.7:1 throw, 16:9; TBD-012):

- **Left, on its side:** a 27 × 48 in image fills the usable glass exactly, from about
  34 in (0.85 m) back.
- **Right, on its side:** a 16:9 image can't fill 3:4. To cover the full 36 in width the
  image is 36 × 64 in from about 45 in (1.14 m) back; the extra 8 in above and below falls
  on the frame and shroud and is drawn black. That spreads the light over about 1.8× the
  area of the left image, so this eye is about 56% as bright (match with `brightness`).
  Alternatives: a 27 in wide image from 34 in back, or a 4:3 projector (TBD-004, TBD-005).
- **Lens height:** level with the middle of the usable glass, about 4 ft (1.2 m) above
  the floor, so the image isn't keystoned.

## To be filled in
- **Still to measure:** width of the right window's divider, and the floor space behind
  the left window (TBD-006).
- **Screen:** cut to the glass; hung with a tension rod or removable hooks.
- **Window grids:** embrace them or remove them for the season (TBD-009). The right
  window's center divider looks fixed, so it is probably embraced.
- **Projector orientation:** flat or on its side (TBD-005, TBD-017); distance about
  0.7 × the image's long side (AAXA P400 class, TBD-012).
- **Shroud:** blackout fabric on a light frame from the projector to the window frame.
