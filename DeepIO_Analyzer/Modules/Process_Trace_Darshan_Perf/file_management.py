# file_management.py
from pathlib import Path
import os

def crear_rutas_y_nombres(output_dir, app_name, dir_fs_scenary, fs_scenarios, base_file_name, dir_perf, name_event):
    base_path = Path(output_dir)
    base_path.mkdir(parents=True, exist_ok=True)
    
    # Sufijos estandarizados
    perf_suffix = f"{app_name}_{dir_perf}_{dir_fs_scenary}_{fs_scenarios}_{name_event}"
    
    # 4. Búsqueda del Parser
    patron_busqueda = f"4_Summary_Global_Avg_{app_name}_Parser_*{name_event}.csv"
    archivos_parser = list(base_path.glob(patron_busqueda))
    archivo_parser_real = archivos_parser[0] if archivos_parser else base_path / "4_Parser_NOT_FOUND.csv"
    
    # 5. Definición de rutas
    paths = {
        'perf': base_path / f"5a_{base_file_name}_{perf_suffix}.csv",
        'parser': archivo_parser_real,
        'iops': base_path / f"5b_{base_file_name}_{perf_suffix}_iops.csv",
        'final': base_path / f"5_Analisis_IO_{app_name}_Parser_Perf_Seff_{fs_scenarios}_{dir_fs_scenary}_{name_event}.csv",
        'seff': base_path / f"2_{base_file_name}_{app_name}_{fs_scenarios}_{dir_fs_scenary}_job_efficiency_{name_event}.csv"
    }
    
    return str(paths['perf']), str(paths['parser']), str(paths['iops']), str(paths['final']), str(paths['seff'])


def crear_rutas_y_nombres2(output_dir, app_name, dir_fs, fs_scenarios, base_file_name, dir_perf, name_event):
    # 1. Validación
    params = [output_dir, app_name, dir_fs, fs_scenarios, base_file_name, dir_perf, name_event]
    if not all(params):
        raise ValueError("Todos los parámetros para la creación de rutas deben ser no vacíos.")

    # 2. Definir ruta base sin subcarpetas extra
    base_path = Path(output_dir)
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Error al crear el directorio {base_path}: {e}")
    
    # 3. Sufijo estándar para los archivos que SÍ creamos aquí (Perf e IOPS)
    #perf_suffix = f"{app_name}_{dir_perf}_{dir_fs}_{fs_scenarios}_{name_event}"
    perf_suffix = f"{app_name}_{dir_perf}_{dir_fs_scenary}_{fs_scenarios}_{name_event}"
    suffix_base = f"{app_name}_Seff_Parser_{dir_perf}_{dir_fs_scenary}_{fs_scenarios}_{name_event}"
   
    # 4. BÚSQUEDA INTELIGENTE DEL ARCHIVO DEL PARSER
    # Busca cualquier archivo que empiece por '4_Summary_Global_Avg_DeepGalaxy_Parser_' 
    # y termine en '_Tesis_26.csv' en la carpeta results, ignorando lo que haya en medio.
    patron_seff = f"2_{base_file_name}_{app_name}_{fs_scenarios}_{dir_fs_scenary}_job_efficiency_{name_event}.csv"
    
    patron_busqueda = f"4_Summary_Global_Avg_{app_name}_Parser_*{name_event}.csv"
    archivos_parser = list(base_path.glob(patron_busqueda))
    
    if archivos_parser:
        # Si lo encuentra, usamos la ruta real exacta que tiene el disco
        archivo_parser_real = archivos_parser[0]
    else:
        # Fallback en caso de que realmente no exista
        archivo_parser_real = base_path / f"4_Summary_Global_Avg_{app_name}_Parser_NOT_FOUND.csv"

    # 5. Consolidación de rutas
    paths = {
        'perf': base_path / f"5a_{base_file_name}_{perf_suffix}.csv",
        'parser': archivo_parser_real,
        'iops': base_path / f"5b_{base_file_name}_{perf_suffix}_iops.csv",
        'parser_perf': base_path / f"5_{base_file_name}_Seff_Parser_Seff_{suffix_base}.csv",
        'seff': base_path / patron_seff
    }
    
    return str(paths['perf']), str(paths['parser']), str(paths['iops']), str(paths['parser_perf']), str(paths['seff'])

def construir_mapa_filesystem(data):
    fs_map = {}
    for line in data:
        if line.startswith("# mount entry:"):
            parts = line.split('\t')
            if len(parts) >= 3:
                fs_map[parts[1].strip()] = parts[2].strip().lower()
    return fs_map