import math
import tkinter as tk

from config import SUIT_SYMBOLS

from hud.ordering import TABLE_ORDER


class TableCanvasMixin:
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
            # +2π·i/n: по часовой стрелке вокруг стола (вид сверху); минус давал обход против часовой.
            angle = math.pi / 2 + 2 * math.pi * i / n
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
