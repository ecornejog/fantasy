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

def expected_matches_swiss(p):
    """
    Expected number of matches in Swiss stage where teams play until
    someone reaches 3 wins or 3 losses (i.e., best of up to 5 matches,
    but stopping when someone gets 3).
    p = per-match win probability (0..1)
    Returns E[N] where N in {3,4,5}.
    """
    q = 1.0 - p

    # Probabilities of finishing in exactly n matches
    P3 = p**3 + q**3
    P4 = 3 * (p**3 * q) + 3 * (q**3 * p)
    P5 = 6 * (p**3 * q**2) + 6 * (q**3 * p**2)

    # numeric safety: normalize if tiny numerical drift
    total = P3 + P4 + P5
    if total <= 0:
        return 3.0
    if abs(total - 1.0) > 1e-8:
        P3 /= total
        P4 /= total
        P5 /= total

    expected = 3.0 * P3 + 4.0 * P4 + 5.0 * P5
    return expected

def expected_points_swiss(p, B, m_max=5):
    """
    p: per-match win probability (0..1)
    B: base points per match for the player (rating based), scalar
    m_max: maximum swiss rounds (default 5)
    Returns: (E_matches, E_points_total)
    """
    q = 1.0 - p

    # scenario probabilities (separate win/lose outcomes)
    P3_win = p**3
    P3_loss = q**3
    P4_win = 3 * (p**3 * q)
    P4_loss = 3 * (q**3 * p)
    P5_win = 6 * (p**3 * q**2)
    P5_loss = 6 * (q**3 * p**2)

    # sanity normalize
    total_prob = P3_win + P3_loss + P4_win + P4_loss + P5_win + P5_loss
    if total_prob <= 0:
        # fallback
        return expected_matches_swiss(p), B * m_max
    # normalize to avoid tiny rounding issues
    P3_win /= total_prob
    P3_loss /= total_prob
    P4_win /= total_prob
    P4_loss /= total_prob
    P5_win /= total_prob
    P5_loss /= total_prob

    # helper: team points for played rounds
    # for finish-with-3-wins at N: teamPts_played = 27 - 3*N
    # for finish-with-3-losses at N: teamPts_played = 6*N - 27
    def total_points_played_win(N):
        team_pts = 27.0 - 3.0 * N
        return B * N + team_pts

    def total_points_played_loss(N):
        team_pts = 6.0 * N - 27.0
        return B * N + team_pts

    # compute scenario totals
    # win cases:
    tp3w = total_points_played_win(3)          # played 3 rounds, 3 wins
    total3w = tp3w * (m_max / 3.0)              # padding multiplies by m_max / N

    tp4w = total_points_played_win(4)
    total4w = tp4w * (m_max / 4.0)

    tp5w = total_points_played_win(5)
    total5w = tp5w * (m_max / 5.0)              # usually just tp5w (no padding) but keep formula

    # loss cases:
    tp3l = total_points_played_loss(3)
    total3l = tp3l - 3.0 * (m_max - 3.0)

    tp4l = total_points_played_loss(4)
    total4l = tp4l - 3.0 * (m_max - 4.0)

    tp5l = total_points_played_loss(5)
    total5l = tp5l - 3.0 * (m_max - 5.0)        # zero extra rounds => same as tp5l

    # expected total points
    E_points = (
        P3_win * total3w +
        P4_win * total4w +
        P5_win * total5w +
        P3_loss * total3l +
        P4_loss * total4l +
        P5_loss * total5l
    )

    # expected matches (exact formula)
    E_matches = 3.0 * (P3_win + P3_loss) + 4.0 * (P4_win + P4_loss) + 5.0 * (P5_win + P5_loss)

    return E_matches, E_points

def get_rounds_from_teams(n_teams, format_token):
    """
    Estima número de rondas (mapas) esperables para formato.
    - single: ceil(log2(n))
    - double: ceil(log2(n)) + 1 (approx)
    - swiss: 3..5; usamos 3 como mínimo
    - group_playoff: aproximamos como single con +1
    """
    print(f"Detectado formato: {format_token}, con {n_teams} equipos.")
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
    expected_points_total_list = []
    expected_points_base_list = []
    expected_team_points_total_list = []

    for _, row in df.iterrows():
        seed = int(row["seed"])
        opp_seed = int(row.get("opp_seed_first_match", seed))

        team_pts = seed_pts_map.get(seed, row["team_points_abs"])
        opp_pts = seed_pts_map.get(opp_seed, team_pts)

        # per-match win prob (ELO-style)
        p_win_first = elo_win_prob(team_pts, opp_pts, scale=ELO_SCALE)
        p_win = p_win_first

        # Base points per match (rating-based)
        B = (row["rating"] - 100.0) / 2.0

        if format_token == "swiss":
            # Use the exact Swiss model (includes padding/elimination)
            E_matches, E_points_total = expected_points_swiss(p_win, B, m_max=5)

            # Derive expected base / team components for diagnostics:
            # For Swiss we compute expected base as:
            #   E_base = sum_over_scenarios(base_points_scenario * P_scenario)
            # where base_points_scenario = B*m_max for win scenarios (because padded to m_max),
            # and = B*N for loss scenarios (no base for padded rounds).
            q = 1.0 - p_win
            P3w = p_win**3
            P4w = 3 * (p_win**3 * q)
            P5w = 6 * (p_win**3 * q**2)
            P3l = q**3
            P4l = 3 * (q**3 * p_win)
            P5l = 6 * (q**3 * p_win**2)
            # normalize tiny drift
            total_prob = P3w + P4w + P5w + P3l + P4l + P5l
            if total_prob <= 0:
                total_prob = 1.0
            P3w /= total_prob; P4w /= total_prob; P5w /= total_prob
            P3l /= total_prob; P4l /= total_prob; P5l /= total_prob

            # base totals per scenario
            base_3w = B * 5.0   # winners padded to m_max => base = B * m_max
            base_4w = B * 5.0
            base_5w = B * 5.0
            base_3l = B * 3.0   # losers: base only for played rounds
            base_4l = B * 4.0
            base_5l = B * 5.0

            E_base = (P3w * base_3w + P4w * base_4w + P5w * base_5w +
                      P3l * base_3l + P4l * base_4l + P5l * base_5l)

            # team component is remainder
            E_team = E_points_total - E_base

            expected_matches = E_matches
            expected_points_total = E_points_total
            expected_points_base = E_base
            expected_team = E_team

        else:
            # Non-Swiss (geometric approx)
            expected_matches = expected_matches_for_player(p_win, rounds) * format_mult

            # Base and team parts computed separately as before:
            expected_points_base = B * expected_matches
            team_points_per_match = 9.0 * p_win - 3.0
            expected_team = team_points_per_match * expected_matches
            expected_points_total = expected_points_base + expected_team

        # append lists
        first_win_probs.append(p_win_first)
        expected_matches_list.append(expected_matches)
        expected_points_total_list.append(expected_points_total)
        expected_points_base_list.append(expected_points_base)
        expected_team_points_total_list.append(expected_team)

    df["first_win_prob"] = first_win_probs
    df["expected_matches"] = expected_matches_list
    df["expected_points_total"] = expected_points_total_list
    df["expected_points_base"] = expected_points_base_list
    df["expected_team_points_total"] = expected_team_points_total_list

    # keep also points_base_per_match for diagnostics
    df["points_base_per_match"] = (df["rating"] - 100.0) / 2.0

    df["first_win_prob"] = first_win_probs
    df["bo5_bonus"] = df["team_power"] * (bo5_multiplier - 1.0) * (df["seed"] <= 4)
    df["rating_norm"] = df["rating"] / max(df["rating"].max(), 1.0)

     # puntos de equipo por partido y total esperado
    # team points per match = 6*p - 3*(1-p) = 9*p - 3
    df["team_points_per_match"] = 9.0 * df["first_win_prob"] - 3.0

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
cols = ["jugador","equipo","first_win_prob","expected_matches",
        "points_base_per_match","expected_points_base","team_points_per_match",
        "expected_team_points_total","expected_points_total","popularity_penalty_factor",
        "adj_expected_points","final_score"]
print(scored_sorted[cols].head(10).to_string(index=False))