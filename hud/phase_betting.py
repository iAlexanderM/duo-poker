import tkinter as tk
from collections import deque
from tkinter import messagebox

from logic.advisor import recommend_action
from models.hand import Hand

from hud.ordering import (
    PREFLOP_ORDER,
    _button_centric_order,
    _postflop_acting_order,
    _street_order,
)
from hud.preflop_dead import apply_preflop_dead
from logic.side_pots import (
    breakdown_matches_pot,
    build_showdown_pots,
    side_pot_lines_for_ui,
)


class PhaseBettingMixin:
    # ══════════════════════════════════════════════════════════════
    #  PHASE 3 — ACTION ROUND
    # ══════════════════════════════════════════════════════════════

    def _post_preflop_dead_money(self):
        self.pot, self.max_bet, ab = apply_preflop_dead(
            self.positions,
            self.stacks,
            self.bets,
            getattr(self, "ante_bb", 0.0),
            getattr(self, "ante_scope", "all"),
        )
        self._seat_ante_posted = ab
        self._hand_pot_contributed = {
            p: round(float(ab.get(p, 0)) + float(self.bets.get(p, 0)), 4)
            for p in self.positions
        }

    def _begin_action_round(self):
        self._action_undo_stack.clear()
        # Префлоп: UTG → … → BB (первый после блайндов). Постфлоп: с SB (в HU: BB → SB).
        # После рейза очередь пересобирается от следующего за рейзером по кругу (_reopen).
        order = _street_order(self.stage, self.positions)
        self.action_queue = deque(
            p for p in order if p in self.active and p not in self.folded)
        self._next_actor()

    def _active_clockwise_after(self, after_pos: str) -> deque[str]:
        """Активные игроки по часовой, начиная со следующего места после рейза/олл-ина."""
        ring = _street_order(self.stage, self.positions)
        if not ring or after_pos not in ring:
            full = (
                PREFLOP_ORDER
                if self.stage == "preflop"
                else _postflop_acting_order(self.positions)
            )
            return deque(
                p for p in full
                if p in self.active and p != after_pos and p not in self.folded
            )
        n = len(ring)
        start = (ring.index(after_pos) + 1) % n
        out: list[str] = []
        for step in range(n - 1):
            pos = ring[(start + step) % n]
            if pos in self.active and pos not in self.folded:
                out.append(pos)
        return deque(out)

    def _fold_until_actor(self, target_pos: str):
        """Сфолдить всех в очереди до target_pos (не включая); один шаг «Назад» откатывает пакет."""
        if not self.action_queue or self.current_actor is None:
            return
        if target_pos not in self.action_queue:
            return
        if self.action_queue[0] == target_pos:
            return

        self._sync_live_stacks()
        self._push_action_undo()

        while self.action_queue and self.action_queue[0] != target_pos:
            pos = self.action_queue.popleft()
            self.folded.add(pos)
            self.active.discard(pos)

        self._next_actor()

    def _next_actor(self):
        while self.action_queue and self.action_queue[0] in self.folded:
            self.action_queue.popleft()

        if not self.action_queue or len(self.active) <= 1:
            self._street_done()
            return

        pos = self.action_queue[0]
        self.current_actor = pos

        stack = max(0.0, self.stacks.get(pos, 0))
        to_call = max(0.0, self.max_bet - self.bets.get(pos, 0))
        # Олл-ин / 0 bb: не спрашивать ни у героя, ни «что сделал X» — авто чек или колл на 0.
        # Не вызывать здесь _sync_live_stacks: старые Entry после олл-ина вернут стек из UI.
        if stack <= 1e-6:
            self._do(pos, "check" if to_call <= 0 else "call")
            return

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
            tk.Entry(bar, textvariable=v, width=7, bg="#302828", fg=self.TEXT,
                     insertbackground=self.TEXT, relief="flat",
                     font=("Arial", 9, "bold")).pack(side="left", padx=(0, 3))

        tk.Label(bar, text="Банк:", bg="#1e1a1a", fg=self.MUTED,
                 font=("Arial", 9, "bold")).pack(side="left", padx=(8, 2))
        self._live_pot = tk.StringVar(value=f"{self.pot:.1f}")
        tk.Entry(bar, textvariable=self._live_pot, width=10, bg="#302828",
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

    def _refresh_live_stack_widgets(self):
        """После изменения self.stacks/pot в коде — иначе Entry перезатрут модель при следующем sync."""
        if hasattr(self, "_live_stacks"):
            for p, var in self._live_stacks.items():
                var.set(f"{self.stacks.get(p, 0):.1f}")
        if hasattr(self, "_live_pot"):
            self._live_pot.set(f"{self.pot:.1f}")

    # ── opponent turn ────────────────────────────────────────────

    def _wizard_undo_bar(self):
        top = tk.Frame(self.wizard, bg=self.PANEL)
        top.pack(fill="x", padx=8, pady=(4, 2))
        tk.Button(
            top, text="← Назад", command=self._undo_action,
            state="normal" if self._action_undo_stack else "disabled",
            bg="#45515d", fg="white", relief="flat",
            font=("Arial", 11, "bold"), padx=12, pady=4,
        ).pack(side="right")

    def _snapshot_action_state(self) -> dict:
        return {
            "stacks": dict(self.stacks),
            "bets": dict(self.bets),
            "pot": self.pot,
            "max_bet": self.max_bet,
            "active": set(self.active),
            "folded": set(self.folded),
            "action_queue": deque(self.action_queue),
        }

    def _push_action_undo(self):
        if len(self._action_undo_stack) >= 200:
            self._action_undo_stack.pop(0)
        self._action_undo_stack.append(self._snapshot_action_state())

    def _undo_action(self):
        if not self._action_undo_stack:
            return
        s = self._action_undo_stack.pop()
        self.stacks = dict(s["stacks"])
        self.bets = dict(s["bets"])
        self.pot = s["pot"]
        self.max_bet = s["max_bet"]
        self.active = set(s["active"])
        self.folded = set(s["folded"])
        self.action_queue = deque(s["action_queue"])
        self.current_actor = self.action_queue[0] if self.action_queue else None
        if not self.action_queue:
            self._next_actor()
            return
        if self.current_actor == self.my_pos:
            self._show_my_turn()
        else:
            self._show_opp_turn(self.current_actor)

    def _show_opp_turn(self, pos: str):
        self._clear_wizard()
        self._draw_table()
        self._wizard_undo_bar()

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
        self._wizard_undo_bar()

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

        slider_from = float(max(min_raise, 0.1))
        slider_to = float(max(max_raise, slider_from + 0.1))
        # Tk.Scale на части сборок плохо масштабирует большой диапазон при малой длине — даём запас по длине.
        self._raise_slider = tk.Scale(
            row2, from_=slider_from, to=slider_to,
            orient="horizontal", resolution=0.5,
            command=on_slider,
            bg=self.PANEL, fg=self.TEXT, troughcolor="#302828",
            highlightthickness=0, sliderrelief="flat",
            font=("Arial", 9), showvalue=False, length=380,
        )
        self._raise_slider.set(float(self.raise_var.get()))
        self._raise_slider.pack(side="left", padx=(8, 0), fill="x", expand=True)

    # ── apply action ─────────────────────────────────────────────

    def _do(self, pos: str, action: str):
        self._sync_live_stacks()
        self._push_action_undo()
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
            self._hand_pot_contributed[pos] = round(
                self._hand_pot_contributed.get(pos, 0) + amt, 4)

        elif action == "raise":
            try:
                to = float(self.raise_var.get())
            except ValueError:
                to = self.max_bet * 2.5
            amt = min(to - already, self.stacks[pos])
            self.stacks[pos] -= amt
            self.bets[pos] = already + amt
            self.pot += amt
            self._hand_pot_contributed[pos] = round(
                self._hand_pot_contributed.get(pos, 0) + amt, 4)
            if self.bets[pos] > self.max_bet:
                self.max_bet = self.bets[pos]
                self._reopen(pos)

        elif action == "allin":
            amt = self.stacks[pos]
            self.stacks[pos] = 0
            self.bets[pos] = already + amt
            self.pot += amt
            self._hand_pot_contributed[pos] = round(
                self._hand_pot_contributed.get(pos, 0) + amt, 4)
            if self.bets[pos] > self.max_bet:
                self.max_bet = self.bets[pos]
                self._reopen(pos)

        self._refresh_live_stack_widgets()
        self._next_actor()

    def _reopen(self, raiser: str):
        self.action_queue = self._active_clockwise_after(raiser)

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

    def _split_pot_among(self, winners: list[str]) -> tuple[float, float]:
        """Делит self.pot поровну между winners. Возвращает (банк до сплита, доля одного)."""
        pot_val = float(self.pot)
        n = len(winners)
        if n <= 0:
            return pot_val, 0.0
        per = pot_val / n
        for w in winners:
            self.stacks[w] = self.stacks.get(w, 0) + per
        dust = pot_val - per * n
        if abs(dust) > 1e-9:
            self.stacks[winners[0]] = self.stacks.get(winners[0], 0) + dust
        self.pot = 0.0
        return pot_val, per

    _SIDE_POT_TOL = 0.15

    def _side_pot_tol_dynamic(self) -> float:
        p = float(self.pot)
        return max(2.0, 0.02 * p) if p > 1e-9 else 2.0

    def _try_begin_side_pot_showdown(self) -> bool:
        hc = getattr(self, "_hand_pot_contributed", None) or {}
        pot_now = float(self.pot)
        tol = self._side_pot_tol_dynamic()
        alive = set(self.active)
        if not breakdown_matches_pot(hc, alive, pot_now, tol):
            return False

        pots, uncalled = build_showdown_pots(hc, alive)
        if not pots:
            return False

        self._begin_side_pot_showdown(pots, uncalled)
        return True

    def _live_bank_labels(self) -> list[str] | None:
        """Подписи банков на столе (сайд-поты отдельно); None — показать один общий."""
        if not self.positions or self.pot <= 1e-9:
            return None
        hc = getattr(self, "_hand_pot_contributed", None) or {}
        alive = set(self.active)
        if not breakdown_matches_pot(hc, alive, float(self.pot), self._side_pot_tol_dynamic()):
            return None
        numbered, unc = side_pot_lines_for_ui(hc, alive)
        lines = [f"Банк {n}: {amt:.1f}" for n, amt, _ in numbered]
        for p, a in sorted(unc.items()):
            if a > 1e-9:
                lines.append(f"↩ {p}: {a:.1f}")
        return lines

    def _begin_side_pot_showdown(
        self,
        pots: list[tuple[float, frozenset[str]]],
        uncalled: dict[str, float],
    ):
        self._sd_summary_prefix = []
        for p, a in sorted(uncalled.items(), key=lambda x: x[0]):
            if a <= 1e-9:
                continue
            self.stacks[p] = self.stacks.get(p, 0) + a
            self._sd_summary_prefix.append(f"Невызванные {a:.1f} bb → {p}")
        uct = sum(uncalled.values())
        self.pot = max(0.0, self.pot - uct)

        self._sd_pots = pots
        self._sd_idx = 0
        self._sd_outcomes: list[tuple[int, float, list[str]]] = []
        self._show_showdown_pot_step()

    def _distribute_sidepot_amount(self, amt: float, winners: list[str]):
        n = len(winners)
        if n <= 0:
            return
        per = amt / n
        for w in winners:
            self.stacks[w] = self.stacks.get(w, 0) + per
        dust = amt - per * n
        if abs(dust) > 1e-9:
            self.stacks[winners[0]] = self.stacks.get(winners[0], 0) + dust
        self.pot = max(0.0, self.pot - amt)

    def _show_showdown_pot_step(self):
        self._clear_wizard()
        self._draw_table()

        if self._sd_idx >= len(self._sd_pots):
            self._finalize_side_pot_showdown()
            return

        amt, elig = self._sd_pots[self._sd_idx]
        ntot = len(self._sd_pots)
        k = self._sd_idx + 1

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 8))

        for line in getattr(self, "_sd_summary_prefix", []):
            tk.Label(
                f, text=line, bg=self.PANEL, fg=self.MUTED,
                font=("Arial", 11),
            ).pack(anchor="w", padx=16, pady=(0, 2))

        tk.Label(
            f,
            text=f"Шоудаун — банк {k} из {ntot}: {amt:.1f} bb",
            bg=self.PANEL, fg=self.TEXT, font=("Arial", 20, "bold"),
        ).pack(pady=(4, 4))
        elig_l = sorted(elig, key=lambda p: PREFLOP_ORDER.index(p) if p in PREFLOP_ORDER else 99)
        tk.Label(
            f,
            text="Претенденты: " + ", ".join(elig_l),
            bg=self.PANEL, fg=self.MUTED, font=("Arial", 12, "bold"),
        ).pack(pady=(0, 10))

        wf = tk.Frame(f, bg=self.PANEL)
        wf.pack(pady=(0, 8))
        for pos in elig_l:
            tk.Button(
                wf, text=pos, width=9,
                bg=self.ACCENT, fg="#111", relief="flat",
                font=("Arial", 13, "bold"),
                command=lambda p=pos: self._sidepot_pick_single(p),
            ).pack(side="left", padx=4)

        tk.Label(
            f, text="Ничья за этот банк:",
            bg=self.PANEL, fg=self.MUTED, font=("Arial", 11, "bold"),
        ).pack(pady=(12, 4))
        tk.Button(
            f, text="Несколько победителей (чоп) →",
            command=self._sidepot_open_chop,
            bg="#45515d", fg="white", relief="flat",
            font=("Arial", 12, "bold"), padx=16, pady=5,
        ).pack(pady=(0, 8))

    def _sidepot_pick_single(self, w: str):
        idx = self._sd_idx
        amt, elig = self._sd_pots[idx]
        if w not in elig:
            return
        self._distribute_sidepot_amount(amt, [w])
        self._sd_outcomes.append((idx + 1, amt, [w]))
        self._sd_idx += 1
        self._show_showdown_pot_step()

    def _sidepot_open_chop(self):
        idx = self._sd_idx
        amt, elig = self._sd_pots[idx]
        self._clear_wizard()
        self._draw_table()

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 8))
        tk.Label(
            f,
            text=f"Чоп банка {idx + 1}  |  {amt:.1f} bb",
            bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold"),
        ).pack(pady=(0, 10))

        self._sidepot_chop_vars = {}
        for pos in sorted(elig, key=lambda p: PREFLOP_ORDER.index(p) if p in PREFLOP_ORDER else 99):
            v = tk.IntVar(value=0)
            self._sidepot_chop_vars[pos] = v
            tk.Checkbutton(
                f, text=pos, variable=v, onvalue=1, offvalue=0,
                bg=self.PANEL, fg=self.TEXT, selectcolor="#302828",
                activebackground=self.PANEL, activeforeground=self.TEXT,
                font=("Arial", 14, "bold"), anchor="w",
            ).pack(fill="x", padx=24, pady=3)

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(14, 10))
        tk.Button(
            bf, text="Подтвердить",
            command=self._sidepot_confirm_chop,
            bg="#2f6f3a", fg="white", relief="flat",
            font=("Arial", 13, "bold"), padx=20, pady=6,
        ).pack(side="left", padx=4)
        tk.Button(
            bf, text="« Назад",
            command=self._show_showdown_pot_step,
            bg="#45515d", fg="white", relief="flat",
            font=("Arial", 11, "bold"), padx=14, pady=4,
        ).pack(side="left", padx=4)

    def _sidepot_confirm_chop(self):
        idx = self._sd_idx
        amt, elig = self._sd_pots[idx]
        if not hasattr(self, "_sidepot_chop_vars"):
            return
        chosen = [p for p, var in self._sidepot_chop_vars.items() if var.get()]
        if not chosen:
            messagebox.showwarning("Чоп", "Отметь хотя бы одного победителя")
            return
        if not all(p in elig for p in chosen):
            messagebox.showerror("Чоп", "Можно только из претендентов этого банка")
            return
        self._sidepot_chop_vars = {}
        self._distribute_sidepot_amount(amt, chosen)
        self._sd_outcomes.append((idx + 1, amt, chosen))
        self._sd_idx += 1
        self._show_showdown_pot_step()

    def _finalize_side_pot_showdown(self):
        self._action_undo_stack.clear()
        self.current_actor = None
        if self.pot > self._side_pot_tol_dynamic():
            messagebox.showwarning(
                "Банк",
                f"После разбивки осталось {self.pot:.2f} bb — проверь вклады вручную.",
            )
        self.pot = 0.0
        self._saved_stacks = dict(self.stacks)
        self._first_hand = False
        self._seat_ante_posted = {}

        self._clear_wizard()
        self._draw_table()
        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 6))

        tk.Label(
            f, text="Раздача завершена (несколько банков)",
            bg=self.PANEL, fg=self.ACCENT, font=("Arial", 17, "bold"),
        ).pack(pady=(0, 8))

        for line in getattr(self, "_sd_summary_prefix", []):
            tk.Label(
                f, text=line, bg=self.PANEL, fg=self.MUTED,
                font=("Arial", 12), wraplength=900,
            ).pack(anchor="w", padx=12, pady=1)

        for num, amt, ws in self._sd_outcomes:
            names = ", ".join(ws)
            n = len(ws)
            sh = f"{amt / n:.1f}" if n else "0"
            tk.Label(
                f,
                text=(f"Банк {num}: {amt:.1f} bb → {names}  "
                      f"({'поровну ~' + sh + ' bb' if n > 1 else 'весь банк'})"),
                bg=self.PANEL, fg=self.TEXT, font=("Arial", 14, "bold"),
                wraplength=920, justify="left", anchor="w",
            ).pack(anchor="w", padx=12, pady=4)

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(12, 14))
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

    def _show_showdown_winner_picker(self):
        self._clear_wizard()
        self._draw_table()

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 8))

        tk.Label(
            f, text=f"Шоудаун  |  Банк: {self.pot:.1f} bb",
            bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold"),
        ).pack(pady=(0, 6))
        tk.Label(
            f, text="Ничья: отметь всех победителей, банк поделится поровну",
            bg=self.PANEL, fg=self.MUTED, font=("Arial", 12),
        ).pack(pady=(0, 12))

        self._showdown_pick_vars = {}
        order_i = {p: i for i, p in enumerate(PREFLOP_ORDER)}
        for pos in sorted(self.active, key=lambda p: order_i.get(p, 99)):
            v = tk.IntVar(value=0)
            self._showdown_pick_vars[pos] = v
            tk.Checkbutton(
                f, text=pos, variable=v, onvalue=1, offvalue=0,
                bg=self.PANEL, fg=self.TEXT, selectcolor="#302828",
                activebackground=self.PANEL, activeforeground=self.TEXT,
                font=("Arial", 14, "bold"),
                anchor="w",
            ).pack(fill="x", padx=24, pady=3)

        bf = tk.Frame(self.wizard, bg=self.PANEL)
        bf.pack(pady=(16, 14))
        tk.Button(
            bf, text="Продолжить",
            command=self._confirm_showdown_winners,
            bg="#2f6f3a", fg="white", relief="flat",
            font=("Arial", 14, "bold"), padx=24, pady=6,
        ).pack(side="left", padx=4)
        tk.Button(
            bf, text="« Назад",
            command=self._hand_over,
            bg="#45515d", fg="white", relief="flat",
            font=("Arial", 12, "bold"), padx=14, pady=4,
        ).pack(side="left", padx=4)

    def _confirm_showdown_winners(self):
        if not hasattr(self, "_showdown_pick_vars"):
            self._hand_over()
            return
        chosen = [p for p, var in self._showdown_pick_vars.items() if var.get()]
        if not chosen:
            messagebox.showwarning("Шоудаун", "Выбери хотя бы одного победителя")
            return
        self._showdown_pick_vars = {}
        self._hand_over(winners=chosen)

    def _hand_over(self, winner: str | None = None, winners: list[str] | None = None):
        self._action_undo_stack.clear()
        self.current_actor = None

        pot_before = float(self.pot)
        distributed = False

        if winners is not None and len(winners) >= 1:
            pot_before, _ = self._split_pot_among(winners)
            distributed = True
        elif winner:
            self.stacks[winner] = self.stacks.get(winner, 0) + self.pot
            self.pot = 0.0
            distributed = True
        elif len(self.active) <= 1:
            w = next(iter(self.active), None)
            if w:
                self.stacks[w] = self.stacks.get(w, 0) + self.pot
                self.pot = 0.0
            distributed = True

        if distributed:
            self._saved_stacks = dict(self.stacks)
            self._first_hand = False

        if self.pot <= 1e-9:
            self._seat_ante_posted = {}

        self._clear_wizard()
        self._draw_table()

        if (
            not distributed
            and len(self.active) > 1
            and winners is None
            and winner is None
            and self._try_begin_side_pot_showdown()
        ):
            return

        f = tk.Frame(self.wizard, bg=self.PANEL)
        f.pack(fill="x", pady=(16, 6))

        if winners is not None and len(winners) >= 1:
            names = ", ".join(winners)
            n = len(winners)
            share_txt = f"{pot_before / n:.1f}" if n else "0"
            tk.Label(
                f,
                text=(f"Победили: {names}  |  Банк {pot_before:.1f} bb поровну "
                      f"(~{share_txt} bb каждому)"),
                bg=self.PANEL, fg=self.ACCENT, font=("Arial", 16, "bold"),
                wraplength=900, justify="center",
            ).pack(pady=(0, 10))
        elif winner:
            tk.Label(
                f,
                text=(f"Победил {winner}  |  Забрал банк {pot_before:.1f} bb  "
                      f"→ стек: {self.stacks[winner]:.1f} bb"),
                bg=self.PANEL, fg=self.ACCENT, font=("Arial", 16, "bold")
            ).pack(pady=(0, 10))
        elif len(self.active) <= 1:
            w = next(iter(self.active), "—")
            tk.Label(f, text=f"Все сфолдили — победил {w}  |  Банк забран",
                     bg=self.PANEL, fg=self.ACCENT, font=("Arial", 16, "bold")
                     ).pack(pady=(0, 10))
        else:
            tk.Label(
                f,
                text=(f"Шоудаун  |  Банк: {self.pot:.1f} bb  |  "
                      "Один банк (вклады не сходятся — ручной режим)"),
                bg=self.PANEL, fg=self.TEXT, font=("Arial", 18, "bold"),
                wraplength=920,
            ).pack(pady=(0, 10))
            wf = tk.Frame(f, bg=self.PANEL)
            wf.pack(pady=(0, 8))
            order_i = {p: i for i, p in enumerate(PREFLOP_ORDER)}
            for pos in sorted(self.active, key=lambda p: order_i.get(p, 99)):
                tk.Button(
                    wf, text=pos, width=8,
                    bg=self.ACCENT, fg="#111", relief="flat",
                    font=("Arial", 13, "bold"),
                    command=lambda p=pos: self._hand_over(winner=p),
                ).pack(side="left", padx=4)
            tk.Label(
                f, text="Ничья / чоп (весь банк):",
                bg=self.PANEL, fg=self.MUTED, font=("Arial", 11, "bold")
            ).pack(pady=(10, 4))
            tk.Button(
                f, text="Несколько победителей →",
                command=self._show_showdown_winner_picker,
                bg="#45515d", fg="white", relief="flat",
                font=("Arial", 12, "bold"), padx=16, pady=5,
            ).pack(pady=(0, 6))
            tk.Label(
                f, text="Если были олл-ины разного размера — обычно включается разбивка банков.",
                bg=self.PANEL, fg=self.MUTED, font=("Arial", 10),
            ).pack(pady=(0, 4))

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

    def _require_pot_distributed(self) -> bool:
        """Шоудаун без выбора победителя оставляет pot > 0 — тогда нельзя начинать новую руку."""
        if self.pot > 1e-9:
            messagebox.showwarning(
                "Банк не разобран",
                "Сначала укажи победителя (кнопка позиции или «Несколько победителей»). "
                "Пока в банке есть фишки, продолжить нельзя.",
            )
            return False
        return True

    def _continue_game(self):
        if not self._require_pot_distributed():
            return
        self._action_undo_stack.clear()
        n = len(self.positions)
        old_seats = self._seat_order()
        seat_stacks = [self.stacks.get(pos, 0) for pos in old_seats]

        # Сдвиг баттона на 1 место по часовой: твоя позиция как в живой игре (BB→SB, SB→BTN, …).
        bo = _button_centric_order(n)
        if self.my_pos in bo:
            self.my_pos = bo[(bo.index(self.my_pos) - 1) % n]

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

        self._post_preflop_dead_money()

        self._show_cards("Выберите ваши карты", self._cards_done_pre)

    def _next_hand(self):
        if not self._require_pot_distributed():
            return
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
        self._action_undo_stack.clear()
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
