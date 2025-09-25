import random
import matplotlib.pyplot as plt

# Ustawienia gry
num_rounds = 20
initial_balance = 100
bet_amount = 10

# Gracze i ich strategie
players = {
    "Marta": {"balance": initial_balance, "strategy": lambda: random.uniform(1.5, 2.5)},
    "Tom": {"balance": initial_balance, "strategy": lambda: 2.0},
    "Alex": {"balance": initial_balance, "strategy": lambda: random.uniform(1.1, 1.8)}
}

# Historia do wykresu
history = {player: [data["balance"]] for player, data in players.items()}

# Funkcja symulująca rundę
def simulate_round():
    crash_point = random.uniform(1.0, 3.0)
    results = {}
    for name, data in players.items():
        if data["balance"] >= bet_amount:
            multiplier = data["strategy"]()
            if multiplier < crash_point:
                win = bet_amount * multiplier
                data["balance"] += win - bet_amount
                results[name] = f"Win ({multiplier:.2f}x) → +{win - bet_amount:.2f}"
            else:
                data["balance"] -= bet_amount
                results[name] = f"Crash at {crash_point:.2f}x → -{bet_amount}"
        else:
            results[name] = "Insufficient funds"
        history[name].append(data["balance"])
    return crash_point, results

# Symulacja wielu rund
game_log = []
for round_num in range(1, num_rounds + 1):
    crash, round_results = simulate_round()
    game_log.append((round_num, crash, round_results))

# Wyniki końcowe
final_balances = {name: data["balance"] for name, data in players.items()}

# Wykres
plt.figure(figsize=(10, 6))
for name, balances in history.items():
    plt.plot(balances, label=name)
plt.title("Stan konta graczy w grze Aviator")
plt.xlabel("Runda")
plt.ylabel("Saldo")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
