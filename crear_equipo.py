# fantasy_teams.py

import argparse
import heapq
from collections import defaultdict

import pandas as pd


MAX_BUDGET = 1000
TEAM_SIZE = 5
MAX_PER_TEAM = 2
TOP_N = 100


def compute_player_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - total_rounds_played
      - base_points
      - team_points
      - padding_points
      - player_points
    """

    df = df.copy()

    numeric_cols = ["precio", "rating", "win_rounds", "loss_rounds", "padding_rounds", "elim_rounds"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["total_rounds_played"] = df["win_rounds"] + df["loss_rounds"]

    df["base_points"] = ((df["rating"] - 100) / 2.0) * df["total_rounds_played"]

    df["team_points"] = (6 * df["win_rounds"]) + (-3 * df["loss_rounds"]) + (-3 * df["elim_rounds"])

    df["padding_points"] = df.apply(
        lambda row: ((row["base_points"] + row["team_points"]) / row["total_rounds_played"])
        if row["total_rounds_played"] > 0
        else 0,
        axis=1,
    )

    # If you do NOT want padding_rounds to multiply, change this line to:
    # df["player_points"] = df["base_points"] + df["team_points"] + df["padding_points"]
    df["player_points"] = (
        df["base_points"] + df["team_points"] + (df["padding_rounds"] * df["padding_points"])
    )

    return df


def generate_valid_teams(df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds the best TOP_N valid teams of size TEAM_SIZE (budget and max players
    per real team respected) without storing all possible teams.

    Uses a min-heap of size TOP_N: the root is always the worst team kept.
    """

    # Sort by points (desc) so we can compute upper bounds for pruning
    df = df.sort_values(
        by=["player_points", "jugador"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)

    names = df["jugador"].tolist()
    real_teams = df["equipo"].tolist()
    prices = df["precio"].tolist()
    points = df["player_points"].tolist()
    n = len(df)

    # prefix[i] = sum of points[:i]  -> best k players starting at i = prefix[i+k] - prefix[i]
    prefix = [0.0]
    for p in points:
        prefix.append(prefix[-1] + p)

    # Heap entries: (total_points, -total_price, chosen_indices)
    # Smaller tuple = worse team (fewer points, or same points but higher price)
    heap = []
    team_count = defaultdict(int)
    chosen = []

    def search(start: int, price: int, pts: float):
        k = TEAM_SIZE - len(chosen)

        if k == 0:
            entry = (pts, -price, tuple(chosen))
            if len(heap) < TOP_N:
                heapq.heappush(heap, entry)
            elif entry > heap[0]:
                heapq.heapreplace(heap, entry)
            return

        for i in range(start, n - k + 1):
            # Upper bound: best case is taking the next k best players from i onwards.
            # It only decreases as i grows, so we can stop the whole loop.
            if len(heap) == TOP_N:
                bound = pts + prefix[i + k] - prefix[i]
                if bound < heap[0][0]:
                    break

            if price + prices[i] > MAX_BUDGET:
                continue
            if team_count[real_teams[i]] >= MAX_PER_TEAM:
                continue

            chosen.append(i)
            team_count[real_teams[i]] += 1
            search(i + 1, price + prices[i], pts + points[i])
            team_count[real_teams[i]] -= 1
            chosen.pop()

    search(0, 0, 0.0)

    # Best first: more points, then lower price
    best = sorted(heap, key=lambda e: (-e[0], -e[1]))

    rows = []
    for rank, (total_points, neg_price, idxs) in enumerate(best, start=1):
        # idxs are already ordered by points desc (and name for ties)
        row = {
            "rank": rank,
            "total_points": total_points,
            "total_price": -neg_price,
        }
        for j, i in enumerate(idxs, start=1):
            row[f"player_{j}"] = names[i]
            row[f"player_{j}_points"] = points[i]
        rows.append(row)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Generate the best valid fantasy teams from a CSV.")
    parser.add_argument("input_csv", help="Path to the input CSV")
    parser.add_argument(
        "-o",
        "--output_csv",
        default="all_possible_teams.csv",
        help="Path to the output CSV",
    )
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)
    df.columns = [c.strip().lower() for c in df.columns]

    required_columns = {
        "jugador",
        "equipo",
        "precio",
        "rating",
        "win_rounds",
        "loss_rounds",
        "padding_rounds",
        "elim_rounds",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

    scored_df = compute_player_points(df)
    teams_df = generate_valid_teams(scored_df)

    if teams_df.empty:
        print("No valid teams found with the current constraints.")
        return

    teams_df.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    print(f"Saved {len(teams_df)} valid teams to: {args.output_csv}")
    print("Top 5 teams:")
    print(teams_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()