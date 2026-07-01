# StatisticsParser.py
"""
Módulo para procesamiento de datos.

Funciones:
    agregar_formato_archivo(data) -> DataFrame
    calcular_total_archivos(data) -> DataFrame
    calcular_promedio_lustre(data) -> DataFrame
    calcular_total_lustre_ost(data) -> DataFrame
    calcular_promedios_resto_columnas(data) -> DataFrame
    procesar_datos(data) -> DataFrame
"""

# Modules/Analysis_DarParser/StatisticsParser.py
"""
Módulo optimizado para el procesamiento y consolidación estadística de trazas de Darshan.
Preserva la integridad de identificadores grandes (Record ID), metadatos de la tesis
y limpia de forma segura las estructuras para entornos NFS y Lustre.
"""

import pandas as pd

def agregar_formato_archivo(data):
    """Asegura que la columna File_Format refleje la realidad del File Name."""
    def corregir(row):
        nombre = str(row['File Name']).lower()
        if nombre.endswith(('.jpg', '.jpeg')):
            return '.jpg'
        return row['File_Format']
    
    data['File_Format'] = data.apply(corregir, axis=1)
    return data    
    
# Modules/Analysis_DarParser/StatisticsParserv2.py
import pandas as pd

def calcular_total_archivos(data):
    """Calcula el total de archivos por Jobid y lo agrega a una nueva columna 'Total_Files'."""
    total_files_per_jobid = data.groupby('Jobid')['File Name'].count().reset_index(name='Total_Files')
    data = pd.merge(data, total_files_per_jobid, on='Jobid', how='left')
    return data

def calcular_promedio_lustre(data):
    """Calcula promedios de Lustre solo si las columnas existen y el FS es lustre."""
    if 'FS Type' in data.columns and 'lustre' in data['FS Type'].unique():
        cols_interes = ['LUSTRE_MDTS', 'LUSTRE_OSTS']
        cols_presentes = [c for c in cols_interes if c in data.columns]
        
        if cols_presentes:
            avg_lustre = data.groupby('Jobid')[cols_presentes].mean().reset_index()
            avg_lustre.columns = ['Jobid'] + [f"{c}_avg" for c in cols_presentes]
            return pd.merge(data, avg_lustre, on='Jobid', how='left')
    return data
    
def calcular_total_lustre_ost(data):
    """Calcula el total de LUSTRE_OST no nulos por Jobid si el FS Type es 'lustre'."""
    if 'FS Type' in data.columns and 'lustre' in data['FS Type'].unique():
        lustre_ost_columns = [col for col in data.columns if 'LUSTRE_OST_ID' in col]
        if lustre_ost_columns:
            data['Total_Lustre_OST'] = data[lustre_ost_columns].notnull().sum(axis=1)
            return data
    return data

def calcular_promedios_resto_columnas(data):
    """
    Calcula los promedios del resto de las columnas de rendimiento por Jobid.
    Filtra y elimina físicamente las columnas de Lustre si el entorno es NFS.
    """
    # Detectar el tipo de FS predominante en la traza
    fs_type = str(data['FS Type'].iloc[0]).lower() if 'FS Type' in data.columns else 'lustre'

    # Definición inteligente de columnas base (Cambiamos el orden para preservar metadatos de la app)
    metadata_cols = [
        'Jobid', 'Nprocs', 'Access_Pattern_Detected', 'Access_Pattern_flag','Record ID', 
        'File_Format', 'File Name', 'FS Type', 'Total_Files'
    ]
    
    # 🆕 Solo incluimos columnas de Lustre en la base si NO estamos en un entorno NFS
    #if 'nfs' not in fs_type:
    #    for col in ['LUSTRE_MDTS_avg', 'LUSTRE_OSTS_avg', 'Total_Lustre_OST']:
    if 'nfs' not in fs_type:
        for col in [
            'LUSTRE_MDTS_avg',
            'LUSTRE_OSTS_avg',
            'Total_Lustre_OST',
            'LUSTRE_OST_ID_0'
        ]:
            if col in data.columns:
                metadata_cols.append(col)

    base_cols_presentes = [col for col in metadata_cols if col in data.columns]
    
    # Columnas que se deben excluir de las operaciones de promedio numérico (.mean)
    #columns_to_exclude = base_cols_presentes + ['LUSTRE_MDTS', 'LUSTRE_OSTS', 'Total_Lustre_OST', 'LUSTRE_MDTS_avg', 'LUSTRE_OSTS_avg'] + [col for col in data.columns if 'LUSTRE_OST_ID' in col]
    columns_to_exclude = base_cols_presentes + [
    'Total_Lustre_OST',
    'LUSTRE_MDTS_avg',
    'LUSTRE_OSTS_avg'
    ]
    columns_to_avg = [col for col in data.columns if col not in columns_to_exclude and data[col].dtype in ['float64', 'int64']]
    
    avg_columns_per_jobid = data.groupby('Jobid')[columns_to_avg].mean().reset_index()
    
    # Extraer metadatos limpios en su formato original
    data_base_clean = data[base_cols_presentes].drop_duplicates()
    
    # Merge final libre de columnas fantasma de Lustre para entornos NFS
    data_avg = pd.merge(data_base_clean, avg_columns_per_jobid, on='Jobid', how='left')
    return data_avg

def procesar_datos(data):
    """Orquesta las transformaciones estadísticas."""
    data = calcular_total_archivos(data)
    data = calcular_promedio_lustre(data)
    data = calcular_total_lustre_ost(data)
    data_avg = calcular_promedios_resto_columnas(data)
    
    sort_cols = [col for col in ['File_Format', 'Total_Lustre_OST'] if col in data_avg.columns]
    if sort_cols:
        return data_avg.sort_values(by=sort_cols)
    return data_avg