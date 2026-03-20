import eval7
from typing import List, Union


def card_to_eval7(card_str: str) -> eval7.Card:
    """Конвертирует строку 'As' -> eval7.Card('As')"""
    return eval7.Card(card_str)


def hand_to_eval7(hand_treys: List[str]) -> tuple:
    """Конвертирует список ['As', 'Kd'] -> tuple(eval7.Card, eval7.Card)"""
    return tuple(card_to_eval7(c) for c in hand_treys)


def board_to_eval7(board_treys: List[str]) -> tuple:
    """Конвертирует борд в tuple для eval7"""
    return tuple(card_to_eval7(c) for c in board_treys) if board_treys else ()


def range_string_to_eval7(range_str: str) -> eval7.HandRange:
    """Парсит PokerStove-строку в объект диапазона"""
    return eval7.HandRange(range_str)
