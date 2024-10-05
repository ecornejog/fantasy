import csv
from itertools import combinations

# Función para leer los datos del CSV, ahora con la columna de 'ranking del equipo'
def leer_jugadores(archivo_csv):
    jugadores = []
    with open(archivo_csv, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            jugador = {
                'nombre': row['jugador'],
                'equipo': row['equipo actual'],
                'precio': int(row['precio']),
                'rating': float(row['rating']),
                'ranking_equipo': int(row['ranking del equipo'])  # Nueva columna de ranking
            }
            jugadores.append(jugador)
    return jugadores

# Función para validar que un equipo no tiene más de 2 jugadores del mismo equipo
def validar_equipo(jugadores):
    equipos = {}
    for jugador in jugadores:
        equipo = jugador['equipo']
        if equipo in equipos:
            equipos[equipo] += 1
            if equipos[equipo] > 2:
                return False
        else:
            equipos[equipo] = 1
    return True

# Función para calcular el mejor equipo posible basado en el rating relativo
def mejor_equipo(jugadores, presupuesto_max=1000):
    mejores_jugadores = []
    mejor_rating_relativo = 0
    
    # Generar todas las combinaciones posibles de 5 jugadores
    for equipo in combinations(jugadores, 5):
        # Verificar que el equipo respeta las reglas (presupuesto y no más de 2 jugadores del mismo equipo)
        total_precio = sum(jugador['precio'] for jugador in equipo)
        if total_precio <= presupuesto_max and validar_equipo(equipo):
            total_rating = sum(jugador['rating'] for jugador in equipo)
            suma_ranking = sum(jugador['ranking_equipo'] for jugador in equipo)
            
            # Calcular el rating relativo
            if suma_ranking > 0:  # Evitar división por cero
                rating_relativo = total_rating / suma_ranking
                
                # Guardar el equipo con el mejor rating relativo
                if rating_relativo > mejor_rating_relativo:
                    mejor_rating_relativo = rating_relativo
                    mejores_jugadores = equipo
    
    return mejores_jugadores, mejor_rating_relativo

# Código principal
archivo_csv = 'jugadores.csv'
jugadores = leer_jugadores(archivo_csv)
equipo_ideal, rating_relativo = mejor_equipo(jugadores)

# Mostrar el equipo ideal y su rating relativo
print("Equipo ideal basado en rating relativo:")
for jugador in equipo_ideal:
    print(f"{jugador['nombre']} ({jugador['equipo']}) - Precio: {jugador['precio']}, Rating: {jugador['rating']}, Ranking del equipo: {jugador['ranking_equipo']}")
print(f"Rating relativo total: {rating_relativo}")
