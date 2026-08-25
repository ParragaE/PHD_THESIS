import os
import re
import math
from ast import literal_eval
import numpy as np
import pandas as pd

def seleccionar_formatos(input_ffort, idx):
    formato_principal = input_ffort[idx]
    formatos_restantes = [
        formato for i, formato in enumerate(input_ffort)
        if i != idx
    ]
    return formato_principal, formatos_restantes


def normalizar_formato(formato):
    """
    Convierte el nombre del directorio al nombre esperado por las funciones
    de visualización.

    Ejemplos
    --------
    HDF5_64bs            -> HDF5
    NPZ_64bs             -> NPZ
    TFRecord_1mts_64bs   -> TFRecord
    TFRecord_256kts_64bs -> TFRecord
    """
    formato = formato.replace("_64bs", "")

    #if formato.startswith("TFRecord"):
    #    return "tfrecords"

    return formato


def acces_mode(access):
    """Devuelve una etiqueta legible para el modo de acceso."""
    if access == 0:
        return "Data Loading Mode Shared"
    elif access == 1:
        return "Data Loading Mode Shared(Reload+Shuffle)"

def convert_to_optimal_unit(values):
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    max_value = max(values)
    for i, unit in enumerate(units):
        if max_value < 1024 ** (i + 1):
            return values / (1024 ** i), unit
    return values / (1024 ** len(units)), units[-1]

def convert_bytes(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("Bytes", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
    
# Función para cambiar 'h5' a 'hdf5' en las etiquetas del eje x
def change_label(fformat):
    fformat = fformat.replace('tfrecords', 'tfrecord')  # Cambiar 'tfrecords' a 'tfrecord'
    fformat = fformat.replace('h5', 'hdf5')  # Cambiar 'h5' a 'hdf5'
    return fformat

def extract_values_from_filename2(filename):
    """
    Extrae los valores específicos del nombre del archivo.

    Args:
        filename (str): El nombre del archivo del cual se extraerán los valores.

    Returns:
        list: Una lista con los valores extraídos del nombre del archivo.
    """
    # Dividir el nombre del archivo en partes con base en los guiones bajos
    parts = filename.split('_')

    # Extraer los valores deseados de acuerdo a las posiciones conocidas
    app_name = parts[1]  # Sabemos que es DLIOv1, lo extraemos directamente
    block_size = parts[2]  # "N1p4bs64"
    file_format = parts[4]  # "tfrecords"
    transfer_size = parts[5].replace("multits", "")  # "256KB"
    file_system = "_".join(parts[-3:])  # "lustre_ss1MBsc1_3528468"

    # Retornar los valores en una lista
    return [app_name, block_size, file_format, transfer_size, file_system]


def build_file_name(filename, event_name):
    """
    Build a new file name based on extracted values from the input filename and an event name.

    Args:
        filename (str): The original filename to extract values from.
        event_name (str): The name of the event to include in the new filename.

    Returns:
        str or None: The constructed file name or None if the filename does not have expected values.
    """
    # Extract values from the original filename
    values, macc = extract_values_from_filename(filename)

    # Ensure extracted values are not empty and the last value is a digit
    if values:
        # Convert list of values to a string representation
        values_str = "_".join(values)
        # Construct the new filename
        new_filename = f"Spatial_Temporal_Pattern_{values_str}_{event_name}.jpg"
        return new_filename, macc

    # Return None if the extracted values do not meet criteria
    return None, None

def extract_values_from_filenameor(filename):
    """
    Extract specific values from a filename based on a predefined pattern.

    Args:
        filename (str): The original filename to extract values from.

    Returns:
        list: A list of extracted values or an empty list if extraction fails.
    """
    # Example extraction logic (replace with actual logic)
    parts = filename.split('_')
    extracted_values = [part for part in parts if part.isalnum()]  # Customize this line as needed
    return extracted_values
    
def extract_values_from_filename(filename):
    """
    Extract specific values from a filename based on a predefined pattern.

    Args:
        filename (str): The original filename to extract values from.

    Returns:
        list: A list of extracted values or an empty list if extraction fails.
    """
    parts = filename.split('_')
    
    # Custom extraction logic based on presumed filename structure
    # Example: Extract application type, specific configurations, and format
    relevant_parts = [parts[1], parts[2], parts[4], parts[5], parts[6], parts[7], parts[8], parts[9]]  # Adjust this based on actual relevance
    print(relevant_parts)
    # Optionally, clean up any non-alphanumeric characters if necessary
    cleaned_parts = [part for part in relevant_parts if part.isalnum() or part.replace('.', '').isalnum()]
    macc=parts[7]
    return cleaned_parts, macc
    
def prepare_ost_data(df):
    df['OST'] = df['OST'].dropna().apply(lambda x: literal_eval(x) if isinstance(x, str) else x)
    unique_osts = set(item for sublist in df['OST'].dropna() for item in sublist)
    return len(unique_osts)

def prepare_table_data(df, num_unique_osts, macc, app_name):
    max_request_size = convert_bytes(df['Request_Size(bytes)'].max())
    min_request_size = convert_bytes(df['Request_Size(bytes)'].min())
    avg_request_size = convert_bytes(df['Request_Size(bytes)'].mean())
    total_io = convert_bytes(df['Request_Size(bytes)'].sum())
    
    unique_nodes = df['Nodes'].nunique()
    unique_io_processes = df['Process_IO'].nunique()
    file_systems = ', '.join(df['File_System'].unique())
    total_operations = df.shape[0]
    unique_file_formats = ', '.join(df['File_name'].apply(lambda x: x.split('.')[-1]).unique())
    access_types = ', '.join(df['Operation_Type'].unique()) + " only"
    
    file_format = df['File_name'].apply(lambda x: x.split('.')[-1]).unique()[0]
    
    if app_name=="DLIOv1":
        #file_type = "Shared" if unique_file_formats == "h5" else "Multi"
        file_type = "Shared" if unique_file_formats in ["h5", "hdf5"] else "Multi"
    else:
        if unique_file_formats in ["h5", "hdf5"]:
            if macc=="M0":
                file_type = "Shared" 
            elif macc=="M1":
                file_type = "Shared reload+Shuffle"
    unique_file_formats=change_label(unique_file_formats)
    table_title= f"IO Data Pattern Table. \nFile Format: {unique_file_formats.upper()}. File System: {file_systems}"
    
    io_sizes = [
        f"Max. Request Size:\n {max_request_size}",
        f"Min. Request Size:\n {min_request_size}",
        f"Avg. Request Size:\n {avg_request_size}",
        f"I/O Total:\n {total_io}"
    ]
    system_info = [
        f"Nodes: {unique_nodes}",
        f"I/O Processes: {unique_io_processes}",
        f"OSTs: {num_unique_osts}",
        f"File System:\n {file_systems}"
    ]
    operations_info = [
        f"Total Operations:\n {total_operations} Reads",
        f"File Format:\n {unique_file_formats}",
        f"Access Types:\n {access_types}",
        f"File Type:\n {file_type}"
        #"File Type: Shared"
        #"File Type: Multi"
    ]

    return [io_sizes, system_info, operations_info], table_title

def val_transf(file_name):
    """
    Extrae el valor de transferencia del nombre del archivo si existe.
    
    Parámetros:
    - file_name: Nombre del archivo como string
    
    Retorna:
    - valor_extraido: Valor de transferencia (si existe) como string
    """
    partes = file_name.split('_')
    valor_extraido = None
    
    # Iterar sobre las partes para encontrar la que contiene 'multits'
    for parte in partes:
        if 'multits' in parte:
            # Remover 'multits' para obtener el valor deseado
            valor_extraido = parte.replace('tfrecordsmultits', '')
            print(f"Valor extraído: {valor_extraido}")  # Salida: 256KB
            break
    if valor_extraido is None:
        print("No se encontró la parte que contiene 'multits'.")
    
    return valor_extraido if valor_extraido else "No especificado"

def get_max_values(df1, df2, ylabel, tlabel, zlabel):
    """Calcula los valores máximos de las columnas especificadas en dos DataFrames."""
    try:
        max_ylabel1 = df1[ylabel].max()
        max_tlabel1 = df1[tlabel].max()
        max_zlabel1 = df1[zlabel].max()
        max_ylabel2 = df2[ylabel].max()
        max_tlabel2 = df2[tlabel].max()
        max_zlabel2 = df2[zlabel].max()
        
        max_ylabel = np.max([max_ylabel1, max_ylabel2])
        max_tlabel = np.max([max_tlabel1, max_tlabel2])
        max_zlabel = np.max([max_zlabel1, max_zlabel2])
        return max_ylabel, max_tlabel, max_zlabel
    except KeyError as e:
        print(f"Error: La columna {str(e)} no se encuentra en uno de los DataFrames.")
        return None, None
        
def save_histogram_data(x, y, hist_x, bin_edges_x, bins_y, hist_y, bin_edges_y, save_path2d):
    """
    Guarda la información de los histogramas en un archivo CSV.

    Parámetros:
    y: array-like
        Datos de y.
    hist_x: array-like
        Histogramas para x.
    bin_edges_x: array-like
        Bordes de los bins para x.
    bins_y: array-like
        Bordes de los bins para y.
    hist_y: array-like
        Histogramas para y.
    bin_edges_y: array-like
        Bordes de los bins para y.
    save_path2d: str
        Ruta donde se guardará el archivo.
    filename: str
        Nombre del archivo CSV a guardar.
    """
    
    # Imprimir longitudes de los arrays
    print(f"Longitud de x: {len(x)}")
    print(f"Longitud de y: {len(y)}")
    print(f"Longitud de hist_x: {len(hist_x)}")
    print(f"Longitud de bin_edges_x: {len(bin_edges_x)}")
    print(f"Longitud de bins_y: {len(bins_y)}")
    print(f"Longitud de hist_y: {len(hist_y)}")
    print(f"Longitud de bin_edges_y: {len(bin_edges_y)}")
    # Ajustar longitudes
    if len(hist_x) > len(bin_edges_x) - 1:
        hist_x = hist_x[:len(bin_edges_x) - 1]
    elif len(hist_x) < len(bin_edges_x) - 1:
        hist_x = np.pad(hist_x, (0, len(bin_edges_x) - 1 - len(hist_x)), mode='constant', constant_values=np.nan)

    # Similar para hist_y y bin_edges_y
    if len(hist_y) > len(bin_edges_y) - 1:
        hist_y = hist_y[:len(bin_edges_y) - 1]
    elif len(hist_y) < len(bin_edges_y) - 1:
        hist_y = np.pad(hist_y, (0, len(bin_edges_y) - 1 - len(hist_y)), mode='constant', constant_values=np.nan)

    # Crear un diccionario con los datos
    data = {
        "y": y,
        "hist_x": hist_x,
        "bin_edges_x": bin_edges_x[:-1],  # Ajuste de longitud
        "bins_y": bins_y[:-1],              # Ajuste de longitud
        "hist_y": hist_y,
        "bin_edges_y": bin_edges_y[:-1]     # Ajuste de longitud
    }
    
    # Convertir el diccionario en un DataFrame
    df_hist = pd.DataFrame(data)
    
    # Formatear save_path2d para que sea un nombre de carpeta válido
    #save_path2d = save_path2d.replace('\n', ' ').replace('.', '').replace(':', '').replace(' ', '_')
    #save_path2d = output_path / f"1_{fname_generated.replace('.jpg', '_3D.jpg')}"    
    # Crear la ruta completa
    #full_path = os.path.join(save_path2d, filename)
    full_path = f"1_histograma_data_{save_path2d.replace('.jpg', '.csv')}" 
    # Crear el directorio si no existe
    #os.makedirs(save_path2d, exist_ok=True)
    
    # Guardar el DataFrame en un archivo CSV
    df_hist.to_csv(full_path, index=False)
    print(f"Datos guardados en {full_path}")


