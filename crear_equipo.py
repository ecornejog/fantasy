import pandas as pd
import itertools
import math
from math import ceil, log2

# ============================
# PARÁMETROS CONFIGURABLES
# ============================
MAX_BUDGET = 1000
TEAM_SIZE = 5
MAX_PER_TEAM = 2

# pesos para combinar puntos HLTV/Valve en "team_power"
WEIGHT_HLTV = 0.6
WEIGHT_VALVE = 0.4

# escala para función tipo Elo (mayor => menos diferencia por punto)
ELO_SCALE = 500.0

# penalización por popularidad (configurable por perfil)
POP_PENALTY_BASE = {
    "consistent": 0.25,
    "semi_anti_meta": 0.40,
    "high_ceiling": 0.20
}

# pesos de componentes del score por perfil
PROFILE_WEIGHTS = {
    "consistent": {"rating": 0.50, "team": 0.25, "first": 0.15, "bo5": 0.10},
    "semi_anti_meta": {"rating": 0.45, "team": 0.30, "first": 0.15, "bo5": 0.10},
    "high_ceiling": {"rating": 0.40, "team": 0.35, "first": 0.15, "bo5": 0.10},
}

# incremento aplicado por formato en partidos esperados
FORMAT_MULTIPLIER = {
    "single": 1.0,
    "double": 1.25,
    "swiss": 1.15,
    "group_playoff": 1.2
}

# ============================
# FUNCIONES AUXILIARES
# ============================

def load_data(path):
    df = pd.read_csv(path)
    # normalizamos pick_rate
    df["pick_rate"] = df.get("pick_rate").fillna(0).astype(float)

    # Si no tienes hltv_points/valve_points rellena con 0 para evitar NaN
    df["hltv_points"] = df.get("hltv_points").fillna(0).astype(float)
    df["valve_points"] = df.get("valve_points").fillna(0).astype(float)

    # rating
    df["rating"] = df["rating"].astype(float)

    return df

def compute_team_power(df):
    """ Crea team_power por jugador (normalizado 0..1) y team_points (para ELO) """
    df = df.copy()
    # normalizamos puntos (evitar division por 0)
    max_hltv = max(df["hltv_points"].max(), 1.0)
    max_valve = max(df["valve_points"].max(), 1.0)

    df["hltv_norm"] = df["hltv_points"] / max_hltv
    df["valve_norm"] = df["valve_points"] / max_valve

    # team_power en 0..1
    df["team_power"] = WEIGHT_HLTV * df["hltv_norm"] + WEIGHT_VALVE * df["valve_norm"]

    # team_points (escala absoluta para ELO): combinación lineal de puntos reales
    df["team_points_abs"] = WEIGHT_HLTV * df["hltv_points"] + WEIGHT_VALVE * df["valve_points"]

    return df

def build_team_strength_by_seed(df):
    """ Agrega fuerza de equipo por seed (media de players del mismo seed) """
    # asumimos que 'seed' es entero y que todos los jugadores del mismo equipo tienen mismo seed
    grouped = df.groupby("seed").agg({
        "team_power": "mean",
        "team_points_abs": "mean"
    }).rename(columns={"team_power": "seed_team_power", "team_points_abs":"seed_team_points"}).reset_index()
    # convertir a dict para lookup rápido
    pow_by_seed = grouped.set_index("seed")["seed_team_power"].to_dict()
    pts_by_seed = grouped.set_index("seed")["seed_team_points"].to_dict()
    return pow_by_seed, pts_by_seed

def elo_win_prob(team_pts, opp_pts, scale=ELO_SCALE):
    """ Probabilidad tipo Elo usando diferencia de puntos """
    # Δ = team - opp; convertimos a prob con scale (mayor scale = menor sensibilidad)
    delta = team_pts - opp_pts
    # prob de ganar (0..1)
    p = 1.0 / (1.0 + 10 ** (-delta / scale))
    return p

def detect_format_token(format_string):
    s = format_string.lower()
    if "swiss" in s:
        return "swiss"
    if "double" in s:
        return "double"
    if "group" in s or "winners advance" in s or "group winners" in s:
        return "group_playoff"
    # por defecto tomamos single elimination si menciona "single" o no se detecta
    return "single"

def get_rounds_from_teams(n_teams, format_token):
    """
    Estima número de rondas (mapas) esperables para formato.
    - single: ceil(log2(n))
    - double: ceil(log2(n)) + 1 (approx)
    - swiss: 3..5; usamos 3 como mínimo
    - group_playoff: aproximamos como single con +1
    """
    if format_token == "single":
        return ceil(log2(max(n_teams,2)))
    if format_token == "double":
        return ceil(log2(max(n_teams,2))) + 1
    if format_token == "swiss":
        # rounds Swiss típicos 3-5; usamos 4 como referencia mediana
        return 4
    if format_token == "group_playoff":
        return ceil(log2(max(n_teams,2))) + 1
    return ceil(log2(max(n_teams,2)))

# ============================
# CÁLCULO DE PARTIDOS ESPERADOS
# ============================
def expected_matches_for_player(p_win, rounds):
    """
    Aproximación: esperamos jugar:
      sum_{k=0}^{rounds-1} P_win^k = (1 - P_win^rounds) / (1 - P_win)
    Esto asume probabilidad similar por ronda (aprox).
    """
    if p_win <= 0:
        return 1.0  # al menos el primer partido
    if p_win >= 1:
        return float(rounds)
    # si p_win ~= 1, evitar numericos
    num = 1 - (p_win ** rounds)
    den = 1 - p_win
    return num / den

# ============================
# COMPUTE FINAL SCORE (versión corregida)
# ============================
def compute_scores_and_expected_points(df, format_string, profile="consistent", pop_lambda=None):
    """
    Calcula columnas: first_win_prob, expected_matches, points_base_per_match,
    expected_points_base, expected_team_points_total, expected_points_total,
    adj_expected_points (aplicada la penalidad por popularidad).
    Además deja final_score (heurístico) para diagnóstico.
    """
    df = df.copy()
    df = compute_team_power(df)  # usa la función ya definida en v2
    n_teams = int(df["seed"].nunique())
    format_token = detect_format_token(format_string)
    rounds = get_rounds_from_teams(n_teams, format_token)
    format_mult = FORMAT_MULTIPLIER.get(format_token, 1.0)
    bo5_multiplier = 1.15 if "bo5" in format_string.lower() else 1.0

    seed_power_map, seed_pts_map = build_team_strength_by_seed(df)

    first_win_probs = []
    expected_matches_list = []
    for _, row in df.iterrows():
        seed = int(row["seed"])
        opp_seed = int(row.get("opp_seed_first_match", seed))
        team_pts = seed_pts_map.get(seed, row["team_points_abs"])
        opp_pts = seed_pts_map.get(opp_seed, team_pts)
        p_win_first = elo_win_prob(team_pts, opp_pts, scale=ELO_SCALE)
        p_win = p_win_first
        expected_matches = expected_matches_for_player(p_win, rounds) * format_mult
        first_win_probs.append(p_win_first)
        expected_matches_list.append(expected_matches)

    df["first_win_prob"] = first_win_probs
    df["expected_matches"] = expected_matches_list
    df["bo5_bonus"] = df["team_power"] * (bo5_multiplier - 1.0) * (df["seed"] <= 4)
    df["rating_norm"] = df["rating"] / max(df["rating"].max(), 1.0)

    # puntos base por partido y esperados
    df["points_base_per_match"] = (df["rating"] - 100.0) / 2.0
    df["expected_points_base"] = df["points_base_per_match"] * df["expected_matches"]

    # puntos de equipo por partido y total esperado
    # team points per match = 6*p - 3*(1-p) = 9*p - 3
    df["team_points_per_match"] = 9.0 * df["first_win_prob"] - 3.0
    df["expected_team_points_total"] = df["team_points_per_match"] * df["expected_matches"]

    # total esperado sin roles/boosters
    df["expected_points_total"] = df["expected_points_base"] + df["expected_team_points_total"]

    # penalidad popularidad: multiplicativa
    if pop_lambda is None:
        pop_lambda = POP_PENALTY_BASE.get(profile, 0.25)
    df["pop_lambda"] = pop_lambda
    df["popularity_penalty_factor"] = 1.0 - df["pick_rate"].fillna(0.0) * pop_lambda
    # evitar negativos:
    df["popularity_penalty_factor"] = df["popularity_penalty_factor"].clip(lower=0.5)  # no bajar más del 50%

    df["adj_expected_points"] = df["expected_points_total"] * df["popularity_penalty_factor"]

    # final_score heurístico para diagnóstico (sin cambiar)
    w = PROFILE_WEIGHTS.get(profile, PROFILE_WEIGHTS["consistent"])
    df["final_score"] = (
        w["rating"] * df["rating_norm"]
        + w["team"] * df["team_power"]
        + w["first"] * df["first_win_prob"]
        + w["bo5"] * df["bo5_bonus"]
    ) - df["pick_rate"].fillna(0) * pop_lambda

    return df

# ============================
# OPTIMIZADOR (sin cambios funcionales)
# ============================
def optimize_team_by_expected_points(df):
    """
    Optimiza sum(adj_expected_points) sujeto a presupuesto y max por equipo.
    Devolvemos mejor equipo, score por adj_expected_points y también total final_score para diagnóstico.
    """
    best_sum = -10**9
    best_team = None
    best_final_score_sum = None
    players = df.to_dict("records")

    for combo in itertools.combinations(players, TEAM_SIZE):
        total_cost = sum(p["precio"] for p in combo)
        if total_cost > MAX_BUDGET:
            continue

        team_counts = {}
        for p in combo:
            team_counts[p["equipo"]] = team_counts.get(p["equipo"], 0) + 1
        if any(count > MAX_PER_TEAM for count in team_counts.values()):
            continue

        adj_points_sum = sum(p.get("adj_expected_points", 0.0) for p in combo)
        # como tie-breaker, sumamos final_score
        final_score_sum = sum(p.get("final_score", 0.0) for p in combo)

        if adj_points_sum > best_sum or (math.isclose(adj_points_sum, best_sum) and final_score_sum > best_final_score_sum):
            best_sum = adj_points_sum
            best_team = combo
            best_final_score_sum = final_score_sum

    return best_team, best_sum, best_final_score_sum

# ============================
# PRINT
# ============================
def print_team(team, adj_points_sum, final_score_sum):
    total_cost = sum(p["precio"] for p in team)
    total_expected_base = sum(p["expected_points_base"] for p in team)
    total_expected_team = sum(p["expected_team_points_total"] for p in team)
    total_expected = sum(p["expected_points_total"] for p in team)
    total_adj = adj_points_sum

    print("\n==============================")
    print("TEAM RESULTADO (optimizado por adj_expected_points)")
    print("==============================")
    for p in team:
        print(f"{p['jugador']} ({p['equipo']}) - Precio: {p['precio']} - ExpMatches: {p['expected_matches']:.2f} "
              f"- ExpBase: {p['expected_points_base']:.2f} - ExpTeam: {p['expected_team_points_total']:.2f} "
              f"- AdjExp: {p['adj_expected_points']:.2f} - final_score: {p['final_score']:.3f}")
    print("------------------------------")
    print(f"Total Cost: {total_cost}")
    print(f"Total Expected Base Points: {total_expected_base:.2f}")
    print(f"Total Expected Team Points: {total_expected_team:.2f}")
    print(f"Total Expected Points (no roles/boosters): {total_expected:.2f}")
    print(f"Total Adjusted Expected Points (objetivo): {total_adj:.2f}")
    print(f"Total final_score (diagnóstico): {final_score_sum:.4f}")
    print("==============================\n")


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    csv_path = "jugadores.csv"
    format_type = input("Ingrese formato torneo (ej: 'Single elimination BO3 Grand Final BO5', 'Swiss BO3', 'Double elimination BO3'): ")
    df = load_data(csv_path)
    profiles = ["consistent", "semi_anti_meta", "high_ceiling"]

    for profile in profiles:
        print(f"\n######## PERFIL: {profile.upper()} ########")
        scored_df = compute_scores_and_expected_points(df, format_type, profile, pop_lambda=None)
        scored_df = scored_df[scored_df["expected_points_total"] > 0].copy()
        team, adj_sum, final_sum = optimize_team_by_expected_points(scored_df)
        if team is None:
            print("No se encontró equipo válido (revisa presupuesto/constraints).")
        else:
            print_team(team, adj_sum, final_sum)
    scored_sorted = scored_df.sort_values(by="adj_expected_points", ascending=False)
print("\nTop 20 jugadores por adj_expected_points (diagnóstico):\n")
cols = ["jugador","equipo","precio","rating","seed","first_win_prob","expected_matches",
        "points_base_per_match","expected_points_base","team_points_per_match",
        "expected_team_points_total","expected_points_total","popularity_penalty_factor",
        "adj_expected_points","final_score"]
print(scored_sorted[cols].head(10).to_string(index=False))