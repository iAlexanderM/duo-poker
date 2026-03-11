import tkinter as tk
from tkinter import ttk, messagebox
from models.card import Card
from models.hand import Hand
from utils.parser import parse_stack
from logic.advisor import recommend_action
from config import ALL_POSITIONS, POSITION_COORDS, RANKS, SUITS, SUIT_SYMBOLS


class PokerAssistantApp:
    def __init__(self, root):
        self.root = root
        root.title("Покерный ассистент (GTO-подход)")
        root.geometry("1400x950+50+50")
        root.resizable(False, False)

        self.selected_position = None
        self.selected_cards = []
        self.board_cards = []
        self.opponent_action = tk.StringVar(value="check")
        self.bet_size = tk.DoubleVar(value=0.0)
        self.stack_var = tk.StringVar(value="50")
        self.opponent_stack_var = tk.StringVar(value="50")
        self.stage_var = tk.StringVar(value="Префлоп")
        self.num_players_var = tk.IntVar(value=9)

        self.position_items = {}  # {pos: id круга}
        self.position_texts = {}  # {pos: id текста}

        self.create_widgets()

    def create_widgets(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=5, pady=5)

        tk.Label(top_frame, text="Стадия:").pack(side="left")
        stage_combo = ttk.Combobox(top_frame, textvariable=self.stage_var,
                                   values=["Префлоп", "Флоп", "Терн", "Ривер"],
                                   state="readonly", width=10)
        stage_combo.pack(side="left", padx=5)
        stage_combo.bind("<<ComboboxSelected>>", self.on_stage_change)

        tk.Label(top_frame, text="Игроков за столом:").pack(side="left", padx=(20, 5))
        players_spin = tk.Spinbox(top_frame, from_=2, to=9, textvariable=self.num_players_var,
                                  width=3, command=self.update_positions_visibility)
        players_spin.pack(side="left")

        new_table_btn = tk.Button(top_frame, text="Новый стол", command=self.reset_table,
                                  bg="#ff9800", fg="white", font=("Arial", 10, "bold"))
        new_table_btn.pack(side="right", padx=10)

        main_horizontal = tk.Frame(self.root)
        main_horizontal.pack(fill="both", expand=True, padx=5, pady=5)

        left_frame = tk.Frame(main_horizontal)
        left_frame.pack(side="left", fill="both", expand=True)

        table_frame = tk.LabelFrame(left_frame, text="Стол", padx=5, pady=5)
        table_frame.pack(fill="both", expand=True)

        self.table_canvas = tk.Canvas(table_frame, width=700, height=450, bg="darkgreen")
        self.table_canvas.pack()
        self.draw_table()

        cards_frame = tk.Frame(left_frame)
        cards_frame.pack(fill="x", pady=5)

        hand_frame = tk.LabelFrame(cards_frame, text="Ваши карты", padx=5, pady=5)
        hand_frame.pack(side="left", fill="both", expand=True)

        self.cards_canvas = tk.Canvas(hand_frame, width=500, height=200, bg="white")
        self.cards_canvas.pack()
        self.draw_card_grid()

        hand_controls = tk.Frame(hand_frame)
        hand_controls.pack(fill="x", pady=5)
        self.selected_cards_label = tk.Label(hand_controls, text="Выбрано: ")
        self.selected_cards_label.pack(side="left")
        tk.Button(hand_controls, text="Сбросить руку", command=self.clear_selected_cards).pack(side="right")

        self.board_frame = tk.LabelFrame(cards_frame, text="Общие карты", padx=5, pady=5)
        self.board_canvas = tk.Canvas(self.board_frame, width=500, height=200, bg="lightgray")
        self.board_canvas.pack()
        tk.Label(self.board_frame,
                 text="Кликните на карты ниже, чтобы добавить на доску (повторный клик удаляет)").pack()
        board_controls = tk.Frame(self.board_frame)
        board_controls.pack()
        tk.Button(board_controls, text="Очистить общие карты", command=self.clear_board_cards).pack(side="left", padx=5)
        self.draw_board_grid()
        self.board_frame.pack_forget()

        right_frame = tk.Frame(main_horizontal, width=300)
        right_frame.pack(side="right", fill="y", padx=5)
        right_frame.pack_propagate(False)

        action_frame = tk.LabelFrame(right_frame, text="Действие оппонента / Стеки", padx=5, pady=5)
        action_frame.pack(fill="x", pady=5)

        actions_row = tk.Frame(action_frame)
        actions_row.pack(fill="x", pady=2)
        tk.Radiobutton(actions_row, text="Чек", variable=self.opponent_action, value="check",
                       command=self.update_bet_entry_state).pack(anchor="w")
        tk.Radiobutton(actions_row, text="Бет", variable=self.opponent_action, value="bet",
                       command=self.update_bet_entry_state).pack(anchor="w")
        tk.Radiobutton(actions_row, text="Рейз", variable=self.opponent_action, value="raise",
                       command=self.update_bet_entry_state).pack(anchor="w")
        tk.Radiobutton(actions_row, text="Олл-ин", variable=self.opponent_action, value="allin",
                       command=self.update_bet_entry_state).pack(anchor="w")

        hint_label = tk.Label(action_frame,
                              text="Чек – оппонент проверил;\nБет/Рейз – введите размер ставки;\nОлл-ин – размер берётся из стека оппонента.",
                              font=("Arial", 8), fg="gray", justify="left")
        hint_label.pack(pady=5)

        stacks_frame = tk.Frame(action_frame)
        stacks_frame.pack(fill="x", pady=5)

        tk.Label(stacks_frame, text="Ваш стек (bb):").grid(row=0, column=0, sticky="w")
        tk.Entry(stacks_frame, textvariable=self.stack_var, width=8).grid(row=0, column=1, padx=5)
        tk.Label(stacks_frame, text="Стек оппонента (bb):").grid(row=1, column=0, sticky="w")
        tk.Entry(stacks_frame, textvariable=self.opponent_stack_var, width=8).grid(row=1, column=1, padx=5)
        tk.Label(stacks_frame, text="Размер ставки (bb):").grid(row=2, column=0, sticky="w")
        self.bet_entry = tk.Entry(stacks_frame, textvariable=self.bet_size, width=8, state="normal")
        self.bet_entry.grid(row=2, column=1, padx=5)

        self.advice_label = tk.Label(action_frame, text="", font=("Arial", 12, "bold"), fg="#2E7D32", wraplength=280)
        self.advice_label.pack(pady=10, fill="x")

        self.advice_button = tk.Button(action_frame, text="Получить совет", command=self.get_advice,
                                       font=("Arial", 12), bg="#4CAF50", fg="white")
        self.advice_button.pack(pady=5)

        info_label = tk.Label(right_frame,
                              text="Совет основан на префлоп-чартах и постфлоп-эквити (расчёт против случайной руки).",
                              font=("Arial", 9), fg="gray", wraplength=280)
        info_label.pack(pady=5)

        self.update_bet_entry_state()
        self.update_positions_visibility()

    def draw_table(self):
        self.table_canvas.create_oval(100, 30, 600, 420, outline="brown", width=3, fill="darkgreen")

        self.position_areas = []
        if not hasattr(self, 'position_items'): self.position_items = {}
        if not hasattr(self, 'position_texts'): self.position_texts = {}

        for pos, (x, y) in POSITION_COORDS.items():
            circle = self.table_canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15,
                fill="lightgray", outline="black", width=2,
                tags=("pos", pos)
            )
            text = self.table_canvas.create_text(
                x, y, text=pos, font=("Arial", 8, "bold"),
                tags=("pos", pos)
            )

            self.position_items[pos] = circle
            self.position_texts[pos] = text

            self.position_areas.append((x - 20, y - 20, x + 20, y + 20, pos))

        self.table_canvas.bind("<Button-1>", self.on_table_click)

        self.table_center_x = (100 + 600) / 2
        self.table_center_y = (30 + 420) / 2

    def update_positions_visibility(self):
        num = self.num_players_var.get()
        if num == 2:
            visible = ['SB', 'BB']
        elif num == 3:
            visible = ['BTN', 'SB', 'BB']
        elif num == 4:
            visible = ['CO', 'BTN', 'SB', 'BB']
        elif num == 5:
            visible = ['UTG', 'CO', 'BTN', 'SB', 'BB']
        elif num == 6:
            visible = ['UTG', 'MP', 'CO', 'BTN', 'SB', 'BB']
        elif num == 7:
            visible = ['UTG', 'UTG+1', 'MP', 'CO', 'BTN', 'SB', 'BB']
        elif num == 8:
            visible = ['UTG', 'UTG+1', 'UTG+2', 'MP', 'CO', 'BTN', 'SB', 'BB']
        else:
            visible = ALL_POSITIONS

        for pos in ALL_POSITIONS:
            if pos in visible:
                self.table_canvas.itemconfig(self.position_items[pos], state='normal')
                self.table_canvas.itemconfig(self.position_texts[pos], state='normal')
            else:
                self.table_canvas.itemconfig(self.position_items[pos], state='hidden')
                self.table_canvas.itemconfig(self.position_texts[pos], state='hidden')

        if self.selected_position and self.selected_position not in visible:
            self.selected_position = None

    def on_table_click(self, event):
        x, y = event.x, event.y
        for (x1, y1, x2, y2, pos) in self.position_areas:
            if x1 <= x <= x2 and y1 <= y <= y2:
                if self.table_canvas.itemcget(self.position_items[pos], 'state') != 'hidden':
                    self.select_position(pos)
                break

    def select_position(self, pos):
        for p in self.position_items:
            self.table_canvas.itemconfig(self.position_items[p], fill="lightgray")
        self.table_canvas.itemconfig(self.position_items[pos], fill="yellow")
        self.selected_position = pos
        self.update_cards_on_table()

    def update_cards_on_table(self):
        self.table_canvas.delete("table_card")
        if self.selected_cards:
            x_start = self.table_center_x - 45 * len(self.selected_cards)
            for i, card in enumerate(self.selected_cards):
                x = x_start + i * 50
                y = self.table_center_y + 50
                self._draw_card_on_table(card, x, y, tag="table_card")
        if self.board_cards:
            x_start = self.table_center_x - 40 * len(self.board_cards)
            for i, card in enumerate(self.board_cards):
                x = x_start + i * 45
                y = self.table_center_y - 30
                self._draw_card_on_table(card, x, y, small=True, tag="table_card")

    def _draw_card_on_table(self, card, x, y, small=False, tag="table_card"):
        w, h = (35, 50) if small else (45, 65)
        self.table_canvas.create_rectangle(x, y, x + w, y + h, fill="white", outline="black", tags=tag)
        rank_display = '10' if card.rank == 'T' else card.rank
        self.table_canvas.create_text(x + 5, y + 5, text=rank_display, anchor="nw", font=("Arial", 10, "bold"),
                                      tags=tag)
        suit_symbol = SUIT_SYMBOLS[card.suit]
        color = "red" if card.suit in ('h', 'd') else "black"
        self.table_canvas.create_text(x + w - 8, y + h - 8, text=suit_symbol, anchor="se", font=("Arial", 14),
                                      fill=color, tags=tag)

    def draw_card_grid(self):
        card_width, card_height = 35, 45
        start_x, start_y = 10, 10
        self.card_rects = []
        for i, suit in enumerate(SUITS):
            for j, rank in enumerate(RANKS):
                x1 = start_x + j * (card_width + 2)
                y1 = start_y + i * (card_height + 2)
                x2 = x1 + card_width
                y2 = y1 + card_height
                self.cards_canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="black")
                rank_display = '10' if rank == 'T' else rank
                self.cards_canvas.create_text(x1 + 5, y1 + 5, text=rank_display, anchor="nw", font=("Arial", 9, "bold"))
                suit_symbol = SUIT_SYMBOLS[suit]
                color = "red" if suit in ('h', 'd') else "black"
                self.cards_canvas.create_text(x1 + card_width - 8, y1 + card_height - 8, text=suit_symbol, anchor="se",
                                              font=("Arial", 14), fill=color)
                self.card_rects.append((x1, y1, x2, y2, suit, rank))
        self.cards_canvas.bind("<Button-1>", self.on_card_click)

    def on_card_click(self, event):
        x, y = event.x, event.y
        for (x1, y1, x2, y2, suit, rank) in self.card_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                card = Card(rank + suit)
                if card in self.selected_cards:
                    self.selected_cards.remove(card)
                else:
                    if len(self.selected_cards) < 2:
                        self.selected_cards.append(card)
                    else:
                        messagebox.showinfo("Инфо",
                                            "Уже выбрано две карты. Чтобы заменить, сначала удалите ненужную кликом на неё.")
                self.update_selected_display()
                self.update_cards_on_table()
                break

    def update_selected_display(self):
        text = "Выбрано: " + ", ".join(str(c) for c in self.selected_cards)
        self.selected_cards_label.config(text=text)

    def clear_selected_cards(self):
        self.selected_cards.clear()
        self.update_selected_display()
        self.update_cards_on_table()

    def draw_board_grid(self):
        card_width, card_height = 35, 45
        start_x, start_y = 10, 10
        self.board_card_rects = []
        for i, suit in enumerate(SUITS):
            for j, rank in enumerate(RANKS):
                x1 = start_x + j * (card_width + 2)
                y1 = start_y + i * (card_height + 2)
                x2 = x1 + card_width
                y2 = y1 + card_height
                self.board_canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="black")
                rank_display = '10' if rank == 'T' else rank
                self.board_canvas.create_text(x1 + 5, y1 + 5, text=rank_display, anchor="nw", font=("Arial", 9, "bold"))
                suit_symbol = SUIT_SYMBOLS[suit]
                color = "red" if suit in ('h', 'd') else "black"
                self.board_canvas.create_text(x1 + card_width - 8, y1 + card_height - 8, text=suit_symbol, anchor="se",
                                              font=("Arial", 14), fill=color)
                self.board_card_rects.append((x1, y1, x2, y2, suit, rank))
        self.board_canvas.bind("<Button-1>", self.on_board_click)

    def on_board_click(self, event):
        x, y = event.x, event.y
        for (x1, y1, x2, y2, suit, rank) in self.board_card_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                card = Card(rank + suit)
                max_cards = self.get_max_board_cards()
                if card in self.board_cards:
                    self.board_cards.remove(card)
                else:
                    if len(self.board_cards) < max_cards:
                        self.board_cards.append(card)
                    else:
                        messagebox.showinfo("Инфо",
                                            f"Для стадии '{self.stage_var.get()}' можно выбрать только {max_cards} общих карт.")
                self.update_board_display()
                self.update_cards_on_table()
                break

    def get_max_board_cards(self):
        stage = self.stage_var.get()
        if stage == "Флоп":
            return 3
        elif stage == "Терн":
            return 4
        elif stage == "Ривер":
            return 5
        else:
            return 0

    def update_board_display(self):
        self.board_canvas.delete("all")
        self.draw_board_grid()

    def clear_board_cards(self):
        self.board_cards.clear()
        self.update_board_display()
        self.update_cards_on_table()

    def reset_table(self):
        self.selected_position = None
        self.selected_cards.clear()
        self.board_cards.clear()
        self.opponent_action.set("check")
        self.bet_size.set(0.0)
        self.stack_var.set("50")
        self.opponent_stack_var.set("50")
        self.stage_var.set("Префлоп")
        self.num_players_var.set(9)
        # Перерисовать стол (снять подсветку)
        self.table_canvas.delete("all")
        self.draw_table()
        self.update_positions_visibility()
        self.update_selected_display()
        self.update_board_display()
        self.update_cards_on_table()
        self.update_bet_entry_state()
        self.advice_label.config(text="")

    def on_stage_change(self, event=None):
        if self.stage_var.get() == "Префлоп":
            self.board_frame.pack_forget()
        else:
            self.board_frame.pack(side="left", fill="both", expand=True, padx=5)
        self.board_cards.clear()
        self.update_board_display()
        self.update_cards_on_table()

    def update_bet_entry_state(self):
        action = self.opponent_action.get()
        if action in ('bet', 'raise'):
            self.bet_entry.config(state="normal")
        else:
            self.bet_entry.config(state="disabled")
        if action == 'allin':
            try:
                opp_stack = float(self.opponent_stack_var.get())
                self.bet_size.set(opp_stack)
            except:
                pass

    def get_advice(self):
        if len(self.selected_cards) != 2:
            messagebox.showerror("Ошибка", "Выберите две карты")
            return
        if not self.selected_position:
            messagebox.showerror("Ошибка", "Выберите позицию на столе")
            return

        stage = self.stage_var.get()
        if stage != "Префлоп":
            max_board = self.get_max_board_cards()
            if len(self.board_cards) != max_board:
                messagebox.showerror("Ошибка",
                                     f"Для стадии '{stage}' необходимо выбрать {max_board} общих карт.\n"
                                     f"Сейчас выбрано: {len(self.board_cards)}")
                return

        action = self.opponent_action.get()
        bet = self.bet_size.get() if action in ('bet', 'raise', 'allin') else None

        if action in ('bet', 'raise') and (bet is None or bet <= 0):
            messagebox.showerror("Ошибка", "Введите размер ставки (больше 0)")
            return

        try:
            stack = parse_stack(self.stack_var.get())
            opp_stack = parse_stack(self.opponent_stack_var.get())
            num_players = self.num_players_var.get()
        except ValueError as e:
            messagebox.showerror("Ошибка", str(e))
            return

        hand = Hand(self.selected_cards[0], self.selected_cards[1])
        position = self.selected_position

        stage_map = {"Префлоп": "preflop", "Флоп": "flop", "Терн": "turn", "Ривер": "river"}
        stage = stage_map[self.stage_var.get()]

        advice = recommend_action(hand, position, stack, action, bet, num_players, self.board_cards, stage)
        self.advice_label.config(text=f"Совет: {advice}")


if __name__ == "__main__":
    root = tk.Tk()
    app = PokerAssistantApp(root)
    root.mainloop()
