"""TS-002 weighted totals and sensitivity check.

Usage: python trials/ts-002/score.py [OUT_JSON]

Weights were set by the owner on 2026-11-08 (study §3). Scores and the evidence behind
each are in study §6.
"""

from __future__ import annotations

import json
import sys

CRITERIA = {  # id: (name, weight)
    "C1": ("Smoothness", 20),
    "C2": ("Path to Pi 5", 25),
    "C3": ("Look iteration", 15),
    "C4": ("Readable by the owner", 15),
    "C5": ("Fits the system", 15),
    "C6": ("Setup and deploy", 10),
}
SCORES = {
    "A": {"C1": 5, "C2": 4, "C3": 4, "C4": 4, "C5": 5, "C6": 3},
    "B": {"C1": 5, "C2": 3, "C3": 5, "C4": 3, "C5": 2, "C6": 3},
}
NAMES = {"A": "Python + moderngl + pygame-ce", "B": "Godot 4"}


def total(option: str, weights: dict[str, int]) -> int:
    return sum(weights[c] * SCORES[option][c] for c in weights)


def main() -> int:
    weights = {c: w for c, (_, w) in CRITERIA.items()}
    assert sum(weights.values()) == 100
    totals = {o: total(o, weights) for o in SCORES}
    leader, runner = sorted(totals, key=totals.get, reverse=True)
    gap = totals[leader] - totals[runner]

    print(f"Weighted totals (max 500): " + ", ".join(f"{o} {NAMES[o]} = {t}" for o, t in totals.items()))
    print(f"Leader {leader} by {gap}.\n")
    print("Single-weight sensitivity (other weights unchanged):")
    sens = {}
    for c, (name, w) in CRITERIA.items():
        diff = SCORES[runner][c] - SCORES[leader][c]   # runner's gain per weight point
        if diff == 0:
            verdict, needed = "no effect (equal scores)", None
        else:
            needed = w + gap / diff                     # weight at which they tie
            if 0 <= needed <= 100:
                verdict = f"tie at weight {needed:.0f} (change {needed - w:+.0f})"
            else:
                verdict = f"would need weight {needed:.0f}: impossible"
        sens[c] = {"name": name, "weight": w, "runner_minus_leader": diff, "tie_weight": needed, "verdict": verdict}
        print(f"  {c} {name:<22} weight {w:>2}: {verdict}")
    close = any(v["tie_weight"] is not None and 0 <= v["tie_weight"] <= 100 and abs(v["tie_weight"] - v["weight"]) <= 10
                for v in sens.values())
    print(f"\nClose (a change of 10 points or less flips it): {'yes' if close else 'no'}")

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump({"weights": weights, "criteria": {c: n for c, (n, _) in CRITERIA.items()},
                       "scores": SCORES, "names": NAMES, "totals": totals, "gap": gap,
                       "sensitivity": sens, "close": close}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
