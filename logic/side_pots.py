"""
Сайд-поты и главный банк (Texas Hold'em NL/PL/L и аналоги).

Алгоритм — итеративное снятие min(оставшийся_вклад) среди активных
(как в ТЗ): каждый слой — пот размером min_bet × число участников с
оставшимся вкладом ≥ min_bet; один участник → невызванная ставка (uncalled).

Dead money (вклад сфолдивших) по ТЗ входит в main pot: добавляется к первому
контестируемому слою (самый «нижний» среди активных).

Порядок списка pots — порядок раздачи на шоудауне: сначала внешние сайд-поты,
последним — главный банк (уже с dead money).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

logger = logging.getLogger(__name__)

EPS = 1e-9


def build_showdown_pots(
    contributions: Mapping[str, float],
    active: set[str],
) -> tuple[list[tuple[float, frozenset[str]]], dict[str, float]]:
    """
    Возвращает (pots, uncalled_bb).

    pots: [(сумма_bb, претенденты), ...] в порядке **раздачи на шоудауне**
    (первый элемент — самый внешний сайд-пот при наличии, последний — main).

    uncalled: невызванные bb по местам (возврат из банка до выбора победителей).
    """
    alive = frozenset(active)
    uncalled: dict[str, float] = {}

    dead = 0.0
    for p, v in contributions.items():
        if p not in alive:
            dead += max(0.0, float(v))

    remaining: dict[str, float] = {
        p: max(0.0, float(contributions.get(p, 0.0))) for p in alive
    }

    # Слои от «main» к «внешним» сайдам (первый слой — минимальный вклад).
    main_first: list[tuple[float, frozenset[str]]] = []

    while True:
        pos_rem = [p for p in alive if remaining.get(p, 0.0) > EPS]
        if not pos_rem:
            break
        min_bet = min(remaining[p] for p in pos_rem)
        participants = [p for p in pos_rem if remaining[p] + EPS >= min_bet]
        pot_size = min_bet * len(participants)
        if len(participants) == 1:
            p0 = participants[0]
            uncalled[p0] = uncalled.get(p0, 0.0) + pot_size
        else:
            main_first.append((pot_size, frozenset(participants)))
        for p in participants:
            remaining[p] = max(0.0, remaining[p] - min_bet)

    if main_first:
        s0, e0 = main_first[0]
        main_first[0] = (s0 + dead, e0)
    elif dead > EPS:
        main_first.append((dead, alive))

    showdown_order = list(reversed(main_first))

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "showdown pots (award order outer→main): %s",
            [(round(a, 4), sorted(e)) for a, e in showdown_order],
        )
        logger.debug("uncalled: %s", {k: round(v, 4) for k, v in uncalled.items()})

    return showdown_order, uncalled


def breakdown_matches_pot(
    contributions: Mapping[str, float],
    active: set[str],
    pot_total: float,
    tol: float,
) -> bool:
    """Сходятся ли сумма вкладов и нарезка с фактическим банком (± tol)."""
    s = sum(max(0.0, float(contributions.get(p, 0))) for p in contributions)
    if abs(s - pot_total) > tol:
        return False
    pots, unc = build_showdown_pots(contributions, active)
    carved = sum(a for a, _ in pots) + sum(unc.values())
    return abs(carved - pot_total) <= tol


def side_pot_lines_for_ui(
    contributions: Mapping[str, float],
    active: set[str],
) -> tuple[list[tuple[int, float, frozenset[str]]], dict[str, float]]:
    """[(номер по порядку раздачи, сумма, претенденты), ...], uncalled."""
    pots, unc = build_showdown_pots(contributions, active)
    numbered = [(i + 1, amt, elig) for i, (amt, elig) in enumerate(pots)]
    return numbered, unc
