"""Оценка руки: префлоп по чартам, постфлоп — equity против диапазона через eval7."""

from __future__ import annotations
import random
from collections import Counter
from itertools import combinations

# >>> НОВАЯ ЗАВИСИМОСТЬ <<<
try:
    import eval7

    EVAL7_AVAILABLE = True
except ImportError:
    EVAL7_AVAILABLE = False

from config import PREFLOP_CHARTS, RANKS, SUITS

_RANK_ORDER = {r: i for i, r in enumerate(RANKS)}


# ========== ПРЕФЛОП (без изменений, оставляем как есть) ==========
def _hand_to_preflop_notation(hand) -> str:
    hi, lo, suited = hand.get_normalized_ranks()
    if hi == lo:
        return f"{hi}{lo}"
    return f"{hi}{lo}{'s' if suited else 'o'}"


def get_preflop_category(hand, position: str, num_players: int) -> str:
    _ = num_players
    notation = _hand_to_preflop_notation(hand)
    chart = PREFLOP_CHARTS.get(position) or PREFLOP_CHARTS["BB"]
    if notation in chart.get("pairs", []) or notation in chart.get("suited", []) or notation in chart.get("offsuit",
                                                                                                          []):
        return "strong"
    return "weak"


# ========== УТИЛИТЫ ДЛЯ EVAL7 ==========
def _to_eval7_format(cards: list) -> list:
    """Конвертирует список Card в список строк типа ['As', 'Kd']"""
    return [c.to_treys() for c in cards if c is not None]


def _get_villain_range_key(stage: str, board_texture: str = 'dry', opponent_type: str = 'standard') -> str:
    """Возвращает строку диапазона в синтаксисе PokerStove для eval7"""
    # Базовые диапазоны — можно расширять
    ranges = {
        'standard': "88+, AJs+, KQs, AQo+",
        'tight': "JJ+, AKs, AKo",
        'loose': "22+, A2s+, K9s+, Q9s+, J9s+, T9s, ATo+, KTo+, QTo+",
        'fish': "Any2",  # eval7 парсит!
    }

    # Упрощённая логика: на мокром борде оппоненты сужают диапазон
    if board_texture == 'wet' and opponent_type != 'fish':
        return "TT+, ATs+, KJs+, QJs, JTs, AKo, AQo"

    return ranges.get(opponent_type, ranges['standard'])


# ========== НОВАЯ ФУНКЦИЯ: equity через eval7 ==========
def get_postflop_equity_eval7(
        hand,
        board,
        villain_range: str = None,
        iterations: int = 3000,
        board_texture: str = 'dry',
        opponent_type: str = 'standard'
) -> float:
    """
    Расчёт эквити через eval7 против диапазона.
    Возвращает float 0.0–1.0

    Если eval7 не установлен — фоллбэк на старую логику.
    """
    if not EVAL7_AVAILABLE:
        # Фоллбэк на старую функцию (чтобы не сломать проект)
        return get_postflop_equity_fallback(hand, board, iterations)

    try:
        hero_cards = tuple(eval7.Card(c) for c in _to_eval7_format([hand.cards[0], hand.cards[1]]))
        board_cards = tuple(eval7.Card(c) for c in _to_eval7_format(board or []))

        # Если диапазон не передан — берём дефолтный по контексту
        if villain_range is None:
            villain_range = _get_villain_range_key('postflop', board_texture, opponent_type)

        villain = eval7.HandRange(villain_range)

        # Если борд неполный — eval7 сам доберёт карты в симуляции
        if len(board_cards) < 5:
            return eval7.py_hand_vs_range_monte_carlo(hero_cards, villain, board_cards, iterations)
        else:
            # Шоудаун — можно использовать точный расчёт (медленнее)
            return eval7.py_hand_vs_range_exact(hero_cards, villain, board_cards)

    except Exception as e:
        # Логирование ошибки (опционально)
        # print(f"[eval7 equity error] {e}")
        return get_postflop_equity_fallback(hand, board, iterations)


# ========== СТАРАЯ ФУНКЦИЯ — переименовываем в fallback ==========
def get_postflop_equity_fallback(hand, board, iterations: int = 500) -> float:
    """Старая логика: против одной случайной руки. Оставлена как фоллбэк."""
    hero = [hand.cards[0], hand.cards[1]]
    brd = [c for c in (board or []) if c is not None]
    dead = {(c.rank, c.suit) for c in hero + brd}
    pool = [c for c in _full_deck_cards() if (c.rank, c.suit) not in dead]
    need_board = 5 - len(brd)
    if need_board < 0:
        brd = brd[:5]
        need_board = 0
    if len(pool) < 2 + need_board:
        return 0.5

    wins = ties = 0
    rng = random.Random(42)
    for _ in range(iterations):
        pick = rng.sample(pool, 2 + need_board)
        opp = pick[:2]
        full_b = brd + pick[2:]
        hs = _best_five_score(hero + full_b)
        os_ = _best_five_score(opp + full_b)
        if hs > os_:
            wins += 1
        elif hs == os_:
            ties += 1
    return (wins + 0.5 * ties) / iterations


# ========== Публичный интерфейс (обратная совместимость) ==========
def get_postflop_equity(hand, board, iterations: int = 500, **kwargs) -> float:
    """
    Единая точка входа.
    Если переданы kwargs для eval7 (villain_range, board_texture, opponent_type) — используем eval7.
    Иначе — фоллбэк на старую логику.
    """
    if EVAL7_AVAILABLE and kwargs:
        return get_postflop_equity_eval7(hand, board, iterations=iterations, **kwargs)
    return get_postflop_equity_fallback(hand, board, iterations)


# ========== Вспомогательные функции (оставляем как есть) ==========
def _full_deck_cards():
    from models.card import Card
    return [Card(r + s) for r in RANKS for s in SUITS]


def _rank_value(rank: str) -> int:
    return _RANK_ORDER[rank] + 2


def _score_exactly_five(cards: list) -> tuple[int, ...]:
    # ... (твой существующий код, не меняем)
    ranks = [_rank_value(c.rank) for c in cards]
    suits = [c.suit for c in cards]
    cnt = Counter(ranks)
    counts = sorted(cnt.values(), reverse=True)
    sorted_by_freq = sorted(cnt.items(), key=lambda x: (x[1], x[0]), reverse=True)
    is_flush = len(set(suits)) == 1
    sr = sorted(set(ranks))
    is_straight = False
    high = 0
    if len(sr) == 5:
        if sr[4] - sr[0] == 4:
            is_straight = True
            high = sr[4]
        if sr == [2, 3, 4, 5, 14]:
            is_straight = True
            high = 5
    if is_flush and is_straight:
        return (8, high)
    if counts == [4, 1]:
        q = sorted_by_freq[0][0]
        k = sorted_by_freq[1][0]
        return (7, q, k)
    if counts == [3, 2]:
        t = sorted_by_freq[0][0]
        p = sorted_by_freq[1][0]
        return (6, t, p)
    if is_flush:
        return (5,) + tuple(sorted(ranks, reverse=True))
    if is_straight:
        return (4, high)
    if counts == [3, 1, 1]:
        t = sorted_by_freq[0][0]
        kickers = sorted([r for r in ranks if r != t], reverse=True)
        return (3, t, kickers[0], kickers[1])
    if counts == [2, 2, 1]:
        p1, p2 = sorted([sorted_by_freq[0][0], sorted_by_freq[1][0]], reverse=True)
        k = sorted_by_freq[2][0]
        return (2, p1, p2, k)
    if counts == [2, 1, 1, 1]:
        p = sorted_by_freq[0][0]
        kickers = sorted([r for r in ranks if r != p], reverse=True)
        return (1, p, kickers[0], kickers[1], kickers[2])
    return (0,) + tuple(sorted(ranks, reverse=True))


def _best_five_score(cards: list) -> tuple[int, ...]:
    if len(cards) < 5:
        return (-1,)
    best: tuple[int, ...] = (-1,)
    for five in combinations(cards, 5):
        best = max(best, _score_exactly_five(list(five)))
    return best
