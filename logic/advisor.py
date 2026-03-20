from logic.evaluator import get_preflop_category, get_postflop_equity


def recommend_action(hand, position, stack, opponent_action=None, bet_to_call=None,
                     num_players=6, board=None, stage='preflop', pot_size_bb=None,
                     # >>> НОВЫЕ ПАРАМЕТРЫ ДЛЯ КОНТЕКСТА <<<
                     villain_type: str = 'standard',
                     board_texture: str = None):
    """
    villain_type: 'tight' | 'standard' | 'loose' | 'fish'
    board_texture: 'dry' | 'wet' | 'paired' | 'scary' (опционально)
    """
    if stage == 'preflop':
        return _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players)
    else:
        return _postflop_advice(
            hand, position, stack, opponent_action, bet_to_call,
            board, pot_size_bb, villain_type, board_texture
        )


def _preflop_advice(hand, position, stack, opponent_action, bet_to_call, num_players):
    # ... (без изменений, оставляем как есть)
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


def _postflop_advice(hand, position, stack, opponent_action, bet_to_call,
                     board, pot_size_bb=None, villain_type='standard', board_texture=None):
    # >>> ИСПОЛЬЗУЕМ НОВЫЙ equity С КОНТЕКСТОМ <<<

    # Авто-определение текстуры борда, если не передана
    if board_texture is None and board:
        board_texture = _detect_board_texture(board)

    equity = get_postflop_equity(
        hand, board,
        iterations=3000,  # Увеличиваем для точности с eval7
        opponent_type=villain_type,
        board_texture=board_texture
    )

    stack_bb = stack

    # >>> УЛУЧШЕННАЯ ЛОГИКА С УЧЁТОМ ПОЗИЦИИ И КОНТЕКСТА <<<

    if opponent_action in (None, 'fold', 'check'):
        # Позиционный бонус
        position_bonus = 0.05 if position in ['BTN', 'CO'] else 0
        # Бонус за мертвые деньги (фолды до нас)
        dead_money_bonus = 0.03  # можно динамически считать

        adjusted_equity = equity + position_bonus + dead_money_bonus

        if adjusted_equity > 0.7:
            return f"Ставка {min(stack_bb, 0.75 * stack_bb):.1f}bb (велью)"
        elif adjusted_equity > 0.55:
            if position in ['BTN', 'CO', 'SB']:
                return f"Ставка {min(stack_bb, 0.5 * stack_bb):.1f}bb (полублеф)"
            else:
                return "Чек"
        else:
            return "Чек"

    if opponent_action in ('bet', 'raise', 'allin'):
        if bet_to_call is None:
            bet_to_call = 0

        # >>> ПРАВИЛЬНЫЙ РАСЧЁТ POT ODDS <<<
        if pot_size_bb is None or pot_size_bb <= 0:
            pot_size_bb = 10  # дефолт, если не передан
        pot_odds = bet_to_call / (pot_size_bb + bet_to_call) if (pot_size_bb + bet_to_call) > 0 else 1

        # Корректировка: на мокром борде против лузового оппонента нужна большая маржа
        texture_penalty = -0.05 if board_texture == 'wet' else 0
        opponent_adjust = -0.03 if villain_type == 'loose' else (0.03 if villain_type == 'tight' else 0)

        required_equity = pot_odds + 0.05 + texture_penalty + opponent_adjust  # 5% маржа + контекст

        if equity > required_equity:
            # Доп. проверка: если эквити очень высокое — можно рейзить
            if equity > 0.7 and stack_bb > bet_to_call * 2:
                return f"Рейз до {min(stack_bb, bet_to_call * 2):.1f}bb"
            return "Колл"
        else:
            return "Фолд"

    return "Неизвестное действие"


def _detect_board_texture(board) -> str:
    """Простая эвристика: мокрый/сухой борд"""
    if not board:
        return 'dry'

    ranks = [c.rank for c in board]
    suits = [c.suit for c in board]

    # Флаш-дро
    if len(set(suits)) == 2 and any(suits.count(s) == 2 for s in set(suits)):
        return 'wet'

    # Стрит-дро или коннекторы
    rank_values = [_RANK_ORDER[r] for r in ranks]
    if len(set(rank_values)) == len(rank_values):  # все разные
        if max(rank_values) - min(rank_values) <= 4:
            return 'wet'

    # Парный борд
    if len(set(ranks)) < len(ranks):
        return 'paired'

    return 'dry'
