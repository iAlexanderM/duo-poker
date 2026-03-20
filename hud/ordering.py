TABLE_ORDER = ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
PREFLOP_ORDER = ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
POSTFLOP_ORDER = ["SB", "BB", "UTG", "UTG+1", "LJ", "HJ", "CO", "BTN"]


def _postflop_acting_order(positions: list[str]) -> list[str]:
    """Порядок ходов на постфлопе; в HU первым ходит BB, затем SB."""
    if len(positions) == 2 and set(positions) == {"SB", "BB"}:
        return ["BB", "SB"]
    return POSTFLOP_ORDER


def _street_order(stage: str, positions: list[str]) -> list[str]:
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
