from config import ALL_POSITIONS, SUIT_SYMBOLS

class CardAndPositionsMixin:
    # ══════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════

    def _ct(self, c) -> str:
        if not c:
            return ""
        return f"{'10' if c.rank == 'T' else c.rank}{SUIT_SYMBOLS[c.suit]}"

    @staticmethod
    def _pos_for_n(n: int) -> list[str]:
        if n == 2: return ["SB", "BB"]
        if n == 3: return ["BTN", "SB", "BB"]
        if n == 4: return ["CO", "BTN", "SB", "BB"]
        if n == 5: return ["UTG", "CO", "BTN", "SB", "BB"]
        if n == 6: return ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
        if n == 7: return ["UTG", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
        return list(ALL_POSITIONS)
