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

# ---------------------------------------------------------------------------
# 1. CONFIGURE YOUR TEAMS HERE
#    Order matters: teams are paired into the Opening Round in the order
#    given, i.e. (team[0] vs team[1]), (team[2] vs team[3]), etc.
#    "rating" can be any skill metric on a comparable scale (e.g. an Elo-like
#    rating, HLTV rating * 1000, etc.) - only the *differences* matter.
# ---------------------------------------------------------------------------
TEAMS = [
    ("magic", 1418),
    ("GL", 1282),
    ("Alliance", 1465),
    ("3DMAX", 1324),
    ("NIP", 1235),
    ("K27", 1256),
    ("Eyeballers", 1293),
    ("Sinners", 1129),
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

# ---------------------------------------------------------------------------
# 4. BRACKET SIMULATION
# ---------------------------------------------------------------------------
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

def simulate_tournament(teams):
    """
    Runs one full simulation of the bracket and returns a dict:
        {team_name: placement_label}
    placement_label is one of: "1st", "2nd", "3rd", "4th", "5th-6th", "7th-8th"
    """
    for team in teams:
        team.reset_stats()

    '''
    # --- GSL BO3 ---
    t = teams  # shorthand, list of X team names in seed order
    # --- opening round ---
    ow1A, ol1A = play_match(t[0], t[15])
    ow2A, ol2A = play_match(t[10], t[5])

    ow1B, ol1B = play_match(t[2], t[11])
    ow2B, ol2B = play_match(t[6], t[9])

    ow1C, ol1C = play_match(t[3], t[12])
    ow2C, ol2C = play_match(t[4], t[13])

    ow1D, ol1D = play_match(t[7], t[14])
    ow2D, ol2D = play_match(t[1], t[8])

    # --- winners round ---
    wwA, wlA =  play_match(ow1A, ow2A)
    wwB, wlB =  play_match(ow1B, ow2B)
    wwC, wlC =  play_match(ow1C, ow2C)
    wwD, wlD =  play_match(ow1D, ow2D)

    wwA.padding_rounds +=1
    wwB.padding_rounds +=1
    wwC.padding_rounds +=1
    wwD.padding_rounds +=1

    # --- elimination match ---
    ewA, elA =  play_match(ol1A, ol2A)
    ewB, elB =  play_match(ol1B, ol2B)
    ewC, elC =  play_match(ol1C, ol2C)
    ewD, elD =  play_match(ol1D, ol2D)

    elA.elim_rounds = 4
    elB.elim_rounds = 4
    elC.elim_rounds = 4
    elD.elim_rounds = 4

    # --- decider match ---
    dwA, dlA =  play_match(wlA, ewA)
    dwB, dlB =  play_match(wlB, ewB)
    dwC, dlC =  play_match(wlC, ewC)
    dwD, dlD =  play_match(wlD, ewD)

    dlA.elim_rounds = 3
    dlB.elim_rounds = 3
    dlC.elim_rounds = 3
    dlD.elim_rounds = 3
    
    # --- single elimination playoff bracket ---
    # --- Quarter finals ---
    qw1, ql1 = play_match(wwA,dwD)
    qw2, ql2 = play_match(wwB,dwC)
    qw3, ql3 = play_match(wwC,dwB)
    qw4, ql4 = play_match(wwD,dwA)

    ql1.elim_rounds = 2
    ql2.elim_rounds = 2
    ql3.elim_rounds = 2
    ql4.elim_rounds = 2

    # --- Semis ---
    sw1, sl1 = play_match(qw1, qw2)
    sw2, sl2 = play_match(qw3, qw4)

    sl1.elim_rounds = 1
    sl2.elim_rounds = 1

    # ---finals ---
    fw, fl = play_match(sw1, sw2)

    placements = {
            fw: "1st",
            fl: "2nd",
            sl1: "3rd-4th",
            sl2: "3rd-4th",
            ql1: "5th-8th",
            ql2: "5th-8th",
            ql3: "5th-8th",
            ql4: "5th-8th",
            dlA: "9th-12th",
            dlB: "9th-12th",
            dlC: "9th-12th",
            dlD: "9th-12th",
            elA: "13th-16th",
            elB: "13th-16th",
            elC: "13th-16th",
            elD: "13th-16th",
        }
    '''

    """
    # --- groups round robin ---
    # --- Group Stage ---
    t_G_A = teams[:len(TEAMS_G_A)]
    t_G_B = teams[len(TEAMS_G_A):]

    stats_G_A, match_log_G_A = simulate_group_stage(t_G_A)
    stats_G_B, match_log_G_B = simulate_group_stage(t_G_B)
    standings_G_A = rank_teams(t_G_A, stats_G_A, match_log_G_A)
    standings_G_B = rank_teams(t_G_B, stats_G_B, match_log_G_B)

    for team in standings_G_A:
        team.win_rounds = stats_G_A[team.name]["wins"]
        team.loss_rounds = stats_G_A[team.name]["losses"]
    for team in standings_G_B:
        team.win_rounds = stats_G_B[team.name]["wins"]
        team.loss_rounds = stats_G_B[team.name]["losses"]

    standings_G_A[3].elim_rounds = 3
    standings_G_B[3].elim_rounds = 3
    standings_G_A[4].elim_rounds = 3
    standings_G_B[4].elim_rounds = 3
    standings_G_A[5].elim_rounds = 3
    standings_G_B[5].elim_rounds = 3

    # --- single elimination bracket ---
    # --- quarterfinals ---
    standings_G_A[0].padding_rounds += 1
    standings_G_B[0].padding_rounds += 1
    qf1_w, qf1_l = play_match(standings_G_B[1], standings_G_A[2])
    qf2_w, qf2_l = play_match(standings_G_A[1], standings_G_B[2])
    qf1_l.elim_rounds = 2
    qf2_l.elim_rounds = 2

    # --- semifinals ---
    sf1_w, sf1_l = play_match(standings_G_A[0], qf1_w)
    sf2_w, sf2_l = play_match(standings_G_B[0], qf2_w)
    sf1_l.elim_rounds = 1
    sf2_l.elim_rounds = 1

    # --- finals ---
    f_w, f_l = play_match(sf1_w, sf2_w)
    
    placements = {
        f_w: "1st",
        f_l: "2nd",
        sf1_l: "3rd-4th",
        sf2_l: "3rd-4th",
        qf1_l: "5th-6th",
        qf2_l: "5th-6th",
        standings_G_A[3]: "7th-8th",
        standings_G_B[3]: "7th-8th",
        standings_G_A[4]: "9th-10th",
        standings_G_B[4]: "9th-10th",
        standings_G_A[5]: "11th-12th",
        standings_G_B[5]: "11th-12th",
    }
    """
    
    # --- Double elimination bracket structure ---
    t = teams  # shorthand, list of X team names in seed order
    # --- Opening Round ---
    ow1, ol1 = play_match(t[2], t[7])
    ow2, ol2 = play_match(t[4], t[3])
    ow3, ol3 = play_match(t[0], t[6])
    ow4, ol4 = play_match(t[1], t[5])

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
PLACEMENT_ORDER = ["1st", "2nd","3rd",  "4th", "5th-6th", "7th-8th"]


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
