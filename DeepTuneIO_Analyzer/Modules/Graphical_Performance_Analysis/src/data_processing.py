import pandas as pd

# Este módulo maneja el procesamiento y ajuste de unidades de los datos.
# Funciones relacionadas con el procesamiento de datos.
# data_processing.py


def convert_to_optimal_unit(values, is_bandwidth):
    """
    Convierte los valores al conjunto óptimo de unidades (MiB/s para ancho de banda, K IOPS para IOPS) y devuelve las unidades.
    """
    max_value = values.max()
    print(max_value)
    if is_bandwidth == "Bandwidth(MiB/s)":
        if max_value < 1024:
            return values, 'MiB/s'
        else:
            return values / 1024, 'GiB/s'
    elif is_bandwidth == "IOPs":
        if max_value < 1000:
            return values, is_bandwidth
        elif max_value < 1000000:
            return values / 1000, f'K {is_bandwidth}'
        else:
            return values / 1000000, f'M {is_bandwidth}'


def adjust_units(data, is_bandwidth):
    """Aplica la conversión óptima de unidades para 'Bandwidth' e 'IOPs'."""
    data = data.copy()  # Hacer una copia explícita del DataFrame completo
    perf_unit = None
    bandwidth_unit = 'MiB/s'
    iops_unit = 'IOPS'
    
    if 'Bandwidth(MiB/s)' in data.columns:
        data.loc[:, is_bandwidth], bandwidth_unit = convert_to_optimal_unit(data[is_bandwidth], is_bandwidth)
        perf_unit = bandwidth_unit
        print(perf_unit)
    if 'IOPs' in data.columns:
        data.loc[:, is_bandwidth], iops_unit = convert_to_optimal_unit(data[is_bandwidth], is_bandwidth)
        perf_unit = iops_unit
    
    return data, perf_unit


def generate_summary(filtered_data, metric_primary1, metric_secondary, fs_type, metric_primary2=None):
    """Genera un resumen agrupado por 'Processes IO' y otras métricas según el tipo de sistema de archivos."""
    #groupby_columns = ['Processes IO']
    #aggregation_dict = {
    #    'Nodes': ['mean']
    #}
    groupby_columns = ['Processes IO', 'Nodes']
    #print("fs_type", fs_type)
    
    if fs_type == 'lustre' and 'LUSTRE_STRIPE_COUNT' in filtered_data.columns:
        #aggregation_dict['LUSTRE_STRIPE_COUNT'] = ['mean']
        groupby_columns.append('LUSTRE_STRIPE_COUNT')
    
    #aggregation_dict[metric_primary1] = ['mean', 'std']
    #aggregation_dict[metric_secondary] = ['mean', 'std']
    
    #if metric_primary2:
    #    aggregation_dict[metric_primary2] = ['mean', 'std']
    
    # Agrupar por las columnas seleccionadas
    #summary = filtered_data.groupby(groupby_columns).agg(aggregation_dict).reset_index()

    # Definir las agregaciones para las métricas primarias y secundarias
    aggregation_dict = {
        metric_primary1: ['mean', 'std'],
        metric_secondary: ['mean', 'std']
    }
    
    # Agregar una métrica primaria adicional si está definida
    if metric_primary2:
        aggregation_dict[metric_primary2] = ['mean', 'std']
    
    # Agrupar por las columnas seleccionadas sin calcular la media para 'Nodes'
    summary = filtered_data.groupby(groupby_columns).agg(aggregation_dict).reset_index()


    # Aplanar el MultiIndex en las columnas concatenando los niveles
    #summary.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in summary.columns]
    summary.columns = [' '.join(col).strip() if isinstance(col, tuple) else col for col in summary.columns]
    # Verifica cómo quedaron las columnas después de aplanar
    #print(f"Columnas después de aplanar: {summary.columns}")

    # Renombrar las columnas para facilitar el acceso
    renamed_columns = ['Processes IO', 'Nodes']
    
    # Si existe una columna de LUSTRE_STRIPE_COUNT, debemos incluir ambas versiones
    if fs_type == 'lustre' and 'LUSTRE_STRIPE_COUNT' in summary.columns:
        renamed_columns.append('LUSTRE stripe count')  # Para el valor "mean"
    
    # Añadir las columnas para la métrica primaria y secundaria
    renamed_columns += [
        f'{metric_primary1}_mean', f'{metric_primary1}_std', 
        f'{metric_secondary}_mean', f'{metric_secondary}_std'
    ]

    if metric_primary2:
        renamed_columns += [f'{metric_primary2}_mean', f'{metric_primary2}_std']
        
    #print(f"Number of columns in summary: {len(summary.columns)}")
    #print(f"Number of renamed columns: {len(renamed_columns)}")
    
    # Verificar si el número de columnas coincide antes de asignar
    if len(renamed_columns) != len(summary.columns):
        raise ValueError(f"Length mismatch: Expected {len(summary.columns)} columns, but got {len(renamed_columns)} column names.")

    # Asignar los nuevos nombres de columnas
    summary.columns = renamed_columns
    
    # Convertir a tipos de datos apropiados
    summary['Processes IO'] = summary['Processes IO'].astype(int)
    summary['Nodes'] = summary['Nodes'].astype(int)
    if 'LUSTRE_STRIPE_COUNT_mean' in summary.columns:
        summary['LUSTRE stripe count'] = summary['LUSTRE stripe count'].astype(int)
    
    # Reemplazar NaN en std con 0
    summary.fillna(0, inplace=True)
    
    return summary
