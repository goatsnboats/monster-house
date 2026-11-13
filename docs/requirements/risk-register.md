# Risk register

> **Status:** Draft for the owner (SRR package, item 4) · **Updated:** 2026-11-12 · **Risks:** [risks.yaml](risks.yaml) · **Grid and table:** [trace.md](trace.md#risks)

What could stop the monster working as intended, how likely it is, how much it would
hurt, and how and by when each risk is retired. Likelihood and impact are proposals,
rated low, medium or high; the owner adjusts them.

## Rules

- **Every risk rated high** (likelihood or impact) has a plan and a gate it must be
  retired by: SRR, PDR or a CDR. The checker enforces it (SRR exit criterion 5).
- **Retiring** a risk usually means running a verification event (`VE-…`) or closing a
  TBD-NNN item; the risk names them, and the checker makes sure they exist.
- **Status:** `open`, `retired` (with how, in `notes`), or `accepted` (the owner chooses to
  live with it).
- **At each review** the register is updated: new risks added, ratings revised, retired
  ones marked.

## The highest risks today (medium likelihood, high impact)

| Risk | Retire by |
|---|---|
| RSK-001 The eye renderer may not reach 60 fps or full-screen on a real Pi 5 | CDR-1 |
| RSK-002 The eyes may be too dim at dusk against street lights | CDR-1 |
| RSK-004 The windows or floor may not fit the projector's throw distance | CDR-1 |
| RSK-006 The monster may not feel right | PDR |
| RSK-007 Porch Wi-Fi may be too weak for the radar and the lips | CDR-2 |
| RSK-011 Falcon Player may not share the porch Pi 5 with the brain and Mosquitto | CDR-3 |
| RSK-013 The voice content may not be ready in time | CDR-3 |

## Gaps the register exposed

- **No requirement says how bright or visible the eyes must be** (RSK-002). A system
  requirement such as "the eyes shall be clearly readable from the sidewalk at dusk",
  with a value to be found by test, may be worth adding at SRR. The owner's call.
