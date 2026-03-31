from __future__ import annotations

from dataclasses import dataclass

from logic.range_model import RangeModel, RangeProfile


@dataclass(frozen=True)
class LinePlan:
    cbet_freq: float
    check_freq: float
    raise_freq: float
    barrel_turn_freq: float
    barrel_river_freq: float
    pot_control_freq: float
    bluff_freq: float


class LineModel:
    def __init__(self):
        self.range_model = RangeModel()

    def flop_plan(self, hero: RangeProfile, villain: RangeProfile, board_state: str, initiative: bool) -> LinePlan:
        if initiative:
            if board_state == "dry":
                return LinePlan(0.68, 0.18, 0.08, 0.45, 0.26, 0.20, 0.22)
            if board_state == "paired":
                return LinePlan(0.42, 0.32, 0.14, 0.30, 0.16, 0.34, 0.12)
            if board_state in ("wet", "scary", "monotone"):
                return LinePlan(0.28, 0.44, 0.10, 0.22, 0.10, 0.52, 0.08)
        else:
            if board_state == "dry":
                return LinePlan(0.18, 0.56, 0.12, 0.18, 0.08, 0.50, 0.10)
            if board_state == "paired":
                return LinePlan(0.12, 0.60, 0.10, 0.14, 0.06, 0.58, 0.08)
            if board_state in ("wet", "scary", "monotone"):
                return LinePlan(0.08, 0.68, 0.08, 0.10, 0.04, 0.70, 0.05)
        return LinePlan(0.25, 0.50, 0.10, 0.20, 0.08, 0.45, 0.10)

    def turn_plan(self, board_state: str, hero_edge: float, initiative: bool) -> LinePlan:
        if initiative:
            if board_state == "dry":
                return LinePlan(0.55, 0.22, 0.10, 0.48, 0.24, 0.22, 0.18)
            if board_state == "paired":
                return LinePlan(0.34, 0.34, 0.12, 0.30, 0.16, 0.36, 0.10)
            if board_state in ("wet", "scary", "monotone"):
                return LinePlan(0.22, 0.50, 0.10, 0.18, 0.08, 0.54, 0.06)
        else:
            if board_state == "dry":
                return LinePlan(0.14, 0.60, 0.12, 0.16, 0.08, 0.54, 0.08)
            if board_state == "paired":
                return LinePlan(0.10, 0.64, 0.10, 0.12, 0.06, 0.62, 0.06)
            if board_state in ("wet", "scary", "monotone"):
                return LinePlan(0.06, 0.72, 0.06, 0.08, 0.04, 0.74, 0.04)
        return LinePlan(0.20, 0.52, 0.10, 0.14, 0.06, 0.48, 0.08)

    def river_plan(self, board_state: str, hero_edge: float, bluff_catch: float, initiative: bool) -> LinePlan:
        if initiative:
            if hero_edge >= 0.10:
                return LinePlan(0.50, 0.18, 0.06, 0.24, 0.18, 0.18, 0.20)
            if board_state in ("wet", "scary", "monotone"):
                return LinePlan(0.18, 0.58, 0.06, 0.10, 0.04, 0.66, 0.04)
            return LinePlan(0.30, 0.38, 0.08, 0.18, 0.08, 0.36, 0.10)
        if bluff_catch >= 0.20 and board_state in ("dry", "paired"):
            return LinePlan(0.10, 0.56, 0.10, 0.08, 0.04, 0.62, 0.08)
        if board_state in ("wet", "scary", "monotone"):
            return LinePlan(0.05, 0.74, 0.04, 0.04, 0.02, 0.78, 0.03)
        return LinePlan(0.12, 0.50, 0.08, 0.08, 0.04, 0.56, 0.06)
