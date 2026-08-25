# Modulos/Analysis_DarParser/ProcessData.py

import os
import re
import pandas as pd
from tqdm.notebook import tqdm
from Analysis_DarParser.ProcessFiles import extraer_datos_de_archivo
from dataset_filter import DatasetFilter, match_io_file

def coincide_dataset(file_path_trace, dataset_prefix):
    if not dataset_prefix:
        return True
    return dataset_prefix.lower() in file_path_trace.lower()


def coincide_formato(file_path_trace, file_format):
    path = file_path_trace.lower()
    fmt = file_format.lower().replace(".", "")

    if fmt in ["h5", "hdf5"]:
        return any(token in path for token in ["h5", "hdf5"])
    elif fmt == "npz":
        return "npz" in path
    elif fmt in ["tfrecord", "tfrecords"]:
        return any(token in path for token in ["tfrecord", "tfrecords"])
    else:
        return fmt in path


def extraer_info_cabecera(data):
    """Extrae JobID, Nprocs y metadatos de ejecución (modo) del log de Darshan."""
    texto = "".join(data[:100])
    
    # 1. Identificador de Job
    jobid_match = re.search(r"# jobid:\s+(\d+)", texto)
    jobid = jobid_match.group(1) if jobid_match else "0000000"

    # 2. Total de Procesos
    nprocs_match = re.search(r"# nprocs:\s+(\d+)", texto)
    nprocs = int(nprocs_match.group(1)) if nprocs_match else 0
    
    # 3. 🆕 EXTRAER MODO DE EJECUCIÓN (-m o -fa)
    # Buscamos la línea que empieza por "# exe:" y capturamos el flag
    exe_match = re.search(r"# exe:.*(-m\s+\d+|-fa\s+\w+)", texto)
    exe_mode = exe_match.group(1) if exe_match else "default"
    
    return jobid, nprocs, exe_mode

def construir_mapa_fs(data):
    """
    Escanea la cabecera del archivo de Darshan y construye un diccionario
    con los puntos de montaje y su tipo real (nfs, lustre, gpfs, etc.)
    """
    fs_map = {}
    for line in data:
        # Buscamos las líneas de montaje que escribe Darshan
        if line.startswith("# mount entry:"):
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                punto_montaje = parts[1].strip()
                tipo_fs = parts[2].strip().lower()
                fs_map[punto_montaje] = tipo_fs
    
    # Salvaguarda: si el archivo no tiene la sección de montaje por algún motivo
    if not fs_map:
        fs_map = {'/mnt': 'nfs', '/p/scratch': 'lustre', '/lustre': 'lustre'}
    return fs_map

def determinar_fs_type(file_path_trace, fs_map):
    """Asigna el sistema de archivos comparando el inicio de la ruta con el mapa real."""
    for mnt_path, mnt_type in fs_map.items():
        if file_path_trace.startswith(mnt_path):
            return mnt_type
    return "nfs" # Fallback por defecto para tus entornos de DeepGalaxy si no coincide

def analizar_directorio_y_procesar(input_dir, df_acumulado, file_format, dataset_filter, app_name):
    if not os.path.exists(input_dir):
        print(f"Error: El directorio {input_dir} no existe.")
        return df_acumulado

    if isinstance(dataset_filter, dict):
        dataset_filter = DatasetFilter(**dataset_filter)
    dataset_filter.validate()

    files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    columnas = [
        'Jobid', 'Nprocs', 'Exe_Mode_Flag', 'Record ID',
        'File_Format', 'File Name', 'FS Type', 'Counter', 'Value'
    ]

    rows_acumuladas = []

    for filename in tqdm(files, desc=f"Procesando {app_name}", unit="it"):
        file_path = os.path.join(input_dir, filename)
        data = extraer_datos_de_archivo(file_path)

        jobid, nprocs, exe_mode = extraer_info_cabecera(data)
        fs_map = construir_mapa_fs(data)

        for line in data:
            if line.startswith('#') or not line.strip():
                continue

            parts = line.split('\t')
            if len(parts) < 6:
                continue

            modulo = parts[0]

            if modulo not in ['POSIX', 'MPI-IO', 'LUSTRE']:
                continue

            record_id = parts[2]
            counter = parts[3]
            value = parts[4]
            file_path_trace = parts[5].strip()

            if match_io_file(file_path_trace, file_format, dataset_filter):
                fs_type = determinar_fs_type(file_path_trace, fs_map)
                file_name = file_path_trace.rsplit('/', 1)[-1]

                clean_format = file_format.lower().replace('.', '')
                if clean_format == "h5":
                    clean_format = "hdf5"

                rows_acumuladas.append([
                    jobid, nprocs, exe_mode, record_id,
                    clean_format, file_name, fs_type, counter, value
                ])

    if rows_acumuladas:
        df_acumulado = pd.DataFrame(rows_acumuladas, columns=columnas)
    else:
        print("⚠️ No se encontraron registros después de aplicar filtros de dataset/formato.")

    return df_acumulado


def analizar_directorio_y_procesar_vo(input_dir, df_acumulado, file_format, dataset_prefix, app_name):
    if not os.path.exists(input_dir):
        print(f"Error: El directorio {input_dir} no existe.")
        return df_acumulado

    files = [f for f in os.listdir(input_dir) if f.endswith('.txt')]
    columnas = ['Jobid', 'Nprocs', 'Exe_Mode_Flag', 'Record ID', 'File_Format', 'File Name', 'FS Type', 'Counter', 'Value']
    
    rows_acumuladas = []

    for filename in tqdm(files, desc=f"Procesando {app_name}", unit="it"):
        file_path = os.path.join(input_dir, filename)
        data = extraer_datos_de_archivo(file_path)
        
        # 1. Extraer metadatos reales de la cabecera del log
        jobid, nprocs, exe_mode = extraer_info_cabecera(data)
        
        # 2. Construir el mapa de File Systems dinámicamente desde el propio archivo
        fs_map = construir_mapa_fs(data)
        
        # 3. Procesar los contadores
        for line in data:
            if line.startswith('#') or not line.strip(): 
                continue
            
            parts = line.split('\t')
            if len(parts) < 6: 
                continue

           
            modulo = parts[0]
            # Solo procesamos contadores puros de rendimiento POSIX y MPI-IO
            if modulo not in ['POSIX', 'MPI-IO', 'LUSTRE']: 
                continue
                
            record_id = parts[2]
            counter = parts[3]
            value = parts[4]
            file_path_trace = parts[5].strip()
            
            # Filtro restrictivo estricto para aislar ÚNICAMENTE el dataset científico
            if dataset_prefix in file_path_trace and file_path_trace.endswith(file_format):
                # Determinar el tipo de FS usando el mapa dinámico que acabamos de extraer
                fs_type = determinar_fs_type(file_path_trace, fs_map)
                
                file_name = file_path_trace.rsplit('/', 1)[-1]
                clean_format = file_format.replace('.', '')
                
                rows_acumuladas.append([
                    jobid, nprocs, exe_mode, record_id, clean_format, file_name, fs_type, counter, value
                ])
                
    if rows_acumuladas:
        df_acumulado = pd.DataFrame(rows_acumuladas, columns=columnas)
               
    return df_acumulado