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
    
    # Generar todas las permutaciones de asignación de roles
    for asignacion in permutations(range(len(roles))):  # Asignación de un rol a cada jugador
        puntuacion_total = 0
        
        for i, rol_index in enumerate(asignacion):
            rol = roles[rol_index]
            prob_grande, prob_pequena = rol['jugadores'][i]
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
for i, rol_index in enumerate(mejor_asig):
    rol = roles[rol_index]
    print(f"Jugador {i+1} asignado a {rol['nombre']}")

print(f"Puntuación total esperada: {puntuacion}")