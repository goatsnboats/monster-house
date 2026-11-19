"""The eye's expressions: each one is just five numbers (EYE-002).

Values from the table in docs/architecture.md §2, which came from
docs/reference/eye-sketch.html:

    open   how far the upper lid is open (1 = normal, above 1 = wide, 0 = shut)
    low    how far the lower lid rises (0 = not at all)
    curve  how much the lower lid smiles (0 = flat, 1 = full smile)
    pupil  pupil size (1 = normal, bigger = excited, smaller = surprised)
    spark  how strongly the "great costume" sparkles show (0-1)
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class Expression:
    open: float
    low: float
    curve: float
    pupil: float
    spark: float

    def blend(self, other: "Expression", t: float) -> "Expression":
        """The expression a fraction t (0-1) of the way from this one to `other`."""
        return Expression(*(getattr(self, f.name) + (getattr(other, f.name) - getattr(self, f.name)) * t
                            for f in fields(self)))


EXPRESSIONS: dict[str, Expression] = {
    "neutral":   Expression(open=1.0,  low=0.0,  curve=0.0, pupil=1.0,  spark=0.0),
    "happy":     Expression(open=0.9,  low=0.38, curve=1.0, pupil=1.15, spark=0.0),
    "sparkle":   Expression(open=0.95, low=0.3,  curve=1.0, pupil=1.3,  spark=1.0),
    "surprised": Expression(open=1.15, low=0.0,  curve=0.0, pupil=0.65, spark=0.0),
    "sleepy":    Expression(open=0.42, low=0.08, curve=0.0, pupil=0.9,  spark=0.0),
    "asleep":    Expression(open=0.0,  low=0.05, curve=0.0, pupil=1.0,  spark=0.0),
}
