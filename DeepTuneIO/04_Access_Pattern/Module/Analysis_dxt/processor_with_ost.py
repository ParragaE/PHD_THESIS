# processor_with_ost — DeepTuneIO Module 06 v5.6.0
# processor_with_ost
import os
import re
import pandas as pd
from tqdm import tqdm
from Analysis_dxt.fs_data_processor_with_ost import process_lustre_line, process_nfs_line
from Analysis_dxt.extractor import extract_variables_from_file
from collections import Counter
from dataset_filter import DatasetFilter, match_io_file
from Analysis_dxt.ost_mapping import add_ost_mapping_columns, build_ost_workload_summary
from Analysis_dxt.lustre_layout import LustreLayoutParser

def process_darshan_file_interactive(
    file_path, file_format, app_name,
    filter_mode="extension", filter_value=None, regex_ignore_case=False
):
    if app_name not in ['DeepGalaxy', 'DLIOv1']:
        raise ValueError(f"Nombre de aplicación no soportado: {app_name}")

    if filter_value is None:
        filter_value = file_format

    dataset_filter = DatasetFilter(
        mode=filter_mode,
        value=filter_value,
        regex_ignore_case=regex_ignore_case,
    )
    dataset_filter.validate()

    es_operations_all = []
    nodos_dict = {}
    current_file = None
    capturing = False
    current_fs_type = None
    dataset_fs_type = None
    total_write_count = 0
    total_read_count = 0
    stripe_size = None
    stripe_count = None
    f_format = file_format
    lustre_layouts_by_file = {}

    regex_pattern_lustre = re.compile(r'X_POSIX\s+(\d+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*(\[.*\])')
    regex_pattern_nfs = re.compile(r'X_POSIX\s+(\d+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)')
    file_start_pattern = re.compile(r'# DXT, file_id: \d+, file_name: (.+)')
    hostname_pattern = re.compile(r'# DXT, rank: (\d+), hostname: (\S+)')
    fstype_pattern = re.compile(r'# DXT, mnt_pt: (\S+), fs_type: (\S+)')
    operations_count = re.compile(r'# DXT, write_count: (\d+), read_count: (\d+)')
    lustre_pattern = re.compile(r'# DXT, Lustre stripe_size: (\d+), Lustre stripe_count: (\d+)')

    with open(file_path, 'r') as file:
        jobid = None

        for line in file:
            if line.strip() == "":
                capturing = False
                current_file = None
                current_fs_type = None
                continue

            m = re.search(r'# jobid: (\d+)', line)
            if m:
                jobid = m.group(1)

            m = hostname_pattern.search(line)
            if m:
                rank, hostname = m.groups()
                nodos_dict[rank] = hostname

            m = fstype_pattern.search(line)
            if m:
                _, current_fs_type = m.groups()
                if capturing:
                    dataset_fs_type = current_fs_type

            if current_fs_type == 'lustre' and current_file:
                # Lustre layout belongs to each individual dataset file.
                if match_io_file(
                    current_file,
                    f_format,
                    dataset_filter,
                ):
                    layout_parser = lustre_layouts_by_file.get(current_file)
                    if layout_parser is None:
                        layout_parser = LustreLayoutParser()
                        lustre_layouts_by_file[current_file] = layout_parser
                    layout_parser.feed(line)

            m = file_start_pattern.search(line)
            if m:
                full_path = m.group(1).strip()
                current_file = full_path.split('/')[-1]
                capturing = match_io_file(full_path, file_format, dataset_filter)
                if capturing and "." in current_file:
                    f_format = current_file.rsplit(".", 1)[-1]
                continue

            if not capturing:
                continue

            if current_fs_type == 'lustre':
                current_layout = lustre_layouts_by_file.get(current_file)
                if current_layout is not None:
                    layout_summary = current_layout.summary()
                    if layout_summary["stripe_size"] is not None:
                        stripe_size = layout_summary["stripe_size"]
                    if layout_summary["stripe_count"] is not None:
                        stripe_count = layout_summary["stripe_count"]

                operation = process_lustre_line(
                    line, current_file, nodos_dict, current_fs_type, regex_pattern_lustre
                )
            elif current_fs_type == 'nfs':
                operation = process_nfs_line(
                    line, current_file, nodos_dict, current_fs_type, regex_pattern_nfs
                )
                stripe_size = 0
                stripe_count = 0
            else:
                operation = None

            if operation:
                es_operations_all.append(operation)

            m = operations_count.search(line)
            if m:
                write_c, read_c = m.groups()
                total_write_count += int(write_c)
                total_read_count += int(read_c)

    df_es_all = pd.DataFrame(es_operations_all)
    app_variables = extract_variables_from_file(file_path, app_name)
    return (
        df_es_all, jobid, dataset_fs_type, total_write_count, total_read_count,
        stripe_size, stripe_count, f_format, app_variables,
        {
            file_name: parser.components
            for file_name, parser in lustre_layouts_by_file.items()
        }
    )

# Función auxiliar para extraer el valor de OST de la columna [OST]
def extract_ost(ost_value):
    """Extrae el valor de OST de una cadena entre corchetes (por ejemplo, '[ 13]' -> '13')."""
    if isinstance(ost_value, str):  # Asegurarse de que es una cadena
        return ost_value.strip('[]').strip()
    elif isinstance(ost_value, list):  # Si es una lista, devolver el primer elemento
        return str(ost_value[0]) if ost_value else ""
    return str(ost_value)  # Convertir a cadena si no lo es
    
# Calcular el estado inicial de los OSTs basado en el DataFrame
def calculate_initial_osts_status(df, stripe_size):
    """Calcula el estado inicial de los OSTs basado en la columna [OST]."""
    previous_osts_status = {}
    # Extraer todos los OSTs únicos de la columna [OST]
    unique_osts = df['OST'].apply(extract_ost).unique()
    for ost in unique_osts:
        previous_osts_status[ost] = (0, False)  # Inicializar todos los OSTs con (0, False)
    return previous_osts_status

def clean_and_split_osts(ost_str):
    """
    Limpia los valores de OST y los convierte en una lista de strings.
    Elimina todos los símbolos '[]' y los espacios en blanco.
    """
    # Eliminar todos los símbolos '[]' y espacios en blanco
    ost_str_cleaned = ost_str.replace('[', '').replace(']', '').strip()
    # Dividir por espacios y filtrar valores vacíos
    ost_list = [ost.strip() for ost in ost_str_cleaned.split() if ost.strip()]
    # Unir los OSTs con ', ' para formar una cadena
    return ', '.join(ost_list)

##################################### Pruebas clean ost
# Función auxiliar para limpiar y separar los valores de OST
def clean_and_split_osts_v3(ost_str):  # no está limpiando correctamente los símbolos [] y los espacios en blanco de los valores de la columna OST
    """Limpia los valores de OST y los convierte en una lista de strings."""
    return ', '.join(ost.strip() for ost in ost_str.strip("[]").split(',') if ost.strip())
    
def clean_and_split_osts_v2(ost_str):
    """
    Limpia los valores de OST y los convierte en una lista de strings.
    Elimina los símbolos '[]' y los espacios en blanco.
    """
    # Eliminar los símbolos '[]' y dividir por ']'
    ost_list = [ost.strip() for ost in ost_str.strip("[]").split(']') if ost.strip()]
    # Unir los OSTs con ', ' para formar una cadena
    return ', '.join(ost_list)

def clean_and_split_osts_v1(ost_str):
    """Limpia y divide los valores de OST en una lista."""
    if isinstance(ost_str, str):  # Asegurarse de que es una cadena
        return [extract_ost(ost) for ost in ost_str.split(',') if ost.strip()]
    elif isinstance(ost_str, list):  # Si es una lista, devolverla directamente
        return [extract_ost(ost) for ost in ost_str]
    return []  # Devolver una lista vacía si no es una cadena ni una lista

def clean_and_split_osts_o(ost_value):
    """
    Limpia los valores de OST y los convierte en una lista de enteros.

    :param ost_str: String que representa los OSTs.
    :return: Lista de OSTs limpios.
    """
    try:
        if isinstance(ost_value, list):  # Si ya es una lista, devolverla directamente
            return ost_value
        elif isinstance(ost_value, str):  # Si es una cadena, limpiarla y dividirla
            cleaned = ost_value.strip('[]').replace(' ', '')
            return [int(x) for x in cleaned.split(',') if x.isdigit()]
        else:  # Si es otro tipo (por ejemplo, NaN), devolver una lista vacía
            return []
    except Exception as e:
        print(f"Error cleaning OSTs: {e}")
        return []
########################################

def process_row(row, ost_accumulated, stripe_size=1048576):
    """Procesa cada fila del DataFrame, asignando longitud a los OSTs según el orden y manejo del excedente."""
    request_size = row['Request_Size(bytes)']
    ost_sequence = row['OST_Clean'].split(', ')
    remaining_length = request_size

    # Verifica si se trata de un OST o múltiples OST en cada operación
    if len(ost_sequence) == 1:
        ost = ost_sequence[0]
        accumulated, exceeded = ost_accumulated.get(ost, (0, False))
        new_accumulated = accumulated + remaining_length

        # Si hay un OST, el excedente se acumula para la siguiente operación
        ost_accumulated[ost] = (new_accumulated, new_accumulated > stripe_size)
        row[f'OST {ost}'] = min(new_accumulated, stripe_size)
    else:
        for ost_index, ost in enumerate(ost_sequence):
            accumulated, exceeded = ost_accumulated.get(ost, (0, False))

            if ost_index == 0 and exceeded:
                # Si el primer OST tiene excedente, intentar acumularlo
                new_accumulated = accumulated
            else:
                new_accumulated = accumulated + remaining_length

            if new_accumulated > stripe_size:
                # Manejo de excedentes
                row[f'OST {ost}'] = stripe_size
                remaining_length = new_accumulated - stripe_size
                if ost_index > 0:
                    ost_accumulated[ost] = (remaining_length, remaining_length > 0)
            else:
                row[f'OST {ost}'] = new_accumulated
                ost_accumulated[ost] = (0, False)
                remaining_length = 0

            if remaining_length == 0:
                break

        # Reiniciar el estado de los OSTs que no están en la secuencia actual
        for ost in set(ost_accumulated.keys()) - set(ost_sequence):
            if not (ost_sequence and ost_sequence[0] == ost):
                ost_accumulated[ost] = (0, False)

    return row, ost_accumulated

########## pruebas process row
def process_row_basic(row, ost_accumulated, stripe_size=1048576):
    """Procesa cada fila del DataFrame, asignando longitud a los OSTs según el orden y manejo del excedente."""
    request_size = row['Request_Size(bytes)']
    ost_sequence = row['OST_Clean'].split(', ')
    
    for ost in ost_sequence:
        if ost_accumulated[ost] + request_size <= stripe_size:
            ost_accumulated[ost] += request_size
            row[f'OST {ost}'] = ost_accumulated[ost]
        else:
            excedente = (ost_accumulated[ost] + request_size) - stripe_size
            row[f'OST {ost}'] = stripe_size
            ost_accumulated[ost] = 0
            if len(ost_sequence) > 1 and ost_sequence.index(ost) + 1 < len(ost_sequence):
                next_ost = ost_sequence[ost_sequence.index(ost) + 1]
                ost_accumulated[next_ost] += excedente
                row[f'OST {next_ost}'] = excedente
            break
    return row

def process_row_v3(row, ost_accumulated, stripe_size):
    """Procesa cada fila del DataFrame, asignando longitud a los OSTs según el orden y manejo del excedente."""
    request_size = row['Request_Size(bytes)']
    ost_sequence = row['OST_Clean'].split(', ')
    remaining_length = request_size

    # Verifica si se trata de un OST o múltiples OST en cada operación
    if len(ost_sequence) == 1:
        ost = ost_sequence[0]
        # Asegurarse de que ost_accumulated[ost] sea una tupla (accumulated, exceeded)
        if ost in ost_accumulated:
            accumulated, exceeded = ost_accumulated[ost]
        else:
            accumulated, exceeded = 0, False  # Valor predeterminado si el OST no existe

        new_accumulated = accumulated + remaining_length

        # Si hay un OST, el excedente se acumula para la siguiente operación
        ost_accumulated[ost] = (new_accumulated, new_accumulated > stripe_size)
        row[f'OST {ost}'] = min(new_accumulated, stripe_size)
    else:
        for ost_index, ost in enumerate(ost_sequence):
            # Asegurarse de que ost_accumulated[ost] sea una tupla (accumulated, exceeded)
            if ost in ost_accumulated:
                accumulated, exceeded = ost_accumulated[ost]
            else:
                accumulated, exceeded = 0, False  # Valor predeterminado si el OST no existe

            if ost_index == 0 and exceeded:
                # Si el primer OST tiene excedente, intentar acumularlo
                new_accumulated = accumulated
            else:
                new_accumulated = accumulated + remaining_length

            if new_accumulated > stripe_size:
                # Manejo de excedentes
                row[f'OST {ost}'] = stripe_size
                remaining_length = new_accumulated - stripe_size
                if ost_index > 0:
                    ost_accumulated[ost] = (remaining_length, remaining_length > 0)
            else:
                row[f'OST {ost}'] = new_accumulated
                ost_accumulated[ost] = (0, False)
                remaining_length = 0

            if remaining_length == 0:
                break

        # Reiniciar el estado de los OSTs que no están en la secuencia actual
        for ost in set(ost_accumulated.keys()) - set(ost_sequence):
            if not (ost_sequence and ost_sequence[0] == ost):
                ost_accumulated[ost] = (0, False)

    return row, ost_accumulated

def process_row_v2(row, ost_accumulated, stripe_size=1048576):
    """Procesa cada fila del DataFrame, asignando longitud a los OSTs según el orden y manejo del excedente."""
    request_size = row['Request_Size(bytes)']
    ost_sequence = row['OST_Clean'].split(', ')
    #print(len(ost_sequence))
    # Verifica si se trata de un OST o múltiples OST en cada operación
    if len(ost_sequence) == 1:
        #print("si:",len(ost_sequence))
        ost = ost_sequence[0]
        accumulated = ost_accumulated.get(ost, (0, False)) 
        new_accumulated = accumulated + request_size
        # Si hay un OST, el excedente se acumula para la siguiente operación
       # ost_accumulated[ost] = (new_accumulated, new_accumulated > stripe_size)
       # row[f'OST {ost}'] = min(new_accumulated, stripe_size)
    
    for ost in ost_sequence:
        if ost_accumulated[ost] + request_size <= stripe_size:
            ost_accumulated[ost] += request_size
            row[f'OST {ost}'] = ost_accumulated[ost]
        else:
            excedente = (ost_accumulated[ost] + request_size) - stripe_size
            row[f'OST {ost}'] = stripe_size
            ost_accumulated[ost] = 0
            if len(ost_sequence) > 1 and ost_sequence.index(ost) + 1 < len(ost_sequence):
                next_ost = ost_sequence[ost_sequence.index(ost) + 1]
                ost_accumulated[next_ost] += excedente
                row[f'OST {next_ost}'] = excedente
            break
    return row


def process_row_V1(row, previous_osts_status, stripe_size):
    current_osts = clean_and_split_osts(row['OST'])
    remaining_length = row['Request_Size(bytes)']

    # Verifica si se trata de un OST o múltiples OST en cada operación
    if len(current_osts) == 1:
       ost = current_osts[0]
       accumulated, _  = previous_osts_status.get(ost, (0, False)) 
       new_accumulated = accumulated + remaining_length
       # Si hay un OST, el excedente se acumula para la siguiente operación
       previous_osts_status[ost] = (new_accumulated, new_accumulated > stripe_size)
       row[f'OST {ost}'] = min(new_accumulated, stripe_size)
    else:
       for ost_index, ost in enumerate(current_osts):
          accumulated, exceeded = previous_osts_status.get(ost, (0, False))
          if ost_index == 0 and exceeded:
             # Si el primer OST tiene excedente, intentar acumularlo
             new_accumulated = accumulated
          else:
             new_accumulated = accumulated + remaining_length
          if new_accumulated > stripe_size:
             # Manejo Excedentes
             row[f'OST {ost}'] = stripe_size
             remaining_length = new_accumulated - stripe_size
             if ost_index > 0:
                previous_osts_status[ost] = (remaining_length, remaining_length > 0) 
          else:
             row[f'OST {ost}'] = new_accumulated
             previous_osts_status[ost] =  (0, False)
             remaining_length = 0
          if remaining_length == 0:
             break
       for ost in set(previous_osts_status.keys()) - set(current_osts):
          if not (current_osts and current_osts[0] == ost): 
             previous_osts_status[ost] =  (0, False)
    return row, previous_osts_status
        

def process_row_o(row, ost_accumulated, stripe_size):
    """
    Procesa cada fila del DataFrame, asignando longitud a los OSTs según el orden y manejo del excedente.

    :param row: Fila del DataFrame que contiene la información de la operación de E/S.
    :param ost_accumulated: Diccionario que almacena la longitud acumulada de cada OST.
    :param stripe_size: Tamaño de la franja en bytes.
    :return: Fila del DataFrame con la longitud de los OSTs actualizada.
    """
    try:
        request_size = float(row['Request_Size(bytes)'])
        ost_sequence = clean_and_split_osts(row['OST_Clean'])  # Usar la función para limpiar y dividir
        #ost_sequence = [int(ost) for ost in row['OST_Clean'].split(',')]  # Asegúrate de que sea una lista de enteros


        #ost_sequence = float(row['OST_Clean']) # revisar

        for ost in ost_sequence:
            if ost_accumulated[ost] + request_size <= stripe_size:
                ost_accumulated[ost] += request_size
                row[f'OST {ost}'] = ost_accumulated[ost]
            else:
                excedente = (ost_accumulated[ost] + request_size) - stripe_size
                row[f'OST {ost}'] = stripe_size
                ost_accumulated[ost] = 0

                # Distribuir el excedente en los OSTs siguientes
                for next_ost in ost_sequence[ost_sequence.index(ost) + 1:]:
                    if next_ost not in ost_accumulated:
                        ost_accumulated[next_ost] = 0

                    if excedente <= 0:
                        break
                    if ost_accumulated[next_ost] + excedente <= stripe_size:
                        ost_accumulated[next_ost] += excedente
                        row[f'OST {next_ost}'] = ost_accumulated[next_ost]
                        excedente = 0
                    else:
                        row[f'OST {next_ost}'] = stripe_size
                        excedente -= (stripe_size - ost_accumulated[next_ost])
                        ost_accumulated[next_ost] = 0
                break
        return row
    except Exception as e:
        print(f"Error procesando fila: {e}")
        return row

#################
def perform_analysis_and_save(dtfrm, output_path, jobid, fs_type, total_write_count,
                              total_read_count, stripe_size, stripe_count, name_envet,
                              output_summary_path, f_format, app_variables, app_name, fs_scenarios,
                              dir_fs=None, lustre_layouts_by_file=None,
                              analysis_dir=None, ost_workload_dir=None):
    """
    Realiza el análisis de las operaciones de E/S incluyendo la métrica de Nodos.
    Guarda los resultados en tres archivos mapeados jerárquicamente.
    """
    dir_fs = f_format
    lustre_layouts_by_file = dict(lustre_layouts_by_file or {})

    trace_dir = os.path.dirname(output_path)
    access_pattern_root = os.path.dirname(trace_dir)
    analysis_dir = analysis_dir or os.path.join(access_pattern_root, "Analysis")
    ost_workload_dir = ost_workload_dir or os.path.join(access_pattern_root, "OST_Workload")
    os.makedirs(analysis_dir, exist_ok=True)
    os.makedirs(ost_workload_dir, exist_ok=True)

    try:
        if not dtfrm.empty:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Verificar que las columnas necesarias existen (Añadimos 'Nodes' a la validación si es Lustre/NFS)
            required_columns = ['Process_IO', 'Offset(bytes)', 'Request_Size(bytes)', 'Start_Time(s)', 'End_Time(s)', 'Operation_Type']
            if not all(col in dtfrm.columns for col in required_columns):
                raise ValueError(f"El DataFrame no contiene las columnas requeridas: {required_columns}")

            # Convertir columnas numéricas
            dtfrm['Request_Size(bytes)'] = pd.to_numeric(dtfrm['Request_Size(bytes)'], errors='coerce')
            dtfrm['Offset(bytes)'] = pd.to_numeric(dtfrm['Offset(bytes)'], errors='coerce')
            dtfrm['Start_Time(s)'] = pd.to_numeric(dtfrm['Start_Time(s)'], errors='coerce')
            dtfrm['End_Time(s)'] = pd.to_numeric(dtfrm['End_Time(s)'], errors='coerce')

            if dtfrm['Request_Size(bytes)'].isna().any():
                print("Advertencia: La columna 'Request_Size(bytes)' contiene valores no numéricos.")
                dtfrm['Request_Size(bytes)'] = dtfrm['Request_Size(bytes)'].fillna(0)

            # Calcular la latencia
            dtfrm['Latency(s)'] = dtfrm['End_Time(s)'] - dtfrm['Start_Time(s)']

            # 🆕 MODIFICACIÓN 1: Agrupar por 'Process_IO' y 'Nodes' para conservar el mapeo en el Summary Process
            # Si por alguna razón la traza no registró nodos, usamos un fallback preventivo
            if 'Nodes' in dtfrm.columns:
                grouped = dtfrm.groupby(['Process_IO', 'Nodes'])
            else:
                dtfrm['Nodes'] = 'Desconocido'
                grouped = dtfrm.groupby(['Process_IO', 'Nodes'])
                
            process_details_list = []

            # Calcular métricas por proceso
            for (process, node_name), df in grouped:
                # 1. Calcular el siguiente offset esperado en un acceso secuencial
                df['Predicted_Sequence_Offset'] = df['Offset(bytes)'] + df['Request_Size(bytes)']

                # 2. Calcular los Offsets Gap
                df['Offsets Gap'] = df['Offset(bytes)'].diff().shift(-1).fillna(0)

                # 3. Contar la frecuencia de cada salto
                df['Count Offset Gap'] = df['Offsets Gap'].map(df['Offsets Gap'].value_counts())

                # 4. Identificar el salto strided más frecuente (moda)
                saltos = df['Offsets Gap'].tolist()
                salto_strided = Counter(saltos).most_common(1)[0][0]

                # 5. Calcular el Offset Strided Predicho
                df['Predicted_Strided_Offset'] = df['Offset(bytes)'] + salto_strided

                # 6. Logical OST mapping for Lustre.
                #
                # We no longer estimate OST load as Request_Size // Stripe_Size.
                # Instead, each operation is mapped using its Offset, Request_Size,
                # the Lustre stripe size and the OST sequence reported by DXT.
                # The result is a logical file-layout distribution, suitable for
                # workload balance/Sankey analysis.
                if fs_type.lower() == 'lustre' and 'OST' in df.columns:
                    try:
                        stripe_size_int = int(stripe_size)
                    except (TypeError, ValueError):
                        stripe_size_int = 0

                    df = add_ost_mapping_columns(
                        df,
                        stripe_size_int,
                        layouts_by_file=lustre_layouts_by_file,
                    )

                process_details_list.append(df)

            # Combinar detalles en un solo DataFrame (_analysis.csv)
            process_details_df = pd.concat(process_details_list, ignore_index=True)

            trace_name = os.path.basename(output_path)
            analysis_name = trace_name.replace('.csv', '_analysis.csv')
            output_path2 = os.path.join(analysis_dir, analysis_name)
            process_details_df.to_csv(output_path2, index=False)
            print(f"Archivo de análisis detallado guardado: {output_path2}")

            # Derived logical OST workload, kept separate from the primary DXT
            # trace analysis so it cannot be confused with observed physical
            # device traffic.
            if fs_type.lower() == 'lustre':
                ost_workload_df = build_ost_workload_summary(process_details_df, jobid)
                if not ost_workload_df.empty:
                    ost_name = trace_name.replace('.csv', '_ost_workload.csv')
                    ost_workload_path = os.path.join(ost_workload_dir, ost_name)
                    ost_workload_df.to_csv(ost_workload_path, index=False)
                    print(
                        "Resumen de carga lógica por OST guardado en:",
                        ost_workload_path
                    )

            # Calcular métricas globales (por jobid)
            total_request_size = dtfrm['Request_Size(bytes)'].sum()
            total_latency = dtfrm['Latency(s)'].sum()
            total_operations = len(dtfrm)
            total_process = dtfrm['Process_IO'].nunique()
            max_request_size = dtfrm['Request_Size(bytes)'].max()
            min_request_size = dtfrm['Request_Size(bytes)'].min()
            iops = total_operations / total_latency if total_latency > 0 else 0

            mean_throughput = total_request_size / total_latency if total_latency > 0 else 0
            mean_request_size = dtfrm['Request_Size(bytes)'].mean()
            std_request_size = dtfrm['Request_Size(bytes)'].std()
            mean_latency_oper = total_latency / total_operations if total_operations > 0 else 0
            mean_latency_oper2 = dtfrm['Latency(s)'].mean()
            std_latency_oper = dtfrm['Latency(s)'].std()
            mean_latency_proc = total_latency / total_process if total_process > 0 else 0

            operation_counts = dtfrm['Operation_Type'].value_counts()
            read_percentage = operation_counts.get('read', 0) / total_operations * 100 if total_operations > 0 else 0
            write_percentage = operation_counts.get('write', 0) / total_operations * 100 if total_operations > 0 else 0

            fs_typ = dtfrm['File_System'].unique()[0]
            
            # 🆕 MODIFICACIÓN CARDINAL: Calcular el TOTAL de nodos únicos en vez de concatenar sus nombres
            # Usamos .nunique() que cuenta eficientemente los valores únicos (ej: si hay jsc_node_01 y jsc_node_02, devolverá 2)
            total_nodes_global = dtfrm['Nodes'].dropna().nunique() if 'Nodes' in dtfrm.columns else 1
            
            # Crear el resumen global (Añadimos la clave 'Nodes')
            global_summary_data = {
                'Jobid': jobid,
                'Nodes': total_nodes_global, # 🆕 Ahora guarda un número entero (ej: 1, 2, 4, 8)
                'File Format': f_format,
                'File System Type': fs_typ,
                'Process_IO': total_process,
                'Write_count': total_write_count,
                'Write Percentage (%)': write_percentage,
                'Read_count': total_read_count,
                'Read Percentage (%)': read_percentage,
                'Request Size Means(bytes)': mean_request_size,
                'Request Size STD(bytes)': std_request_size,
                'Max Request Size (bytes)': max_request_size,
                'Min Request Size (bytes)': min_request_size,
                'Latency x Operation Means(s)': mean_latency_oper,
                'Latency x Operation Means2(s)': mean_latency_oper2,
                'Latency x Operation STD(s)': std_latency_oper,
                'Latency x Process Means(s)': mean_latency_proc,
                'Throughput Means(bytes/s)': mean_throughput,
                'IOPS': iops
            }

            if fs_typ == 'lustre' and 'OST_Mapping_Valid' in process_details_df.columns:
                global_summary_data['OST_Mapping_Valid_Operations'] = int(
                    process_details_df['OST_Mapping_Valid'].sum()
                )
                global_summary_data['OST_Mapping_Invalid_Operations'] = int(
                    (~process_details_df['OST_Mapping_Valid']).sum()
                )
                global_summary_data['OST_Mapping_Coverage'] = (
                    float(process_details_df['OST_Mapping_Valid'].mean())
                    if len(process_details_df) > 0 else 0.0
                )
                if 'OST_Byte_Conservation' in process_details_df.columns:
                    byte_ok = process_details_df['OST_Byte_Conservation'].fillna(False).astype(bool)
                    global_summary_data['OST_Byte_Conservation_Operations'] = int(byte_ok.sum())
                    global_summary_data['OST_Byte_Conservation_Failures'] = int((~byte_ok).sum())
                    global_summary_data['OST_Byte_Conservation_Rate'] = (
                        float(byte_ok.mean()) if len(byte_ok) > 0 else 0.0
                    )
                global_summary_data['LUSTRE_Layout_Files'] = len(lustre_layouts_by_file)
                global_summary_data['LUSTRE_Layout_Components'] = sum(
                    len(components)
                    for components in lustre_layouts_by_file.values()
                )
                global_summary_data['LUSTRE_Layout_OSTs'] = ";".join(
                    str(ost)
                    for components in lustre_layouts_by_file.values()
                    for comp in components
                    for ost in comp.osts
                )
                if 'OST_Layout_Match' in process_details_df.columns:
                    # Normalize the validation column before counting.
                    #
                    # Depending on pandas dtype inference, values can arrive as
                    # bool/numpy.bool_, numeric 1/0, or strings "True"/"False".
                    # Counting with `(checked == True)` directly can therefore
                    # produce Validated > 0 while Match == Mismatch == 0.
                    raw_match = process_details_df['OST_Layout_Match']

                    def _normalize_layout_match(value):
                        if pd.isna(value):
                            return pd.NA
                        if isinstance(value, bool):
                            return value
                        if isinstance(value, (int, float)):
                            if value == 1:
                                return True
                            if value == 0:
                                return False
                        value_str = str(value).strip().lower()
                        if value_str in {'true', '1', 'yes'}:
                            return True
                        if value_str in {'false', '0', 'no'}:
                            return False
                        return pd.NA

                    normalized_match = raw_match.map(_normalize_layout_match).astype('boolean')
                    known = normalized_match.notna()
                    checked = normalized_match.loc[known]

                    validated_ops = int(known.sum())
                    match_ops = int(checked.sum())
                    mismatch_ops = int(validated_ops - match_ops)

                    # Internal invariant: every validated operation must be
                    # classified as either match or mismatch.
                    if validated_ops != match_ops + mismatch_ops:
                        raise RuntimeError(
                            "OST layout validation invariant violated: "
                            f"validated={validated_ops}, match={match_ops}, "
                            f"mismatch={mismatch_ops}"
                        )

                    global_summary_data['OST_Layout_Validated_Operations'] = validated_ops
                    global_summary_data['OST_Layout_Match_Operations'] = match_ops
                    global_summary_data['OST_Layout_Mismatch_Operations'] = mismatch_ops
                    global_summary_data['OST_Layout_Match_Rate'] = (
                        float(match_ops / validated_ops)
                        if validated_ops > 0 else None
                    )

            if fs_typ == 'lustre':
                global_summary_data['Stripe_size'] = stripe_size
                global_summary_data['Stripe_count'] = stripe_count
            elif fs_typ == 'nfs':
                global_summary_data['Stripe_size'] = 0
                global_summary_data['Stripe_count'] = 0

            if app_variables:
                global_summary_data.update(app_variables)

            global_summary_df = pd.DataFrame([global_summary_data])

            global_summary_path = os.path.join(output_summary_path, f'3_Summary_Global_{app_name}_DXT_{dir_fs}_{fs_scenarios}_{name_envet}.csv')
            if os.path.exists(global_summary_path):
                existing_global_summary_df = pd.read_csv(global_summary_path)
                combined_global_df = pd.concat([existing_global_summary_df, global_summary_df], ignore_index=True)
            else:
                combined_global_df = global_summary_df

            combined_global_df.to_csv(global_summary_path, index=False)
            print("Resumen global guardado con éxito en:", global_summary_path)

            # Calcular métricas por proceso (Summary Process)
            process_summary_data = []

            # 🆕 MODIFICACIÓN 3: Iteramos desempaquetando la tupla modificada (process, node_name)
            for (process, node_name), df in grouped:
                total_request_size_process = df['Request_Size(bytes)'].sum()
                total_latency_process = df['Latency(s)'].sum()
                total_operations_process = len(df)
                max_request_size_process = df['Request_Size(bytes)'].max()
                min_request_size_process = df['Request_Size(bytes)'].min()
                latency_std_process = df['Latency(s)'].std()
                iops_process = total_operations_process / total_latency_process if total_latency_process > 0 else 0

                mean_throughput_process = total_request_size_process / total_latency_process if total_latency_process > 0 else 0
                mean_request_size_process = df['Request_Size(bytes)'].mean()
                std_request_size_process = df['Request_Size(bytes)'].std()
                mean_latency_oper_process = total_latency_process / total_operations_process if total_operations_process > 0 else 0

                operation_counts_process = df['Operation_Type'].value_counts()
                read_percentage_process = operation_counts_process.get('read', 0) / total_operations_process * 100 if total_operations_process > 0 else 0
                write_percentage_process = operation_counts_process.get('write', 0) / total_operations_process * 100 if total_operations_process > 0 else 0

                process_summary_data.append({
                    'Jobid': jobid,
                    'Process_IO': process,
                    #'Nodes': node_name,       # 🆕 Agregado al CSV por Proceso
                    'HostName': node_name, # Añadimos el hostname asociado al proceso/rank
                    'File Format': f_format,
                    'File System Type': fs_typ,
                    'Write_count': total_write_count,
                    'Read_count': total_read_count,
                    'Read Percentage (%)': read_percentage_process,
                    'Write Percentage (%)': write_percentage_process,
                    'Request Size Means(bytes)': mean_request_size_process,
                    'Request Size STD(bytes)': std_request_size_process,
                    'Max Request Size (bytes)': max_request_size_process,
                    'Min Request Size (bytes)': min_request_size_process,
                    'Latency x Operation Means(s)': mean_latency_oper_process,
                    'Latency x Operation Std(s)': latency_std_process,
                    'Throughput Means(bytes/s)': mean_throughput_process,
                    'IOPS': iops_process
                })

            process_summary_df = pd.DataFrame(process_summary_data)

            process_summary_path = os.path.join(output_summary_path, f'3_Summary_Process_{app_name}_DXT_{dir_fs}_{fs_scenarios}_{name_envet}.csv')
            if os.path.exists(process_summary_path):
                existing_process_summary_df = pd.read_csv(process_summary_path)
                combined_process_df = pd.concat([existing_process_summary_df, process_summary_df], ignore_index=True)
            else:
                combined_process_df = process_summary_df

            combined_process_df.to_csv(process_summary_path, index=False)
            print("Resumen por proceso guardado con éxito en:", process_summary_path)

            return global_summary_df
        else:
            print("No se encontraron datos para guardar.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error durante el análisis o el guardado de archivos: {e}")
        return pd.DataFrame()



def perform_analysis_and_save_vbuena(dtfrm, output_path, jobid, fs_type, total_write_count,
                              total_read_count, stripe_size, stripe_count, name_envet,
                              output_summary_path, f_format, app_variables, app_name, fs_scenarios, dir_fs=None):
    """
    Realiza el análisis de las operaciones de E/S y guarda los resultados en tres archivos:
    1. Un resumen global por jobid.
    2. Un resumen por proceso.
    3. Un archivo detallado con las operaciones por proceso.

    Args:
        dtfrm (DataFrame): DataFrame con las operaciones de E/S.
        output_path (str): Ruta para guardar el archivo de análisis.
        jobid (str): ID del trabajo.
        fs_type (str): Tipo de sistema de archivos.
        total_write_count (int): Total de escrituras.
        total_read_count (int): Total de lecturas.
        stripe_size (int): Tamaño de stripe.
        stripe_count (int): Número de stripe.
        name_envet (str): Nombre del evento.
        output_summary_path (str): Ruta para guardar los resúmenes.
        f_format (str): Formato del archivo.
        app_variables (dict): Variables específicas de la aplicación.
        app_name (str): Nombre de la aplicación.
        fs_scenarios (str): Escenario del sistema de archivos.
        dir_fs (str, optional): Directorio del sistema de archivos.

    Returns:
        DataFrame: DataFrame con los resultados del análisis global.
    """
    #if f_format == "h5":
    #    f_format = "hdf5"
    dir_fs = f_format

    try:
        if not dtfrm.empty:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Verificar que las columnas necesarias existen
            required_columns = ['Process_IO', 'Offset(bytes)', 'Request_Size(bytes)', 'Start_Time(s)', 'End_Time(s)', 'Operation_Type']
            if not all(col in dtfrm.columns for col in required_columns):
                raise ValueError(f"El DataFrame no contiene las columnas requeridas: {required_columns}")

            # Convertir columnas numéricas
            dtfrm['Request_Size(bytes)'] = pd.to_numeric(dtfrm['Request_Size(bytes)'], errors='coerce')
            dtfrm['Offset(bytes)'] = pd.to_numeric(dtfrm['Offset(bytes)'], errors='coerce')
            dtfrm['Start_Time(s)'] = pd.to_numeric(dtfrm['Start_Time(s)'], errors='coerce')
            dtfrm['End_Time(s)'] = pd.to_numeric(dtfrm['End_Time(s)'], errors='coerce')

            # Verificar valores faltantes
            if dtfrm['Request_Size(bytes)'].isna().any():
                print("Advertencia: La columna 'Request_Size(bytes)' contiene valores no numéricos.")
                dtfrm['Request_Size(bytes)'] = dtfrm['Request_Size(bytes)'].fillna(0)

            # Calcular la latencia
            dtfrm['Latency(s)'] = dtfrm['End_Time(s)'] - dtfrm['Start_Time(s)']

            # Agrupar los datos por proceso
            grouped = dtfrm.groupby('Process_IO')
            process_details_list = []

            # Calcular métricas por proceso
            for process, df in grouped:
                # Calcular la latencia
               # df['Latency(s)'] = df['End_Time(s)'] - df['Start_Time(s)']

                # 1. Calcular el siguiente offset esperado en un acceso secuencial
                df['Predicted_Sequence_Offset'] = df['Offset(bytes)'] + df['Request_Size(bytes)']

                # 2. Calcular los Offsets Gap (diferencias entre offsets consecutivos)
                df['Offsets Gap'] = df['Offset(bytes)'].diff().shift(-1).fillna(0)

                # 3. Contar la frecuencia de cada salto (Count Offset Gap)
                df['Count Offset Gap'] = df['Offsets Gap'].map(df['Offsets Gap'].value_counts())

                # 4. Identificar el salto strided más frecuente (moda)
                saltos = df['Offsets Gap'].tolist()
                salto_strided = Counter(saltos).most_common(1)[0][0]  # Obtiene el salto más frecuente

                # 5. Calcular el Offset Strided Predicho
                df['Predicted_Strided_Offset'] = df['Offset(bytes)'] + salto_strided

                # 6. Procesar OSTs si el sistema de archivos es LUSTRE
                if fs_type.lower() == 'lustre' and 'OST' in df.columns:
                    # Limpiar y dividir los OSTs
                    #df['OST_Clean'] = df['OST'].apply(clean_and_split_osts)
                    #unique_osts_cleaned = list(set(ost for sublist in df['OST_Clean'] for ost in sublist))

                    # Inicializar acumuladores para cada OST
                    #ost_accumulated = {ost: 0 for ost in unique_osts_cleaned}

                    # Procesar cada fila para acumular métricas por OST
                    #df = df.apply(lambda row: process_row(row, ost_accumulated, stripe_size), axis=1)

                    # Calcula el estado inicial de los OSTS
                    #previus_osts_status = calculate_initial_osts_status(df,stripe_size)
                    # Añade columnas para cada OST dinámicamente
                    #unique_osts = df['OST'].apply(extract_ost).unique()
                    #for ost in unique_osts:
                    #    df[f'OST {ost}'] = 0  # Inicializar las columnas de OST con 0
                    #for index, row in df.iterrows():
                    #    df.loc[index], previus_osts_status = process_row(row, previus_osts_status, stripe_size)
                    # Limpiar y dividir los OSTs
                    df['OST_Clean'] = df['OST'].apply(clean_and_split_osts)
                    unique_osts_cleaned = list(set(ost for sublist in df['OST_Clean'] for ost in sublist.split(', ')))                   # Inicializar acumuladores para cada OST
                    # Crear columnas de OST en el DataFrame e inicializarlas con 0
                    for ost in unique_osts_cleaned:
                        df[f'OST {ost}'] = 0
                    # Procesar cada fila para asignar valores a las columnas de OST
		    #remaining_length = row['Request_Size(bytes)']
                    stripe_size = int(stripe_size)  # Ensure stripe_size is an integer                    
                    for index, row in df.iterrows():
                        remaining_length = int(row['Request_Size(bytes)'])
                        ost_sequence = row['OST_Clean'].split(', ')
                        num_osts = len(ost_sequence)
                        # Calcular el número máximo de OSTs a usar
                        max_osts_to_use = min(num_osts, remaining_length // stripe_size)
                        # Si max_osts_to_use es 0 (por ejemplo, si remaining_length < stripe_size),
                        # se usa al menos 1 OST.
                        if max_osts_to_use == 0:
                            max_osts_to_use = 1
    
                        # Distribuir el remaining_length entre los OSTs
                        size_per_ost = remaining_length / max_osts_to_use
                        for i in range(max_osts_to_use):
                            ost = ost_sequence[i]
                            df.at[index, f'OST {ost}'] = size_per_ost

                        # Distribuir el remaining_length entre los OSTs
                        #if max_osts_to_use > 0:
                        #    size_per_ost = remaining_length / max_osts_to_use
                        #    for i in range(max_osts_to_use):
                        #        ost = ost_sequence[i]
                        #        df.at[index, f'OST {ost}'] = size_per_ost
                        #elif num_osts == 1:
                        #   size_per_ost = remaining_length
                        #   for i in range(num_osts):
                        #        ost = ost_sequence[i] 
                        #        df.at[index, f'OST {ost}'] = size_per_ost
                        #print('num_osts',num_osts, 'remaining_length',remaining_length // stripe_size)
                        #print()
                         
                        #print('max_osts_to_use', max_osts_to_use)   
                        #for ost in ost_sequence:
                            #df.at[index, f'OST {ost}'] = row['Request_Size(bytes)'] 
                        #    df.at[index, f'OST {ost}'] = remaining_length / max_osts_to_use
                    #ost_accumulated = {ost: (0, False) for ost in unique_osts_cleaned}  # Inicializar con tuplas (0, False)
                    # Procesar cada fila para acumular métricas por OST
                    #df = df.apply(lambda row: process_row(row, ost_accumulated, stripe_size), axis=1)

                # Guardar los detalles por proceso
                process_details_list.append(df)

            # Combinar todos los detalles de los procesos en un solo DataFrame
            process_details_df = pd.concat(process_details_list, ignore_index=True)

            # Guardar el archivo de análisis detallado por proceso
            output_path2 = os.path.join(output_path.replace('.csv', '_analysis.csv'))
            if not os.path.exists(output_path2):
                process_details_df.to_csv(output_path2, index=False)
                print(f"Archivo de análisis detallado guardado: {output_path2}")

            # Calcular métricas globales (por jobid)
            total_request_size = dtfrm['Request_Size(bytes)'].sum()
            total_latency = dtfrm['Latency(s)'].sum()
            total_operations = len(dtfrm)
            total_process = dtfrm['Process_IO'].nunique()  # Cuenta valores únicos
            max_request_size = dtfrm['Request_Size(bytes)'].max()
            min_request_size = dtfrm['Request_Size(bytes)'].min()
            std_latency_oper = dtfrm['Latency(s)'].std()
            iops = total_operations / total_latency if total_latency > 0 else 0

            mean_throughput = total_request_size / total_latency if total_latency > 0 else 0
            mean_request_size = dtfrm['Request_Size(bytes)'].mean()
            std_request_size = dtfrm['Request_Size(bytes)'].std()
            mean_latency_oper = total_latency / total_operations if total_operations > 0 else 0
            mean_latency_oper2 = dtfrm['Latency(s)'].mean()
            std_latency_oper = dtfrm['Latency(s)'].std()
            mean_latency_proc = total_latency / total_process if total_process > 0 else 0
            #utilization_factor = total_latency / total_operations if total_operations > 0 else 0 # revisar este calculo

            operation_counts = dtfrm['Operation_Type'].value_counts()
            read_percentage = operation_counts.get('read', 0) / total_operations * 100 if total_operations > 0 else 0
            write_percentage = operation_counts.get('write', 0) / total_operations * 100 if total_operations > 0 else 0

            fs_typ = dtfrm['File_System'].unique()[0]
            #ttl_process = df['Process_IO'].nunique()
            # Crear el resumen global
            global_summary_data = {
                'Jobid': jobid,
                'File Format': f_format,
                'File System Type': fs_typ,
                'Process_IO':total_process,
                'Write_count': total_write_count,
                'Write Percentage (%)': write_percentage,
                'Read_count': total_read_count,
                'Read Percentage (%)': read_percentage,
                'Request Size Means(bytes)': mean_request_size,
                'Request Size STD(bytes)': std_request_size,
                'Max Request Size (bytes)': max_request_size,
                'Min Request Size (bytes)': min_request_size,
                'Latency x Operation Means(s)': mean_latency_oper,
                'Latency x Operation Means2(s)': mean_latency_oper2,
                'Latency x Operation STD(s)': std_latency_oper,
                'Latency x Process Means(s)': mean_latency_proc,
                'Throughput Means(bytes/s)': mean_throughput,
                'IOPS': iops
                #'Utilization Factor': utilization_factor,
               }

            if fs_typ == 'lustre':
                global_summary_data['Stripe_size'] = stripe_size
                global_summary_data['Stripe_count'] = stripe_count
            elif fs_typ == 'nfs':
                global_summary_data['Stripe_size'] = 0
                global_summary_data['Stripe_count'] = 0

            if app_variables:
                global_summary_data.update(app_variables)

            global_summary_df = pd.DataFrame([global_summary_data])

            # Guardar el resumen global
            global_summary_path = os.path.join(output_summary_path, f'3_Summary_Global_{app_name}_DXT_{dir_fs}_{fs_scenarios}_{name_envet}.csv')
            #global_summary_path = os.path.join(output_summary_path, f'3_Summary_Global_{app_name}_DXT_{dir_fs}_{fs_scenarios}_{name_envet}.csv')
            if os.path.exists(global_summary_path):
                existing_global_summary_df = pd.read_csv(global_summary_path)
                combined_global_df = pd.concat([existing_global_summary_df, global_summary_df], ignore_index=True)
            else:
                combined_global_df = global_summary_df

            combined_global_df.to_csv(global_summary_path, index=False)
            print("Resumen global guardado con éxito en:", global_summary_path)

            # Calcular métricas por proceso
            process_summary_data = []

            for process, df in grouped:
                total_request_size_process = df['Request_Size(bytes)'].sum()
                total_latency_process = df['Latency(s)'].sum()
                total_operations_process = len(df)
                max_request_size_process = df['Request_Size(bytes)'].max()
                min_request_size_process = df['Request_Size(bytes)'].min()
                latency_std_process = df['Latency(s)'].std()
                iops_process = total_operations_process / total_latency_process if total_latency_process > 0 else 0

                mean_throughput_process = total_request_size_process / total_latency_process if total_latency_process > 0 else 0
                mean_request_size_process = df['Request_Size(bytes)'].mean()
                std_request_size_process = df['Request_Size(bytes)'].std()
                mean_latency_oper_process = total_latency_process / total_operations_process if total_operations_process > 0 else 0
                #utilization_factor_process = total_latency_process / total_operations_process if total_operations_process > 0 else 0

                operation_counts_process = df['Operation_Type'].value_counts()
                read_percentage_process = operation_counts_process.get('read', 0) / total_operations_process * 100 if total_operations_process > 0 else 0
                write_percentage_process = operation_counts_process.get('write', 0) / total_operations_process * 100 if total_operations_process > 0 else 0

                process_summary_data.append({
                    'Jobid': jobid,
                    'Process_IO': process,
                    'File Format': f_format,
                    'File System Type': fs_typ,
                    'Write_count': total_write_count,
                    'Read_count': total_read_count,
                    'Read Percentage (%)': read_percentage_process,
                    'Write Percentage (%)': write_percentage_process,
                    'Request Size Means(bytes)': mean_request_size_process,
                    'Request Size STD(bytes)': std_request_size_process,
                    'Max Request Size (bytes)': max_request_size_process,
                    'Min Request Size (bytes)': min_request_size_process,
                    'Latency x Operation Means(s)': mean_latency_oper_process,
                    'Latency x Operation Std(s)': latency_std_process,
                    'Throughput Means(bytes/s)': mean_throughput_process,
                    'IOPS': iops_process
                 #   'Utilization Factor': utilization_factor_process,
                 })

            process_summary_df = pd.DataFrame(process_summary_data)

            # Guardar el resumen por proceso
            process_summary_path = os.path.join(output_summary_path, f'3_Summary_Process_{app_name}_DXT_{dir_fs}_{fs_scenarios}_{name_envet}.csv')
            if os.path.exists(process_summary_path):
                existing_process_summary_df = pd.read_csv(process_summary_path)
                combined_process_df = pd.concat([existing_process_summary_df, process_summary_df], ignore_index=True)
            else:
                combined_process_df = process_summary_df

            combined_process_df.to_csv(process_summary_path, index=False)
            print("Resumen por proceso guardado con éxito en:", process_summary_path)

            return global_summary_df
        else:
            print("No se encontraron datos para guardar.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error durante el análisis o el guardado de archivos: {e}")
        return pd.DataFrame()



###########################
def process_all_files_in_directory(directory_path, output_directory, file_format, name_envet, 
                                   output_summary_path, app_name, dir_fs=None, fs_scenarios=None, dir_bench=None,
                                   filter_mode="extension", filter_value=None, regex_ignore_case=False):
    """
    Procesa todos los archivos en un directorio con salida visual limpia en Jupyter.
    """
    analysis_frames = []
    files = []
    jobid = None
    fs_type = None
    df = None
    
    os.makedirs(output_directory, exist_ok=True)

    if app_name == "DeepGalaxy":
        dir_fs
    if app_name == "DLIOv1":
        dir_fs = dir_bench
 
    if os.path.isdir(directory_path):
        try:
            files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
        except Exception as e:
            print(f"Failed to list files in the directory: {e}")
    else:
        print(f"Directory does not exist: {directory_path}")
    
    if files:
        # 🆕 Inicializamos tqdm usando un bloque 'with' controlado
        with tqdm(files, desc="Análisis DXT", unit="archivo") as pbar:
            for filename in pbar:
                file_path = os.path.join(directory_path, filename)
                
                # 🆕 En lugar de hacer print(), actualizamos el texto a la derecha de la barra de progreso
                # Recortamos el nombre del archivo si es muy largo para que no desfigure la barra
                pbar.set_postfix_str(f"Fichero actual: {filename[:40]}...")
                
                df, jobid, fs_type, total_write_count, total_read_count, stripe_size, stripe_count, f_format, app_variables, lustre_layouts_by_file = process_darshan_file_interactive(file_path, file_format, app_name, filter_mode, filter_value, regex_ignore_case)
                
                output_path = os.path.join(output_directory, filename.replace('.txt', '.csv'))
                if not os.path.exists(output_path):
                    df.to_csv(output_path, index=False)
                    # ❌ QUITAMOS/COMENTAMOS este print para no romper la barra
                    # print(f"Archivo procesado y guardado: {output_path}")
        
                analysis_df = perform_analysis_and_save(
                    df, output_path, jobid, fs_type, total_write_count, total_read_count,
                    stripe_size, stripe_count, name_envet, output_summary_path,
                    f_format, app_variables, app_name, fs_scenarios, dir_fs,
                    lustre_layouts_by_file=lustre_layouts_by_file
                )

                if analysis_df is not None:
                    analysis_frames.append(analysis_df)
                    
        # 🆕 Al salir del bucle, dejamos un único mensaje de confirmación limpio
        print(f"✔ ¡Procesamiento completado! Se analizaron con éxito {len(files)} archivos.")
    else:
        print("No files to process.")   
            
    if analysis_frames:
        combined_analysis_path = os.path.join(os.path.dirname(output_path), f'3_Resumen_analysis_{app_name}_{dir_fs}_{fs_scenarios}_DXT_{name_envet}.csv')

        if os.path.exists(combined_analysis_path):
            combined_analysis_df = pd.read_csv(combined_analysis_path)
            combined_df = pd.concat([combined_analysis_df] + analysis_frames, ignore_index=True)
        else:
            combined_df = pd.concat(analysis_frames, ignore_index=True)

        combined_df.to_csv(combined_analysis_path, index=False)
        # 🆕 Cambiado a un print estático final fuera del bucle masivo
        print("📊 Reportes consolidados y guardados en la raíz de resultados.")
        
    return jobid, fs_type, df



def process_all_files_in_directory_vbuena(directory_path, output_directory, file_format, name_envet, 
                                   output_summary_path, app_name, dir_fs=None, fs_scenarios=None, dir_bench=None):
 

    """
    Procesa todos los archivos en un directorio y realiza el análisis de E/S.

    Args:
        directory_path (str): Ruta del directorio con los archivos de Darshan.
        output_directory (str): Ruta del directorio para guardar los resultados.
        file_format (str): Formato del archivo a buscar.
        name_envet (str): Nombre del evento.
        output_summary_path (str): Ruta para guardar el resumen.
        dir_fs (str): Directorio del sistema de archivos.
        fs_scenarios (str): Escenarios del sistema de archivos.
        app_name (str): Nombre de la aplicación (DeepGalaxy o DLIOv1).

    Returns:
        tuple: jobid, tipo de sistema de archivos y DataFrame con los datos procesados.
    """
    analysis_frames = []
    files = []
    jobid = None
    fs_type = None
    df = None
    
    os.makedirs(output_directory, exist_ok=True)

    if app_name == "DeepGalaxy":
        dir_fs
    if app_name == "DLIOv1":
        dir_fs = dir_bench
 
    if os.path.isdir(directory_path):
        try:
            files = [f for f in os.listdir(directory_path) if f.endswith('.txt')]
        except Exception as e:
            print(f"Failed to list files in the directory: {e}")
    else:
        print(f"Directory does not exist: {directory_path}")
    
    if files:
        for filename in tqdm(files, desc="Procesando archivos", unit="archivo"):
            file_path = os.path.join(directory_path, filename)
            print(f"Procesando archivo: {file_path}")
            df, jobid, fs_type, total_write_count, total_read_count, stripe_size, stripe_count, f_format, app_variables, lustre_layouts_by_file = process_darshan_file_interactive(
                file_path, file_format, app_name
            )
            # Guarda fichero procesado de DXT Darshan
            output_path = os.path.join(output_directory, filename.replace('.txt', '.csv'))
            if not os.path.exists(output_path):
                df.to_csv(output_path, index=False)
                print(f"Archivo procesado y guardado: {output_path}")
    
            analysis_df = perform_analysis_and_save(
                df, output_path, jobid, fs_type, total_write_count, total_read_count,
                stripe_size, stripe_count, name_envet, output_summary_path,
                f_format, app_variables, app_name, fs_scenarios, dir_fs,
                lustre_layouts_by_file=lustre_layouts_by_file
            )

            if analysis_df is not None:
                analysis_frames.append(analysis_df)
    else:
        print("No files to process.")   
            
    if analysis_frames:
        #combined_analysis_path = os.path.join(os.path.dirname(output_path), f'3_Resumen_analysis_{app_name}_{f_format}_{dir_fs}_{fs_scenarios}_DXT_{name_envet}.csv')
        combined_analysis_path = os.path.join(os.path.dirname(output_path), f'3_Resumen_analysis_{app_name}_{dir_fs}_{fs_scenarios}_DXT_{name_envet}.csv')

        if os.path.exists(combined_analysis_path):
            combined_analysis_df = pd.read_csv(combined_analysis_path)
            combined_df = pd.concat([combined_analysis_df] + analysis_frames, ignore_index=True)
        else:
            combined_df = pd.concat(analysis_frames, ignore_index=True)

        combined_df.to_csv(combined_analysis_path, index=False)

        print("Datos y análisis guardados con éxito en:", combined_analysis_path)
    return jobid, fs_type, df
