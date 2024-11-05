import csv
from itertools import combinations

# Función para leer el archivo CSV
def leer_jugadores(archivo_csv):
    jugadores = []
    with open(archivo_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            jugadores.append({
                'jugador': row['jugador'],
                'equipo': row['equipo'],
                'precio': int(row['precio']),
                'rating': float(row['rating']),
                'ranking_equipo': int(row['ranking_equipo'])  # Nueva columna de ranking
            })
    return jugadores

# Función para obtener el "peso de ranking" del equipo
def obtener_peso_ranking(ranking_equipo):
    # Agrupación de rangos: de 1 a 5 -> 1, de 6 a 10 -> 2, y así sucesivamente
    return (ranking_equipo - 1) // 5 + 1

# Función para calcular el mejor equipo
def mejor_equipo(jugadores, presupuesto, num_jugadores=5, max_por_equipo=2):
    mejor_puntuacion_relativa = float('-inf')
    mejor_combinacion = None
    
    # Generar todas las combinaciones posibles de equipos de 'num_jugadores' jugadores
    for equipo in combinations(jugadores, num_jugadores):
        if sum(j['precio'] for j in equipo) > presupuesto:
            continue  # Saltar si el equipo excede el presupuesto
        
        # Contar jugadores por equipo
        equipos_conteo = {}
        for j in equipo:
            equipos_conteo[j['equipo']] = equipos_conteo.get(j['equipo'], 0) + 1
        
        # Verificar la restricción de máximo de jugadores por equipo
        if any(c > max_por_equipo for c in equipos_conteo.values()):
            continue  # Saltar si algún equipo excede el límite permitido
        
        # Calcular rating total y peso total del ranking
        rating_total = sum(j['rating'] for j in equipo)
        peso_ranking_total = sum(obtener_peso_ranking(j['ranking_equipo']) for j in equipo)
        
        # Calcular el rating relativo (rating total dividido por el peso del ranking total)
        puntuacion_relativa = rating_total / peso_ranking_total
        
        # Guardar la mejor combinación
        if puntuacion_relativa > mejor_puntuacion_relativa:
            mejor_puntuacion_relativa = puntuacion_relativa
            mejor_combinacion = equipo
    
    return mejor_combinacion, mejor_puntuacion_relativa

# Código principal
archivo_csv = 'jugadores.csv'
jugadores = leer_jugadores(archivo_csv)
presupuesto = 1000

# Obtener el mejor equipo
mejor_equipo_seleccionado, mejor_puntuacion_relativa = mejor_equipo(jugadores, presupuesto)

# Mostrar el equipo seleccionado y la puntuación relativa
print("Mejor equipo seleccionado:")
for j in mejor_equipo_seleccionado:
    print(f"Jugador: {j['jugador']}, Equipo: {j['equipo']}, Precio: {j['precio']}, Rating: {j['rating']}, Ranking Equipo: {j['ranking_equipo']}")

print(f"Puntuación relativa del equipo: {mejor_puntuacion_relativa}")
