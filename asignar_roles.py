import csv
from itertools import permutations

# ----------------------------------
# CALCULO EV DE ROL
# ----------------------------------
def ev_rol(prob_grande, prob_pequena):
    pG = prob_grande / 100
    pP = prob_pequena / 100
    pF = 1 - pG - pP
    return 5 * pG + 2 * pP - 2 * pF


# ----------------------------------
# LECTURA CSV ROLES
# ----------------------------------
def leer_roles(path):
    roles = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)  # rol, jugador1...
        for row in reader:
            roles.append({
                "nombre": row[0],
                "probs": [
                    tuple(map(int, c.split("/")))
                    for c in row[1:]
                ]
            })
    return roles


# ----------------------------------
# ASIGNACION OPTIMA
# ----------------------------------
def mejor_asignacion_roles(roles, num_jugadores=5):
    mejor_ev = float("-inf")
    mejor_asignacion = None

    for roles_sel in permutations(roles, num_jugadores):
        ev_total = 0

        for j in range(num_jugadores):
            probG, probP = roles_sel[j]["probs"][j]
            ev_total += ev_rol(probG, probP)

        if ev_total > mejor_ev:
            mejor_ev = ev_total
            mejor_asignacion = roles_sel

    return mejor_asignacion, mejor_ev


# ----------------------------------
# MAIN (ejemplo)
# ----------------------------------
roles = leer_roles("roles.csv")

asignacion, ev_roles = mejor_asignacion_roles(roles)

print("\nAsignación óptima de roles:")
for i, rol in enumerate(asignacion, 1):
    print(f"Jugador {i} → {rol['nombre']}")

print(f"\nEV total por roles: {ev_roles:.2f}")