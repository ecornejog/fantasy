import csv
from itertools import combinations
from collections import Counter

# -----------------------------
# CONFIG TORNEO
# -----------------------------
TORNEO = {
    "partidos_min": 3,
    "partidos_opt": 3,
    "total_equipos": 16
}

PRESUPUESTO = 1000
NUM_JUGADORES = 5
MAX_POR_EQUIPO = 2


# -----------------------------
# UTILIDADES
# -----------------------------
def puntos_base(rating):
    return (rating - 100) / 2


def probabilidad_avance(ranking, total_equipos):
    return max(0.05, 1 - ranking / total_equipos)


def partidos_esperados(ranking):
    p = probabilidad_avance(ranking, TORNEO["total_equipos"])
    return (
        p * TORNEO["partidos_opt"]
        + (1 - p) * TORNEO["partidos_min"]
    )


def puntos_team(ranking):
    p = probabilidad_avance(ranking, TORNEO["total_equipos"])
    return 6 * p - 3 * (1 - p)


# -----------------------------
# LECTURA CSV
# -----------------------------
def leer_jugadores(path):
    jugadores = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            jugadores.append({
                "nombre": r["jugador"],
                "equipo": r["equipo"],
                "precio": int(r["precio"]),
                "rating": float(r["rating"]),
                "ranking": int(r["ranking_equipo"])
            })
    return jugadores


# -----------------------------
# EV POR JUGADOR
# -----------------------------
def ev_jugador(j):
    pe = partidos_esperados(j["ranking"])
    return pe * (
        puntos_base(j["rating"])
        + puntos_team(j["ranking"])
    )


# -----------------------------
# BUSQUEDA MEJORES EQUIPOS
# -----------------------------
def mejores_equipos(jugadores, top_n=10):
    equipos_validos = []

    for team in combinations(jugadores, NUM_JUGADORES):
        if sum(j["precio"] for j in team) > PRESUPUESTO:
            continue

        conteo = Counter(j["equipo"] for j in team)
        if any(v > MAX_POR_EQUIPO for v in conteo.values()):
            continue

        ev_total = sum(ev_jugador(j) for j in team)

        equipos_validos.append((ev_total, team))

    equipos_validos.sort(reverse=True, key=lambda x: x[0])
    return equipos_validos[:top_n]


# -----------------------------
# MAIN
# -----------------------------
jugadores = leer_jugadores("jugadores.csv")
top_equipos = mejores_equipos(jugadores)

for i, (ev, team) in enumerate(top_equipos, 1):
    print(f"\nEquipo #{i} | EV total: {ev:.2f}")
    for j in team:
        print(
            f"  {j['nombre']:10s} | {j['equipo']:8s} | "
            f"€{j['precio']:3d} | rating {j['rating']}"
        )