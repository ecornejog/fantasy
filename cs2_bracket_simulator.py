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
import itertools
from functools import lru_cache

# ---------------------------------------------------------------------------
# 1. CONFIGURE YOUR TEAMS HERE
#    Order matters: teams are paired into the Opening Round in the order
#    given, i.e. (team[0] vs team[1]), (team[2] vs team[3]), etc.
#    "rating" can be any skill metric on a comparable scale (e.g. an Elo-like
#    rating, HLTV rating * 1000, etc.) - only the *differences* matter.
# ---------------------------------------------------------------------------
TEAMS = [
    ("Spirit", 2004),
    ("Vitality", 1961),
    ("Furia", 1834),
    ("Mouz", 1945),
    ("Falcons", 1899),
    ("Aurora", 1813),
    ("Parivision", 1607),
    ("1Win", 1555),
]


N_SIMULATIONS = 100_000  # set the number of simulations to run
RANDOM_SEED = 1  # set an integer here for reproducible results, or leave None

# ---------------------------------------------------------------------------
# 2. TEAM OBJECT
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
# 3.1. ROUND ROBIN SCHEDULING
# ---------------------------------------------------------------------------

def simulate_bo1(team_a, team_b):
    """
    Simulates a single BO1 map round-by-round.
    Each round, team_a's win probability is derived from the VRS rating gap
    via win_probability(). First to 13 rounds wins; if the score reaches
    12-12, the match ends in a draw (per this tournament's rules - no OT).

    Returns (rounds_a, rounds_b).
    """
    rounds_a = 0
    rounds_b = 0

    while True:
        p_a_round = win_probability(team_a.rating, team_b.rating)
        if random.random() < p_a_round:
            rounds_a += 1
        else:
            rounds_b += 1

        if rounds_a == 13 or rounds_b == 13:
            return rounds_a, rounds_b
        if rounds_a == 12 and rounds_b == 12:
            return rounds_a, rounds_b  # draw

def generate_round_robin_schedule(teams):
    """Returns a list of (team_a, team_b) pairs - one match per pair."""
    return list(itertools.combinations(teams, 2))

def simulate_group_stage(teams):
    """
    Simulates every match in a single round robin group.
    `teams` is a list of Team objects (need .name and .rating).

    Returns:
      stats: {team_name: {"points","wins","draws","losses",
                           "rounds_won","rounds_lost"}}
      match_log: list of (team_a_name, team_b_name, rounds_a, rounds_b)
                 used for head-to-head tiebreaking
    """
    stats = {
        team.name: {
            "points": 0, "wins": 0, "draws": 0, "losses": 0,
            "rounds_won": 0, "rounds_lost": 0,
        }
        for team in teams
    }
    match_log = []

    schedule = generate_round_robin_schedule(teams)
    for team_a, team_b in schedule:
        rounds_a, rounds_b = simulate_bo1(team_a, team_b)
        match_log.append((team_a.name, team_b.name, rounds_a, rounds_b))

        stats[team_a.name]["rounds_won"] += rounds_a
        stats[team_a.name]["rounds_lost"] += rounds_b
        stats[team_b.name]["rounds_won"] += rounds_b
        stats[team_b.name]["rounds_lost"] += rounds_a

        if rounds_a > rounds_b:
            stats[team_a.name]["points"] += 3
            stats[team_a.name]["wins"] += 1
            stats[team_b.name]["losses"] += 1
        elif rounds_b > rounds_a:
            stats[team_b.name]["points"] += 3
            stats[team_b.name]["wins"] += 1
            stats[team_a.name]["losses"] += 1
        else:
            stats[team_a.name]["points"] += 1
            stats[team_b.name]["points"] += 1
            stats[team_a.name]["draws"] += 1
            stats[team_b.name]["draws"] += 1

    return stats, match_log

def rank_teams(teams, stats, match_log):
    """
    teams: list of Team objects (the same ones passed into simulate_group_stage)
    Returns a list of Team objects, sorted best-to-worst, ready to feed
    straight into the playoff bracket simulator (e.g. as the `t` list in
    simulate_tournament()).
    """
    teams_by_name = {team.name: team for team in teams}
    team_names = list(teams_by_name.keys())

    def round_diff(name):
        return stats[name]["rounds_won"] - stats[name]["rounds_lost"]

    def head_to_head(name, group):
        """(points, round_diff) earned only in matches against other teams in group."""
        h2h_points = 0
        h2h_rd = 0
        for ta, tb, ra, rb in match_log:
            if ta == name and tb in group:
                h2h_points += 3 if ra > rb else (1 if ra == rb else 0)
                h2h_rd += ra - rb
            elif tb == name and ta in group:
                h2h_points += 3 if rb > ra else (1 if rb == ra else 0)
                h2h_rd += rb - ra
        return h2h_points, h2h_rd

    # Primary sort: points desc, then round diff desc
    ordered = sorted(
        team_names,
        key=lambda t: (-stats[t]["points"], -round_diff(t)),
    )

    # Resolve groups tied on both points and round diff via head-to-head
    final_order = []
    i = 0
    while i < len(ordered):
        j = i
        while (
            j < len(ordered)
            and stats[ordered[j]]["points"] == stats[ordered[i]]["points"]
            and round_diff(ordered[j]) == round_diff(ordered[i])
        ):
            j += 1

        group = ordered[i:j]
        if len(group) == 1:
            final_order.extend(group)
        else:
            group_sorted = sorted(
                group, key=lambda t: head_to_head(t, group), reverse=True
            )
            final_order.extend(group_sorted)
        i = j

    # Map names back to the actual Team objects
    return [teams_by_name[name] for name in final_order]


# ---------------------------------------------------------------------------
# 3.2. LIVE RATING UPDATE (ESL SWISS STAGE)
# ---------------------------------------------------------------------------
def live_rating_adjustment(x):
    """
    ESL formula: 5 * (1 - 1 / (1 + 10^((X - 8) / 10)))
    X = how much better (lower number) the OTHER team's live rating is than
    yours. Result is between 0 and 5: the bigger the upset, the bigger the move.
    """
    return 5 * (1 - 1 / (1 + 10 ** ((x - 8) / 10)))


def update_live_ratings(winner, loser):
    """
    winner / loser are entries of the `state` dict used in simulate_swiss_stage.

    ASSUMPTION: ESL only publishes the formula from the point of view of the
    team being adjusted, so here the same amount is applied in both
    directions (winner improves, loser worsens). If you want a different
    treatment for the loser, this is the only place to change.
    """
    x = winner["live"] - loser["live"]   # > 0 means the loser had the better rating
    delta = live_rating_adjustment(x)
    winner["live"] -= delta              # lower number = better
    loser["live"] += delta

@lru_cache(maxsize=None)
def _index_pairings(n):
    """
    Every way to split indices 0..n-1 into n/2 pairs (n must be even).
    n=8 -> 105 options, n=6 -> 15, n=4 -> 3. Cached because it's reused
    thousands of times in a Monte Carlo run.
    """
    def build(items):
        if not items:
            return [()]
        first, rest = items[0], items[1:]
        result = []
        for k, partner in enumerate(rest):
            remaining = rest[:k] + rest[k + 1:]
            for sub in build(remaining):
                result.append(((first, partner),) + sub)
        return result

    return tuple(build(tuple(range(n))))


def pair_pool(pool, state):
    """
    Pairs one result-pool (teams with the same W-L record) using ESL's rule:

      - Ideal opponent of a team = the rating as far ABOVE the pool's average
        live rating as the team is below it, i.e. 2*avg - live_rating.
      - Deviation = ideal opponent rating - actual opponent rating, squared.
      - The pairing with the lowest total wins; rematches are penalised.

    For a match between A and B, both teams' deviations are identical
    (2*avg - live_A - live_B), so ESL's per-team sum is just double the
    per-match sum. Doubling doesn't change which pairing is best, so each
    match is counted once here.
    """
    REMATCH_PENALTY = 1_000_000

    if len(pool) % 2 != 0:
        raise ValueError(f"Pool has an odd number of teams: {pool}")

    avg = sum(state[name]["live"] for name in pool) / len(pool)

    best_cost = None
    best_pairing = None
    for index_pairing in _index_pairings(len(pool)):
        cost = 0.0
        for i, j in index_pairing:
            a, b = pool[i], pool[j]
            if b in state[a]["opponents"]:
                cost += REMATCH_PENALTY
            cost += (2 * avg - state[a]["live"] - state[b]["live"]) ** 2
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best_pairing = index_pairing

    return [(pool[i], pool[j]) for i, j in best_pairing]

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

    t = teams  # shorthand, list of X team names in seed order
    # --- playoff bracket ---
    # --- quarterfinals ---
    
    qf1_w, qf1_l = play_match(t[1], t[6])
    qf2_w, qf2_l = play_match(t[7], t[5])
    qf3_w, qf3_l = play_match(t[4], t[0])
    qf4_w, qf4_l = play_match(t[2], t[3])
    qf1_l.elim_rounds = 2
    qf2_l.elim_rounds = 2
    qf3_l.elim_rounds = 2
    qf4_l.elim_rounds = 2

    # --- semifinals ---
    sf1_w, sf1_l = play_match(qf1_w, qf2_w)
    sf2_w, sf2_l = play_match(qf3_w, qf4_w)

    # --- finals ---
    tpd_w, tpd_l = play_match(sf1_l, sf2_l)  # 3rd place match
    f_w, f_l = play_match(sf1_w, sf2_w)
    
    placements = {
        f_w: "1st",
        f_l: "2nd",
        tpd_w: "3rd",
        tpd_l: "4th",
        qf1_l: "5th-8th",
        qf2_l: "5th-8th",
        qf3_l: "5th-8th",
        qf4_l: "5th-8th",
    }

    return placements

# ---------------------------------------------------------------------------
# 5. MONTE CARLO LOOP
# ---------------------------------------------------------------------------
PLACEMENT_ORDER = ["1st", "2nd", "3rd", "4th", "5th-8th"]



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
