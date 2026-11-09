# ICD-012 — Sequence and audio upload

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** SHW-038 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

How lip sequences (`.fseq`) and voice clips get from the desktop to Falcon Player before
the show (architecture §1, §5).

```yaml
id: ICD-012
title: Sequence and audio upload
status: skeleton
ends:
  - {component: xlights}
  - {component: falcon-player}
medium: Wi-Fi, FPP upload
```

## To be filled in
- **Method:** xLights' upload to FPP, or FPP's web page; checked against the installed FPP
  (TBD-015).
- **Naming:** one playlist per clip, same name as the audio and sequence (THM-006).
- **Source:** the theme folder's `audio/` and `sequences/` ([ICD-005](ICD-005-theme-folder.md)).
