from logic.evaluator import get_preflop_category, get_postflop_equity


def recommend_action(hand, position, stack, opponent_action=None, bet_to_call=None, num_players=6, board=None,
                     stage='preflop'):
    if stage == 'preflop':
        return _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players)
    else:
        return _postflop_advice(hand, position, stack, opponent_action, bet_to_call, board)


def _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players):
    category = get_preflop_category(hand, position, num_players)
    stack_bb = stack

    if opponent_action in (None, 'fold', 'check'):
        if category == 'strong':
            if stack_bb < 10:
                return "All-in"
            else:
                raise_size = "3bb" if position == 'SB' else "2.5bb"
                return f"Рейз до {raise_size}"
        else:
            if position == 'BB':
                return "Чек"
            else:
                return "Фолд"

    if opponent_action in ('bet', 'raise', 'allin'):
        if bet_to_call is None:
            bet_to_call = 0
        if category == 'strong':
            if bet_to_call <= stack_bb * 0.5:
                return f"Рейз до {min(stack_bb, bet_to_call * 2):.1f}bb"
            else:
                return "Колл"
        else:
            return "Фолд"

    return "Неизвестное действие"


def _postflop_advice(hand, position, stack, opponent_action, bet_to_call, board):
    equity = get_postflop_equity(hand, board)
    stack_bb = stack

    if opponent_action in (None, 'fold', 'check'):
        if equity > 0.7:
            return f"Ставка {min(stack_bb, 0.75 * stack_bb):.1f}bb (для велью)"
        elif equity > 0.5:
            if position in ['BTN', 'CO', 'SB']:
                return f"Ставка {min(stack_bb, 0.5 * stack_bb):.1f}bb (полублеф)"
            else:
                return "Чек"
        else:
            return "Чек"

    if opponent_action in ('bet', 'raise', 'allin'):
        if bet_to_call is None:
            bet_to_call = 0
        pot_odds = bet_to_call / (2 * bet_to_call) if bet_to_call > 0 else 0
        if equity > pot_odds + 0.1:
            return "Колл"
        else:
            return "Фолд"

    return "Неизвестное действие"
