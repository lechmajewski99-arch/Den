#!/usr/bin/env python3
import random
from collections import Counter

# --- CONSTANTS ---
ranks = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
suits = ["♠", "♣", "♥", "♦"]
STARTING_MONEY = 100
BET_AMOUNT = 10  # fixed-limit bet

# --- FUNCTIONS ---
def build_shuffled_deck():
    deck = [rank + suit for rank in ranks for suit in suits]
    random.shuffle(deck)
    return deck

def deal_cards(deck, num_players, cards_each=5):
    hands = {}
    for player in range(1, num_players + 2):
        hand = [deck.pop(0) for _ in range(cards_each)]
        if player == 1:
            hands["You"] = hand
        else:
            hands[f"AI Player {player-1}"] = hand
    return hands

def betting_round(hands, money, pot, active_players, round_name="Betting Round"):
    print(f"\n--- {round_name} ---")
    current_bets = {player: 0 for player in active_players}
    players_to_act = list(active_players)
    highest_bet = 0

    while players_to_act:
        for player in players_to_act.copy():
            if player not in active_players:
                players_to_act.remove(player)
                continue

            if player == "You":
                print(f"\nYour hand: {hands['You']}")
                print(f"You have ${money['You']} | Current pot: ${pot} | Highest bet: ${highest_bet}")

                while True:
                    if highest_bet == 0:
                        action = input("Do you want to 'bet' or 'check'? ").strip().lower()
                        if action in ["bet", "check"]:
                            break
                    else:
                        action = input("Do you want to 'call', 'raise', or 'pass'? ").strip().lower()
                        if action in ["call", "raise", "pass"]:
                            break
                    print("Invalid input! Try again.")

                if action == "pass":
                    active_players.remove(player)
                    players_to_act.remove(player)
                    print("You folded.")
                elif action == "check":
                    print("You checked.")
                    players_to_act.remove(player)
                elif action == "bet":
                    money[player] -= BET_AMOUNT
                    pot += BET_AMOUNT
                    current_bets[player] += BET_AMOUNT
                    highest_bet = BET_AMOUNT
                    print(f"You bet ${BET_AMOUNT}.")
                    players_to_act = list(active_players)
                elif action == "call":
                    to_call = highest_bet - current_bets[player]
                    money[player] -= to_call
                    pot += to_call
                    current_bets[player] += to_call
                    print(f"You called ${to_call}.")
                    players_to_act.remove(player)
                elif action == "raise":
                    to_call = highest_bet - current_bets[player]
                    money[player] -= (to_call + BET_AMOUNT)
                    pot += (to_call + BET_AMOUNT)
                    current_bets[player] += (to_call + BET_AMOUNT)
                    highest_bet += BET_AMOUNT
                    print(f"You raised ${BET_AMOUNT}.")
                    players_to_act = list(active_players)

            else:  # AI player
                if highest_bet == 0:
                    decision = random.choice(["bet", "check"])
                    if decision == "bet":
                        if money[player] >= BET_AMOUNT:
                            money[player] -= BET_AMOUNT
                            pot += BET_AMOUNT
                            current_bets[player] += BET_AMOUNT
                            highest_bet = BET_AMOUNT
                            print(f"{player} bets ${BET_AMOUNT}.")
                            players_to_act = list(active_players)
                        else:
                            print(f"{player} cannot bet, checks instead.")
                    else:
                        print(f"{player} checks.")
                    players_to_act.remove(player)
                else:
                    to_call = highest_bet - current_bets[player]
                    if to_call > 0:
                        decision = random.choice(["call", "fold"])
                        if decision == "call" and money[player] >= to_call:
                            money[player] -= to_call
                            pot += to_call
                            current_bets[player] += to_call
                            print(f"{player} calls ${to_call}.")
                        else:
                            active_players.remove(player)
                            print(f"{player} folds.")
                    else:
                        decision = random.choice(["raise", "check"])
                        if decision == "raise" and money[player] >= BET_AMOUNT:
                            money[player] -= BET_AMOUNT
                            pot += BET_AMOUNT
                            current_bets[player] += BET_AMOUNT
                            highest_bet += BET_AMOUNT
                            print(f"{player} raises ${BET_AMOUNT}.")
                            players_to_act = list(active_players)
                        else:
                            print(f"{player} checks.")
                    players_to_act.remove(player)
    return pot, active_players

def exchange_phase(hands, deck, active_players):
    print("\n--- Draw/Exchange Phase ---")
    
    if "You" in active_players:
        print("Your hand:")
        for i, card in enumerate(hands["You"], 1):
            print(f"{i}: {card}")
        while True:
            indices_input = input(
                "Enter numbers of cards to exchange (1-5) separated by spaces, or Enter to keep all: "
            ).strip()
            if indices_input == "":
                indices = []
                break
            try:
                indices = [int(i)-1 for i in indices_input.split()]
                if all(0 <= i < 5 for i in indices):
                    break
                else:
                    print("Invalid numbers! Please enter 1-5.")
            except ValueError:
                print("Invalid input!")
        for i in indices:
            if deck:
                hands["You"][i] = deck.pop(0)
        print("Your new hand:")
        for i, card in enumerate(hands["You"], 1):
            print(f"{i}: {card}")

    for player in active_players:
        if player != "You":
            num_ai_exchange = random.randint(0,5)
            for _ in range(num_ai_exchange):
                if deck:
                    idx = random.randint(0,4)
                    hands[player][idx] = deck.pop(0)
            print(f"{player} exchanged {num_ai_exchange} cards.")

def evaluate_hand(hand):
    ranks_in_hand = [card[:-1] for card in hand]
    counts = Counter(ranks_in_hand)
    counts_values = counts.values()
    if 4 in counts_values:
        return (7, ranks_in_hand)
    elif 3 in counts_values and 2 in counts_values:
        return (6, ranks_in_hand)
    elif 3 in counts_values:
        return (3, ranks_in_hand)
    elif list(counts_values).count(2) == 2:
        return (2, ranks_in_hand)
    elif 2 in counts_values:
        return (1, ranks_in_hand)
    else:
        return (0, ranks_in_hand)

def determine_winner(hands, active_players):
    scores = {}
    for player in active_players:
        scores[player] = evaluate_hand(hands[player])
    winner = max(scores, key=lambda x: scores[x])
    return winner, scores

# --- MAIN LOOP ---
num_ai = int(input("How many AI players do you want to play against? "))
money = {"You": STARTING_MONEY}
for i in range(1, num_ai+1):
    money[f"AI Player {i}"] = STARTING_MONEY

while True:
    if money["You"] <= 0:
        print("You ran out of money. Game over!")
        break
    if all(money[f"AI Player {i}"] <= 0 for i in range(1,num_ai+1)):
        print("All AI players ran out of money. You win the game!")
        break

    deck = build_shuffled_deck()
    hands = deal_cards(deck, num_ai)
    pot = 0
    active_players = set([player for player, m in money.items() if m>0])

    # First betting
    pot, active_players = betting_round(hands, money, pot, active_players, "First Betting Round")
    if len(active_players) == 1:
        winner = next(iter(active_players))
        print(f"{winner} wins the pot of ${pot} by default!")
        money[winner] += pot
        continue

    # Exchange
    exchange_phase(hands, deck, active_players)

    # Second betting
    pot, active_players = betting_round(hands, money, pot, active_players, "Second Betting Round")
    if len(active_players) == 1:
        winner = next(iter(active_players))
        print(f"{winner} wins the pot of ${pot} by default!")
        money[winner] += pot
        continue

    # Showdown
    print("\n--- Showdown ---")
    for player in active_players:
        print(player, "->", hands[player])
    winner, scores = determine_winner(hands, active_players)
    print(f"\nWinner is {winner} with hand score {scores[winner][0]}!")
    money[winner] += pot

    print("\nMoney after this hand:")
    for player, amount in money.items():
        print(f"{player}: ${amount}")

    cont = input("\nDo you want to play another hand? (y/n): ").strip().lower()
    if cont != "y":
        print("Thanks for playing!")
        break
