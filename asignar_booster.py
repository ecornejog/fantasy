import csv
import math

#TODO - IMPORTANTE: cambiar el numero de partidos y equipos si es necesario

# ----------------------------------
# FUNCIONES
# ----------------------------------
def leer_boosters(path):
    """
    Lee boosters CSV:
    booster,jugador1,jugador2,...,jugadorN
    """
    boosters = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            booster_name = row[0]
            probs = [int(x) for x in row[1:]]  # porcentaje
            boosters.append({
                "nombre": booster_name,
                "probs": probs
            })
    return boosters


def calcular_partidos_esperados(ranking_equipo, total_equipos=16, min_partidos=3, opt_partidos=3):
    """
    Misma formula de FASE A
    """
    p = max(0.05, 1 - ranking_equipo / total_equipos)
    return p * opt_partidos + (1 - p) * min_partidos


def ev_booster(p_exito):
    """
    EV máximo por booster = 5
    """
    ev = 5 * p_exito
    return min(ev, 5)


def asignar_boosters_por_jugador(jugadores, boosters):
    """
    Asigna boosters a jugadores según partidos esperados.
    Cada booster solo puede asignarse a un jugador.
    """
    # 1️⃣ Calculamos partidos esperados
    for j in jugadores:
        j["partidos_esperados"] = calcular_partidos_esperados(j["ranking_equipo"])

    # 2️⃣ Preparamos lista de posibles asignaciones (EV, jugador, booster)
    posibles = []
    for idx_j, jugador in enumerate(jugadores):
        for booster in boosters:
            p_exito = booster["probs"][idx_j] / 100
            ev = ev_booster(p_exito)
            posibles.append({
                "ev": ev,
                "jugador": jugador["nombre"],
                "booster": booster["nombre"]
            })

    # 3️⃣ Ordenamos por EV descendente
    posibles.sort(key=lambda x: x["ev"], reverse=True)

    # 4️⃣ Asignación respetando:
    # - boosters únicos
    # - número máximo de boosters por jugador = partidos esperados
    asignaciones = {j["nombre"]: [] for j in jugadores}
    boosters_usados = set()

    for item in posibles:
        jugador = item["jugador"]
        booster = item["booster"]
        max_boosters = math.ceil(
            next(j["partidos_esperados"] for j in jugadores if j["nombre"] == jugador)
        )

        if booster in boosters_usados:
            continue
        if len(asignaciones[jugador]) >= max_boosters:
            continue

        asignaciones[jugador].append((booster, item["ev"]))
        boosters_usados.add(booster)

    return asignaciones

# ------------------------
# EJEMPLO DE USO
# ------------------------
jugadores = [
    {"nombre": "osee", "ranking_equipo": 8},
    {"nombre": "xfloud", "ranking_equipo": 10},
    {"nombre": "swish", "ranking_equipo": 13},
    {"nombre": "afro", "ranking_equipo": 14},
    {"nombre": "luken", "ranking_equipo": 15}
]

boosters = leer_boosters("boosters.csv")
asignaciones = asignar_boosters_por_jugador(jugadores, boosters)

# ----------------------------------
# VISUALIZACION CLARA
# ----------------------------------
for jugador, boosts in asignaciones.items():
    boosts_str = ", ".join([f"{b[0]} ({b[1]:.2f})" for b in boosts])
    print(f"{jugador} → {boosts_str}")