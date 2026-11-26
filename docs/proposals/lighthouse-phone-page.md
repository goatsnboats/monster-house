# Proposal for lighthouse: publish the Monster House phone page on the tailnet

> **Status:** drafted by monster-house, for lighthouse to take into `changes/` · **Date:** 2026-11-26 · **Owner's choice:** option A, `tailscale serve` (2026-11-26) · **Requirements:** SYS-038 (as changed 2026-11-26), SHW-031 · **Interface:** [ICD-004](../interfaces/ICD-004-phone-page.md)

Monster House can't edit lighthouse's files, so this is the draft. Lighthouse copies it
into its `changes/` with the next number and adds the index row, its own way.

## What and why

Stage 0 Step 6 adds the monster's phone page: big buttons (great costume, burp, sing,
mute, sleep now, wake now) and the current mood. The brain serves it from its own
process on **127.0.0.1:8080**, as the machine rules require. The owner's phone has to
reach it. The owner chose (2026-11-26) to publish it the way gloss is published, with
`tailscale serve`: HTTPS, on the tailnet only, never Funnel. It then also works away
from home.

## Resources

- **Port:** 8080 on 127.0.0.1 (already planned in `docs/ports.md`), plus **HTTPS 8080 on
  the tailnet** for `tailscale serve`. Lighthouse picks the tailnet port if 8080 doesn't
  suit.
- **Tailscale serve** on `lighthouse.tail3dcfe9.ts.net` (1.104.7, no serve config today).
- No new units: in Stage 0 the brain runs by hand, so the page is there only while it
  runs. Nothing answers on the tailnet port when it isn't.

## Steps (as `gandriano`, root)

1. Publish it, in the background (it survives reboots):

   ```bash
   sudo tailscale serve --bg --https=8080 http://127.0.0.1:8080
   ```

   Why: makes `https://lighthouse.tail3dcfe9.ts.net:8080/` show the page on the owner's
   tailnet devices, with Tailscale's certificate. Check the flags against
   `tailscale serve --help` first (written for 1.104.7).

2. Check it:

   ```bash
   tailscale serve status
   ```

   Expected: one entry, `https://lighthouse.tail3dcfe9.ts.net:8080` → `http://127.0.0.1:8080`.

3. Update `docs/ports.md`: 8080 bound to 127.0.0.1, published to the tailnet as HTTPS
   8080 by `tailscale serve`, owner monster-house.

Alternative for lighthouse to weigh: the idea already in its list, `tailscale set
--operator=dev`, would let `dev` run step 1 itself. It is wider than this one need.

## Rollback

```bash
sudo tailscale serve --https=8080 off
```

## Risks

- **No login on the page.** Anyone on the tailnet can press the buttons. Today the tailnet
  is the owner's own devices. A Tailscale ACL can narrow it to the owner's phone later.
- **Away from home.** The page works wherever the phone is on Tailscale. That's what the
  owner chose; SYS-038 now says "only for the owner's devices on the tailnet".
- **Funnel stays off.** Nothing here is reachable from the internet.

## Impact on other projects

None: a new tailnet port on lighthouse, and a local port already listed for monster-house.
gloss is on the NAS, not here.
