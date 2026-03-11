from models.card import Card
from config import RANKS


class Hand:
    def __init__(self, card1: Card, card2: Card):
        self.cards = [card1, card2]

    def __repr__(self):
        return f"Hand({self.cards[0]}, {self.cards[1]})"

    def __str__(self):
        return f"{self.cards[0]} {self.cards[1]}"

    def get_normalized_ranks(self):
        r1 = self.cards[0].rank
        r2 = self.cards[1].rank
        suited = (self.cards[0].suit == self.cards[1].suit)
        idx1 = RANKS.index(r1)
        idx2 = RANKS.index(r2)
        if idx1 >= idx2:
            return (r1, r2, suited)
        else:
            return (r2, r1, suited)

    def to_treys(self):
        """Список строк для treys."""
        return [c.to_treys() for c in self.cards]
