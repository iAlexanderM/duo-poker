import tkinter as tk
from tkinter import messagebox

from config import ALL_POSITIONS

class PhaseSetupMixin:
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
        self._action_undo_stack.clear()

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

