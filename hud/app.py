import tkinter as tk
from collections import deque

from models.card import Card

from hud.canvas_slots import CanvasSlotsMixin
from hud.card_and_positions import CardAndPositionsMixin
from hud.phase_betting import PhaseBettingMixin
from hud.phase_deck import PhaseDeckMixin
from hud.phase_setup import PhaseSetupMixin
from hud.table_canvas import TableCanvasMixin


class PokerFullHUDApp(
    CardAndPositionsMixin,
    CanvasSlotsMixin,
    TableCanvasMixin,
    PhaseBettingMixin,
    PhaseDeckMixin,
    PhaseSetupMixin,
):
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
        self._action_undo_stack: list[dict] = []

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
