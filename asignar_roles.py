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
def mejor_asignacion(roles, num_jugadores):
    mejor_puntuacion_total = float('-inf')
    mejor_asignacion_roles = None

    # Generar todas las permutaciones de roles (seleccionando una para cada jugador)
    for asignacion in permutations(roles, num_jugadores):  # Elegimos 'num_jugadores' roles de entre todos los disponibles
        puntuacion_total = 0
        
        # Iterar sobre los jugadores y asignar un rol
        for jugador_index in range(num_jugadores):
            prob_grande, prob_pequena = asignacion[jugador_index]['jugadores'][jugador_index]
            puntuacion_total += calcular_puntuacion(prob_grande, prob_pequena)
        
        # Guardar la asignación con la mejor puntuación total
        if puntuacion_total > mejor_puntuacion_total:
            mejor_puntuacion_total = puntuacion_total
            mejor_asignacion_roles = asignacion
    
    return mejor_asignacion_roles, mejor_puntuacion_total

# Código principal
archivo_csv = 'roles.csv'
roles = leer_probabilidades(archivo_csv)
num_jugadores = len(roles[0]['jugadores'])  # Número de jugadores a asignar (puede ser 5 o cualquier cantidad)

mejor_asig, puntuacion = mejor_asignacion(roles, num_jugadores)

# Mostrar el resultado de la mejor asignación
print("Mejor asignación de roles:")
for i, rol_asignado in enumerate(mejor_asig):
    print(f"Jugador {i+1} asignado a {rol_asignado['nombre']}")

print(f"Puntuación total esperada: {puntuacion}")