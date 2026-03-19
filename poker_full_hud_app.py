import math
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk

from config import ALL_POSITIONS, RANKS, SUITS, SUIT_SYMBOLS
from logic.advisor import recommend_action
from models.card import Card
from models.hand import Hand
from utils.parser import parse_cards, parse_stack

TABLE_ORDER = ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
PREFLOP_ORDER = ["UTG", "UTG+1", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
POSTFLOP_ORDER = ["SB", "BB", "UTG", "UTG+1", "LJ", "HJ", "CO", "BTN"]


class PokerFullHUDApp:

    WIDTH = 1280
    HEIGHT = 960

    BG = "#1a1516"
    PANEL = "#242020"
    FELT = "#186b32"
    FELT_DEEP = "#14582a"
    RAIL = "#8b6a56"
    TEXT = "#f0e8e0"
    MUTED = "#b0a49a"
    ACCENT = "#ffd84d"

    CLR_FOLD = "#555252"
    CLR_CHECK = "#2f6f3a"
    CLR_CALL = "#2a7a5a"
    CLR_RAISE = "#952b35"
    CLR_ALLIN = "#6b1a22"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Poker HUD")
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+40+40")
        self.root.resizable(False, False)
        self.root.configure(bg=self.BG)

        self.positions: list[str] = []
        self.my_pos = "BTN"
        self.stacks: dict[str, float] = {}
        self._saved_stacks: dict[str, float] = {}
        self._saved_nplayers = 8
        self._first_hand = True
        self.active: set[str] = set()
        self.folded: set[str] = set()
        self.pot = 0.0
        self.bets: dict[str, float] = {}
        self.max_bet = 0.0
        self.stage = "preflop"
        self.action_queue: deque[str] = deque()
        self.current_actor: str | None = None

        self.hole: list[Card | None] = [None, None]
        self.board: list[Card | None] = [None] * 5
        self.max_board = 0
        self.active_slot = ("hole", 0)

        self.deck_btns: dict[str, tk.Button] = {}
        self.slot_rects: dict[tuple, tuple] = {}
        self.raise_var = tk.StringVar(value="2.5")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_columnconfigure(0, weight=1)

        cf = tk.Frame(self.root, bg=self.PANEL, highlightbackground="#4e4040", highlightthickness=1)
        cf.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        self.canvas = tk.Canvas(cf, bg=self.BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.wizard = tk.Frame(self.root, bg=self.PANEL,
                               highlightbackground="#4e4040", highlightthickness=1)
        self.wizard.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.root.after(100, self._show_setup)

    def _clear_wizard(self):
        for w in self.wizard.winfo_children():
            w.destroy()

    # ══════════════════════════════════════════════════════════════
    #  PHASE 1 — SETUP
    # ══════════════════════════════════════════════════════════════

    def _show_setup(self):
        self.current_actor = None
        self.positions = []
        self._clear_wizard()
        self._draw_table()

        tk.Label(self.wizard, text="Настройка раздачи",
                 bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold")
                 ).pack(pady=(16, 12))

        # Position
        pf = tk.Frame(self.wizard, bg=self.PANEL)
        pf.pack(pady=(0, 10))
        tk.Label(pf, text="Ваша позиция:", bg=self.PANEL, fg=self.MUTED,
                 font=("Arial", 13, "bold")).pack(side="left", padx=(0, 10))
        self._pos_btns = {}
        for pos in ALL_POSITIONS:
            b = tk.Button(pf, text=pos, width=7,
                          bg=self.ACCENT if pos == self.my_pos else "#333",
                          fg="#111" if pos == self.my_pos else self.TEXT,
                          relief="flat", font=("Arial", 11, "bold"),
                          command=lambda p=pos: self._sel_pos(p))
            b.pack(side="left", padx=2)
            self._pos_btns[pos] = b

        # Inputs
        inp = tk.Frame(self.wizard, bg=self.PANEL)
        inp.pack(pady=(0, 10))

        my_st = f"{self._saved_stacks.get(self.my_pos, 50.0):.1f}" if self._saved_stacks else "50"
        opp_example = next((v for k, v in self._saved_stacks.items() if k != self.my_pos), 100.0)
        opp_st = f"{opp_example:.1f}" if self._saved_stacks else "100"

        self._nplayers = tk.IntVar(value=self._saved_nplayers)
        self._my_stack_s = tk.StringVar(value=my_st)
        self._opp_stack_s = tk.StringVar(value=opp_st)

        for txt, var, w in [
            ("Игроков:", self._nplayers, 4),
            ("Мой стек bb:", self._my_stack_s, 8),
            ("Стек оппонентов bb:", self._opp_stack_s, 8),
        ]:
            tk.Label(inp, text=txt, bg=self.PANEL, fg=self.MUTED,
                     font=("Arial", 12, "bold")).pack(side="left", padx=(12, 4))
            if isinstance(var, tk.IntVar):
                tk.Spinbox(inp, from_=2, to=8, textvariable=var, width=w,
                           bg="#302828", fg=self.TEXT, relief="flat",
                           font=("Arial", 12, "bold")).pack(side="left")
            else:
                tk.Entry(inp, textvariable=var, width=w, bg="#302828",
                         fg=self.TEXT, insertbackground=self.TEXT, relief="flat",
                         font=("Arial", 12, "bold")).pack(side="left")

        # Per-player stack overrides (if stacks saved)
        if self._saved_stacks:
            tk.Label(self.wizard, text="Стеки с прошлой раздачи (можно изменить):",
                     bg=self.PANEL, fg=self.MUTED, font=("Arial", 11)
                     ).pack(pady=(4, 2))
            sf = tk.Frame(self.wizard, bg=self.PANEL)
            sf.pack(pady=(0, 8))
            self._stack_overrides: dict[str, tk.StringVar] = {}
            positions = self._pos_for_n(self._saved_nplayers)
            for pos in positions:
                v = tk.StringVar(value=f"{self._saved_stacks.get(pos, 100.0):.1f}")
                self._stack_overrides[pos] = v
                lbl_fg = self.ACCENT if pos == self.my_pos else self.MUTED
                tk.Label(sf, text=pos, bg=self.PANEL, fg=lbl_fg,
                         font=("Arial", 10, "bold")).pack(side="left", padx=(6, 2))
                tk.Entry(sf, textvariable=v, width=6, bg="#302828", fg=self.TEXT,
                         insertbackground=self.TEXT, relief="flat",
                         font=("Arial", 10, "bold")).pack(side="left", padx=(0, 4))
        else:
            self._stack_overrides = {}

        btns_f = tk.Frame(self.wizard, bg=self.PANEL)
        btns_f.pack(pady=(4, 16))
        tk.Button(btns_f, text="Начать раздачу →", command=self._start_hand,
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 14, "bold"), padx=30, pady=6
                  ).pack(side="left", padx=4)
        if not self._first_hand:
            tk.Button(btns_f, text="Сбросить стеки", command=self._reset_stacks,
                      bg=self.CLR_FOLD, fg="white", relief="flat",
                      font=("Arial", 11, "bold"), padx=14, pady=4
                      ).pack(side="left", padx=4)

    def _reset_stacks(self):
        self._saved_stacks = {}
        self._first_hand = True
        self._show_setup()

    def _sel_pos(self, pos):
        self.my_pos = pos
        for p, b in self._pos_btns.items():
            b.config(bg=self.ACCENT if p == pos else "#333",
                     fg="#111" if p == pos else self.TEXT)

    def _start_hand(self):
        n = self._nplayers.get()
        try:
            my_stack = float(self._my_stack_s.get())
            opp_stack = float(self._opp_stack_s.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат стека")
            return

        self.positions = self._pos_for_n(n)
        if self.my_pos not in self.positions:
            messagebox.showerror("Ошибка",
                                 f"{self.my_pos} нет при {n} игроках")
            return

        self._saved_nplayers = n

        if self._stack_overrides:
            self.stacks = {}
            for p in self.positions:
                if p in self._stack_overrides:
                    try:
                        self.stacks[p] = float(self._stack_overrides[p].get())
                    except ValueError:
                        self.stacks[p] = opp_stack
                else:
                    self.stacks[p] = my_stack if p == self.my_pos else opp_stack
        else:
            self.stacks = {p: (my_stack if p == self.my_pos else opp_stack)
                           for p in self.positions}
        self.active = set(self.positions)
        self.folded = set()
        self.bets = {p: 0.0 for p in self.positions}
        self.max_bet = 0.0
        self.stage = "preflop"
        self.max_board = 0
        self.board = [None] * 5
        self.hole = [None, None]
        self.active_slot = ("hole", 0)
        self.pot = 0.0

        if "SB" in self.positions:
            a = min(0.5, self.stacks["SB"])
            self.bets["SB"] = a
            self.stacks["SB"] -= a
        if "BB" in self.positions:
            a = min(1.0, self.stacks["BB"])
            self.bets["BB"] = a
            self.stacks["BB"] -= a
        self.max_bet = 1.0
        self.pot = sum(self.bets.values())

        self._show_cards("Выберите ваши карты", self._cards_done_pre)

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

    # ══════════════════════════════════════════════════════════════
    #  PHASE 3 — ACTION ROUND
    # ══════════════════════════════════════════════════════════════

    def _begin_action_round(self):
        order = PREFLOP_ORDER if self.stage == "preflop" else POSTFLOP_ORDER
        self.action_queue = deque(
            p for p in order if p in self.active and p not in self.folded)
        self._next_actor()

    def _next_actor(self):
        while self.action_queue and self.action_queue[0] in self.folded:
            self.action_queue.popleft()

        if not self.action_queue or len(self.active) <= 1:
            self._street_done()
            return

        pos = self.action_queue[0]
        self.current_actor = pos

        if pos == self.my_pos:
            self._show_my_turn()
        else:
            self._show_opp_turn(pos)

    # ── live-editable stacks row ─────────────────────────────────

    def _build_stacks_bar(self, parent):
        bar = tk.Frame(parent, bg="#1e1a1a")
        bar.pack(fill="x", padx=12, pady=(6, 2))

        self._live_stacks: dict[str, tk.StringVar] = {}
        for pos in self.positions:
            dead = pos in self.folded
            fg = self.ACCENT if pos == self.my_pos else ("#666" if dead else self.MUTED)
            tk.Label(bar, text=pos, bg="#1e1a1a", fg=fg,
                     font=("Arial", 9, "bold")).pack(side="left", padx=(4, 1))
            v = tk.StringVar(value=f"{self.stacks.get(pos, 0):.1f}")
            self._live_stacks[pos] = v
            tk.Entry(bar, textvariable=v, width=5, bg="#302828", fg=self.TEXT,
                     insertbackground=self.TEXT, relief="flat",
                     font=("Arial", 9, "bold")).pack(side="left", padx=(0, 3))

        tk.Label(bar, text="Банк:", bg="#1e1a1a", fg=self.MUTED,
                 font=("Arial", 9, "bold")).pack(side="left", padx=(8, 2))
        self._live_pot = tk.StringVar(value=f"{self.pot:.1f}")
        tk.Entry(bar, textvariable=self._live_pot, width=6, bg="#302828",
                 fg=self.TEXT, insertbackground=self.TEXT, relief="flat",
                 font=("Arial", 9, "bold")).pack(side="left")

    def _sync_live_stacks(self):
        if not hasattr(self, "_live_stacks"):
            return
        for pos, var in self._live_stacks.items():
            try:
                self.stacks[pos] = float(var.get())
            except ValueError:
                pass
        try:
            self.pot = float(self._live_pot.get())
        except ValueError:
            pass

    # ── opponent turn ────────────────────────────────────────────

    def _show_opp_turn(self, pos: str):
        self._clear_wizard()
        self._draw_table()

        to_call = max(0.0, self.max_bet - self.bets.get(pos, 0))

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(10, 4))

        tk.Label(f, text=f"Что сделал {pos}?", bg=self.PANEL, fg=self.TEXT,
                 font=("Arial", 22, "bold")).pack(pady=(0, 4))
        tk.Label(f, text=(f"Банк: {self.pot:.1f} bb  |  "
                          f"Ставка: {self.max_bet:.1f} bb  |  "
                          f"Стек {pos}: {self.stacks[pos]:.1f} bb"),
                 bg=self.PANEL, fg=self.MUTED, font=("Arial", 12)
                 ).pack(pady=(0, 8))

        row = tk.Frame(f, bg=self.PANEL)
        row.pack()
        self._action_buttons(row, pos, to_call)

        self._build_stacks_bar(self.wizard)

    # ── my turn ──────────────────────────────────────────────────

    def _show_my_turn(self):
        self._clear_wizard()
        self._draw_table()

        to_call = max(0.0, self.max_bet - self.bets.get(self.my_pos, 0))

        if to_call <= 0:
            oa, btc = "check", None
        else:
            oa, btc = "raise", to_call
        board_cards = [self.board[i] for i in range(self.max_board)
                       if self.board[i]]
        hand = Hand(self.hole[0], self.hole[1])
        pot_bb = self.pot if self.stage != "preflop" else None

        advice = recommend_action(
            hand=hand, position=self.my_pos,
            stack=self.stacks[self.my_pos],
            opponent_action=oa, bet_to_call=btc,
            num_players=len(self.active),
            board=board_cards, stage=self.stage, pot_size_bb=pot_bb,
        )

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(10, 4))

        tk.Label(f, text=f"Твой ход ({self.my_pos})", bg=self.PANEL,
                 fg=self.ACCENT, font=("Arial", 22, "bold")).pack(pady=(0, 6))
        tk.Label(f, text=f"Рекомендация: {advice}",
                 bg="#302424", fg="#f6e58f",
                 font=("Arial", 18, "bold"), padx=20, pady=12
                 ).pack(pady=(0, 6))
        tk.Label(f, text=(f"Банк: {self.pot:.1f} bb  |  "
                          f"До колла: {to_call:.1f} bb  |  "
                          f"Стек: {self.stacks[self.my_pos]:.1f} bb"),
                 bg=self.PANEL, fg=self.MUTED, font=("Arial", 12)
                 ).pack(pady=(0, 8))

        row = tk.Frame(f, bg=self.PANEL)
        row.pack()
        self._action_buttons(row, self.my_pos, to_call)

        self._build_stacks_bar(self.wizard)

    # ── shared action buttons ────────────────────────────────────

    def _action_buttons(self, parent, pos, to_call):
        stack = self.stacks.get(pos, 0)
        already = self.bets.get(pos, 0)
        min_raise = max(self.max_bet * 2, 2.5)
        max_raise = already + stack

        def btn(text, color, cmd, w=8):
            return tk.Button(parent, text=text, command=cmd, bg=color,
                             fg="white", relief="flat",
                             font=("Arial", 14, "bold"), width=w, height=2)

        # Row 1: Fold + Check/Call + Raise button
        row1 = tk.Frame(parent, bg=self.PANEL)
        row1.pack(fill="x", pady=(0, 6))

        btn("Фолд", self.CLR_FOLD,
            lambda: self._do(pos, "fold")).pack(in_=row1, side="left", padx=4)

        if to_call <= 0:
            btn("Чек", self.CLR_CHECK,
                lambda: self._do(pos, "check")).pack(in_=row1, side="left", padx=4)
        else:
            btn(f"Колл {to_call:.1f}", self.CLR_CALL,
                lambda: self._do(pos, "call"), w=11).pack(in_=row1, side="left", padx=4)

        self.raise_var.set(f"{min(min_raise, max_raise):.1f}")

        btn("Рейз →", self.CLR_RAISE,
            lambda: self._do(pos, "raise"), w=9).pack(in_=row1, side="left", padx=4)

        tk.Entry(row1, textvariable=self.raise_var, width=7, bg="#302828",
                 fg=self.TEXT, insertbackground=self.TEXT, relief="flat",
                 font=("Arial", 14, "bold")).pack(side="left", padx=2, ipady=8)
        tk.Label(row1, text="bb", bg=self.PANEL, fg=self.MUTED,
                 font=("Arial", 11)).pack(side="left")

        # Row 2: % buttons + slider
        row2 = tk.Frame(parent, bg=self.PANEL)
        row2.pack(fill="x")

        self._slider_updating = False

        def _set_raise(val: float):
            val = max(min(val, max_raise), min_raise)
            self.raise_var.set(f"{val:.1f}")
            self._slider_updating = True
            self._raise_slider.set(val)
            self._slider_updating = False

        def set_pct(pct):
            self._sync_live_stacks()
            raw = self.pot * (pct / 100.0)
            _set_raise(raw)

        for pct in [33, 50, 75, 100]:
            raw = self.pot * (pct / 100.0)
            actual = max(min(raw, max_raise), min_raise)
            label = f"{pct}%" if pct < 100 else "Пот"
            below = raw < min_raise
            display = f"{actual:.1f}" if below else f"{raw:.1f}"
            bg = "#2a2525" if below else "#3a3030"
            tk.Button(row2, text=f"{label}\n{display}",
                      command=lambda p=pct: set_pct(p),
                      bg=bg, fg="#888" if below else self.TEXT, relief="flat",
                      font=("Arial", 10, "bold"), width=6, height=2,
                      ).pack(side="left", padx=2)

        def do_allin():
            _set_raise(max_raise)

        tk.Button(row2, text=f"Олл-ин\n{max_raise:.1f}",
                  command=do_allin,
                  bg=self.CLR_ALLIN, fg="white", relief="flat",
                  font=("Arial", 10, "bold"), width=7, height=2,
                  ).pack(side="left", padx=4)

        def on_slider(val):
            if not self._slider_updating:
                self.raise_var.set(f"{float(val):.1f}")

        slider_from = max(min_raise, 0.1)
        slider_to = max(max_raise, slider_from + 0.1)

        self._raise_slider = tk.Scale(
            row2, from_=slider_from, to=slider_to,
            orient="horizontal", resolution=0.5,
            command=on_slider,
            bg=self.PANEL, fg=self.TEXT, troughcolor="#302828",
            highlightthickness=0, sliderrelief="flat",
            font=("Arial", 9), showvalue=False, length=280,
        )
        self._raise_slider.set(float(self.raise_var.get()))
        self._raise_slider.pack(side="left", padx=(8, 0), fill="x", expand=True)

    # ── apply action ─────────────────────────────────────────────

    def _do(self, pos: str, action: str):
        self._sync_live_stacks()
        self.action_queue.popleft()
        already = self.bets.get(pos, 0.0)

        if action == "fold":
            self.folded.add(pos)
            self.active.discard(pos)

        elif action == "check":
            pass

        elif action == "call":
            amt = min(self.max_bet - already, self.stacks[pos])
            self.stacks[pos] -= amt
            self.bets[pos] = already + amt
            self.pot += amt

        elif action == "raise":
            try:
                to = float(self.raise_var.get())
            except ValueError:
                to = self.max_bet * 2.5
            amt = min(to - already, self.stacks[pos])
            self.stacks[pos] -= amt
            self.bets[pos] = already + amt
            self.pot += amt
            if self.bets[pos] > self.max_bet:
                self.max_bet = self.bets[pos]
                self._reopen(pos)

        elif action == "allin":
            amt = self.stacks[pos]
            self.stacks[pos] = 0
            self.bets[pos] = already + amt
            self.pot += amt
            if self.bets[pos] > self.max_bet:
                self.max_bet = self.bets[pos]
                self._reopen(pos)

        self._next_actor()

    def _reopen(self, raiser: str):
        order = PREFLOP_ORDER if self.stage == "preflop" else POSTFLOP_ORDER
        remaining = deque(
            p for p in order
            if p in self.active and p != raiser and p not in self.folded
        )
        self.action_queue = remaining

    # ── street transition ────────────────────────────────────────

    def _street_done(self):
        self.current_actor = None

        if len(self.active) <= 1:
            self._hand_over()
            return

        self.bets = {p: 0.0 for p in self.positions}
        self.max_bet = 0.0

        stages = {"preflop": ("flop", 3), "flop": ("turn", 4),
                  "turn": ("river", 5)}
        if self.stage in stages:
            nxt, bc = stages[self.stage]
            self._show_transition(nxt, bc)
        else:
            self._hand_over()

    def _show_transition(self, nxt: str, board_count: int):
        self._clear_wizard()
        self._draw_table()
        names = {"flop": "Флоп", "turn": "Терн", "river": "Ривер"}

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=20)
        tk.Label(f, text=f"Переход на {names[nxt]}  |  Банк: {self.pot:.1f} bb",
                 bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold")
                 ).pack(pady=(0, 12))
        tk.Button(f, text=f"Ввести карты {names[nxt]} →",
                  command=lambda: self._go_street(nxt, board_count),
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 14, "bold"), padx=20, pady=6).pack()
        tk.Button(f, text="Завершить раздачу", command=self._hand_over,
                  bg=self.CLR_FOLD, fg="white", relief="flat",
                  font=("Arial", 12, "bold"), padx=14, pady=4
                  ).pack(pady=(10, 0))

    def _go_street(self, stage: str, board_count: int):
        self.stage = stage
        self.max_board = board_count
        for i in range(self.max_board):
            if not self.board[i]:
                self.active_slot = ("board", i)
                break
        names = {"flop": "Флоп", "turn": "Терн", "river": "Ривер"}
        self._show_cards(f"Введите карты {names[stage]}", self._cards_done_post)

    def _hand_over(self, winner: str | None = None):
        self.current_actor = None

        if winner:
            self.stacks[winner] = self.stacks.get(winner, 0) + self.pot
            self.pot = 0
        elif len(self.active) <= 1:
            w = next(iter(self.active), None)
            if w:
                self.stacks[w] = self.stacks.get(w, 0) + self.pot
                self.pot = 0

        self._saved_stacks = dict(self.stacks)
        self._first_hand = False

        self._clear_wizard()
        self._draw_table()
        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 6))

        if winner:
            tk.Label(f, text=f"Победил {winner}  |  Забрал банк {self.pot:.1f} → стек: {self.stacks[winner]:.1f} bb",
                     bg=self.PANEL, fg=self.ACCENT, font=("Arial", 16, "bold")
                     ).pack(pady=(0, 10))
        elif len(self.active) <= 1:
            w = next(iter(self.active), "—")
            tk.Label(f, text=f"Все сфолдили — победил {w}  |  Банк забран",
                     bg=self.PANEL, fg=self.ACCENT, font=("Arial", 16, "bold")
                     ).pack(pady=(0, 10))
        else:
            tk.Label(f, text=f"Шоудаун  |  Банк: {self.pot:.1f} bb  |  Кто выиграл?",
                     bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold")
                     ).pack(pady=(0, 10))
            wf = tk.Frame(f, bg=self.PANEL)
            wf.pack(pady=(0, 10))
            for pos in sorted(self.active):
                tk.Button(wf, text=pos, width=8,
                          bg=self.ACCENT, fg="#111", relief="flat",
                          font=("Arial", 13, "bold"),
                          command=lambda p=pos: self._hand_over(winner=p)
                          ).pack(side="left", padx=4)
            tk.Label(f, text="(Нажми позицию победителя — банк уйдёт ему в стек)",
                     bg=self.PANEL, fg=self.MUTED, font=("Arial", 11)
                     ).pack(pady=(0, 6))

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(4, 14))
        tk.Button(bf, text="▶ Продолжить игру", command=self._continue_game,
                  bg="#2f6f3a", fg="white", relief="flat",
                  font=("Arial", 14, "bold"), padx=30, pady=6
                  ).pack(side="left", padx=4)
        tk.Button(bf, text="Настройки раздачи", command=self._next_hand,
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 11, "bold"), padx=14, pady=4
                  ).pack(side="left", padx=4)
        tk.Button(bf, text="Править стеки", command=self._manual_edit,
                  bg="#45515d", fg="white", relief="flat",
                  font=("Arial", 11, "bold"), padx=14, pady=4
                  ).pack(side="left", padx=4)

    def _continue_game(self):
        n = len(self.positions)
        old_seats = self._seat_order()
        seat_stacks = [self.stacks.get(pos, 0) for pos in old_seats]

        pos_list = [p for p in TABLE_ORDER if p in self.positions]
        idx = pos_list.index(self.my_pos)
        self.my_pos = pos_list[(idx + 1) % len(pos_list)]

        self.positions = self._pos_for_n(n)
        new_seats = self._seat_order()
        self.stacks = {pos: seat_stacks[i] for i, pos in enumerate(new_seats)}

        self._saved_stacks = dict(self.stacks)
        self._saved_nplayers = n
        self._first_hand = False

        self.active = set(self.positions)
        self.folded = set()
        self.bets = {p: 0.0 for p in self.positions}
        self.max_bet = 0.0
        self.stage = "preflop"
        self.max_board = 0
        self.board = [None] * 5
        self.hole = [None, None]
        self.active_slot = ("hole", 0)
        self.pot = 0.0

        if "SB" in self.positions:
            a = min(0.5, self.stacks["SB"])
            self.bets["SB"] = a
            self.stacks["SB"] -= a
        if "BB" in self.positions:
            a = min(1.0, self.stacks["BB"])
            self.bets["BB"] = a
            self.stacks["BB"] -= a
        self.max_bet = 1.0
        self.pot = sum(self.bets.values())

        self._show_cards("Выберите ваши карты", self._cards_done_pre)

    def _next_hand(self):
        self._saved_stacks = dict(self.stacks)
        self._show_setup()

    def _manual_edit(self):
        self._clear_wizard()
        tk.Label(self.wizard, text="Ручная правка стеков",
                 bg=self.PANEL, fg=self.TEXT, font=("Arial", 16, "bold")
                 ).pack(pady=(14, 10))

        sf = tk.Frame(self.wizard, bg=self.PANEL)
        sf.pack(pady=(0, 8))
        self._edit_vars: dict[str, tk.StringVar] = {}
        for pos in self.positions:
            v = tk.StringVar(value=f"{self.stacks.get(pos, 0):.1f}")
            self._edit_vars[pos] = v
            lbl_fg = self.ACCENT if pos == self.my_pos else self.MUTED
            tk.Label(sf, text=pos, bg=self.PANEL, fg=lbl_fg,
                     font=("Arial", 11, "bold")).pack(side="left", padx=(8, 2))
            tk.Entry(sf, textvariable=v, width=7, bg="#302828", fg=self.TEXT,
                     insertbackground=self.TEXT, relief="flat",
                     font=("Arial", 11, "bold")).pack(side="left", padx=(0, 6))

        pf = tk.Frame(self.wizard, bg=self.PANEL)
        pf.pack(pady=(0, 4))
        tk.Label(pf, text="Банк:", bg=self.PANEL, fg=self.MUTED,
                 font=("Arial", 11, "bold")).pack(side="left", padx=(0, 4))
        self._edit_pot = tk.StringVar(value=f"{self.pot:.1f}")
        tk.Entry(pf, textvariable=self._edit_pot, width=8, bg="#302828",
                 fg=self.TEXT, insertbackground=self.TEXT, relief="flat",
                 font=("Arial", 11, "bold")).pack(side="left")

        tk.Button(self.wizard, text="Применить и продолжить",
                  command=self._apply_manual_edit,
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 13, "bold"), padx=20, pady=6
                  ).pack(pady=(8, 14))

    def _apply_manual_edit(self):
        for pos, var in self._edit_vars.items():
            try:
                self.stacks[pos] = float(var.get())
            except ValueError:
                pass
        try:
            self.pot = float(self._edit_pot.get())
        except ValueError:
            pass
        self._saved_stacks = dict(self.stacks)
        self._hand_over()

    def _manual_edit_midgame(self):
        self._clear_wizard()
        tk.Label(self.wizard, text="Ручная правка (во время раздачи)",
                 bg=self.PANEL, fg=self.TEXT, font=("Arial", 16, "bold")
                 ).pack(pady=(14, 10))

        sf = tk.Frame(self.wizard, bg=self.PANEL)
        sf.pack(pady=(0, 8))
        self._mg_vars: dict[str, tk.StringVar] = {}
        for pos in self.positions:
            v = tk.StringVar(value=f"{self.stacks.get(pos, 0):.1f}")
            self._mg_vars[pos] = v
            dead = pos in self.folded
            lbl_fg = self.ACCENT if pos == self.my_pos else ("#666" if dead else self.MUTED)
            tk.Label(sf, text=pos, bg=self.PANEL, fg=lbl_fg,
                     font=("Arial", 11, "bold")).pack(side="left", padx=(8, 2))
            tk.Entry(sf, textvariable=v, width=7, bg="#302828", fg=self.TEXT,
                     insertbackground=self.TEXT, relief="flat",
                     font=("Arial", 11, "bold")).pack(side="left", padx=(0, 6))

        pf = tk.Frame(self.wizard, bg=self.PANEL)
        pf.pack(pady=(0, 4))
        tk.Label(pf, text="Банк:", bg=self.PANEL, fg=self.MUTED,
                 font=("Arial", 11, "bold")).pack(side="left", padx=(0, 4))
        self._mg_pot = tk.StringVar(value=f"{self.pot:.1f}")
        tk.Entry(pf, textvariable=self._mg_pot, width=8, bg="#302828",
                 fg=self.TEXT, insertbackground=self.TEXT, relief="flat",
                 font=("Arial", 11, "bold")).pack(side="left")

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(8, 14))
        tk.Button(bf, text="Применить и продолжить",
                  command=self._apply_mg_edit,
                  bg="#8c5e2f", fg="white", relief="flat",
                  font=("Arial", 13, "bold"), padx=20, pady=6
                  ).pack(side="left", padx=4)
        tk.Button(bf, text="Отмена",
                  command=lambda: self._next_actor(),
                  bg=self.CLR_FOLD, fg="white", relief="flat",
                  font=("Arial", 11, "bold"), padx=14, pady=4
                  ).pack(side="left", padx=4)

    def _apply_mg_edit(self):
        for pos, var in self._mg_vars.items():
            try:
                self.stacks[pos] = float(var.get())
            except ValueError:
                pass
        try:
            self.pot = float(self._mg_pot.get())
        except ValueError:
            pass
        self._next_actor()

    # ══════════════════════════════════════════════════════════════
    #  TABLE DRAWING
    # ══════════════════════════════════════════════════════════════

    def _draw_table(self):
        c = self.canvas
        c.update_idletasks()
        cw = max(c.winfo_width(), 800)
        ch = max(c.winfo_height(), 400)
        c.delete("all")
        self.slot_rects = {}

        cx, cy = cw // 2, ch // 2 - 50
        rx = min(cw // 2 - 60, 370)
        ry = min(ch // 2 - 100, 170)

        c.create_oval(cx - rx - 24, cy - ry - 24, cx + rx + 24, cy + ry + 24,
                      fill=self.RAIL, outline="#cbb8aa", width=3)
        c.create_oval(cx - rx, cy - ry, cx + rx, cy + ry,
                      fill=self.FELT, outline="#2d5f35", width=2)
        c.create_oval(cx - rx + 26, cy - ry + 26, cx + rx - 26, cy + ry - 26,
                      fill=self.FELT_DEEP, outline="#347340", width=2)

        c.create_text(cx, cy - 30, text=f"Банк: {self.pot:.1f} BB",
                      fill="#e7d8a5", font=("Arial", 15, "bold"))

        if not self.positions:
            return

        seats = self._seat_order()
        n = len(seats)

        for i, pos in enumerate(seats):
            angle = math.pi / 2 - 2 * math.pi * i / n
            if i == 0:
                sx, sy = cx, cy + ry + 48
            else:
                sx = cx + (rx + 60) * math.cos(angle)
                sy = cy + (ry + 46) * math.sin(angle)
            sx, sy = int(sx), int(sy)

            acting = pos == self.current_actor
            me = pos == self.my_pos
            dead = pos in self.folded

            if acting:
                fill, fg, ol = "#ff6644", "#fff", "#ff4422"
            elif me:
                fill, fg, ol = self.ACCENT, "#111", "#111"
            elif dead:
                fill, fg, ol = "#444", "#777", "#333"
            else:
                fill, fg, ol = "#223328", self.TEXT, "#111"

            c.create_oval(sx - 40, sy - 20, sx + 40, sy + 20,
                          fill=fill, outline=ol, width=2 if acting else 1)
            c.create_text(sx, sy - 5, text=pos, fill=fg,
                          font=("Arial", 11, "bold"))
            c.create_text(sx, sy + 11,
                          text=f"{self.stacks.get(pos, 0):.0f} bb",
                          fill=fg if not dead else "#555",
                          font=("Arial", 9))

            bet = self.bets.get(pos, 0)
            if bet > 0:
                bx = sx + (cx - sx) * 0.35
                by = sy + (cy - sy) * 0.35
                c.create_text(int(bx), int(by), text=f"{bet:.1f}",
                              fill="#ddd", font=("Arial", 10, "bold"))

        # Board
        bw, bh, gap = 54, 76, 7
        total_w = self.max_board * bw + max(self.max_board - 1, 0) * gap
        bx0 = cx - total_w / 2
        by0 = cy + 5
        for i in range(self.max_board):
            x = bx0 + i * (bw + gap)
            bounds = (x, by0, x + bw, by0 + bh)
            self.slot_rects[("board", i)] = bounds
            self._draw_card(bounds, self.board[i], ("board", i), 15)

        # Hole cards — below my seat
        hw, hh, hg = 72, 100, 8
        hx1 = cx - hw - hg // 2
        hx2 = cx + hg // 2
        hy = cy + ry + 78
        self.slot_rects[("hole", 0)] = (hx1, hy, hx1 + hw, hy + hh)
        self.slot_rects[("hole", 1)] = (hx2, hy, hx2 + hw, hy + hh)
        self._draw_card(self.slot_rects[("hole", 0)], self.hole[0],
                        ("hole", 0), 22)
        self._draw_card(self.slot_rects[("hole", 1)], self.hole[1],
                        ("hole", 1), 22)

    def _draw_card(self, bounds, card, target, fsize):
        c = self.canvas
        x1, y1, x2, y2 = [int(v) for v in bounds]
        active = self.active_slot == target
        c.create_rectangle(x1, y1, x2, y2, fill="#fff",
                           outline=self.ACCENT if active else "#222",
                           width=4 if active else 2)
        if card is None:
            c.create_text((x1 + x2) // 2, (y1 + y2) // 2, text="—",
                          fill="#aaa", font=("Arial", fsize, "bold"))
        else:
            rank = "10" if card.rank == "T" else card.rank
            sym = SUIT_SYMBOLS[card.suit]
            color = "#d32f2f" if card.suit in ("h", "d") else "#111"
            c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                          text=f"{rank}\n{sym}", fill=color,
                          font=("Arial", fsize, "bold"))

    def _seat_order(self) -> list[str]:
        if self.my_pos not in TABLE_ORDER:
            return self.positions
        idx = TABLE_ORDER.index(self.my_pos)
        rotated = TABLE_ORDER[idx:] + TABLE_ORDER[:idx]
        return [p for p in rotated if p in self.positions]

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


if __name__ == "__main__":
    root = tk.Tk()
    PokerFullHUDApp(root)
    root.mainloop()
