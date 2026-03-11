from config import RANKS, SUITS, SUIT_SYMBOLS


class Card:
    def __init__(self, code: str):
        if len(code) < 2:
            raise ValueError(f"Неверный формат карты: {code}")
        rank = code[0].upper()
        suit = code[1].lower()
        if rank not in RANKS:
            raise ValueError(f"Неверный ранг: {rank}")
        if suit not in SUITS:
            raise ValueError(f"Неверная масть: {suit}")
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"Card('{self.rank}{self.suit}')"

    def __str__(self):
        rank_display = '10' if self.rank == 'T' else self.rank
        return f"{rank_display}{SUIT_SYMBOLS[self.suit]}"

    def display_rank(self):
        return '10' if self.rank == 'T' else self.rank

    def to_treys(self):
        """Конвертация в формат treys: 'As' 'Kd' и т.д."""
        return self.rank + self.suit
