"""
CS2 Bracket Simulator
==========================================

Win probabilities between two teams are derived from Elo-style rating using
the standard logistic formula:

    P(A beats B) = 1 / (1 + 10 ^ ((Rating_B - Rating_A) / 400))

HOW TO USE
----------
1. Edit the TEAMS list below: n (name, rating) tuples, in bracket order,
   i.e. paired as they appear in the Opening Round:
     (seed1, seed2), (seed3, seed4), (seed5, seed6), (seed7, seed8)
2. Adjust N_SIMULATIONS if you want more/less precision (default 100,000).
3. Run:  python cs2_bracket_simulator.py
4. Results print to the console and are also saved to bracket_results.csv
"""

import random
import csv
from collections import defaultdict

# ---------------------------------------------------------------------------
# 1. CONFIGURE YOUR TEAMS HERE
#    Order matters: teams are paired into the Opening Round in the order
#    given, i.e. (team[0] vs team[1]), (team[2] vs team[3]), etc.
#    "rating" can be any skill metric on a comparable scale (e.g. an Elo-like
#    rating, HLTV rating * 1000, etc.) - only the *differences* matter.
# ---------------------------------------------------------------------------
TEAMS = [
    ("MOUZ", 1893),
    ("Vitality", 1810),
    ("Furia", 1761),
    ("Aurora", 1540),
    ("NAVI", 1534),
    ("magic", 1464),
    ("MIBR", 1522),
    ("NRG", 1167),
]

N_SIMULATIONS = 100_000
RANDOM_SEED = 1  # set an integer here for reproducible results, or leave None

# ---------------------------------------------------------------------------
# 3. TEAM OBJECT
# ---------------------------------------------------------------------------
class Team:
    def __init__(self, name, rating):
        self.name = name
        self.rating = rating
        self.reset_stats()

    def reset_stats(self):
        self.win_rounds = 0
        self.loss_rounds = 0
        self.elim_rounds = 0
        self.padding_rounds = 0

    def __repr__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Team) and self.name == other.name

# ---------------------------------------------------------------------------
# 3. WIN PROBABILITY MODEL
# ---------------------------------------------------------------------------
def win_probability(rating_a, rating_b):
    """Probability that team A beats team B, Elo-style."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def play_match(team_a, team_b):
    """
    Resolves a single match between two Team objects.
    Updates win_rounds / loss_rounds on the teams and returns (winner, loser).
    """
    p_a_wins = win_probability(team_a.rating, team_b.rating)
    if random.random() < p_a_wins:
        winner, loser = team_a, team_b
    else:
        winner, loser = team_b, team_a

    winner.win_rounds += 1
    loser.loss_rounds += 1
    return winner, loser


# ---------------------------------------------------------------------------
# 4. BRACKET SIMULATION
# ---------------------------------------------------------------------------
def simulate_tournament(teams):
    """
    Runs one full simulation of the bracket and returns a dict:
        {team_name: placement_label}
    placement_label is one of: "1st", "2nd", "3rd", "4th", "5th-6th", "7th-8th"
    """
    for team in teams:
        team.reset_stats()

    t = teams  # shorthand, list of 8 team names in seed order

    # --- Double elimination bracket structure ---
    # --- Opening Round ---
    ow1, ol1 = play_match(t[0], t[7])
    ow2, ol2 = play_match(t[4], t[3])
    ow3, ol3 = play_match(t[1], t[5])
    ow4, ol4 = play_match(t[2], t[6])

    # --- Upper Semis ---
    usw1, usl1 = play_match(ow1, ow2)
    usw2, usl2 = play_match(ow3, ow4)

    usw1.padding_rounds += 1
    usw2.padding_rounds += 1

    # --- Upper Final ---
    ufw, ufl = play_match(usw1, usw2)

    ufw.padding_rounds += 1

    # --- Lower Bracket Round 1 (LR1) ---
    lr1w1, lr1l1 = play_match(ol1, ol2)
    lr1w2, lr1l2 = play_match(ol3, ol4)

    lr1l1.elim_rounds = 4 
    lr1l2.elim_rounds = 4 

    # --- Lower Semis (cross-paired to avoid immediate rematches) ---
    lsw1, lsl1 = play_match(lr1w1, usl2)
    lsw2, lsl2 = play_match(lr1w2, usl1)

    lsl1.elim_rounds = 3
    lsl2.elim_rounds = 3

    # --- Lower Final ---
    lfw, lfl = play_match(lsw1, lsw2)

    lfl.elim_rounds = 2

    # --- Cons. Final (3rd place decider) ---
    cfw, cfl = play_match(ufl, lfw)

    cfl.elim_rounds = 1

    # --- Grand Final ---
    gfw, gfl = play_match(ufw, cfw)

    placements = {
        gfw: "1st",
        gfl: "2nd",
        cfl: "3rd",
        lfl: "4th",
        lsl1: "5th-6th",
        lsl2: "5th-6th",
        lr1l1: "7th-8th",
        lr1l2: "7th-8th",
    }
    return placements

# ---------------------------------------------------------------------------
# 5. MONTE CARLO LOOP
# ---------------------------------------------------------------------------
PLACEMENT_ORDER = ["1st", "2nd", "3rd", "4th", "5th-6th", "7th-8th"]


def run_simulations(teams, n_sims):
    placement_counts = {team.name: defaultdict(int) for team in teams}
    stat_sums = {
        team.name: {"win_rounds": 0, "loss_rounds": 0, "padding_rounds": 0, "elim_rounds": 0
                     }
        for team in teams
    }

    for _ in range(n_sims):
        result = simulate_tournament(teams)

        for team, place in result.items():
            placement_counts[team.name][place] += 1

        # after the bracket is fully resolved, every team's stats for this
        # simulation are final - collect them before the next reset
        for team in teams:
            s = stat_sums[team.name]
            s["win_rounds"] += team.win_rounds
            s["loss_rounds"] += team.loss_rounds
            s["padding_rounds"] += team.padding_rounds
            s["elim_rounds"] += team.elim_rounds

    return placement_counts, stat_sums


def print_results(placement_counts, stat_sums, n_sims, team_names):
    col_width = max(len(name) for name in team_names) + 2

    # --- Placement probability table ---
    header = "Team".ljust(col_width) + "".join(p.rjust(10) for p in PLACEMENT_ORDER)
    print(header)
    print("-" * len(header))

    sorted_teams = sorted(team_names, key=lambda tm: placement_counts[tm]["1st"], reverse=True)

    for team in sorted_teams:
        row = team.ljust(col_width)
        for place in PLACEMENT_ORDER:
            pct = 100.0 * placement_counts[team][place] / n_sims
            row += f"{pct:9.2f}%"
        print(row)

    # --- Average stats / results table ---
    print()
    stat_header = (
        "Team".ljust(col_width)
        + "AvgWins".rjust(10) + "AvgLoss".rjust(10)
        + "AvgPad".rjust(10) + "AvgElim".rjust(10) 
    )
    print(stat_header)
    print("-" * len(stat_header))

    for team in sorted_teams:
        s = stat_sums[team]
        row = (
            team.ljust(col_width)
            + f"{s['win_rounds'] / n_sims:10.2f}"
            + f"{s['loss_rounds'] / n_sims:10.2f}"
            + f"{s['padding_rounds'] / n_sims:10.2f}"
            + f"{s['elim_rounds'] / n_sims:10.2f}"
        )
        print(row)


def save_csv(placement_counts, stat_sums, n_sims, team_names, path="bracket_results.csv"):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Team"] + PLACEMENT_ORDER
            + ["Avg_Wins", "Avg_Losses","Avg_Padding_Rounds", "Avg_Elim_Rounds"]
        )
        for team in team_names:
            s = stat_sums[team]
            row = [team] + [
                f"{100.0 * placement_counts[team][place] / n_sims:.2f}"
                for place in PLACEMENT_ORDER
            ] + [
                f"{s['win_rounds'] / n_sims:.2f}",
                f"{s['loss_rounds'] / n_sims:.2f}",
                f"{s['padding_rounds'] / n_sims:.2f}",
                f"{s['elim_rounds'] / n_sims:.2f}",
            ]
            writer.writerow(row)
    print(f"\nResults saved to {path}")


# ---------------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    teams = [Team(name, rating) for name, rating in TEAMS]
    team_names = [team.name for team in teams]

    print(f"Simulating {N_SIMULATIONS:,} tournaments...\n")
    placement_counts, stat_sums = run_simulations(teams, N_SIMULATIONS)
    print_results(placement_counts, stat_sums, N_SIMULATIONS, team_names)
    save_csv(placement_counts, stat_sums, N_SIMULATIONS, team_names)
