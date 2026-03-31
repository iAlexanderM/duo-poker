from __future__ import annotations

from dataclasses import dataclass

from config import RANKS
from models.hand import Hand

_RANK_ORDER = {r: i for i, r in enumerate(RANKS)}


@dataclass(frozen=True)
class RangeProfile:
    label: str
    aggression: float
    tightness: float
    showdown_strength: float
    bluff_frequency: float


class RangeModel:
    def hero_open_range(self, position: str, num_players: int) -> RangeProfile:
        base = {
            "UTG": RangeProfile("UTG_open", 0.28, 0.78, 0.72, 0.18),
            "UTG+1": RangeProfile("UTG1_open", 0.32, 0.74, 0.70, 0.18),
            "LJ": RangeProfile("LJ_open", 0.38, 0.69, 0.67, 0.20),
            "HJ": RangeProfile("HJ_open", 0.45, 0.62, 0.62, 0.22),
            "CO": RangeProfile("CO_open", 0.58, 0.50, 0.56, 0.26),
            "BTN": RangeProfile("BTN_open", 0.68, 0.40, 0.50, 0.31),
            "SB": RangeProfile("SB_open", 0.52, 0.54, 0.60, 0.21),
            "BB": RangeProfile("BB_defend", 0.45, 0.58, 0.63, 0.15),
        }
        profile = base.get(position, base["BB"])
        if num_players >= 8:
            return RangeProfile(profile.label, profile.aggression - 0.03, min(0.95, profile.tightness + 0.04), profile.showdown_strength + 0.02, profile.bluff_frequency - 0.01)
        if num_players <= 5:
            return RangeProfile(profile.label, profile.aggression + 0.04, max(0.20, profile.tightness - 0.05), profile.showdown_strength - 0.02, profile.bluff_frequency + 0.03)
        return profile

    def estimate_villain_range(self, villain_type: str, street: str, board_texture: str, action: str | None, bet_to_call_bb: float, pot_size_bb: float) -> RangeProfile:
        base = {
            "tight": RangeProfile("tight", 0.26, 0.82, 0.78, 0.10),
            "standard": RangeProfile("standard", 0.42, 0.60, 0.62, 0.18),
            "loose": RangeProfile("loose", 0.56, 0.42, 0.54, 0.27),
            "fish": RangeProfile("fish", 0.38, 0.50, 0.40, 0.12),
        }
        p = base.get(villain_type, base["standard"])
        if action in ("raise", "allin"):
            if board_texture in ("wet", "scary"):
                p = RangeProfile(p.label, p.aggression - 0.04, min(0.95, p.tightness + 0.08), p.showdown_strength + 0.08, p.bluff_frequency - 0.03)
            else:
                p = RangeProfile(p.label, p.aggression + 0.02, p.tightness, p.showdown_strength + 0.03, p.bluff_frequency + 0.02)
        if action == "bet" and street in ("flop", "turn"):
            if bet_to_call_bb > 0 and pot_size_bb > 0:
                pot_ratio = bet_to_call_bb / pot_size_bb
                if pot_ratio >= 0.66:
                    p = RangeProfile(p.label, p.aggression - 0.03, min(0.95, p.tightness + 0.05), p.showdown_strength + 0.05, p.bluff_frequency - 0.02)
        return p

    def hero_strength_bucket(self, hand: Hand) -> float:
        r1, r2, suited = hand.get_normalized_ranks()
        i1, i2 = _RANK_ORDER[r1], _RANK_ORDER[r2]
        score = max(i1, i2) / 12.0
        if r1 == r2:
            score += 0.18
        if suited:
            score += 0.05
        if abs(i1 - i2) <= 1:
            score += 0.06
        if abs(i1 - i2) >= 4:
            score -= 0.05
        return min(1.0, max(0.0, score))

    def range_vs_range_edge(self, hero: RangeProfile, villain: RangeProfile, board_texture: str) -> float:
        edge = hero.showdown_strength - villain.showdown_strength
        edge += (hero.aggression - villain.aggression) * 0.25
        edge += (villain.tightness - hero.tightness) * 0.20
        if board_texture in ("wet", "scary"):
            edge -= 0.04 if villain.tightness > 0.7 else 0.01
        elif board_texture == "dry":
            edge += 0.03
        return edge

    def bluff_catch_adjustment(self, villain: RangeProfile, board_texture: str) -> float:
        base = villain.bluff_frequency
        if board_texture in ("wet", "scary"):
            base -= 0.04
        if villain.tightness > 0.7:
            base -= 0.05
        return max(0.0, min(0.5, base))
