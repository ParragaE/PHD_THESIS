# LoadFile.py
"""
Módulo para manejo de operaciones de carga de archivos CSV.

Funciones:
    cargar_datos(file_path) -> DataFrame
    guardar_datos(data, file_path) -> None
"""

import pandas as pd

def cargar_datos(file_path):
    """Carga datos de un archivo CSV y devuelve un DataFrame."""
    return pd.read_csv(file_path)

def guardar_datos(data, file_path):
    """Guarda datos en un archivo CSV."""
    data.to_csv(file_path, index=False)
