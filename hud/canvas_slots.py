import tkinter as tk

from models.card import Card

class CanvasSlotsMixin:
    # ══════════════════════════════════════════════════════════════
    #  CARD PICKING
    # ══════════════════════════════════════════════════════════════

    def _on_canvas_click(self, event):
        for target, (x1, y1, x2, y2) in self.slot_rects.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.active_slot = target
                self._draw_table()
                self._upd_cards_lbl()
                return

    def _pick_card(self, card: Card):
        t, idx = self.active_slot
        cs = str(card)
        if t == "hole":
            if self.hole[idx] and str(self.hole[idx]) == cs:
                self.hole[idx] = None
            else:
                self._remove_card(card)
                self.hole[idx] = card
        else:
            if idx >= self.max_board:
                return
            if self.board[idx] and str(self.board[idx]) == cs:
                self.board[idx] = None
            else:
                self._remove_card(card)
                self.board[idx] = card

        self._auto_advance()
        self._draw_table()
        self._refresh_deck()
        self._upd_cards_lbl()

    def _auto_advance(self):
        t, idx = self.active_slot
        if t == "hole":
            if idx == 0 and self.hole[0] and not self.hole[1]:
                self.active_slot = ("hole", 1)
            elif idx == 1 and self.hole[1] and self.max_board > 0:
                for j in range(self.max_board):
                    if not self.board[j]:
                        self.active_slot = ("board", j)
                        return
        elif t == "board":
            for j in range(idx + 1, self.max_board):
                if not self.board[j]:
                    self.active_slot = ("board", j)
                    return

    def _clear_slot(self):
        t, idx = self.active_slot
        if t == "hole":
            self.hole[idx] = None
        elif idx < self.max_board:
            self.board[idx] = None
        self._draw_table()
        self._refresh_deck()
        self._upd_cards_lbl()

    def _remove_card(self, card: Card):
        cs = str(card)
        for i in range(2):
            if self.hole[i] and str(self.hole[i]) == cs:
                self.hole[i] = None
        for i in range(5):
            if self.board[i] and str(self.board[i]) == cs:
                self.board[i] = None

    def _refresh_deck(self):
        sel = ({str(c) for c in self.hole if c} |
               {str(self.board[i]) for i in range(5) if self.board[i]})
        for code, btn in self.deck_btns.items():
            btn.config(bg="#ffeb3b" if code in sel else "white",
                       relief="sunken" if code in sel else "raised")

