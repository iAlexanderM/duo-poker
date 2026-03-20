import eval7
from utils.eval7_adapter import hand_to_eval7, board_to_eval7, range_string_to_eval7


class EquityCalculator:
    """Обёртка над eval7 для расчёта equity с кэшированием"""

    def __init__(self, monte_carlo_iterations: int = 5000):
        self.iterations = monte_carlo_iterations

    def calculate_equity_exact(
            self,
            hero_hand_treys: List[str],
            villain_range_str: str,
            board_treys: List[str]
    ) -> float:
        """
        Точный расчёт (перебор всех комбинаций) — медленно, но точно.
        Возвращает equity от 0.0 до 1.0
        """
        hero = hand_to_eval7(hero_hand_treys)
        villain = range_string_to_eval7(villain_range_str)
        board = board_to_eval7(board_treys)

        return eval7.py_hand_vs_range_exact(hero, villain, board)

    def calculate_equity_monte_carlo(
            self,
            hero_hand_treys: List[str],
            villain_range_str: str,
            board_treys: List[str],
            iterations: int = None
    ) -> float:
        """
        Monte Carlo — быстро, подходит для HUD.
        iterations: количество симуляций (по умолчанию 5000)
        """
        hero = hand_to_eval7(hero_hand_treys)
        villain = range_string_to_eval7(villain_range_str)
        board = board_to_eval7(board_treys)

        iters = iterations or self.iterations
        return eval7.py_hand_vs_range_monte_carlo(hero, villain, board, iters)

    def get_equity_with_confidence(
            self,
            hero_hand_treys: List[str],
            villain_range_str: str,
            board_treys: List[str],
            use_exact_if_small: bool = True
    ) -> dict:
        """
        Умный выбор метода: точный, если диапазон маленький, иначе Monte Carlo.
        Возвращает: {'equity': float, 'method': str, 'confidence': float}
        """
        villain = range_string_to_eval7(villain_range_str)

        # Если диапазон маленький (< 50 рук) — используем точный расчёт
        if use_exact_if_small and len(villain) < 50:
            equity = self.calculate_equity_exact(hero_hand_treys, villain_range_str, board_treys)
            return {'equity': equity, 'method': 'exact', 'confidence': 1.0}
        else:
            equity = self.calculate_equity_monte_carlo(hero_hand_treys, villain_range_str, board_treys)
            # Грубая оценка доверия: больше итераций = выше уверенность
            confidence = min(0.99, 0.7 + (self.iterations / 20000))
            return {'equity': equity, 'method': 'monte_carlo', 'confidence': confidence}
