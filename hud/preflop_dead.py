"""Анте и блайнды в начале префлопа: анте только в банк, не в bets."""


def apply_preflop_dead(
    positions: list[str],
    stacks: dict[str, float],
    bets: dict[str, float],
    ante_bb: float,
    ante_scope: str,
) -> tuple[float, float, dict[str, float]]:
    """
    Мутирует stacks и bets. Возвращает (pot, max_bet, ante_by_seat).
    ante_by_seat: сколько bb анте положил каждый (только ненулевые).
    ante_scope: 'all' — анте со всех активных мест; 'bb_only' — только с ББ.
    """
    pot = 0.0
    ante_by_seat: dict[str, float] = {}
    ante = max(0.0, float(ante_bb or 0))

    if ante > 0:
        if ante_scope == "bb_only" and "BB" in positions:
            pay = min(ante, max(0.0, stacks.get("BB", 0)))
            stacks["BB"] = stacks.get("BB", 0) - pay
            pot += pay
            if pay > 0:
                ante_by_seat["BB"] = pay
        else:
            for p in positions:
                pay = min(ante, max(0.0, stacks.get(p, 0)))
                stacks[p] = stacks.get(p, 0) - pay
                pot += pay
                if pay > 0:
                    ante_by_seat[p] = pay

    for p in positions:
        bets[p] = 0.0

    if "SB" in positions:
        a = min(0.5, max(0.0, stacks.get("SB", 0)))
        bets["SB"] = a
        stacks["SB"] = stacks.get("SB", 0) - a
    if "BB" in positions:
        a = min(1.0, max(0.0, stacks.get("BB", 0)))
        bets["BB"] = a
        stacks["BB"] = stacks.get("BB", 0) - a

    max_bet = 1.0 if "BB" in positions else 0.0
    pot += sum(bets.values())
    return pot, max_bet, ante_by_seat
