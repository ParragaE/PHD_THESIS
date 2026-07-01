# ProcessFiles.py
"""
Módulo para manejo de operaciones de lectura y escritura de archivos.

Funciones:
    extraer_datos_de_archivo(file_path) -> list
    escribir_a_csv(path_output, header, data_rows, is_header) -> None
"""

import os
import csv

def extraer_datos_de_archivo(file_path):
    """Lee el contenido de un archivo y devuelve sus líneas."""
    with open(file_path, 'r') as f:
        return f.readlines()

def escribir_a_csv(path_output, header, data_rows, is_header):
    """Escribe o actualiza los datos procesados a un archivo CSV."""
    file_exists = os.path.isfile(path_output)
    with open(path_output, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        if not file_exists or is_header:
            writer.writerow(header)
        writer.writerows(data_rows)
