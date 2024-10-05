import csv
from itertools import permutations

# Función para leer el archivo CSV
def leer_probabilidades(archivo_csv):
    roles = []
    with open(archivo_csv, newline='') as csvfile:
        reader = csv.reader(csvfile)
        headers = next(reader)  # Leer los encabezados
        for row in reader:
            rol = {
                'nombre': row[0],
                'jugadores': [list(map(int, val.split('/'))) for val in row[1:]]
            }
            roles.append(rol)
    return roles

# Función para calcular la puntuación esperada de un jugador dado un rol
def calcular_puntuacion(prob_grande, prob_pequena):
    puntos_grande = prob_grande * 5 / 100
    puntos_pequena = prob_pequena * 2 / 100
    puntos_fallo = -2 * (1 - (prob_grande + prob_pequena) / 100)
    return puntos_grande + puntos_pequena + puntos_fallo

# Función para calcular la mejor asignación de roles
def mejor_asignacion(roles):
    mejor_puntuacion_total = float('-inf')
    mejor_asignacion_roles = None
    
    # Generar todas las permutaciones de asignación de roles a jugadores
    jugadores = list(range(len(roles[0]['jugadores'])))  # Número de jugadores
    for asignacion in permutations(jugadores):
        puntuacion_total = 0
        
        # Iterar sobre los jugadores y asignar un rol
        for jugador_index, jugador_asignado in enumerate(asignacion):
            prob_grande, prob_pequena = roles[jugador_index]['jugadores'][jugador_asignado]
            puntuacion_total += calcular_puntuacion(prob_grande, prob_pequena)
        
        # Guardar la asignación con la mejor puntuación total
        if puntuacion_total > mejor_puntuacion_total:
            mejor_puntuacion_total = puntuacion_total
            mejor_asignacion_roles = asignacion
    
    return mejor_asignacion_roles, mejor_puntuacion_total

# Código principal
archivo_csv = 'roles.csv'
roles = leer_probabilidades(archivo_csv)
mejor_asig, puntuacion = mejor_asignacion(roles)

# Mostrar el resultado de la mejor asignación
print("Mejor asignación de roles:")
for i, jugador_asignado in enumerate(mejor_asig):
    rol = roles[i]
    print(f"Jugador {jugador_asignado + 1} asignado a {rol['nombre']}")

print(f"Puntuación total esperada: {puntuacion}")