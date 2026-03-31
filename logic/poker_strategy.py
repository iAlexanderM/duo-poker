from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Action(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE_SMALL = "raise_small"
    RAISE_VALUE = "raise_value"
    RAISE_LARGE = "raise_large"
    SHOVE = "shove"


class HandClass(str, Enum):
    PREMIUM = "premium"
    STRONG_VALUE = "strong_value"
    VALUE = "value"
    MARGINAL_SHOWDOWN = "marginal_showdown"
    WEAK_SHOWDOWN = "weak_showdown"
    DRAW = "draw"
    SEMIBLUFF = "semibluff"
    BLUFF = "bluff"


class BoardClass(str, Enum):
    DRY = "dry"
    WET = "wet"
    MONOTONE = "monotone"
    PAIRED = "paired"
    SCARY = "scary"


@dataclass(frozen=True)
class Decision:
    action: Action
    sizing_bb: float | None = None
    reason: str = ""
