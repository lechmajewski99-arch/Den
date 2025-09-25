# marta_agent.py
# Marta jako zewnętrzna strategia do Twojej gry (gra zostaje nietknięta).
# - train_marta_to_file(...)  [opcjonalne] – offline "charakteryzuje" wagi i zapisuje do JSON
# - make_marta_strategy(..., mode="capped"| "unbounded", cap=..., k_unbound=...) -> funkcja bez argumentów

import json
import math
import random
from typing import List, Dict, Any, Optional, Callable

MIN_CASHOUT = 1.10   # zawsze >1, żeby był zysk

def _sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)

def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

# --- generator z ciężkim ogonem (do "systemów z dupy") ---
def _pareto(xm: float = 2.0, alpha: float = 1.3) -> float:
    # losuje z Pareto(xm, alpha); rośnie do ∞
    u = 1.0 - random.random()
    return xm / (u ** (1.0 / alpha))

class _MartaPerceptron:
    """Wewnętrzny, lekki model Marty. Działa bez danych z gry (funkcja bez argumentów)."""
    def __init__(self):
        # minimalny zestaw cech nieuwarunkowanych na stanie gry
        # [bias, mood, superstition, drift]
        self.w: List[float] = [0.0, 0.3, 0.3, 0.2]
        self._mood = 0.0              # [-1, 1]
        self._drift = 0.0
        self.risk_bias = 0.25         # pcha w górę
        self.noise_decision = 0.10    # losowość decyzji

    def _features(self) -> List[float]:
        superstition = 2.0 * (random.random() - 0.5)  # [-1, 1]
        return [1.0, self._mood, superstition, self._drift]

    def _base_score(self) -> float:
        x = self._features()
        z = sum(wi * xi for wi, xi in zip(self.w, x))
        p = _sigmoid(z)  # 0..1
        return p

    def decide_cashout(
        self,
        *,
        mode: str = "capped",
        cap: Optional[float] = 10.0,
        k_unbound: float = 5.0,
        pareto_prob: float = 0.12,
        override_prob: float = 0.35
    ) -> float:
        """
        mode="capped": cashout w [MIN_CASHOUT, cap]
        mode="unbounded": cashout w [MIN_CASHOUT, ∞) poprzez transformację p/(1-p)
        - k_unbound: skala agresji dla trybu unbounded (większe => częściej bardzo wysokie)
        - pareto_prob: szansa na "dziki" strzał z ogona Pareto (10+)
        - override_prob: szansa na nadpisanie "systemem z dupy"
        """
        p = self._base_score()

        if mode == "unbounded":
            # transformacja rosnąca do ∞ wraz z p→1
            # m = MIN + k * p/(1-p)
            denom = max(1e-6, 1.0 - p)
            m = MIN_CASHOUT + k_unbound * (p / denom)
        else:
            # ograniczony zakres [MIN, cap]
            _cap = cap if (cap is not None and cap > MIN_CASHOUT) else 10.0
            m = MIN_CASHOUT + p * (_cap - MIN_CASHOUT)

        # ryzykowny bias – podciąga ku wysokim wartościom
        if mode == "capped":
            _cap = cap if (cap is not None and cap > MIN_CASHOUT) else 10.0
            target_high = MIN_CASHOUT + 0.85 * (_cap - MIN_CASHOUT)
            m = m * (1 - self.risk_bias) + target_high * self.risk_bias
        else:
            # w unbounded po prostu dodajemy odchył w górę zależny od p
            m += self.risk_bias * (1.0 + 4.0 * p)

        # "systemy z dupy" – nadpisania
        if random.random() < override_prob:
            picks = []
            # "hot hand"
            picks.append(random.uniform(2.5, cap if (mode == "capped" and cap) else 6.0))
            # "odkuwka"
            picks.append(random.uniform(3.0, cap if (mode == "capped" and cap) else 12.0))
            # "szósty zmysł"
            picks.append(random.uniform(2.0, cap if (mode == "capped" and cap) else 8.0))
            m = random.choice(picks)

        # ciężki ogon (rzadko bardzo duże wartości)
        if mode == "unbounded" and random.random() < pareto_prob:
            m = max(m, _pareto(xm=2.0, alpha=random.uniform(1.2, 1.8)))

        # chaos decyzyjny
        m += random.gauss(0.0, self.noise_decision)

        # dryfy stanów
        self._mood  = _clip(0.9 * self._mood  + random.uniform(-0.12, 0.12), -1.0, 1.0)
        self._drift = _clip(0.98 * self._drift + random.uniform(-0.02, 0.02), -1.0, 1.0)

        # zabezpieczenie numeryczne
        m = max(MIN_CASHOUT, m)
        if not math.isfinite(m):
            m = 2.0
        # miękki limit bezpieczeństwa (ogranicza tylko absurdalne overflowy)
        return min(m, 1e9)

    # ===== prościutki trening offline (charakteryzowanie) =====
    def train_offline(self, episodes: int = 3000, seed: int = 123) -> None:
        random.seed(seed)
        lr = 0.03
        for _ in range(episodes):
            desired = random.uniform(2.2, 8.0)  # uczymy "ryzykowny styl", nie precyzję względem crasha
            p = self._base_score()
            # y_hat w "capped" z cap=10
            y_hat = MIN_CASHOUT + p * (10.0 - MIN_CASHOUT)
            dy_dz = (10.0 - MIN_CASHOUT) * p * (1 - p)
            grad = (y_hat - desired) * dy_dz
            x = self._features()
            for i in range(len(self.w)):
                self.w[i] -= lr * grad * x[i]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "w": self.w,
            "risk_bias": self.risk_bias,
            "noise_decision": self.noise_decision,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "_MartaPerceptron":
        o = cls()
        o.w = list(d.get("w", o.w))
        o.risk_bias = float(d.get("risk_bias", o.risk_bias))
        o.noise_decision = float(d.get("noise_decision", o.noise_decision))
        return o

# =================== API DLA TWOJEJ GRY ===================

def train_marta_to_file(path: str = "marta_weights.json", episodes: int = 3000, seed: int = 123) -> None:
    m = _MartaPerceptron()
    m.train_offline(episodes=episodes, seed=seed)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(m.to_dict(), f)
    print(f"[marta_agent] Zapisano wagi do: {path}")

def make_marta_strategy(
    path: str = "marta_weights.json",
    *,
    mode: str = "capped",          # "capped" albo "unbounded"
    cap: Optional[float] = 10.0,   # używane tylko w mode="capped"
    k_unbound: float = 5.0         # skala agresji w mode="unbounded"
) -> Callable[[], float]:
    """Zwraca ZERO-ARGUMENTOWĄ funkcję do wstawienia jako strategy w grze."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        model = _MartaPerceptron.from_dict(data)
    except FileNotFoundError:
        model = _MartaPerceptron()
        print("[marta_agent] Uwaga: brak wag – używam domyślnych.")

    # funkcja bez argumentów — zgodna z Twoją grą
    def _strategy() -> float:
        return model.decide_cashout(mode=mode, cap=cap, k_unbound=k_unbound)

    return _strategy
