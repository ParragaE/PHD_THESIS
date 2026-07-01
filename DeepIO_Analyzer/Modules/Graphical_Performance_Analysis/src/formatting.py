# formatting.py
# Este mÃ³dulo se encarga de formatear los DataFrames para las tablas de rendimiento.

# formatting.py

def summary_formatted_general(summary, metric_primary1, metric_secondary, secondary_unit, fs_type, metric_primary2=None):
    #"""
    #Aplica formato adecuado a los DataFrames según el tipo de sistema de archivos (Lustre/NFS).
    #"""

    summary_formatted = summary.copy()

    # Aplicar formato para cada columna según el tipo de dato
    for col in summary_formatted.columns:
        if col in ['Processes IO', 'Nodes', 'LUSTRE stripe count']:
            summary_formatted[col] = summary_formatted[col].apply(lambda x: f"{int(x):d}" if isinstance(x, (int, float)) else x)
        else:
            summary_formatted[col] = summary_formatted[col].apply(lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else x)

    # Verificar las columnas existentes en el DataFrame
   # print(f"Columns in summary_formatted: {summary_formatted.columns}")

    # Definir los nombres de las columnas
    column_names = ['Processes IO', 'Nodes']
    
    # Incluir la columna 'LUSTRE stripe count' si aplica
    if fs_type == 'lustre' and 'LUSTRE stripe count' in summary_formatted.columns:
        column_names.append('LUSTRE \nstripe count')
        
    metric_secondary = metric_secondary.split('(')[0].strip()  # 'Bandwidth'
    
    # Añadir métricas primarias y secundarias
    column_names += [
        f'{metric_primary1} \nMean', f'{metric_primary1} \nStd', 
        f'{metric_secondary} \n({secondary_unit}) Mean', f'{metric_secondary} \n({secondary_unit}) Std'
    ]

    # Si hay una segunda métrica primaria, añadir sus columnas
    if metric_primary2:
        column_names += [f'{metric_primary2} \nMean', f'{metric_primary2} \nStd']
    
    #print(f"Column names to assign: {column_names}")
    
    # Verificar si el número de columnas coincide antes de asignar los nombres
    if len(column_names) != len(summary_formatted.columns):
        raise ValueError(f"Length mismatch: Expected {len(column_names)} columns, but got {len(summary_formatted.columns)} columns.\n"
                         f"Expected columns: {column_names}\n"
                         f"Actual columns: {list(summary_formatted.columns)}")

    # Asignar los nuevos nombres de columnas
    summary_formatted.columns = column_names
    return summary_formatted
