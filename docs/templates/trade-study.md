# TS-NNN — <the question, in a few words>

> **Status:** Framing · **Date:** YYYY-MM-DD · **Decides:** <one line> · **ADR:** — · **Affects:** <requirements, studies, plan steps>

Status moves through `Framing` → `Awaiting weights` (Stop 1) → `Evaluating` →
`Recommended` (Stop 2) → `Decided (owner, YYYY-MM-DD, <where>)`.

## 1. Question
One sentence: what is being decided.

## 2. Context
- **What depends on it:** requirements, other studies, stage-plan steps.
- **Constraints and owner direction:** with dates.
- **Deadline:** when the answer is needed, and what waits for it.
- **Cost to reverse:** what changing course later would cost.

## 3. Criteria

### Gates (must pass)
| ID | Gate | How checked | Traces to |
|---|---|---|---|
| G1 | … | … | SYS-… |

### Weighted criteria
| ID | Criterion | Weight | How measured | 1 = | 3 = | 5 = |
|---|---|---|---|---|---|---|
| C1 | … | _proposed_ | … | … | … | … |

Weights total 100. The owner sets them at Stop 1.

## 4. Options

### Screened out
| Option | Reason |
|---|---|
| … | Fails G2: … |

### Shortlist
**A — <name>.** A short description of what choosing this means in practice.

## 5. Evidence
| # | Option | Criterion | Finding | Kind | Source |
|---|---|---|---|---|---|
| E1 | A | C1 | … | measured / documented / judgment | command and machine, or link (version, date checked) |

Trial code, if any: `trials/<slug>/`.

## 6. Scores
| Criterion | Weight | A | B | C |
|---|---|---|---|---|
| C1 | … | 3 (E1) | … | … |
| **Weighted total (max 500)** | 100 | … | … | … |

## 7. Sensitivity
The smallest single-weight change that makes the runner-up tie, whether the result is
close, and which gates passed only narrowly.

## 8. Recommendation
The option, its main risks, what would change the recommendation, and the cost of
reversing it.

## 9. Decision
*Open.* When decided: the option, the owner, the date and where they decided, plus any
requirement allocations it changes.

## Links
The ADR, related studies, requirements and trials.
