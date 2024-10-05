import csv
from itertools import permutations

# Función para leer el archivo CSV
def leer_boosters(archivo_csv):
    boosters = []
    with open(archivo_csv, newline='') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)  # Leer los encabezados
        for row in reader:
            booster = {
                'nombre': row[0],
                'jugadores': [int(val) for val in row[1:]]
            }
            boosters.append(booster)
    return boosters

# Función para calcular la puntuación esperada de un jugador dado un booster
def calcular_puntuacion(probabilidad):
    return (probabilidad * 5) / 100  # Puntos si se cumple la misión

# Función para calcular la mejor asignación de boosters
def mejor_asignacion(boosters):
    mejor_puntuacion_total = float('-inf')
    mejor_asignacion_boosters = None
    
    # Obtener el número de jugadores (asumiendo que todos los boosters tienen el mismo número de jugadores)
    num_jugadores = len(boosters[0]['jugadores'])
    
    # Generar todas las permutaciones de asignación de boosters a jugadores
    for asignacion in permutations(range(len(boosters)), num_jugadores):  # Permutaciones de boosters
        puntuacion_total = 0
        
        # Iterar sobre los jugadores y asignar un booster
        for jugador_index in range(num_jugadores):
            booster_index = asignacion[jugador_index]
            probabilidad = boosters[booster_index]['jugadores'][jugador_index]
            puntuacion_total += calcular_puntuacion(probabilidad)
        
        # Guardar la asignación con la mejor puntuación total
        if puntuacion_total > mejor_puntuacion_total:
            mejor_puntuacion_total = puntuacion_total
            mejor_asignacion_boosters = asignacion
    
    return mejor_asignacion_boosters, mejor_puntuacion_total

# Código principal
archivo_csv = 'boosters.csv'
boosters = leer_boosters(archivo_csv)
mejor_asig, puntuacion = mejor_asignacion(boosters)

# Mostrar el resultado de la mejor asignación
print("Mejor asignación de boosters:")
for i, booster_index in enumerate(mejor_asig):
    booster = boosters[booster_index]
    print(f"Jugador {i+1} asignado a {booster['nombre']}")

print(f"Puntuación total esperada: {puntuacion}")
