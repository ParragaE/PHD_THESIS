# data_extraction
import re

def extract_data(patterns, text):
    """
    Extrae datos del texto utilizando patrones de expresión regular (Original restaurado).
    """
    extracted_data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            extracted_data[key] = match.group(1)
        else:
            extracted_data[key] = None
    return extracted_data

def obtener_metadatos(formato):
    """Devuelve el tamaño de metadatos en bytes según el formato."""
    if not formato: return 0
    mapping = {'hdf5': 16, 'npz': 5, 'tfrecord': 0}
    return mapping.get(formato.lower(), 0)

def normalizar_unidades(df):
    # 1. Detectar la unidad dominante o la mayor encontrada
    unidades_prioridad = {'Bytes': 0, 'KiB': 1, 'MiB': 2, 'GiB': 3, 'TiB': 4}
    max_unidad = df['IO_Unit_Detected'].map(unidades_prioridad).max()
    unidad_final = [k for k, v in unidades_prioridad.items() if v == max_unidad][0]
    
    # 2. Convertir toda la columna a esa unidad
    divisor = 1024 ** max_unidad
    df[f'IO_Total({unidad_final})'] = df['IO_Total(bytes)'] / divisor
    
    # 3. Eliminar columnas temporales
    return df.drop(columns=['IO_Total(bytes)', 'IO_Unit_Detected'])

def obtener_patterns_perf(app_name):
    if app_name == "DeepGalaxy":
        return {
            'Jobid': r'jobid:\s+(\d+)',
            'File_Format': r'(?:output_bw_\d+(?:_h5repack)?|DeepGalaxy_bw\d+_[a-zA-Z0-9_]+|DG_bw\d+_[a-zA-Z0-9_]+)\.(hdf5)',
            'Access_Mode': r'-m\s+(\d+)',
            'Processes IO': r'nprocs:\s+(\d+)',
            'Data': r'-d\s+(\S+)',
            'Num_Camera': r'--num-camera\s+(\d+)',
            'Total_Files': r'-nf\s+(\S+)',
            'Transfer_Size': r'-ts\s+(\S+)',
            'BatchSize': r'-bs\s+(\d+)',
            'Run_Time(s)': r'run time:\s+(\S+)',
            'IO_Total(bytes)': r'total_bytes:\s+(\d+)',
            'Unique_IO_Time(s)': r'unique files: slowest_rank_io_time:\s+(\d+\.\d+)',
            'Shared_IO_Time(s)': r'shared files: time_by_slowest:\s+(\d+\.\d+)',
            'IO_Time(s)': r'agg_time_by_slowest:\s+(\d+\.\d+)',
            'Bandwidth(MiB/s)': r'agg_perf_by_slowest:\s+(\d+\.\d+)',
        }

    elif app_name == "DLIOv1":
        return {
            'Jobid': r'jobid:\s+(\d+)',
            'File_Format': r'-f\s+(\w+)',
            'Access_Mode': r'-fa\s+(\w+)',
            'Processes IO': r'nprocs:\s+(\d+)',
            'Num_files': r'-nf\s+(\d+)',
            'Num_samples': r'-sf\s+(\d+)',
            'Record_length': r'-rl\s+(\d+)',
            'Total_Files': r'-nf\s+(\d+)',
            'Transfer_Size': r'-ts\s+(\S+)',
            'BatchSize': r'-bs\s+(\d+)',
            'Run_Time(s)': r'run time:\s+(\S+)',
            'IO_Total(bytes)': r'total_bytes:\s+(\d+)',
            'Unique_IO_Time(s)': r'unique files: slowest_rank_io_time:\s+(\d+\.\d+)',
            'Shared_IO_Time(s)': r'shared files: time_by_slowest:\s+(\d+\.\d+)',
            'IO_Time(s)': r'agg_time_by_slowest:\s+(\d+\.\d+)',
            'Bandwidth(MiB/s)': r'agg_perf_by_slowest:\s+(\d+\.\d+)',
        }

    else:
        raise ValueError(f"Aplicación no soportada: {app_name}")


def convert_bytes_auto(bytes_value):
    """Conversión segura de bytes."""
    try:
        bytes_value = float(bytes_value)
    except (ValueError, TypeError):
        return 0.0, "B"

    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
        if bytes_value < 1024.0:
            return round(bytes_value, 2), unit
        bytes_value /= 1024.0
    return round(bytes_value, 2), 'PiB'