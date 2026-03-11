import random
from models.card import Card
from models.hand import Hand
from config import RANKS, SUITS, PREFLOP_CHARTS

# Попытка импорта treys для точного расчёта эквити
try:
    from treys import Card as TreysCard, Evaluator, Deck

    TREYS_AVAILABLE = True
except ImportError:
    TREYS_AVAILABLE = False


def get_preflop_category(hand: Hand, position: str, num_players: int = 6):
    """
    Определяет, входит ли рука в диапазон игры для данной позиции.
    Возвращает 'strong' (играем) или 'weak' (не играем).
    """
    r1, r2, suited = hand.get_normalized_ranks()
    if r1 == r2:
        hand_str = r1 + r2
    else:
        hand_str = r1 + r2 + ('s' if suited else 'o')
    # Проверяем по чарту
    chart = PREFLOP_CHARTS.get(position, {})
    if hand_str in chart.get('pairs', []) or hand_str in chart.get('suited', []) or hand_str in chart.get('offsuit',
                                                                                                          []):
        return 'strong'
    else:
        return 'weak'


def calculate_equity_vs_random(hand_cards, board_cards=None, iterations=1000):
    """
    Рассчитывает эквити руки против случайной руки.
    hand_cards: список строк для treys (['As','Kd'])
    board_cards: список строк для treys (['2h','3c','4d'])
    iterations: количество симуляций.
    Возвращает эквити (0..1).
    Если treys недоступна, возвращает приблизительное значение (0.5).
    """
    if not TREYS_AVAILABLE:
        return 0.5

    from treys import Evaluator, Deck
    evaluator = Evaluator()
    wins = 0
    total = 0
    for _ in range(iterations):
        deck = Deck()
        for c in hand_cards:
            deck.cards.remove(TreysCard.new(c))
        if board_cards:
            for c in board_cards:
                deck.cards.remove(TreysCard.new(c))
        opp_hand = deck.draw(2)
        hand_treys = [TreysCard.new(c) for c in hand_cards]
        board_treys = [TreysCard.new(c) for c in board_cards] if board_cards else []
        remaining = 5 - len(board_treys)
        if remaining > 0:
            community = board_treys + deck.draw(remaining)
        else:
            community = board_treys

        # Оценка силы
        score_us = evaluator.evaluate(hand_treys, community)
        score_opp = evaluator.evaluate(opp_hand, community)
        if score_us < score_opp:
            wins += 1
        total += 1
    return wins / total if total > 0 else 0.5


def get_postflop_equity(hand: Hand, board, iterations=500):
    hand_treys = [c.to_treys() for c in hand.cards]
    board_treys = [c.to_treys() for c in board] if board else []
    return calculate_equity_vs_random(hand_treys, board_treys, iterations)
