import tkinter as tk
from tkinter import messagebox

from config import RANKS, SUITS, SUIT_SYMBOLS
from models.card import Card

class PhaseDeckMixin:
    # ══════════════════════════════════════════════════════════════
    #  PHASE 2 — CARD SELECTION
    # ══════════════════════════════════════════════════════════════

    def _show_cards(self, title: str, done_cb):
        self._done_cb = done_cb
        self._clear_wizard()
        self._draw_table()

        tk.Label(self.wizard, text=title, bg=self.PANEL, fg=self.TEXT,
                 font=("Arial", 16, "bold")).pack(pady=(12, 8))

        deck = tk.Frame(self.wizard, bg=self.PANEL)
        deck.pack(padx=20, pady=(0, 6))
        self.deck_btns = {}
        for row, suit in enumerate(SUITS):
            for col, rank in enumerate(RANKS):
                card = Card(rank + suit)
                sym = SUIT_SYMBOLS[suit]
                txt = f"{'10' if rank == 'T' else rank}{sym}"
                fg = "#d32f2f" if suit in ("h", "d") else "#111"
                btn = tk.Button(deck, text=txt,
                                command=lambda c=card: self._pick_card(c),
                                width=5, bg="white", fg=fg, relief="raised",
                                font=("Arial", 11, "bold"))
                btn.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                self.deck_btns[str(card)] = btn
            deck.grid_columnconfigure(col, weight=1)
        self._refresh_deck()

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(2, 12))
        self._cards_lbl = tk.Label(bf, text="", bg=self.PANEL, fg=self.ACCENT,
                                   font=("Arial", 12, "bold"))
        self._cards_lbl.pack(side="left", padx=(0, 16))
        self._upd_cards_lbl()
        tk.Button(bf, text="Очистить", command=self._clear_slot,
                  bg="#694142", fg="white", relief="flat",
                  font=("Arial", 11, "bold"), padx=10).pack(side="left", padx=(0, 10))
        tk.Button(bf, text="Готово →", command=done_cb,
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 13, "bold"), padx=20, pady=4).pack(side="left")

    def _upd_cards_lbl(self):
        parts = []
        h = [self._ct(c) for c in self.hole if c]
        if h:
            parts.append(f"Рука: {' '.join(h)}")
        b = [self._ct(self.board[i]) for i in range(self.max_board) if self.board[i]]
        if b:
            parts.append(f"Борд: {' '.join(b)}")
        t, i = self.active_slot
        parts.append(f"[{'Карта' if t == 'hole' else 'Борд'} {i + 1}]")
        if hasattr(self, "_cards_lbl"):
            self._cards_lbl.config(text="  ".join(parts))

    def _cards_done_pre(self):
        if not self.hole[0] or not self.hole[1]:
            messagebox.showerror("Ошибка", "Выберите 2 карты")
            return
        self._begin_action_round()

    def _cards_done_post(self):
        filled = sum(1 for i in range(self.max_board) if self.board[i])
        if filled < self.max_board:
            messagebox.showerror("Ошибка",
                                 f"Нужно {self.max_board} карт борда")
            return
        self._begin_action_round()

