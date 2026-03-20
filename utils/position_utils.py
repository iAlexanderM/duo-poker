# utils.py
from constants import PREFLOP_ORDER, POSTFLOP_ORDER


def _postflop_acting_order(positions: list[str]) -> list[str]:
    """Порядок ходов на постфлопе; в HU первым ходит BB, затем SB."""
    if len(positions) == 2 and set(positions) == {"SB", "BB"}:
        return ["BB", "SB"]
    return POSTFLOP_ORDER


def _street_order(stage: str, positions: list[str]) -> list[str]:
    from constants import PREFLOP_ORDER
    full = PREFLOP_ORDER if stage == "preflop" else _postflop_acting_order(positions)
    return [p for p in full if p in positions]


def _button_centric_order(n: int) -> list[str]:
    """
    Порядок мест по часовой стрелке от баттона (баттон первый).
    При сдвиге баттона на одно место по столу твоя позиция в списке
    смещается на один шаг «к баттону»: BB→SB, SB→BTN, BTN→CO, …, UTG→BB.
    """
    if n == 2:
        return ["SB", "BB"]
    if n == 3:
        return ["BTN", "SB", "BB"]
    if n == 4:
        return ["CO", "BTN", "SB", "BB"]
    if n == 5:
        return ["UTG", "CO", "BTN", "SB", "BB"]
    if n == 6:
        return ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    if n == 7:
        return ["UTG", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
    return ["BTN", "SB", "BB", "UTG", "UTG+1", "LJ", "HJ", "CO"]


def _pos_for_n(n: int) -> list[str]:
    if n == 2: return ["SB", "BB"]
    if n == 3: return ["BTN", "SB", "BB"]
    if n == 4: return ["CO", "BTN", "SB", "BB"]
    if n == 5: return ["UTG", "CO", "BTN", "SB", "BB"]
    if n == 6: return ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    if n == 7: return ["UTG", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
    return list(ALL_POSITIONS)


def _ct(c) -> str:
    from config import SUIT_SYMBOLS
    if not c:
        return ""
    return f"{'10' if c.rank == 'T' else c.rank}{SUIT_SYMBOLS[c.suit]}"
