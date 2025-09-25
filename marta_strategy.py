# marta_agent.py
# -------------------------------------------------------------
# Marta w osobnym module.
# - train_marta_to_file(...) — uczy Martę offline i zapisuje wagi do JSON.
# - make_marta_strategy(...) — ładuje wagi i ZWRACA zero-argumentową funkcję
#   do wstawienia w players["Marta"]["strategy"], BEZ zmiany kodu gry.
#   W środku: perceptron + "systemy z dupy" + ryzyko.
# -------------------------------------------------------------

import json
import math
import random
from typing import List, Dict, Any

# Zakres rozsądnych cashoutów dla gracza (gra nadal ma crash w [1, ∞))
MIN_CASHOUT = 1.10
MAX_CASHOUT = 10.0

# --- proste funkcje pomocnicze ---
def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

# --- generator crasha do self-play (offline training) ---
# Eksponencjalny ogon: crash w [1, ∞). To NIE jest używane przez grę,
# tylko przez trening offline.
def _sample_crash(lam: float = 1.2) -> float:
    return 1.0 + random.expovariate(lam)

# ============================================================
#                 WEWNĘTRZNY MODEL MARTY
# ============================================================
class _MartaPerceptron:
    """
    Lekki perceptron Marty używany TYLKO offline (trening) i online (predykcja).
    W grze nie ma uczenia online, bo strategia ma zero argumentów.
    """
    def __init__(self, init_balance: float = 100.0):
        # Wagi dla cech: [bias, mood, superstition, drift]
        # (używamy TYLKO cech, które nie wymagają danych z gry)
        # Dlaczego tak? Bo w grze strategia nic nie dostaje (brak crash/balance).
        self.w: List[float] = [0.0, 0.3, 0.3, 0.2]

        # Stan pseudo-wewnętrzny (niezależny od gry)
        self._mood = 0.0           # [-1, 1]
        self._drift = 0.0          # powolny dryf decyzyjny
        self.risk_bias = 0.25      # skłonność w górę
        self.noise_decision = 0.10 # losowość w decyzji

    def _features(self) -> List[float]:
        superstition = 2.0 * (random.random() - 0.5)  # [-1, 1]
        return [1.0, self._mood, superstition, self._drift]

    def decide_cashout(self) -> float:
        x = self._features()
        z = sum(wi * xi for wi, xi in zip(self.w, x))
        p = _sigmoid(z)
        m = MIN_CASHOUT + p * (MAX_CASHOUT - MIN_CASHOUT)

        # ryzykanctwo
        m = m * (1 - self.risk_bias) + (MIN_CASHOUT + 0.85 * (MAX_CASHOUT - MIN_CASHOUT)) * self.risk_bias

        # systemy z dupy (nadpisanie ~35%)
        if random.random() < 0.35:
            systems = [
                ("hot_hand", random.uniform(2.5, MAX_CASHOUT)),
                ("odkuwka",  random.uniform(3.0, MAX_CASHOUT)),
                ("lucky",    random.uniform(2.0, MAX_CASHOUT)),
                ("szosty",   random.uniform(2.0, MAX_CASHOUT)),
            ]
            m = random.choice(systems)[1]

        # chaos
        m += random.gauss(0.0, self.noise_decision)

        # dryfy stanów (lekko)
        self._mood  = _clip(0.9 * self._mood  + random.uniform(-0.12, 0.12), -1.0, 1.0)
        self._drift = _clip(0.98 * self._drift + random.uniform(-0.02, 0.02), -1.0, 1.0)

        return _clip(m, MIN_CASHOUT, MAX_CASHOUT)

    # --------- OFFLINE TRAINING (self-play) ----------
    def train_offline(self, episodes: int = 3000, seed: int = 123) -> None:
        """
        Uczy wagi na sztucznych danych (bez balansu/crasha z gry).
        Cel: „wzmocnić” skłonność do ryzyka i rozrzut decyzji.
        Tu nie naśladujemy dokładnego optymalizatora — trening jest
        po to, by wagi dawały „charakter Marty”.
        """
        random.seed(seed)
        lr = 0.03
        for _ in range(episodes):
            # syntetyczne "docelowe" wyjście m_target: preferuj wysoko
            # (tu uczymy tylko 'styl' ryzykowny, nie precyzję względem crasha)
            desired = random.uniform(2.2, MAX_CASHOUT)

            # forward
            x = self._features()
            z = sum(wi * xi for wi, xi in zip(self.w, x))
            p = _sigmoid(z)
            y_hat = MIN_CASHOUT + p * (MAX_CASHOUT - MIN_CASHOUT)

            # prosta aktualizacja w stronę desired (MSE)
            dy_dz = (MAX_CASHOUT - MIN_CASHOUT) * p * (1 - p)
            grad = (y_hat - desired) * dy_dz
            for i in range(len(self.w)):
                self.w[i] -= lr * grad * x[i]

    # --------- SERIALIZACJA ---------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "w": self.w,
            "risk_bias": self.risk_bias,
            "noise_decision": self.noise_decision,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "_MartaPerceptron":
        obj = cls()
        obj.w = list(d.get("w", [0.0, 0.3, 0.3, 0.2]))
        obj.risk_bias = float(d.get("risk_bias", 0.25))
        obj.noise_decision = float(d.get("noise_decision", 0.10))
        return obj

# ============================================================
#                  API DLA TWOJEJ GRY
# ============================================================

def train_marta_to_file(path: str = "marta_weights.json", episodes: int = 3000, seed: int = 123) -> None:
    """
    Uczy Martę OFFLINE i zapisuje wagi do JSON.
    Uruchamiasz to JEDEN raz przed grą (np. z konsoli/REPL).
    """
    m = _MartaPerceptron()
    m.train_offline(episodes=episodes, seed=seed)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(m.to_dict(), f)
    print(f"[marta_agent] Zapisano wagi do: {path}")

def make_marta_strategy(path: str = "marta_weights.json"):
    """
    Ładuje zapisane wagi i ZWRACA ZERO-ARGUMENTOWĄ FUNKCJĘ
    do wstawienia w players['Marta']['strategy'].
    Gra NIE musi nic wiedzieć o Marcie.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = _MartaPerceptron.from_dict(data)
    except FileNotFoundError:
        # fallback: jeśli ktoś zapomniał trenować, bierzemy „fabryczne” wagi
        model = _MartaPerceptron()
        print("[marta_agent] Uwaga: nie znaleziono wag, używam domyślnych.")

    # ZWRACAMY FUNKCJĘ BEZ ARGUMENTÓW (jak Twoje lambda: ...)
    def _strategy() -> float:
        return model.decide_cashout()

    return _strategy


train_marta_to_file(path="marta_weights.json", episodes=40000, seed=123)
