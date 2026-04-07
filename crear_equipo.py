# fantasy_teams.py

import argparse
from collections import Counter
from itertools import combinations

import pandas as pd


MAX_BUDGET = 1000
TEAM_SIZE = 5
MAX_PER_TEAM = 2
TOP_N = 100


def compute_player_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - total_rounds
      - base_points
      - team_points
      - padding_points
      - player_points
    """

    df = df.copy()

    # Make sure numeric columns are numeric
    numeric_cols = ["precio", "rating", "win_rounds", "loss_rounds", "padding_rounds", "elim_rounds", "rat_multiplier"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["total_rounds_played"] = df["win_rounds"] + df["loss_rounds"]

    # Base points
    df["base_points"] = (((df["rating"]* df["rat_multiplier"]) - 100) / 2.0) * df["total_rounds_played"]

    # Team points
    df["team_points"] = (6 * df["win_rounds"]) + (-3 * df["loss_rounds"]) + (-3 * df["elim_rounds"])

    # Padding points per round
    df["padding_points"] = df.apply(
        lambda row: ((row["base_points"] + row["team_points"]) / row["total_rounds_played"])
        if row["total_rounds_played"] > 0
        else 0,
        axis=1,
    )

    # Final player score
    # If you do NOT want padding_rounds to multiply, change this line to:
    # df["player_points"] = df["base_points"] + df["team_points"] + df["padding_points"]
    df["player_points"] = (
        df["base_points"] + df["team_points"] + (df["padding_rounds"] * df["padding_points"])
    )

    return df


def generate_valid_teams(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates all valid teams of size TEAM_SIZE,
    respecting budget and max players from the same real team.
    """

    players = df.to_dict("records")
    valid_teams = []

    for combo in combinations(players, TEAM_SIZE):
        total_price = sum(p["precio"] for p in combo)
        if total_price > MAX_BUDGET:
            continue

        team_counter = Counter(p["equipo"] for p in combo)
        if any(count > MAX_PER_TEAM for count in team_counter.values()):
            continue

        # Sort players inside the team for consistent output
        combo_sorted = sorted(combo, key=lambda x: (-x["player_points"], x["jugador"]))

        total_points = sum(p["player_points"] for p in combo_sorted)

        row = {
            "total_points": total_points,
            "total_price": total_price,
        }

        for i, p in enumerate(combo_sorted, start=1):
            row[f"player_{i}"] = p["jugador"]
            row[f"player_{i}_points"] = p["player_points"]

        valid_teams.append(row)

    result = pd.DataFrame(valid_teams)

    if not result.empty:
        result = result.sort_values(
            by=["total_points", "total_price"],
            ascending=[False, True],
        ).reset_index(drop=True)

        result = result.head(TOP_N).copy()

        result.insert(0, "rank", range(1, len(result) + 1))


    return result


def main():
    parser = argparse.ArgumentParser(description="Generate all valid fantasy teams from a CSV.")
    parser.add_argument("input_csv", help="Path to the input CSV")
    parser.add_argument(
        "-o",
        "--output_csv",
        default="all_possible_teams.csv",
        help="Path to the output CSV",
    )
    args = parser.parse_args()

    # Read and normalize column names
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
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {sorted(missing)}")

    # Compute player scoring
    scored_df = compute_player_points(df)

    # Generate teams
    teams_df = generate_valid_teams(scored_df)

    if teams_df.empty:
        print("No valid teams found with the current constraints.")
        return

    # Save result
    teams_df.to_csv(args.output_csv, index=False, encoding="utf-8-sig")

    print(f"Saved {len(teams_df)} valid teams to: {args.output_csv}")
    print("Top 5 teams:")
    print(teams_df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()