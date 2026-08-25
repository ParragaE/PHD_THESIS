# Modulos/Analysis_DarParser/data_debugger.py
import os
import re
import pandas as pd
import numpy as np

def identificar_patrones_acceso(df):
    """
    Clasificador heuristico basado en ratios de E/S.
    """
    def evaluar_fila(row):
        # USAR EL FLAG REAL DE LA APLICACION
        exe_mode = str(row.get('Exe_Mode_Flag', '')).lower()

        # Buscamos el patron '-m' seguido de un espacio y un numero
        match = re.search(r'-m\s+(\d+)', exe_mode)
        
        if match:
            valor_m = int(match.group(1)) # Convertimos a numero entero
            if valor_m > 0:
                return "Shared+Reload+Shuffle"
            else:
                return "Shared"
            
        # Logica de DLIOv1 (-fa shared vs file_per_process)
        if 'fa shared' in exe_mode:
            return "Shared"
        elif 'fa multi' in exe_mode:
            return "file_per_process"
        
        fastest_rank = row.get('POSIX_FASTEST_RANK', 0)
        slowest_rank = row.get('POSIX_SLOWEST_RANK', 0)
        nprocs = row.get('Nprocs', 1)
        
        # 1. Clasificacion Individual
        if nprocs == 1 or (fastest_rank == slowest_rank and nprocs <= 1):
            return "Individual"
        
        # 2. Metricas de E/S
        bytes_leidos = row.get('POSIX_BYTES_READ', 0)
        max_byte = row.get('POSIX_MAX_BYTE_READ', 1) # Evitar div por cero
        total_lecturas = row.get('POSIX_READS', 1)   # Evitar div por cero
        consec_lecturas = row.get('POSIX_CONSEC_READS', 0)
        seq_lecturas = row.get('POSIX_SEQ_READS', 0)
        
        if max_byte == 0 or total_lecturas == 0:
            return "Shared (Escritura/Estandar)"
            
        ratio_relectura = bytes_leidos / max_byte
        ratio_secuencialidad = (consec_lecturas + seq_lecturas) / total_lecturas
        
        # 3. arbol de decision
        if ratio_relectura > 1.5:
            return "Shared+Reload+Shuffle" if ratio_secuencialidad < 0.20 else "Shared+Reload"
        elif ratio_secuencialidad < 0.20:
            return "Shared+Reload+Shuffle" if ratio_relectura > 1.1 else "Shared+Shuffle"
        else:
            return "Shared"

    # Aplicacion segura: si ya existe, la sobreescribimos; si no, la creamos
    df['Access_Pattern_Detected'] = df.apply(evaluar_fila, axis=1)

    def evaluar_fila_exe(row):
        # USAR EL FLAG REAL DE LA APLICACI”N
        exe_mode = str(row.get('Exe_Mode_Flag', '')).lower()
        
        # Logica de DeepGalaxy (-m 0 -> Shared, -m 1 -> Shared+Shuffle)
        if 'm 0' in exe_mode:
            return "Shared"
        elif 'm ' in exe_mode:
            return "Shared+Reload+Shuffle"
            
        # Logica de DLIOv1 (-fa shared vs file_per_process)
        if 'fa shared' in exe_mode:
            return "Shared"
        elif 'fa multi' in exe_mode:
            return "file_per_process"
        # Fallback a la heur®™stica fisica si el flag no es claro
        return "Shared (Detectado Fisicamente)"
        
    df['Access_Pattern_flag'] = df.apply(evaluar_fila_exe, axis=1)
    
    # Reordenamiento seguro para que la columna aparezca al principio
    cols = ['Jobid', 'Nprocs', 'Access_Pattern_Detected', 'Access_Pattern_flag'] + [c for c in df.columns if c not in ['Jobid', 'Nprocs', 'Access_Pattern_Detected', 'Access_Pattern_flag']]
    return df[cols]

def leer_valores_filtro_y_transformar(path_output):
    """Pivota las m√©tricas de Darshan a columnas para preparar el an√°lisis estad√≠stico."""
    if os.path.exists(path_output):
        data = pd.read_csv(path_output)
        if not data.empty:
            indices = ["Jobid"]
            for col in ["Nprocs", "Exe_Mode_Flag"]:
                if col in data.columns:
                    indices.append(col)
            indices.extend(["Record ID", "File_Format", "File Name", "FS Type"])
            
            pivot_table = data.pivot_table(index=indices, 
                                           columns="Counter", 
                                           values="Value", 
                                           aggfunc='first').reset_index()
                                           
            pivot_table.to_csv(path_output, index=False)
            print(f"[Pivot] Transformacion a matriz completada.")

def actualizar_y_depurar_csv(output_path, path_output_dep):
    """Limpia ceros y ejecuta el clasificador de patrones."""
    if not os.path.exists(output_path):
        return
    
    df = pd.read_csv(output_path)
    
    # 1. Limpieza de datos
    # CODIGO OPTIMIZADO (Limpio y sin advertencias)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(df[col])
    df = df.loc[:, (df != 0).any(axis=0)]
    
    # 2. Clasificacion heuristica
    df = identificar_patrones_acceso(df)
    
    df.to_csv(path_output_dep, index=False)
    print(f"[4b] Archivo depurado y clasificado: {path_output_dep}")