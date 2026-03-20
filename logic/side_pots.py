"""
Сайд-поты по правилам покера (main + side).

1) Вклад сфолдивших (не в active) — «мёртвые» фишки: один банк, претенденты — все
   оставшиеся в раздаче (кто не фолднул).

2) Среди активных с положительным вкладом — сортировка по возрастанию вклада
   за руку и нарезка уровнями (как min×n, затем дельты): каждый слой получают
   только те активные, кто вложил не меньше текущего уровня; претенденты на
   этот банк — ровно они (без короткого стека на следующих уровнях).

Пример: активные вклады 100,105,105,105 → 400 (четверо) + 15 (трое). Сфолднувший
с 20 bb даёт отдельный банк 20 на оставшихся, затем нарезка по живым.

Невызванный остаток (один плательщик на уровне) — в uncalled.
"""


def build_showdown_pots(
    contributions: dict[str, float],
    active: set[str],
) -> tuple[list[tuple[float, frozenset[str]]], dict[str, float]]:
    """
    Возвращает (pots, uncalled_bb).
    pots: [(сумма_bb, претенденты), ...] по порядку от первого банка к сайдам.
    """
    alive = frozenset(active)
    pots: list[tuple[float, frozenset[str]]] = []
    uncalled: dict[str, float] = {}

    dead = 0.0
    for p, v in contributions.items():
        if p not in alive:
            dead += max(0.0, float(v))
    if dead > 1e-9:
        pots.append((dead, frozenset(alive)))

    active_payers = sorted(
        (p for p in alive if contributions.get(p, 0) > 1e-9),
        key=lambda p: contributions[p],
    )
    if not active_payers:
        return pots, uncalled

    k = len(active_payers)
    prev = 0.0
    cvals = [contributions[p] for p in active_payers]

    for i in range(k):
        delta = cvals[i] - prev
        if delta <= 1e-9:
            prev = cvals[i]
            continue
        payers = active_payers[i:]
        amount = delta * len(payers)
        if len(payers) == 1:
            p0 = payers[0]
            uncalled[p0] = uncalled.get(p0, 0) + amount
        else:
            pots.append((amount, frozenset(payers)))
        prev = cvals[i]

    return pots, uncalled


def breakdown_matches_pot(
    contributions: dict[str, float],
    active: set[str],
    pot_total: float,
    tol: float,
) -> bool:
    """Сходятся ли сумма вкладов и разбивка с фактическим банком."""
    s = sum(max(0.0, float(contributions.get(p, 0))) for p in contributions)
    if abs(s - pot_total) > tol:
        return False
    pots, unc = build_showdown_pots(contributions, active)
    carved = sum(a for a, _ in pots) + sum(unc.values())
    return abs(carved - pot_total) <= tol


def side_pot_lines_for_ui(
    contributions: dict[str, float],
    active: set[str],
) -> tuple[list[tuple[int, float, frozenset[str]]], dict[str, float]]:
    """[(номер, сумма, претенденты), ...], uncalled."""
    pots, unc = build_showdown_pots(contributions, active)
    numbered = [(i + 1, amt, elig) for i, (amt, elig) in enumerate(pots)]
    return numbered, unc
