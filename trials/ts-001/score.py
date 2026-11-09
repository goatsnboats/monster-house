"""TS-001: weighted totals under the three locked weight sets, plus sensitivity."""
crit = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"]
scores = {  # 1-5 per criterion, evidence in TS-001 §5
    "A":  [4, 4, 3, 3, 5, 3, 4, 5],
    "A'": [3, 3, 3, 2, 3, 3, 4, 4],
    "B":  [3, 4, 4, 2, 4, 4, 4, 3],
    "C":  [2, 2, 5, 4, 3, 4, 3, 1],
    "D":  [3, 4, 4, 4, 4, 4, 4, 2],
}
weights = {
    "W1 Proposed":          [20, 20, 10, 10, 15, 5, 10, 10],
    "W2 More formality":    [15, 20, 20, 15, 10, 5, 10, 5],
    "W3 Readability first": [25, 20, 5, 5, 20, 5, 10, 10],
}
for name, w in weights.items():
    assert sum(w) == 100
    tot = {o: sum(a * b for a, b in zip(w, s)) for o, s in scores.items()}
    rank = sorted(tot, key=tot.get, reverse=True)
    lead, run = rank[0], rank[1]
    print(f"{name}: " + "  ".join(f"{o}={tot[o]}" for o in rank))
    gap = tot[lead] - tot[run]
    flips = []
    for i, c in enumerate(crit):
        d = scores[run][i] - scores[lead][i]
        if d > 0:
            flips.append((gap / d, c))
    flips.sort()
    print(f"   leader {lead} by {gap} over {run}; smallest single-weight increase to tie: "
          + (", ".join(f"{c} +{dw:.0f}" for dw, c in flips[:3]) if flips else "none (runner-up never better)"))
    # D vs A specifically (the owner's two candidates)
    gapda = tot["A"] - tot["D"]
    fl = sorted((gapda / (scores["D"][i] - scores["A"][i]), c) for i, c in enumerate(crit) if scores["D"][i] > scores["A"][i])
    print(f"   A minus D = {gapda}; D ties A with: " + ", ".join(f"{c} +{dw:.0f}" for dw, c in fl))
