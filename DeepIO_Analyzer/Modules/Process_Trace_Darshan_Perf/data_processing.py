# data_processing.py
import os
import csv
import re
import pandas as pd
from tqdm import tqdm
from Modules.Process_Trace_Darshan_Perf.data_extraction import extract_data, obtener_metadatos, convert_bytes_auto

def extraer_parametros_exe(data):
    """Extrae parámetros desde la línea de ejecución usando regex."""
    params = {'BatchSize': 0, 'Transfer_Size': 0}
    # Busca -bs o -ts seguidos de espacios y números
    bs_match = re.search(r'-bs\s+(\d+)', data)
    ts_match = re.search(r'-ts\s+(\d+)', data)
    
    if bs_match: params['BatchSize'] = int(bs_match.group(1))
    if ts_match: params['Transfer_Size'] = int(ts_match.group(1))
    return params
    
def procesar_archivos_log(path_input, patterns, app_name, fs_scenarios):
    """
    Processes log files and extracts information based on patterns.

    Parameters:
    path_input (str): Directory path of log files.
    patterns (dict): Dictionary with regex patterns to extract data.

    Returns:
    tuple: List of dictionaries with extracted data and conversion unit.
    """
    data_list = []
    files = []
    conversion_unit = None

    if not os.path.isdir(path_input):
        print(f"Directory does not exist: {path_input}")
    else:
        try:
            files = [file for file in os.scandir(path_input) if file.name.endswith(".txt") and file.is_file()]
            print(f"Procesando {len(files)} archivos de log...")
        except Exception as e:
            print(f"Error accessing files in {path_input}: {e}")

    for file in tqdm(files, desc='Procesando logs'):
        if '_Sw_' in file.name or '_Mw_' in file.name:
            continue

        with open(file.path, 'r') as f:
            data = f.read()
            
            extracted = extract_data(patterns, data)

            formato = extracted['File_Format']
            
            accmode = extracted['Access_Mode']
            metadatos = obtener_metadatos(formato)
            
            # Adjust Scale_Type based on Access_Mode
            #scale_type = 'ss' if accmode == '0' else 'ws' if accmode == '1' else 'No_Scaling'
            if app_name == 'DeepGalaxy':
                scale_type = 'ss' if accmode == '0' else 'ws' if accmode == '1' else 'No_Scaling'

                # Extract values to calculate Samples
                d_value = 36 if extracted['Data'] == 's_*' else 1
                num_camera = int(extracted['Num_Camera']) if extracted['Num_Camera'] else 1
                samples = d_value * num_camera * 71
                num_files = 1
            if app_name == 'DLIOv1':
                scale_type = 'ss' if fs_scenarios.startswith('Strong_') else 'ws' if fs_scenarios.startswith('Weak_') else 'No_Scaling'
                # Extract values to calculate Samples
                samples = extracted.get('Num_samples')
                num_files = extracted.get('Num_files')

                
            extracted['Processes IO'] = int(extracted['Processes IO']) if extracted['Processes IO'] else None
            extracted['Nodes'] = extracted['Processes IO'] // 4 if extracted['Processes IO'] else None
            total_bytes = float(extracted['IO_Total(bytes)']) if extracted['IO_Total(bytes)'] else 0
            if total_bytes:
                converted_bytes, conversion_unit = convert_bytes_auto(total_bytes)
                extracted[f'IO_Total({conversion_unit})'] = f'{converted_bytes:.3f}'
            else:
                extracted[f'IO_Total({conversion_unit})'] = 0

            io_time = float(extracted['IO_Time(s)']) if 'IO_Time(s)' in extracted else \
                      float(extracted.get('Unique_IO_Time(s)', 0)) + float(extracted.get('Shared_IO_Time(s)', 0))
            
            extracted['Transfer_Size'] = int(extracted.get('Transfer_Size') or 0)
            extracted['BatchSize'] = int(extracted.get('BatchSize') or 4)
            run_time = float(extracted['Run_Time(s)']) if extracted['Run_Time(s)'] else 0
            extracted['IO_Time Ratio'] = io_time / run_time if run_time else None
            extracted['Scale_Type'] = scale_type
            extracted['Access_Mode'] = accmode or '0'
            extracted['Metadata_teorico'] = metadatos
            extracted['IO_Time(s)'] = io_time
            extracted['Samples'] = samples
            extracted['Total_Files'] = num_files

            data_list.append(extracted)
    
    data_list = [entry for entry in data_list if entry['File_Format'] is not None]
    
    data_list.sort(key=lambda x: (x['File_Format'], x['Access_Mode'], x['Scale_Type'], x['Transfer_Size'], x['Nodes']))

    df = pd.DataFrame(data_list)
    data_list = df.to_dict(orient='records')
    
    for extracted in data_list:
        total_bytes = float(extracted['IO_Total(bytes)']) if extracted['IO_Total(bytes)'] else 0
        nprocs = int(extracted['Processes IO']) if extracted['Processes IO'] else 1
        nodos = int(extracted['Nodes']) if extracted['Nodes'] else 1
        samples = int(extracted['Samples']) if extracted['Samples'] else 1
        nfiles = int(extracted['Total_Files']) if extracted['Total_Files'] else 1

        extracted['Bytes_per_Proc'] = total_bytes / nprocs
        extracted['Bytes_per_Node'] = total_bytes / nodos
        extracted['Processes_per_Node'] = nprocs / nodos
        extracted['Total_Samples'] = samples * nfiles

    return data_list, conversion_unit

def guardar_datos(data_list, path_output, conversion_unit):
    """
    Saves the processed data into a CSV file.

    Parameters:
    data_list (list): List of dictionaries with processed data.
    path_output (str): Output file path.
    conversion_unit (str): Conversion unit for bytes.
    """
    fieldnames = ['Jobid', 'File_Format', 'Access_Mode', 'Scale_Type', 'Nodes', 'Processes IO', 'Processes_per_Node',
                  'Samples', 'Total_Samples', 'Total_Files', 'Transfer_Size', 'BatchSize', 'Metadata_teorico',
                  'IO_Total(bytes)', f'IO_Total({conversion_unit})', 'IO_Time(s)', 'Run_Time(s)',
                  'Bandwidth(MiB/s)', 'IO_Time Ratio', 'Bytes_per_Proc', 'Bytes_per_Node']
    # Verifica la ruta de salida
    print(f"Guardando datos en: {path_output}")
    # Verifica los datos antes de guardar
    #print(f"Datos a guardar: {data_list[:5]}")  # Imprime los primeros 5 registros para verificar

    # Asegúrate de que el directorio de salida existe
    output_dir = os.path.dirname(path_output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(path_output, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for data_dict in data_list:
            clean_dict = {k: v for k, v in data_dict.items() if k in fieldnames}
            writer.writerow(clean_dict)

def procesar_archivos_log1(path_input, patterns, app_name, fs_scenarios, default_bs=0, default_ts=0):
    """Procesa logs y extrae métricas de rendimiento."""
    data_list = []
    
    if not os.path.isdir(path_input):
        print(f"Directorio inexistente: {path_input}")
        return [], None

    files = [f for f in os.scandir(path_input) if f.name.endswith(".txt") and f.is_file()]
    
    for file in tqdm(files, desc='Procesando logs'):
        if '_Sw_' in file.name or '_Mw_' in file.name:
            continue

        with open(file.path, 'r') as f:
            data = f.read()
            extracted = extract_data(patterns, data)
            
            # --- 1. Extracción dinámica ---
            config_exe = extraer_parametros_exe(data)
            
            # --- 2. Filtrado ---
            formato = extracted.get('File_Format')
            if not formato: continue
            
            # --- 3. Cálculos base ---
            accmode = str(extracted.get('Access_Mode') or '0')
            nprocs = int(extracted.get('Processes IO') or 1)
            total_bytes = float(extracted.get('IO_Total(bytes)') or 0)
            io_time = float(extracted.get('IO_Time(s)') or 0)
            if io_time == 0:
                io_time = float(extracted.get('Unique_IO_Time(s)') or 0) + float(extracted.get('Shared_IO_Time(s)') or 0)
            run_time = float(extracted.get('Run_Time(s)') or 0)

            # --- 4. Lógica de App ---
            if app_name == 'DeepGalaxy':
                scale_type = 'ss' if accmode == '0' else 'ws' if accmode == '1' else 'No_Scaling'
                d_value = 36 if extracted.get('Data') == 's_*' else 1
                num_camera = int(extracted.get('Num_Camera') or 1)
                samples = d_value * num_camera * 71
                num_files = 1
            else:
                scale_type = 'ss' if fs_scenarios.startswith('Strong_') else 'ws' if fs_scenarios.startswith('Weak_') else 'No_Scaling'
                samples = int(extracted.get('Num_samples') or 0)
                num_files = int(extracted.get('Num_files') or 1)

            # --- 5. Inyección de métricas y Parámetros Dinámicos ---
            extracted.update({
                'Processes IO': nprocs,
                'Nodes': nprocs // 4 if nprocs else 1,
                'IO_Time(s)': io_time,
                'Run_Time(s)': run_time,
                'Scale_Type': scale_type,
                'Access_Mode': accmode,
                'Metadata_teorico': obtener_metadatos(formato),
                'Samples': samples,
                'Total_Files': num_files,
                'BatchSize': config_exe['BatchSize'] if config_exe['BatchSize'] > 0 else default_bs,
                'Transfer_Size': config_exe['Transfer_Size'] if config_exe['Transfer_Size'] > 0 else default_ts,
                'IO_Time Ratio': (io_time / run_time) if run_time > 0 else 0,
                'Bandwidth(MiB/s)': (total_bytes / (1024**2)) / io_time if io_time > 0 else 0
            })

            if total_bytes:
                converted_bytes, conversion_unit = convert_bytes_auto(total_bytes)
                extracted[f'IO_Total({conversion_unit})'] = f'{converted_bytes:.3f}'
            else:
                extracted[f'IO_Total({conversion_unit})'] = 0

            print(extracted[f'IO_Total({conversion_unit})'])
            
            data_list.append(extracted) 
            
    # --- 5. Cálculos finales y derivaciones ---
    for item in data_list:
        total_b = float(item.get('IO_Total(bytes)') or 0)
        nprocs = item.get('Processes IO', 1)
        nodos = item.get('Nodes', 1)
        item.update({
            'Bytes_per_Proc': total_b / nprocs if nprocs > 0 else 0,
            'Bytes_per_Node': total_b / nodos if nodos > 0 else 0,
            'Processes_per_Node': nprocs / nodos if nodos > 0 else 0,
            'Total_Samples': item.get('Samples', 0) * item.get('Total_Files', 1)
        })

    return data_list, 'MiB'

def guardar_datos1(data_list, path_output, conversion_unit):
    """Guarda con una lista de campos estricta."""
    fieldnames = ['Jobid', 'File_Format', 'Access_Mode', 'Scale_Type', 'Nodes', 'Processes IO', 
                  'Processes_per_Node', 'Samples', 'Total_Samples', 'Total_Files', 'Transfer_Size', 
                  'BatchSize', 'Metadata_teorico', 'IO_Total(bytes)', f'IO_Total({conversion_unit})', 
                  'IO_Time(s)', 'Run_Time(s)', 'Bandwidth(MiB/s)', 'IO_Time Ratio', 
                  'Bytes_per_Proc', 'Bytes_per_Node']
    
    os.makedirs(os.path.dirname(path_output), exist_ok=True)
    with open(path_output, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data_list)