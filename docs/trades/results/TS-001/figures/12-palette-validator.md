# Palette check for figure 12

Run by the dataviz skill's `validate_palette.js` inside the chart page (light mode, surface `#fcfcfb`), palette `#2a78d6, #eb6834, #1baf7a`.

| Check | Result | Detail |
|---|---|---|
| Lightness band | PASS | all 3 inside L 0.43–0.77 |
| Chroma floor | PASS | all 3 >= 0.1 |
| CVD separation | PASS | worst adjacent #1baf7a↔#eb6834 ΔE 9.2 (deutan) · tritan 32.7 |
| Normal-vision floor | PASS | worst adjacent #1baf7a↔#eb6834 ΔE 27.6 (normal) |
| Contrast vs surface | WARN | below 3:1 — relief required (visible labels or table view): [["#1baf7a",2.74]] |

The contrast WARN on aqua (#1baf7a, 2.74:1) is met with relief: each series has its own marker shape, there's a labeled legend, and the report gives the full score table.
