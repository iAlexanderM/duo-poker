from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from logic.evaluator import get_preflop_category, get_postflop_equity
from logic.range_model import RangeModel
from logic.line_model import LineModel
from models.card import Card
from models.hand import Hand
from config import RANKS


class Action(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    VALUE_BET = "value_bet"
    BLUFF = "bluff"
    SEMIBLUFF = "semibluff"
    RAISE = "raise"
    SHOVE = "shove"


class HandState(str, Enum):
    PREMIUM = "premium"
    STRONG_VALUE = "strong_value"
    VALUE = "value"
    MARGINAL_SHOWDOWN = "marginal_showdown"
    DRAW = "draw"
    SEMIBLUFF = "semibluff"
    AIR = "air"


class BoardState(str, Enum):
    DRY = "dry"
    WET = "wet"
    PAIRED = "paired"
    MONOTONE = "monotone"
    SCARY = "scary"


_RANK_ORDER = {r: i for i, r in enumerate(RANKS)}


@dataclass(frozen=True)
class Decision:
    action: Action
    sizing_bb: float | None = None
    reason: str = ""
    confidence: float = 0.0


class PokerDecisionEngine:
    def __init__(self):
        self.range_model = RangeModel()
        self.line_model = LineModel()

    def recommend(
        self,
        hand: Hand,
        position: str,
        stack_bb: float | None = None,
        opponent_action: str | None = None,
        bet_to_call_bb: float | None = None,
        num_players: int = 6,
        board: list[Card] | None = None,
        stage: str = "preflop",
        pot_size_bb: float | None = None,
        villain_type: str = "standard",
        board_texture: str | None = None,
    ) -> Decision:
        if stack_bb is None:
            stack_bb = 0.0
        if stage == "preflop":
            return self._preflop(hand, position, stack_bb, opponent_action, bet_to_call_bb, num_players)
        return self._postflop(hand, position, stack_bb, opponent_action, bet_to_call_bb, board or [], pot_size_bb, villain_type, board_texture, stage, num_players)

    def _preflop(self, hand: Hand, position: str, stack_bb: float, opponent_action: str | None, bet_to_call_bb: float | None, num_players: int) -> Decision:
        cat = get_preflop_category(hand, position, num_players)
        notch = self._preflop_hand_strength(hand)
        hero_range = self.range_model.hero_open_range(position, num_players)

        if opponent_action in (None, "fold", "check"):
            if stack_bb <= 12 and notch >= 0.88:
                return Decision(Action.SHOVE, stack_bb, "Короткий стек + премиум рука", 0.92)
            if cat == "strong" or notch >= 0.82:
                size = 2.2 if position in ("BTN", "CO") else 2.5
                if position == "SB":
                    size = 3.0
                if position in ("BTN", "CO") and hero_range.aggression > 0.5:
                    size = 2.1
                return Decision(Action.BET, size, "Опен-рейз по позиции и силе руки", 0.76)
            if position == "BB":
                return Decision(Action.CHECK, None, "BB защищает без опена", 0.70)
            return Decision(Action.FOLD, None, "Слабая рука без инициативы", 0.72)

        bet_to_call_bb = 0.0 if bet_to_call_bb is None else bet_to_call_bb
        villain = self.range_model.estimate_villain_range("standard", "preflop", "dry", opponent_action, bet_to_call_bb, max(1.0, stack_bb))
        edge = self.range_model.range_vs_range_edge(hero_range, villain, "dry")

        if cat == "strong" or notch >= 0.86:
            if bet_to_call_bb <= max(1.0, 0.25 * stack_bb):
                return Decision(Action.CALL, None, "Премиум рука — защищаем диапазон", 0.74)
            if bet_to_call_bb <= 0.55 * stack_bb and stack_bb <= 25:
                if edge >= 0.08:
                    return Decision(Action.SHOVE, stack_bb, "Сильный префлоп-спот для давления", 0.78)
                return Decision(Action.CALL, None, "Стек позволяет реализовать эквити", 0.70)
            if edge >= 0.12 and bet_to_call_bb <= 0.35 * stack_bb:
                return Decision(Action.RAISE, min(stack_bb, bet_to_call_bb * 2.8), "Префлоп-рейз против диапазона оппа", 0.71)
            return Decision(Action.FOLD, None, "Слишком дорогое продолжение префлоп", 0.79)

        playability = self._preflop_playability(hand, position)
        if bet_to_call_bb <= 0.12 * stack_bb and playability >= 0.7 and edge >= -0.04:
            return Decision(Action.CALL, None, "Пограничный колл по odds и playability", 0.55)
        if playability >= 0.82 and edge >= 0.05 and bet_to_call_bb <= 0.18 * stack_bb:
            return Decision(Action.CALL, None, "Хорошая реализация эквити против диапазона", 0.58)
        return Decision(Action.FOLD, None, "Недостаточно силы для продолжения", 0.86)

    def _postflop(self, hand: Hand, position: str, stack_bb: float, opponent_action: str | None, bet_to_call_bb: float | None, board: list[Card], pot_size_bb: float | None, villain_type: str, board_texture: str | None, stage: str = "postflop", num_players: int = 6) -> Decision:
        if board_texture is None:
            board_texture = self._detect_board_texture(board)

        pot_size_bb = 10.0 if not pot_size_bb or pot_size_bb <= 0 else float(pot_size_bb)
        bet_to_call_bb = 0.0 if bet_to_call_bb is None else float(bet_to_call_bb)

        equity = get_postflop_equity(
            hand, board,
            iterations=4000,
            opponent_type=villain_type,
            board_texture=board_texture,
        )

        hand_state = self._classify_hand(hand, board, equity)
        board_state = self._classify_board(board)
        spr = stack_bb / max(1e-9, pot_size_bb)
        hero_bucket = self.range_model.hero_strength_bucket(hand)
        villain_range = self.range_model.estimate_villain_range(villain_type, stage if stage else "postflop", board_texture, opponent_action, bet_to_call_bb, pot_size_bb)
        hero_profile = self.range_model.hero_open_range(position, num_players)
        range_edge = self.range_model.range_vs_range_edge(hero_profile, villain_range, board_texture) + (hero_bucket - 0.5) * 0.05
        bluff_catch = self.range_model.bluff_catch_adjustment(villain_range, board_texture)
        line_board = board_state.value
        flop_plan = self.line_model.flop_plan(hero_profile, villain_range, line_board, opponent_action in (None, "fold", "check"))
        turn_plan = self.line_model.turn_plan(line_board, range_edge, opponent_action in (None, "fold", "check"))
        river_plan = self.line_model.river_plan(line_board, range_edge, bluff_catch, opponent_action in (None, "fold", "check"))

        if opponent_action in (None, "fold", "check"):
            line = flop_plan if stage == "flop" else turn_plan if stage == "turn" else river_plan
            if hand_state in (HandState.PREMIUM, HandState.STRONG_VALUE):
                size = self._value_bet_size(board_state, pot_size_bb, stack_bb, spr)
                if board_state in (BoardState.WET, BoardState.SCARY) and range_edge < 0.05:
                    return Decision(Action.CHECK, None, "Контроль банка: опасная доска и нет явного перевеса диапазона", 0.72)
                if line.check_freq > 0.4 and board_state in (BoardState.WET, BoardState.SCARY):
                    return Decision(Action.CHECK, None, "Линия борда требует больше слоуплея", 0.70)
                return Decision(Action.VALUE_BET, size, "Велью-бет по сильной готовой руке", 0.88)
            if hand_state in (HandState.DRAW, HandState.SEMIBLUFF) and board_state in (BoardState.WET, BoardState.SCARY):
                size = self._semibluff_size(board_state, pot_size_bb, stack_bb)
                if bluff_catch < 0.16 and range_edge < 0.04:
                    return Decision(Action.CHECK, None, "Слишком мало фолд-эквити для полублефа", 0.66)
                if line.bluff_freq < 0.08:
                    return Decision(Action.CHECK, None, "Линия борда не поддерживает агрессию", 0.64)
                return Decision(Action.SEMIBLUFF, size, "Полублеф с дро/блокерами", 0.68)
            if hand_state == HandState.VALUE and board_state in (BoardState.DRY, BoardState.PAIRED):
                size = self._thin_value_size(board_state, pot_size_bb)
                if line.pot_control_freq > 0.50 and range_edge < 0.06:
                    return Decision(Action.CHECK, None, "Пот-контроль лучше тонкого добора", 0.60)
                return Decision(Action.BET, size, "Тонкое велью", 0.61)
            if hand_state == HandState.MARGINAL_SHOWDOWN and board_state == BoardState.DRY and position in ("BTN", "CO"):
                return Decision(Action.CHECK, None, "Контроль банка с шоудаун-вэлью", 0.60)
            if line.check_freq > 0.60:
                return Decision(Action.CHECK, None, "Чек по структуре линии", 0.67)
            return Decision(Action.CHECK, None, "Чек для контроля банка", 0.67)

        if opponent_action in ("bet", "raise", "allin"):
            line = flop_plan if stage == "flop" else turn_plan if stage == "turn" else river_plan
            price = self._required_equity(board_state, villain_type, bet_to_call_bb, pot_size_bb, opponent_action, hand_state)
            if equity < price:
                return Decision(Action.FOLD, None, "Не хватает эквити против ставки/рейза", 0.84)

            if hand_state in (HandState.PREMIUM, HandState.STRONG_VALUE) and self._can_raise_for_value(board_state, spr, stack_bb, bet_to_call_bb):
                size = self._raise_for_value_size(board_state, pot_size_bb, bet_to_call_bb, stack_bb)
                if board_state in (BoardState.WET, BoardState.SCARY) and range_edge < 0.04:
                    return Decision(Action.CALL, None, "Сильная рука, но диапазонный перевес недостаточен для разгона", 0.76)
                if line.pot_control_freq > 0.55 and board_state in (BoardState.WET, BoardState.SCARY):
                    return Decision(Action.CALL, None, "Линия предпочитает пот-контроль", 0.74)
                return Decision(Action.RAISE, size, "Сильная рука — рейзим на велью", 0.82)
            if hand_state in (HandState.PREMIUM, HandState.STRONG_VALUE) and board_state in (BoardState.WET, BoardState.SCARY):
                return Decision(Action.CALL, None, "Сильная рука, но раздувать банк опасно", 0.74)

            if hand_state in (HandState.DRAW, HandState.SEMIBLUFF) and board_state in (BoardState.WET, BoardState.SCARY):
                if self._can_raise_for_semi(board_state, spr, stack_bb, bet_to_call_bb) and range_edge >= -0.02 and line.raise_freq >= 0.08:
                    size = self._semibluff_raise_size(board_state, pot_size_bb, bet_to_call_bb, stack_bb)
                    return Decision(Action.RAISE, size, "Полублеф-рейз по дро и блокерам", 0.63)
                return Decision(Action.CALL, None, "Дро достаточно для колла, но не для разгона", 0.56)
            if hand_state == HandState.PREMIUM and board_state in (BoardState.WET, BoardState.SCARY) and bet_to_call_bb > 0.3 * pot_size_bb:
                return Decision(Action.CALL, None, "Натсы есть, но рейз может изолировать против сильного диапазона", 0.73)

            if hand_state == HandState.VALUE:
                if board_state in (BoardState.WET, BoardState.SCARY) and bet_to_call_bb >= 0.45 * pot_size_bb:
                    return Decision(Action.CALL, None, "Контроль банка на опасном борде", 0.62)
                if range_edge >= 0.08 and board_state == BoardState.DRY and line.raise_freq > 0.10:
                    return Decision(Action.RAISE, self._raise_for_value_size(board_state, pot_size_bb, bet_to_call_bb, stack_bb), "Тонкое велью через рейз", 0.66)
                return Decision(Action.CALL, None, "Колл по достаточному эквити", 0.70)

            if hand_state == HandState.MARGINAL_SHOWDOWN:
                if board_state in (BoardState.WET, BoardState.SCARY, BoardState.PAIRED):
                    return Decision(Action.CALL, None, "Пограничная рука: защищаемся коллом", 0.53)
                return Decision(Action.CALL, None, "Шоудаун-вэлью хватает для колла", 0.58)

            if line.bluff_freq >= 0.18 and bluff_catch >= 0.18:
                return Decision(Action.CALL, None, "Колл против линии с блефами", 0.57)
            return Decision(Action.FOLD, None, "Слабая рука без достаточной реализации", 0.75)

        return Decision(Action.CHECK, None, "Fallback", 0.5)

    def _short_action_text(self, decision: Decision) -> str:
        action = decision.action.value
        if action in ("bet", "raise", "value_bet", "semibluff") and decision.sizing_bb is not None:
            if action == "bet":
                return f"Ставка {decision.sizing_bb:.1f} bb"
            if action == "raise":
                return f"Рейз до {decision.sizing_bb:.1f} bb"
            if action == "value_bet":
                return f"Велью-бет {decision.sizing_bb:.1f} bb"
            return f"Полублеф {decision.sizing_bb:.1f} bb"
        if action == "shove":
            return "All-in"
        return {
            "fold": "Фолд",
            "check": "Чек",
            "call": "Колл",
            "raise": "Рейз",
        }.get(action, action)


    def _preflop_hand_strength(self, hand: Hand) -> float:
        r1, r2, suited = hand.get_normalized_ranks()
        i1, i2 = _RANK_ORDER[r1], _RANK_ORDER[r2]
        base = max(i1, i2) / 12.0
        pair_bonus = 0.15 if r1 == r2 else 0.0
        suited_bonus = 0.06 if suited else 0.0
        connector_bonus = 0.08 if abs(i1 - i2) <= 2 else 0.0
        gap_penalty = 0.03 * max(0, abs(i1 - i2) - 2)
        return min(1.0, max(0.0, 0.35 + 0.5 * base + pair_bonus + suited_bonus + connector_bonus - gap_penalty))

    def _preflop_playability(self, hand: Hand, position: str) -> float:
        r1, r2, suited = hand.get_normalized_ranks()
        i1, i2 = _RANK_ORDER[r1], _RANK_ORDER[r2]
        score = 0.45
        if suited:
            score += 0.12
        if abs(i1 - i2) <= 1:
            score += 0.14
        if position in ("CO", "BTN", "SB"):
            score += 0.08
        if r1 == r2:
            score += 0.10
        return min(1.0, score)

    def _detect_board_texture(self, board: list[Card]) -> str:
        return self._classify_board(board).value

    def _classify_board(self, board: list[Card]) -> BoardState:
        if not board:
            return BoardState.DRY
        suits = [c.suit for c in board]
        ranks = [c.rank for c in board]
        values = sorted({_RANK_ORDER[r] for r in ranks})
        if len(set(suits)) == 1:
            return BoardState.SCARY
        if len(set(ranks)) < len(ranks):
            return BoardState.PAIRED
        if len(values) >= 3 and max(values) - min(values) <= 4:
            return BoardState.WET
        if any(suits.count(s) == 2 for s in set(suits)):
            return BoardState.WET
        return BoardState.DRY

    def _classify_hand(self, hand: Hand, board: list[Card], equity: float) -> HandState:
        hole = hand.cards
        if len(board) < 3:
            if equity >= 0.78:
                return HandState.PREMIUM
            if equity >= 0.66:
                return HandState.STRONG_VALUE
            return HandState.VALUE if equity >= 0.55 else HandState.AIR

        board_suits = [c.suit for c in board]
        all_cards = hole + board
        rank_counts = {r: sum(1 for c in all_cards if c.rank == r) for r in set(c.rank for c in all_cards)}
        pair_cnt = sorted(rank_counts.values(), reverse=True)
        suited_count = max(board_suits.count(s) for s in set(board_suits)) if board_suits else 0

        if pair_cnt[:2] == [4, 1] or pair_cnt[:2] == [3, 2]:
            return HandState.PREMIUM
        if equity >= 0.83:
            return HandState.PREMIUM
        if equity >= 0.72:
            return HandState.STRONG_VALUE
        if equity >= 0.60:
            return HandState.VALUE
        if self._has_draw(hole, board):
            return HandState.SEMIBLUFF if equity >= 0.45 else HandState.DRAW
        if suited_count >= 3 or self._gutshot_or_oesd(hole, board):
            return HandState.DRAW
        if equity >= 0.48:
            return HandState.MARGINAL_SHOWDOWN
        return HandState.AIR

    def _has_draw(self, hole: list[Card], board: list[Card]) -> bool:
        cards = hole + board
        ranks = sorted({_RANK_ORDER[c.rank] for c in cards})
        suits = [c.suit for c in cards]
        flush_draw = any(suits.count(s) >= 4 for s in set(suits))
        straight_draw = self._gutshot_or_oesd(hole, board)
        return flush_draw or straight_draw

    def _gutshot_or_oesd(self, hole: list[Card], board: list[Card]) -> bool:
        cards = hole + board
        vals = sorted(set(_RANK_ORDER[c.rank] for c in cards))
        if len(vals) < 4:
            return False
        for start in range(0, 9):
            window = set(range(start, start + 5))
            inter = window.intersection(vals)
            if len(inter) >= 4:
                return True
        return False

    def _required_equity(self, board_state: BoardState, villain_type: str, bet_to_call_bb: float, pot_size_bb: float, opponent_action: str, hand_state: HandState) -> float:
        pot_odds = bet_to_call_bb / (pot_size_bb + bet_to_call_bb) if pot_size_bb + bet_to_call_bb > 0 else 1.0
        margin = 0.06
        if board_state in (BoardState.WET, BoardState.SCARY):
            margin += 0.08
        elif board_state == BoardState.PAIRED:
            margin += 0.05
        if villain_type == "tight":
            margin += 0.04
        elif villain_type == "loose":
            margin -= 0.02
        if opponent_action == "allin":
            margin += 0.05
        if hand_state in (HandState.DRAW, HandState.SEMIBLUFF):
            margin -= 0.03
        return min(0.95, max(0.20, pot_odds + margin))

    def _value_bet_size(self, board_state: BoardState, pot_size_bb: float, stack_bb: float, spr: float) -> float:
        if board_state in (BoardState.WET, BoardState.SCARY):
            size = 0.55 * pot_size_bb
        elif board_state == BoardState.PAIRED:
            size = 0.45 * pot_size_bb
        else:
            size = 0.66 * pot_size_bb
        return min(stack_bb, max(0.33 * pot_size_bb, size))

    def _thin_value_size(self, board_state: BoardState, pot_size_bb: float) -> float:
        if board_state in (BoardState.DRY, BoardState.PAIRED):
            return 0.33 * pot_size_bb
        return 0.25 * pot_size_bb

    def _semibluff_size(self, board_state: BoardState, pot_size_bb: float, stack_bb: float) -> float:
        base = 0.33 * pot_size_bb if board_state == BoardState.DRY else 0.5 * pot_size_bb
        return min(stack_bb, max(0.25 * pot_size_bb, base))

    def _semibluff_raise_size(self, board_state: BoardState, pot_size_bb: float, bet_to_call_bb: float, stack_bb: float) -> float:
        target = bet_to_call_bb * 2.4 if board_state in (BoardState.WET, BoardState.SCARY) else bet_to_call_bb * 2.0
        return min(stack_bb, max(target, pot_size_bb * 0.9))

    def _raise_for_value_size(self, board_state: BoardState, pot_size_bb: float, bet_to_call_bb: float, stack_bb: float) -> float:
        if board_state in (BoardState.WET, BoardState.SCARY):
            return min(stack_bb, max(bet_to_call_bb * 2.0, pot_size_bb * 0.8))
        return min(stack_bb, max(bet_to_call_bb * 2.5, pot_size_bb))

    def _can_raise_for_value(self, board_state: BoardState, spr: float, stack_bb: float, bet_to_call_bb: float) -> bool:
        return not (board_state in (BoardState.WET, BoardState.SCARY) and spr > 2.5 and bet_to_call_bb > 0.35 * stack_bb)

    def _can_raise_for_semi(self, board_state: BoardState, spr: float, stack_bb: float, bet_to_call_bb: float) -> bool:
        return spr <= 8 and bet_to_call_bb <= 0.3 * stack_bb


def recommend_action(*args, **kwargs):
    engine = PokerDecisionEngine()
    if "stack" in kwargs and "stack_bb" not in kwargs:
        kwargs["stack_bb"] = kwargs.pop("stack")
    if "bet_to_call" in kwargs and "bet_to_call_bb" not in kwargs:
        kwargs["bet_to_call_bb"] = kwargs.pop("bet_to_call")
    if "pot_size" in kwargs and "pot_size_bb" not in kwargs:
        kwargs["pot_size_bb"] = kwargs.pop("pot_size")
    return engine.recommend(*args, **kwargs)
