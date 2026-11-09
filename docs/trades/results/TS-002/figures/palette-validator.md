# Palette check for the TS-002 charts

Run by the dataviz skill's `validate_palette.js` inside the chart pages (light mode, surface `#fcfcfb`), palette `#2a78d6, #eb6834` (A = categorical slot 1, B = slot 2).

| Check | Result | Detail |
|---|---|---|
| Lightness band | PASS | all 2 inside L 0.43–0.77 |
| Chroma floor | PASS | all 2 >= 0.1 |
| CVD separation | PASS | worst adjacent #eb6834↔#2a78d6 ΔE 24.7 (protan) · tritan 32.7 |
| Normal-vision floor | PASS | worst adjacent #eb6834↔#2a78d6 ΔE 33.6 (normal) |
| Contrast vs surface | PASS | all 2 >= 3:1 |
