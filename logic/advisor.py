from __future__ import annotations

from dataclasses import dataclass

from config import RANKS
from logic.evaluator import get_preflop_category, get_postflop_equity
from logic.poker_strategy import Action, BoardClass, Decision, HandClass

_RANK_ORDER = {r: i for i, r in enumerate(RANKS)}


def recommend_action(hand, position, stack, opponent_action=None, bet_to_call=None,
                     num_players=6, board=None, stage='preflop', pot_size_bb=None,
                     villain_type: str = 'standard', board_texture: str = None):
    if stage == 'preflop':
        return _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players)
    return _postflop_advice(
        hand, position, stack, opponent_action, bet_to_call,
        board, pot_size_bb, villain_type, board_texture
    )


def _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players):
    category = get_preflop_category(hand, position, num_players)
    stack_bb = stack
    if opponent_action in (None, 'fold', 'check'):
        if category == 'strong':
            if stack_bb <= 12:
                return "All-in"
            raise_size = "2.2bb" if position in ('BTN', 'CO') else "2.5bb"
            return f"Рейз до {raise_size}"
        return "Чек" if position == 'BB' else "Фолд"

    if opponent_action in ('bet', 'raise', 'allin'):
        bet_to_call = 0 if bet_to_call is None else bet_to_call
        if category != 'strong':
            return "Фолд"
        if bet_to_call <= stack_bb * 0.25:
            return "Колл"
        if bet_to_call <= stack_bb * 0.5 and stack_bb <= 20:
            return "Колл"
        return "Фолд" if bet_to_call > stack_bb * 0.6 else f"Рейз до {min(stack_bb, bet_to_call * 2):.1f}bb"
    return "Неизвестное действие"


def _postflop_advice(hand, position, stack, opponent_action, bet_to_call,
                     board, pot_size_bb=None, villain_type='standard', board_texture=None):
    if board_texture is None and board:
        board_texture = _detect_board_texture(board)

    equity = get_postflop_equity(
        hand, board,
        iterations=3000,
        opponent_type=villain_type,
        board_texture=board_texture
    )
    stack_bb = stack
    pot_size_bb = 10 if not pot_size_bb or pot_size_bb <= 0 else pot_size_bb

    if opponent_action in (None, 'fold', 'check'):
        if board_texture in ('wet', 'paired') and equity < 0.7:
            return "Чек"
        if equity >= 0.82:
            return f"Ставка {min(stack_bb, 0.66 * pot_size_bb):.1f}bb (велью)"
        if equity >= 0.62 and position in ['BTN', 'CO', 'SB']:
            return f"Ставка {min(stack_bb, 0.33 * pot_size_bb):.1f}bb (тонкое велью/полублеф)"
        return "Чек"

    if opponent_action in ('bet', 'raise', 'allin'):
        bet_to_call = 0 if bet_to_call is None else bet_to_call
        pot_odds = bet_to_call / (pot_size_bb + bet_to_call) if (pot_size_bb + bet_to_call) > 0 else 1

        scare_penalty = 0.08 if board_texture in ('wet', 'paired') else 0.0
        tight_bonus = 0.04 if villain_type == 'tight' else 0.0
        loose_penalty = -0.03 if villain_type == 'loose' else 0.0
        required_equity = pot_odds + 0.06 + scare_penalty + tight_bonus + loose_penalty

        if equity < required_equity:
            return "Фолд"

        if equity >= 0.78 and stack_bb > bet_to_call * 2 and board_texture not in ('wet', 'paired'):
            raise_size = min(stack_bb, max(bet_to_call * 2.2, pot_size_bb * 0.8))
            return f"Рейз до {raise_size:.1f}bb"

        if board_texture in ('wet', 'paired') and equity < 0.85:
            return "Колл"

        return "Колл"

    return "Неизвестное действие"


def _detect_board_texture(board) -> str:
    if not board:
        return 'dry'

    ranks = [c.rank for c in board]
    suits = [c.suit for c in board]

    if len(set(suits)) == 1:
        return 'scary'
    if len(set(suits)) == 2 and any(suits.count(s) == 2 for s in set(suits)):
        return 'wet'

    rank_values = [_RANK_ORDER[r] for r in ranks]
    if len(set(ranks)) < len(ranks):
        return 'paired'
    if len(set(rank_values)) == len(rank_values) and max(rank_values) - min(rank_values) <= 4:
        return 'wet'

    return 'dry'
