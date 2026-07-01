# Modulos/Process_Trace_Darshan_Perf/data_analysis.py
import os
import pandas as pd
import numpy as np


def consolidar_definitivo(path_iops_csv, path_seff_csv, path_output_final):
    """
    Integra el reporte de eficiencia (seff) con los datos consolidados de IOPS.
    """
    # 1. Carga de datos
    df_iops = pd.read_csv(path_iops_csv)
    df_seff = pd.read_csv(path_seff_csv)
    
    # 2. Asegurar que Jobid sea del mismo tipo para el merge
    df_iops['Jobid'] = df_iops['Jobid'].astype(int)
    df_seff['Jobid'] = df_seff['Jobid'].astype(int)
    
    # 3. Merge: Unimos por Jobid
    # Se usa 'left' para mantener todas las filas de IOPS aunque no tengan match de eficiencia
    df_final = pd.merge(df_iops, df_seff, on='Jobid', how='left')
    
    # 4. Limpieza post-fusión
    # A veces el reporte seff trae columnas duplicadas de info general; eliminamos prefijos si existen
    cols_to_drop = [c for c in df_final.columns if c.endswith('_y')]
    df_final.drop(columns=cols_to_drop, inplace=True)
    
    # 5. Guardado final
    df_final.to_csv(path_output_final, index=False)
    print(f"✅ Archivo definitivo creado exitosamente: {path_output_final}")


def limpiar_columnas_vacias(df):
    """
    Elimina columnas que contienen únicamente el valor 0.
    """
    # Filtramos columnas numéricas donde todos los valores son 0
    # Usamos (df[col] == 0).all() para identificar columnas constantes en cero
    cols_a_eliminar = [col for col in df.columns if (pd.api.types.is_numeric_dtype(df[col])) and (df[col] == 0).all()]
    
    print(f"🧹 Columnas eliminadas por estar vacías (todo ceros): {len(cols_a_eliminar)}")
    return df.drop(columns=cols_a_eliminar)


def ordenar_columnas_csv(df):
    """
    Agrupa y ordena las columnas del DataFrame en bloques lógicos.
    """
    # 1. Definir los bloques de columnas en el orden deseado
    bloque_config = [
        'Jobid','File Name', 'File_Format', 'Record ID', 'Access_Mode', 'Access_Pattern_Detected', 'Access_Pattern_flag',
'Scale_Type', 'FS Type', 'Nodes', 'Processes IO', 'Nprocs', 'Processes_per_Node', 'BatchSize', 'Transfer_Size', 'Metadata_teorico'
    ]
    
    bloque_datos = [
        'Samples', 'Total_Samples', 'Total_Files', 'IO_Total(bytes)', 'IO_Total(GB)', 'IO_Total(MiB)', 'Bytes_per_Proc', 'Bytes_per_Node'
    ]
    
    bloque_rendimiento = [
    'Total_Operations',
    'Adjusted_Reads',
    'Metadata_Operations',
    'IO_Time(s)',
    'Total_IO_Time',
    'Total_Metadata_Time',
    'Run_Time(s)',
    'IO_Time Ratio',
    'Bandwidth(MiB/s)',
    'IOPs_App',
    'IOPs_POSIX',
    'IOPs'
    ]
    
    # 2. Identificar bloques dinámicos
    # Lustre y módulos científicos
    bloque_lustre = sorted([c for c in df.columns if c.startswith('LUSTRE_')])
    bloque_modulos = sorted([c for c in df.columns if c.startswith(('H5', 'MPI', 'PNETCDF', 'DAOS', 'DFS'))])
    
    # POSIX y otros (lo que sobre)
    columnas_conocidas = bloque_config + bloque_datos + bloque_rendimiento + bloque_lustre + bloque_modulos
    bloque_posix_miscelanea = sorted([c for c in df.columns if c not in columnas_conocidas])
    
    # 3. Combinar orden final
    nuevo_orden = bloque_config + bloque_datos + bloque_rendimiento + bloque_lustre + bloque_modulos + bloque_posix_miscelanea
    
    # 4. Reindexar
    columnas_existentes = [c for c in nuevo_orden if c in df.columns]    
    return df[columnas_existentes]


def consolidar_rendimiento(path_perf_csv, path_parser_csv, path_output_csv):
    """
    Función maestra: Fusiona datos de rendimiento y parser, calcula métricas de I/O,
    IOPS, Bandwidth y Latencia de Metadatos. Limpia columnas duplicadas o vacías.
    """
    if not os.path.exists(path_perf_csv) or not os.path.exists(path_parser_csv):
        raise FileNotFoundError("Archivos de entrada no encontrados.")

    # 1. Carga
    perf_df = pd.read_csv(path_perf_csv)
    parser_df = pd.read_csv(path_parser_csv)

    # 2. Normalización de formatos (h5/tfrecords) para evitar fallos en el merge
    format_mapping = {'hdf5': 'h5', 'tfrecord': 'tfrecords'}
    perf_df['File_Format'] = perf_df['File_Format'].replace(format_mapping)
    parser_df['File_Format'] = parser_df['File_Format'].replace(format_mapping)

    # 3. Fusión lógica
    merged_df = pd.merge(perf_df, parser_df, on=['Jobid', 'File_Format'], how='left')

    # === PROTECCIÓN CONTRA COLUMNAS FALTANTES ===
    # Si Darshan no registró una operación (ej. cero escrituras), la columna no existirá.
    # Las creamos rellenadas con 0.0 para que las matemáticas nunca fallen.
    cols_necesarias = [
        'POSIX_READS', 'POSIX_WRITES', 
        'POSIX_F_READ_END_TIMESTAMP', 'POSIX_F_READ_START_TIMESTAMP',
        'POSIX_F_WRITE_END_TIMESTAMP', 'POSIX_F_WRITE_START_TIMESTAMP',
        'POSIX_F_OPEN_END_TIMESTAMP', 'POSIX_F_OPEN_START_TIMESTAMP',
        'POSIX_F_CLOSE_END_TIMESTAMP', 'POSIX_F_CLOSE_START_TIMESTAMP',
        'POSIX_FSYNC_END_TIMESTAMP', 'POSIX_FSYNC_START_TIMESTAMP',
        'POSIX_OPENS', 'POSIX_CLOSURES', 'POSIX_FSYNCS', 'POSIX_FDSYNCS'
    ]
    
    for col in cols_necesarias:
        if col not in merged_df.columns:
            merged_df[col] = 0.0
        else:
            merged_df[col] = merged_df[col].fillna(0.0)

    # 4. Cálculo de Operaciones Ajustadas
    # POSIX_READS ya viene agregado desde el Parser:
    # - HDF5 shared: rank = -1, contador agregado por Darshan.
    # - NPZ/TFRecord multi: una fila por rank/fichero, agregada después en el Summary.
    # Por tanto, NO se debe multiplicar otra vez por Processes IO.
    merged_df['Adjusted_Reads'] = merged_df['POSIX_READS']
    
    # Ahora la suma es segura porque sabemos que POSIX_WRITES existe y es numérica
    merged_df['Total_Operations'] = merged_df['Adjusted_Reads'] + merged_df['POSIX_WRITES']

    # 5. Métricas de Tiempo (Matemática segura vectorizada)
    merged_df['Total_IO_Time'] = merged_df.get('POSIX_F_READ_TIME', 0.0) + merged_df.get('POSIX_F_WRITE_TIME', 0.0)
    
    #merged_df['Total_IO_Time'] = (merged_df['POSIX_F_READ_END_TIMESTAMP'] - merged_df['POSIX_F_READ_START_TIMESTAMP']) + \
     #                            (merged_df['POSIX_F_WRITE_END_TIMESTAMP'] - merged_df['POSIX_F_WRITE_START_TIMESTAMP'])
    
    # Usamos el acumulador nativo de Darshan que incluye stat, seek, open, close, etc.
    if 'POSIX_F_META_TIME' in merged_df.columns:
        merged_df['Total_Metadata_Time'] = merged_df['POSIX_F_META_TIME']
    else:
        # Fallback de seguridad por si una traza muy antigua no tiene la columna
        merged_df['Total_Metadata_Time'] = (
            (merged_df['POSIX_F_OPEN_END_TIMESTAMP'] - merged_df['POSIX_F_OPEN_START_TIMESTAMP']) +
            (merged_df['POSIX_F_CLOSE_END_TIMESTAMP'] - merged_df['POSIX_F_CLOSE_START_TIMESTAMP']) +
            (merged_df['POSIX_FSYNC_END_TIMESTAMP'] - merged_df['POSIX_FSYNC_START_TIMESTAMP'])
        )

    # 6. Cálculo Final de IOPS y Latencia
    cols_meta = ['POSIX_OPENS', 'POSIX_CLOSURES', 'POSIX_FSYNCS', 'POSIX_FDSYNCS']
    merged_df['Metadata_Operations'] = merged_df[cols_meta].sum(axis=1)

    # IOPS basado en tiempos POSIX acumulados Darshan
    tiempo_total = (
        merged_df['Total_IO_Time'] +
        merged_df['Total_Metadata_Time']
    ).replace(0, np.nan)

    merged_df['IOPs_POSIX'] = (
        merged_df['Total_Operations'] +
        merged_df['Metadata_Operations']
    ) / tiempo_total

    # IOPS basado en el tiempo real de E/S de la aplicación
    merged_df['IOPs_App'] = (
        merged_df['Total_Operations']
    ) / merged_df['IO_Time(s)'].replace(0, np.nan)

    # Mantener compatibilidad con el resto del pipeline
    merged_df['IOPs'] = merged_df['IOPs_App']

    # =========================================================
    # === LIMPIEZA FINAL DE COLUMNAS (Sanitización de Datos) ===
    # =========================================================
    
    # 1. Eliminar duplicadas del merge
    cols_to_drop = [c for c in merged_df.columns if c.endswith('_y')]
    merged_df.drop(columns=cols_to_drop, inplace=True)
    merged_df.rename(columns={c: c.replace('_x', '') for c in merged_df.columns if c.endswith('_x')}, inplace=True)

    # 2. APLICAR LIMPIEZA DE COLUMNAS VACÍAS (NUEVO)
    merged_df = limpiar_columnas_vacias(merged_df)

    # 3. Rellenar vacíos técnicos
    for col in ['Transfer_Size', 'BatchSize']:
        if col in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(0)

    # 4. Recalcular columnas críticas
    if 'IO_Total(bytes)' in merged_df.columns:
        merged_df['IO_Total(MiB)'] = merged_df['IO_Total(bytes)'] / (1024 * 1024)

    # 5. Asegurar tipos de datos numéricos
    numeric_cols = merged_df.select_dtypes(include=[np.number]).columns
    merged_df[numeric_cols] = merged_df[numeric_cols].fillna(0)
    
    # 6. Verificación de seguridad
    assert not any(c.endswith('_x') or c.endswith('_y') for c in merged_df.columns), \
        f"Aún existen columnas duplicadas."

    # 7. ORDENAR COLUMNAS (Añadido)
    merged_df = ordenar_columnas_csv(merged_df)
    
    # 8. Guardado final
    merged_df.to_csv(path_output_csv, index=False)
    print(f"✔ Rendimiento consolidado y LIMPIO guardado en: {path_output_csv}")
    return merged_df