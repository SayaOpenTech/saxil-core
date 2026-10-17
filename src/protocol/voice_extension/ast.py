"""Logical AST for SAXIL W2 (voice extension). Not a text language."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Ent:
    eid: int
    typ: str
    ref: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class Num:
    v: int | str
    unit: str | None = None


@dataclass(frozen=True)
class Date:
    y: int
    mo: int
    d: int


@dataclass(frozen=True)
class Time:
    h: int | None = None
    m: int | None = None
    rel: str | None = None
    weekday: str | None = None
    unit: str | None = None
    v: int | None = None


@dataclass(frozen=True)
class Cmp:
    op: str
    left: str
    right: Num | int | str


@dataclass(frozen=True)
class SemanticFrame:
    speaker: str
    act: str
    intent: str
    polarity: str
    action: str | None = None
    object: Ent | None = None
    attribute: Any = None
    time: Date | Time | None = None
    affect: str | None = None
    qtype: str | None = None
    request: str | None = None
    cond: Cmp | None = None
    known: tuple[Ent, ...] = field(default_factory=tuple)
    modality: str | None = None
    uncertainty: str | None = None

    def fact_count(self) -> int:
        n = 4  # speaker act intent polarity
        for x in (
            self.action,
            self.object,
            self.attribute,
            self.time,
            self.affect,
            self.qtype,
            self.request,
            self.cond,
            self.modality,
            self.uncertainty,
        ):
            if x not in (None, "", ()):
                n += 1
        n += len(self.known)
        return n


@dataclass(frozen=True)
class VUnit:
    op: str
    w: str | None = None
    v: int | str | None = None
    unit: str | None = None
    spoken: str | None = None
    mode: str | None = None
    y: int | None = None
    mo: int | None = None
    d: int | None = None
    h: int | None = None
    m: int | None = None
    rel: str | None = None
    weekday: str | None = None
    pause: str | None = None


@dataclass(frozen=True)
class VerbalUtt:
    utt_type: str
    units: tuple[VUnit, ...]

    def unit_count(self) -> int:
        return len(self.units)
