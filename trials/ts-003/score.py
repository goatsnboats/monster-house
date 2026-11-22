"""TS-003 weighted totals and sensitivity check.

Usage: python trials/ts-003/score.py [OUT_JSON]

Weights were set by the owner on 2026-11-22 (study §3). Scores and the evidence behind
each are in study §6.
"""

from __future__ import annotations

import json
import sys

CRITERIA = {  # id: (name, weight)
    "C1": ("One source, no drift", 35),
    "C2": ("Readable for the owner", 20),
    "C3": ("Catches mistakes", 10),
    "C4": ("Footprint on the Pi", 15),
    "C5": ("Dependency risk", 20),
}
SCORES = {
    "A": {"C1": 4, "C2": 5, "C3": 5, "C4": 5, "C5": 5},
    "B": {"C1": 3, "C2": 3, "C3": 5, "C4": 2, "C5": 2},
    "C": {"C1": 3, "C2": 3, "C3": 4, "C4": 4, "C5": 3},
    "D": {"C1": 5, "C2": 4, "C3": 5, "C4": 5, "C5": 5},
}
NAMES = {"A": "ICD-first, standard library", "B": "pydantic v2", "C": "msgspec", "D": "Generated from the ICDs"}


def total(option: str, weights: dict[str, int]) -> int:
    return sum(weights[c] * SCORES[option][c] for c in weights)


def main() -> int:
    weights = {c: w for c, (_, w) in CRITERIA.items()}
    assert sum(weights.values()) == 100
    totals = {o: total(o, weights) for o in SCORES}
    ranked = sorted(totals, key=totals.get, reverse=True)
    leader, runner = ranked[0], ranked[1]
    gap = totals[leader] - totals[runner]

    print("Weighted totals (max 500): " + ", ".join(f"{o} {NAMES[o]} = {totals[o]}" for o in ranked))
    print(f"Leader {leader} by {gap} over {runner}.\n")
    print(f"Single-weight sensitivity, {runner} against {leader} (other weights unchanged):")
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
        print(f"  {c} {name:<24} weight {w:>2}: {verdict}")
    close = any(v["tie_weight"] is not None and 0 <= v["tie_weight"] <= 100 and abs(v["tie_weight"] - v["weight"]) <= 10
                for v in sens.values())
    print(f"\nClose (a change of 10 points or less to one weight flips it): {'yes' if close else 'no'}")

    # Moving points from one criterion to another keeps the total at 100.
    print(f"\nShifting weight between two criteria ({runner} against {leader}):")
    shifts = []
    for give, (gname, gw) in CRITERIA.items():
        for take, (tname, tw) in CRITERIA.items():
            gain = SCORES[runner][take] - SCORES[leader][take] - (SCORES[runner][give] - SCORES[leader][give])
            if give != take and gain > 0 and gap / gain <= gw:
                shifts.append({"from": give, "to": take, "points": gap / gain})
    for s in sorted(shifts, key=lambda s: s["points"]):
        print(f"  move {s['points']:.1f} points from {s['from']} to {s['to']}: tie")

    # One score point: which single score change, by one point, would flip the leader?
    print("\nOne-point score changes that tie or flip the result:")
    flips = []
    for o in (leader, runner):
        for c in CRITERIA:
            for step in (-1, 1):
                s = SCORES[o][c] + step
                if 1 <= s <= 5:
                    SCORES[o][c] = s
                    new = {k: total(k, weights) for k in SCORES}
                    if new[leader] <= new[runner]:
                        what = "tie" if new[leader] == new[runner] else "flips"
                        flips.append(f"{o} {c} {s - step} -> {s}: {leader} {new[leader]}, {runner} {new[runner]} ({what})")
                    SCORES[o][c] = s - step
    for f in flips:
        print("  " + f)

    if len(sys.argv) > 1:
        with open(sys.argv[1], "w") as f:
            json.dump({"weights": weights, "criteria": {c: n for c, (n, _) in CRITERIA.items()},
                       "scores": SCORES, "names": NAMES, "totals": totals, "gap": gap,
                       "sensitivity": sens, "close": close, "shifts": shifts, "one_point_flips": flips},
                      f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
