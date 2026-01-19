import csv
from itertools import combinations
from collections import Counter

# ------------------------
# Lectura del CSV
# ------------------------
def leer_jugadores(archivo_csv):
    jugadores = []
    with open(archivo_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jugadores.append({
                'nombre': row['jugador'],
                'equipo': row['equipo'],
                'precio': int(row['precio']),
                'rating': float(row['rating']),
                'ranking': int(row['ranking_equipo'])
            })
    return jugadores


# ------------------------
# Función objetivo mejorada
# ------------------------
def calcular_score(equipo, alpha=1.5, beta=0.4):
    rating_total = sum(j['rating'] for j in equipo)

    # Penalización no lineal por ranking
    penalizacion_ranking = sum((j['ranking']) ** alpha for j in equipo)

    # Penalización por concentración en equipos top
    jugadores_top = sum(1 for j in equipo if j['ranking'] <= 5)
    penalizacion_diversidad = 1 + beta * jugadores_top

    return rating_total / penalizacion_ranking / penalizacion_diversidad


# ------------------------
# Búsqueda del mejor equipo
# ------------------------
def mejor_equipo(jugadores, presupuesto, n=5, max_por_equipo=2):
    mejor_score = float('-inf')
    mejor_team = None

    for equipo in combinations(jugadores, n):
        if sum(j['precio'] for j in equipo) > presupuesto:
            continue

        conteo = Counter(j['equipo'] for j in equipo)
        if any(v > max_por_equipo for v in conteo.values()):
            continue

        score = calcular_score(equipo)

        if score > mejor_score:
            mejor_score = score
            mejor_team = equipo

    return mejor_team, mejor_score


# ------------------------
# MAIN
# ------------------------
jugadores = leer_jugadores("jugadores.csv")
equipo, score = mejor_equipo(jugadores, presupuesto=1000)

print("Equipo óptimo:")
for j in equipo:
    print(f"{j['nombre']} | {j['equipo']} | ranking {j['ranking']} | rating {j['rating']}")

print(f"\nScore final: {score:.4f}")
