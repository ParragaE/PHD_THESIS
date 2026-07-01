# Funciones utilitarias generales.
# utilities.py
# Este módulo contiene funciones utilitarias que no encajan directamente en otras categorías.
import re

def acces_mode(access):
    """Devuelve una etiqueta legible para el modo de acceso."""
    if access == 'ss':
        return "Data loading mode shared"
    else:
        return "Data loading mode shared(reload+shuffle)"


def acces_mode_scaling(access):
    """Devuelve una etiqueta legible para el tipo de scaling."""
    if access == 'weak':
        return "Weak Scaling Type"
    else:
        return "Strong Scaling Type"

def dividir_nombre(nombre):
    # Ajustamos el patrón para que sea más flexible
    pattern = r'Output_(DG)(bw\d+)_?(f\d+c\d+)?(x\d+)(o?)'
    
    # Usamos re.match para encontrar las partes del nombre
    match = re.match(pattern, nombre)
    
    if match:
        # Si se encuentran coincidencias, devolvemos las partes del nombre
        return match.groups()
    else:
        # Si no hay coincidencia, mostramos el nombre que no pudo ser dividido
        print(f"No se pudo dividir el nombre: {nombre}")
        return None

def construir_nombre(nombre):
    # Dividimos el nombre en partes
    partes = dividir_nombre(nombre)
    
    if partes:
        # Asignamos cada parte a una variable
        parte1, parte2, parte3, parte4, parte5 = partes
        
        # Reconstruimos el nombre usando las partes, asegurando que las partes opcionales estén correctas
        fs = f"{parte1}_{parte2}_{parte3 if parte3 else ''}{parte4}_{parte5 if parte5 else ''}".strip("_")
        
        # Retornamos el nombre final
        return fs
    else:
        return "Nombre inválido"
        
# Función para extraer la extensión del archivo y guardarla en una nueva columna
def extraer_extension(df, columna):
    # Creamos una nueva columna 'fil_form' con la extensión del archivo
    df['fil_form'] = df[columna].str.split('.').str[-1]
    return df
