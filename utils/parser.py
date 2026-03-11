from models.card import Card
from models.hand import Hand
from config import ALL_POSITIONS


def parse_cards(text: str):
    parts = text.strip().split()
    if len(parts) != 2:
        raise ValueError("Введите две карты через пробел")
    cards = [Card(part) for part in parts]
    return Hand(cards[0], cards[1])


def parse_position(text: str):
    pos = text.strip().upper()
    if pos not in ALL_POSITIONS:
        raise ValueError(f"Неизвестная позиция. Допустимы: {', '.join(ALL_POSITIONS)}")
    return pos


def parse_stack(text: str):
    text = text.strip().lower()
    if text.endswith('bb'):
        text = text[:-2]
    try:
        stack = int(text)
    except ValueError:
        raise ValueError("Стек должен быть целым числом, опционально с 'bb'")
    return stack
