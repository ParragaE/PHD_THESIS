import os
import matplotlib.pyplot as plt
from Modules.Graphical_Performance_Analysis.src.data_processing import adjust_units, generate_summary
from Modules.Graphical_Performance_Analysis.src.formatting import summary_formatted_general
from Modules.Graphical_Performance_Analysis.src.utilities import acces_mode
from Modules.Graphical_Performance_Analysis.src.prediction import prediction_lineal, prediction_polinomial, prediction_polinomial1
from matplotlib.colors import LinearSegmentedColormap



# Funciones para generar tablas y gráficos.
# Este módulo contiene funciones para generar tablas y gráficos de rendimiento.

# plotting.py

def tabla_perf(summary_formatted, access_label, file_format, output_dir, metric_secondary, secondary_unit, fs_type, metric_primary2=None, global_counter=0):
    """
    Genera y guarda una tabla de rendimiento como imagen.
    """
    # Parametros de ajuste de la tabla
    figsize_width = 20
    figsize_height = 10
    font_size = 25
    cell_scale_x = 2
    cell_scale_y = 2

    # Determinar el número máximo de columnas en table_data
    #max_columns = len(summary_formatted.columns)
    max_columns = max(len(row) for row in summary_formatted)
    # Ajustar colWidths a la cantidad de columnas
    colWidths = [1.8] * max_columns

    # Generar y guardar tabla como imagen
    fig, ax = plt.subplots(figsize=(figsize_width, figsize_height))
    ax.axis('off')
    ax.axis('tight')

    # Crear y configurar la tabla con colWidths ajustado
    table = ax.table(cellText=summary_formatted.values, colWidths=colWidths, colLabels=summary_formatted.columns, 
                     loc='center', cellLoc='center', bbox=[-0.5, 0.1, 1.5, 0.8])

    # Ajustar el tamaño de la fuente para todo el texto en la tabla
    table.set_fontsize(font_size)
    table.auto_set_font_size(False)
    table.scale(cell_scale_x, cell_scale_y)

    # Formatear encabezados
    for (i, j), cell in table.get_celld().items():
        if i == 0:  # La fila 0 contiene las cabeceras
            cell.set_facecolor('gray')
            cell.set_text_props(color='white')

    # Definir el nombre del archivo de salida
    table_out = f"{global_counter}_Table_Performance_Analysis_{access_label}_{file_format}_{fs_type}_Scaling.png"
    table_output_dir = os.path.join(output_dir, table_out)

    try:
        plt.savefig(table_output_dir, format='png', bbox_inches='tight', dpi=300)
        plt.show()
        plt.close(fig)
    except Exception as e:
        print(f"Failed to save the table image: {e}")



def plot_performance_combined(data, dir_bench, output_dir, fs_scenary, global_counter, processes_to_include,
                          ylabel_primary, secondary_label, 
                          Y_metric_prin1, Y_color_prin1,
                          Y_metric_sec1, Y_color_sec1,
                          Y_metric_prin2=None, Y_color_prin2=None
                         ):    

    """
    Genera y guarda gráficos de rendimiento combinados.
    """
    unique_access = data['Scale_Type'].unique()
    unique_formats = data['File_Format'].unique()
    #processes_to_include = [4, 8, 16, 32, 48, 64]  # Ajuste de procesos

    for access in unique_access:
        access_label = acces_mode(access)
        for file_format in unique_formats:
            for fs_type in data['FS Type'].unique():
                for unique_ts in data['Transfer_Size'].unique():
                    # Filtrar datos para el modo de acceso, formato de archivo y tipo de sistema de archivos actual
                    filtered_data = data[
                        (data['Scale_Type'] == access) & 
                        (data['File_Format'] == file_format) & 
                        (data['FS Type'] == fs_type) & 
                        (data['Transfer_Size'] == unique_ts) &
                        (data['Processes IO'].isin(processes_to_include))
                    ]
                    if access == "ss":
                        ylim=600
                        ylim2=35000
                    else:
                        #ylim=15000
                        #ylim2=35000
                        #ylim=30000
                        ylim2=400
                       
                    if filtered_data.empty:
                        continue
                    print("secondary_label", secondary_label)
                    # Ajustar unidades
                    if secondary_label == "Data Transfer Rate":
                        is_bandwidth = 'Bandwidth(MiB/s)'
                        secondary_unit='MiB/s'
                    elif secondary_label == "I/O Operations per Second":
                        is_bandwidth = 'IOPs'
                        secondary_unit='IOPs'
                        
                    #adjusted_data, secondary_unit = adjust_units(filtered_data, is_bandwidth)
                    adjusted_data = filtered_data
                    print(secondary_unit)
                    # Generar resumen
                    summary = generate_summary(adjusted_data, Y_metric_prin1, Y_metric_sec1, fs_type, Y_metric_prin2)
                    
                    # Formatear resumen
                    summary_formatted = summary_formatted_general(summary, Y_metric_prin1, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2)
                    
                    # Crear tabla de rendimiento
                    tabla_perf(summary_formatted, access_label, file_format, output_dir, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2, global_counter)
                    
                    # Incrementar el contador global
                    global_counter += 1

                    # Crear el gráfico
                    fig, ax1 = plt.subplots(figsize=(14, 10))
                    
                    # Asegurar que 'Processes IO' sea de tipo numérico
                    summary['Processes IO'] = summary['Processes IO'].astype(int)
                    positions = summary['Processes IO'].values

                    # Gráfico de barras para la métrica secundaria
                    ax1.bar(positions - 7/15, summary[f'{Y_metric_sec1}_mean'], width=3, color=Y_color_sec1, 
                            label=f"{secondary_label} ({secondary_unit})", alpha=0.8)

                    ax1.set_xticks(positions)
                    # Verificar si 'LUSTRE stripe count' está en el DataFrame
                    if 'LUSTRE stripe count' in summary.columns:
                        # Si la columna existe, crear la etiqueta con ella
                        #ax1.set_xticklabels(summary['Nodes'].astype(str) + "N" + "-" + summary['Processes IO'].astype(str) + "p" + "-" +  
                        #                    f"-{summary['LUSTRE stripe count'].astype(str)}OST", rotation=30, ha='right')
                        ax1.set_xticklabels(
                            summary['Nodes'].astype(int).astype(str) + "N" + "-" + 
                            summary['Processes IO'].astype(int).astype(str) + "p" + "-" + 
                            summary['LUSTRE stripe count'].astype(int).astype(str) + "OST", 
                            rotation=30, 
                            ha='right'
                        )

                    else:
                        # Si la columna no existe, crear la etiqueta sin ella
                        ax1.set_xticklabels(summary['Nodes'].astype(str) + "N" + "-" +  summary['Processes IO'].astype(str) + "p", rotation=30, ha='right')

                    # Etiquetas de los ejes
                    ax1.set_xlabel('Nodes(N) - Processes IO(p)' + (" - Object Storage Target(OST)" if fs_type == 'lustre' else ""))
                    ax1.set_ylabel(secondary_label + f" ({secondary_unit})", color=Y_color_sec1)
                    #ax1.set_ylim(0, max(summary[f'{Y_metric_sec1}_mean']) * 1.5)
                    #ax1.set_ylim(0, ylim)
                    ax1.tick_params(axis='y', colors=Y_color_sec1)
                    ax1.legend(loc='upper left')

                    # Eje Y secundario para la métrica principal
                    ax2 = ax1.twinx()
                    ax2.plot(positions, summary[f'{Y_metric_prin1}_mean'], color=Y_color_prin1, label=Y_metric_prin1, marker='o')
                    ax2.fill_between(positions, summary[f'{Y_metric_prin1}_mean'] - summary[f'{Y_metric_prin1}_std'], 
                                     summary[f'{Y_metric_prin1}_mean'] + summary[f'{Y_metric_prin1}_std'], color=Y_color_prin1, alpha=0.2)

                    if Y_metric_prin2:
                        ax2.plot(positions, summary[f'{Y_metric_prin2}_mean'], color=Y_color_prin2, label=Y_metric_prin2, marker='x')
                        ax2.fill_between(positions, summary[f'{Y_metric_prin2}_mean'] - summary[f'{Y_metric_prin2}_std'], 
                                         summary[f'{Y_metric_prin2}_mean'] + summary[f'{Y_metric_prin2}_std'], color=Y_color_prin2, alpha=0.2)
                    
                    ax2.set_ylabel(f"{ylabel_primary}", color=Y_color_prin1)
                    ax2.tick_params(axis='y', labelcolor=Y_color_prin1)
                    #ax2.set_ylim(0, ylim2)
                    
                    #if Y_metric_prin2 is None:
                    #    ax2.set_ylim(0, max(summary[f'{Y_metric_prin1}_mean']) * 1.5)
                    #else:
                    #    max_y = max(summary[f'{Y_metric_prin1}_mean'].max(), summary[f'{Y_metric_prin2}_mean'].max())
                    #    ax2.set_ylim(0, max_y * 1.5)
                    
                    ax2.legend(loc='upper right')

                    # Título del gráfico
                    title_base = f'Performance Analysis: {Y_metric_prin1}'
                    if Y_metric_prin2:
                        title_base += f' - {Y_metric_prin2}'
                    title_base += f' and {secondary_label}\n File System: {fs_type.upper()} - File Format: {file_format.upper()}'
                    if dir_bench == "DLIOv1":
                        title_base += f' - Transfer Size: {unique_ts}'
                    title_base += f'\n{access_label}'.upper()
                    plt.title(title_base)

                    plt.grid(True, which="both", ls="--")
                    plt.tight_layout()

                    # Guardar gráfico
                    file_out = f"{global_counter}_Graphic_Performance_Analysis_{access_label}_{file_format}_{fs_type}_Scaling.jpg"
                    file_output_dir = os.path.join(output_dir, file_out)
                    plt.savefig(file_output_dir, format='jpg', bbox_inches='tight', dpi=300)
                    plt.show()
                    plt.close(fig)


def plot_perf_log2(data, dir_bench, output_dir, fs_scenary, global_counter, processes_to_include,
                          ylabel_primary, secondary_label, 
                          Y_metric_prin1, Y_color_prin1,
                          Y_metric_sec1, Y_color_sec1,
                          Y_metric_prin2=None, Y_color_prin2=None
                         ):    

    """
    Genera y guarda gráficos de rendimiento combinados con opciones de escala logarítmica.
    """
    unique_access = data['Scale_Type'].unique()
    unique_formats = data['File_Format'].unique()
    #processes_to_include = [4, 8, 16, 32, 48, 64]  # Ajuste de procesos

    for access in unique_access:
        access_label = acces_mode(access)
        for file_format in unique_formats:
            for fs_type in data['FS Type'].unique():
                for unique_ts in data['Transfer_Size'].unique():
                    # Filtrar datos para el modo de acceso, formato de archivo y tipo de sistema de archivos actual
                    filtered_data = data[
                        (data['Scale_Type'] == access) & 
                        (data['File_Format'] == file_format) & 
                        (data['FS Type'] == fs_type) & 
                        (data['Transfer_Size'] == unique_ts) &
                        (data['Processes IO'].isin(processes_to_include))
                    ]
                    if access == "ss":
                        ylim=600
                        ylim2=35000
                    else:
                        ylim2=400
                       
                    if filtered_data.empty:
                        continue

                    # Ajustar unidades
                    if secondary_label == "Data Transfer Rate":
                        is_bandwidth = 'Bandwidth(MiB/s)'
                        secondary_unit='MiB/s'
                    elif secondary_label == "I/O Operations per Second":
                        is_bandwidth = 'IOPs'
                        secondary_unit='IOPs'
                        
                    adjusted_data = filtered_data

                    # Generar resumen
                    summary = generate_summary(adjusted_data, Y_metric_prin1, Y_metric_sec1, fs_type, Y_metric_prin2)
                    
                    # Formatear resumen
                    summary_formatted = summary_formatted_general(summary, Y_metric_prin1, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2)
                    
                    # Crear tabla de rendimiento
                    tabla_perf(summary_formatted, access_label, file_format, output_dir, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2, global_counter)
                    
                    # Incrementar el contador global
                    global_counter += 1

                    # Crear el gráfico
                    fig, ax1 = plt.subplots(figsize=(14, 10))
                    
                    # Asegurar que 'Processes IO' sea de tipo numérico
                    summary['Processes IO'] = summary['Processes IO'].astype(int)
                    positions = summary['Processes IO'].values

                    # Gráfico de barras para la métrica secundaria
                    ax1.bar(positions - 7/15, summary[f'{Y_metric_sec1}_mean'], width=3, color=Y_color_sec1, 
                            label=f"{secondary_label} ({secondary_unit})", alpha=0.8)

                    ax1.set_xticks(positions)

                    # Verificar si 'LUSTRE stripe count' está en el DataFrame
                    if 'LUSTRE stripe count' in summary.columns:
                        ax1.set_xticklabels(
                            summary['Nodes'].astype(int).astype(str) + "N" + 
                            "-" + summary['Processes IO'].astype(int).astype(str) + "p" + 
                            "-" + summary['LUSTRE stripe count'].astype(int).astype(str) + "OST", 
                            rotation=30, ha='right'
                        )
                    else:
                        ax1.set_xticklabels(summary['Nodes'].astype(str) + "N" + "-" + summary['Processes IO'].astype(str) + "p", rotation=30, ha='right')

                    # Etiquetas de los ejes
                    ax1.set_xlabel('Nodes(N) - Processes IO(p)' + (" - Object Storage Target(OST)" if fs_type == 'lustre' else ""))
                    ax1.set_ylabel(secondary_label + f" ({secondary_unit})", color=Y_color_sec1)

                    # Cambiar a escala logarítmica en el eje Y de la métrica secundaria
                    #ax1.set_yscale('log')
                    ax1.tick_params(axis='y', colors=Y_color_sec1)
                    ax1.legend(loc='upper left')

                    # Eje Y secundario para la métrica principal
                    ax2 = ax1.twinx()
                    ax2.plot(positions, summary[f'{Y_metric_prin1}_mean'], color=Y_color_prin1, label=Y_metric_prin1, marker='o')
                    ax2.fill_between(positions, summary[f'{Y_metric_prin1}_mean'] - summary[f'{Y_metric_prin1}_std'], 
                                     summary[f'{Y_metric_prin1}_mean'] + summary[f'{Y_metric_prin1}_std'], color=Y_color_prin1, alpha=0.2)

                    if Y_metric_prin2:
                        ax2.plot(positions, summary[f'{Y_metric_prin2}_mean'], color=Y_color_prin2, label=Y_metric_prin2, marker='x')
                        ax2.fill_between(positions, summary[f'{Y_metric_prin2}_mean'] - summary[f'{Y_metric_prin2}_std'], 
                                         summary[f'{Y_metric_prin2}_mean'] + summary[f'{Y_metric_prin2}_std'], color=Y_color_prin2, alpha=0.2)

                    # Cambiar a escala logarítmica en el eje Y de la métrica principal
                    ax2.set_yscale('log')
                    ax2.set_ylabel(f"{ylabel_primary}", color=Y_color_prin1)
                    ax2.tick_params(axis='y', labelcolor=Y_color_prin1)
                    ax2.legend(loc='upper right')

                    # Título del gráfico
                    title_base = f'Performance Analysis: {Y_metric_prin1}'
                    if Y_metric_prin2:
                        title_base += f' - {Y_metric_prin2}'
                    title_base += f' and {secondary_label}\n File System: {fs_type.upper()} - File Format: {file_format.upper()}'
                    if dir_bench == "DLIOv1":
                        title_base += f' - Transfer Size: {unique_ts}'
                    title_base += f'\n{access_label}'.upper()
                    plt.title(title_base)

                    plt.grid(True, which="both", ls="--")
                    plt.tight_layout()

                    # Guardar gráfico
                    file_out = f"{global_counter}_Graphic_Performance_Analysis_{access_label}_{file_format}_{fs_type}_Scaling.jpg"
                    file_output_dir = os.path.join(output_dir, file_out)
                    plt.savefig(file_output_dir, format='jpg', bbox_inches='tight', dpi=300)
                    plt.show()
                    plt.close(fig)

def plot_perf_log(data, dir_bench, output_dir, fs_scenary, global_counter,
                  processes_to_include, ylabel_primary, secondary_label,
                  Y_metric_prin1, Y_color_prin1, Y_metric_sec1, Y_color_sec1,
                  Y_metric_prin2=None, Y_color_prin2=None
                 ):    

    """
    Genera y guarda gráficos de rendimiento combinados, intercambiando el gráfico de barras al eje secundario y el gráfico de líneas al eje primario.
    """
    unique_access = data['Scale_Type'].unique()
    unique_formats = data['File_Format'].unique()
    #processes_to_include = [4, 32, 64]  # Ajuste de procesos

    for access in unique_access:
        access_label = acces_mode(access)
        for file_format in unique_formats:
            for fs_type in data['FS Type'].unique():
                for unique_ts in data['Transfer_Size'].unique():
                    # Filtrar datos para el modo de acceso, formato de archivo y tipo de sistema de archivos actual
                    filtered_data = data[
                        (data['Scale_Type'] == access) & 
                        (data['File_Format'] == file_format) & 
                        (data['FS Type'] == fs_type) & 
                        (data['Transfer_Size'] == unique_ts) &
                        (data['Processes IO'].isin(processes_to_include))
                    ]
                    if access == "ss":
                        ylim=600
                        ylim2=700
                    else:
                        ylim2=20000
                       
                    if filtered_data.empty:
                        continue

                    # Ajustar unidades
                    if secondary_label == "Data Transfer Rate":
                        is_bandwidth = 'Bandwidth(MiB/s)'
                        secondary_unit='MiB/s'
                    elif secondary_label == "I/O Operations per Second":
                        is_bandwidth = 'IOPs'
                        secondary_unit='IOPs'
                        
                    adjusted_data = filtered_data

                    # Generar resumen
                    summary = generate_summary(adjusted_data, Y_metric_prin1, Y_metric_sec1, fs_type, Y_metric_prin2)
                    
                    # Formatear resumen
                    summary_formatted = summary_formatted_general(summary, Y_metric_prin1, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2)
                    
                    # Crear tabla de rendimiento
                    tabla_perf(summary_formatted, access_label, file_format, output_dir, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2, global_counter)
                    
                    # Incrementar el contador global
                    global_counter += 1

                    # Crear el gráfico
                    fig, ax1 = plt.subplots(figsize=(14, 10))
                    
                    # Asegurar que 'Processes IO' sea de tipo numérico
                    summary['Processes IO'] = summary['Processes IO'].astype(int)
                    positions = summary['Processes IO'].values

                    # Gráfico de líneas para la métrica principal (eje primario)
                    ax1.plot(positions, summary[f'{Y_metric_prin1}_mean'], color=Y_color_prin1, label=Y_metric_prin1, marker='o')
                    ax1.fill_between(positions, summary[f'{Y_metric_prin1}_mean'] - summary[f'{Y_metric_prin1}_std'], 
                                     summary[f'{Y_metric_prin1}_mean'] + summary[f'{Y_metric_prin1}_std'], color=Y_color_prin1, alpha=0.2)

                    if Y_metric_prin2:
                        ax1.plot(positions, summary[f'{Y_metric_prin2}_mean'], color=Y_color_prin2, label=Y_metric_prin2, marker='x')
                        ax1.fill_between(positions, summary[f'{Y_metric_prin2}_mean'] - summary[f'{Y_metric_prin2}_std'], 
                                         summary[f'{Y_metric_prin2}_mean'] + summary[f'{Y_metric_prin2}_std'], color=Y_color_prin2, alpha=0.2)

                    ax1.set_ylabel(f"{ylabel_primary}", color=Y_color_prin1)
                    ax1.tick_params(axis='y', labelcolor=Y_color_prin1)
                    
                    # Ajustar el límite superior del eje Y primario en escala logarítmica
                    # Establecer el límite superior del eje Y primario en escala logarítmica
                    max_value_principal = max(summary[f'{Y_metric_prin1}_mean'])
                    min_value_principal = min(summary[f'{Y_metric_prin1}_mean'])  # Asegúrate de que sea mayor que 0
                    #ax1.set_ylim(min_value_principal * 0.8, max_value_principal * 2)  # Amplía el límite superior al doble
                    #ax1.set_ylim(max(1e-1, min_value_principal * 0.8), max_value_principal * 1.2)
                    # Ajustar el límite superior del eje Y primario en escala logarítmica
                    ax1.set_ylim(1, 1e7)  # Ajusta el límite superior a 10^7 y el inferior a 1 (o según lo que desees)

                    
                    # Cambiar la escala del eje primario a logarítmica (si lo deseas)
                    ax1.set_yscale('log')
                    ax1.legend(loc='upper left')

                    # Eje Y secundario para la métrica secundaria (barras)
                    ax2 = ax1.twinx()
                    ax2.bar(positions - 7/15, summary[f'{Y_metric_sec1}_mean'], width=3, color=Y_color_sec1, 
                            label=f"{secondary_label} ({secondary_unit})", alpha=0.8)

                    # Etiquetas de los ejes
                    ax2.set_xticks(positions)
                    if 'LUSTRE stripe count' in summary.columns:
                        ax2.set_xticklabels(
                            summary['Nodes'].astype(int).astype(str) + "N" + 
                            "-" + summary['Processes IO'].astype(int).astype(str) + "p"
                            "-" + summary['LUSTRE stripe count'].astype(int).astype(str) + "OST", 
                            rotation=30, ha='right'
                        )
                    else:
                        ax2.set_xticklabels(summary['Nodes'].astype(str) + "N" + "-" + summary['Processes IO'].astype(str) + "p", rotation=30, ha='right')

                    ax2.set_ylabel(secondary_label + f" ({secondary_unit})", color=Y_color_sec1)
                    #ax2.set_ylim(0, max(summary[f'{Y_metric_sec1}_mean']) * 1.5)
                    ax2.set_ylim(0, ylim2)
                    # Mantener escala lineal para el eje secundario (barras)
                    ax2.tick_params(axis='y', colors=Y_color_sec1)
                    ax2.legend(loc='upper right')

                    # Título del gráfico
                    title_base = f'Performance Analysis: {Y_metric_prin1}'
                    if Y_metric_prin2:
                        title_base += f' - {Y_metric_prin2}'
                    title_base += f' and {secondary_label}\n File System: {fs_type.upper()} - File Format: {file_format.upper()}'
                    if dir_bench == "DLIOv1":
                        title_base += f' - Transfer Size: {unique_ts}'
                    title_base += f'\n{access_label}'.upper()
                    plt.title(title_base)

                    plt.grid(True, which="both", ls="--")
                    plt.tight_layout()

                    # Guardar gráfico
                    file_out = f"{global_counter}_Graphic_Performance_Analysis_{access_label}_{file_format}_{fs_type}_Scaling.jpg"
                    file_output_dir = os.path.join(output_dir, file_out)
                    plt.savefig(file_output_dir, format='jpg', bbox_inches='tight', dpi=300)
                    plt.show()
                    plt.close(fig)



def plot_performance_combined_with_ideal(data, dir_bench, output_dir, fs_scenary, global_counter, 
                                         processes_to_include,
                                          ylabel_primary, secondary_label, 
                                          Y_metric_prin1, Y_color_prin1,
                                          Y_metric_sec1, Y_color_sec1,
                                          Y_metric_prin2=None, Y_color_prin2=None
                                         ):    

    """
    Genera y guarda gráficos de rendimiento combinados.
    """
    unique_access = data['Scale_Type'].unique()
    unique_formats = data['File_Format'].unique()
    #processes_to_include = [4, 8, 32, 64]  # Ajuste de procesos
    #processes_to_include = [4, 8, 16, 32, 64]  # Ajuste de procesos
    for access in unique_access:
        access_label = acces_mode(access)
        for file_format in unique_formats:
            for fs_type in data['FS Type'].unique():
                for unique_ts in data['Transfer_Size'].unique():
                    # Filtrar datos para el modo de acceso, formato de archivo y tipo de sistema de archivos actual
                    filtered_data = data[
                        (data['Scale_Type'] == access) & 
                        (data['File_Format'] == file_format) & 
                        (data['FS Type'] == fs_type) & 
                        (data['Transfer_Size'] == unique_ts) &
                        (data['Processes IO'].isin(processes_to_include))
                    ]

                    if filtered_data.empty:
                        continue
                    print("secondary_label", secondary_label)
                    # Ajustar unidades
                    if secondary_label == "Data Transfer Rate":
                        is_bandwidth = 'Bandwidth(MiB/s)'
                        secondary_unit='MiB/s'
                    elif secondary_label == "I/O Operations per Second":
                        is_bandwidth = 'IOPs'
                        secondary_unit='IOPs'
                        
                    adjusted_data, secondary_unit = adjust_units(filtered_data, is_bandwidth)

                    # Generar resumen
                    summary = generate_summary(adjusted_data, Y_metric_prin1, Y_metric_sec1, fs_type, Y_metric_prin2)
                    
                    # Formatear resumen
                    summary_formatted = summary_formatted_general(summary, Y_metric_prin1, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2)
                    
                    # Crear tabla de rendimiento
                    tabla_perf(summary_formatted, access_label, file_format, output_dir, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2, global_counter)
                    
                    # Incrementar el contador global
                    global_counter += 1
 
                    # Crear el gráfico
                    fig, ax1 = plt.subplots(figsize=(14, 10))
                    
                    # Asegurar que 'Processes IO' sea de tipo numérico
                    summary['Processes IO'] = summary['Processes IO'].astype(int)
                    positions = summary['Processes IO'].values

                    # Predicción lineal
                    #y_pred_linear, margin_of_error = prediction_lineal(summary, 'Processes IO', 'Nodes', Y_metric_prin1, positions)
                    #y2_pred_linear, margin_of_error2 = prediction_lineal(summary, 'Processes IO', 'Nodes', Y_metric_sec1, positions)
                    #y_pred_linear, margin_of_error = prediction_polinomial(summary, 'Processes IO', 'Nodes', Y_metric_prin1, 2)
                    #y2_pred_linear, margin_of_error2 = prediction_polinomial(summary, 'Processes IO', 'Nodes', Y_metric_sec1, 2)
                    y_pred_linear, margin_of_error = prediction_polinomial1(summary, 'Processes IO',  Y_metric_prin1, 2)
                    y2_pred_linear, margin_of_error2 = prediction_polinomial1(summary, 'Processes IO', Y_metric_sec1, 2)

                    # Gráfico de barras para la métrica secundaria
                    ax1.bar(positions - 7/15, summary[f'{Y_metric_sec1}_mean'], width=3, color=Y_color_sec1, 
                            label=f"{secondary_label} ({secondary_unit})", alpha=0.8)

                    ax1.set_xticks(positions)
                    # Verificar si 'LUSTRE stripe count' está en el DataFrame
                    if 'LUSTRE stripe count' in summary.columns:
                        # Si la columna existe, crear la etiqueta con ella
                        ax1.set_xticklabels(
                            summary['Nodes'].astype(int).astype(str) + "N" + "-" + 
                            summary['Processes IO'].astype(int).astype(str) + "p" + "-" + 
                            summary['LUSTRE stripe count'].astype(int).astype(str) + "OST", 
                            rotation=30, 
                            ha='right'
                        )
                    else:
                        # Si la columna no existe, crear la etiqueta sin ella
                        ax1.set_xticklabels(summary['Nodes'].astype(str) + "N" + "-" +summary['Processes IO'].astype(str) + "p", rotation=30, ha='right')
                        
                        
                    color_list = [(0, 'green'), (0.5, 'red'), (1, 'blue')]
    
                    cmap = LinearSegmentedColormap.from_list('cool_custom', color_list) # DeepGalaxy

                    # Etiquetas de los ejes
                    ax1.set_xlabel('Nodes(N) - Processes IO(p)' + (" - Object Storage Target(OST)" if fs_type == 'lustre' else ""))
                    ax1.set_ylabel(secondary_label + f" ({secondary_unit})", color=Y_color_sec1)
                    ax1.set_ylim(0, max(summary[f'{Y_metric_sec1}_mean']) * 1.5)
                    ax1.tick_params(axis='y', colors=Y_color_sec1)
                    ax1.legend(loc='upper left')

                    # Eje Y secundario para la métrica principal
                    ax2 = ax1.twinx()
                    # Añadir línea ideal para el tiempo de IO
                    ax2.plot(positions, y_pred_linear, color='red', linewidth=2, marker='D', label='Predicción Polinómica')
                    # Añadir margen de error a la línea de tendencia
                    ax2.fill_between(positions, y_pred_linear - margin_of_error, y_pred_linear + margin_of_error, color='red', alpha=0.2)
                    
                    #ax2.scatter(data['Processes IO'], data['IO_Time(s)'])
                    ax2.scatter(filtered_data['Processes IO'], filtered_data['IO_Time(s)'])
                    
                    
                    ax2.plot(positions, summary[f'{Y_metric_prin1}_mean'], color=Y_color_prin1, label=Y_metric_prin1, marker='o')
                    
                    ax2.fill_between(positions, summary[f'{Y_metric_prin1}_mean'] - summary[f'{Y_metric_prin1}_std'], 
                                     summary[f'{Y_metric_prin1}_mean'] + summary[f'{Y_metric_prin1}_std'], color=Y_color_prin1, alpha=0.2)
                                     
                    

                    if Y_metric_prin2:
                        ax2.plot(positions, summary[f'{Y_metric_prin2}_mean'], color=Y_color_prin2, label=Y_metric_prin2, marker='x')
                        ax2.fill_between(positions, summary[f'{Y_metric_prin2}_mean'] - summary[f'{Y_metric_prin2}_std'], 
                                         summary[f'{Y_metric_prin2}_mean'] + summary[f'{Y_metric_prin2}_std'], color=Y_color_prin2, alpha=0.2)
                    
                    ax2.set_ylabel(f"{ylabel_primary}", color=Y_color_prin1)
                    ax2.tick_params(axis='y', labelcolor=Y_color_prin1)
                    
                    if Y_metric_prin2 is None:
                        ax2.set_ylim(0, max(summary[f'{Y_metric_prin1}_mean']) * 1.5)
                    else:
                        max_y = max(summary[f'{Y_metric_prin1}_mean'].max(), summary[f'{Y_metric_prin2}_mean'].max())
                        ax2.set_ylim(0, max_y * 1.5)
                    
                    ax2.legend(loc='upper right')
                    
                    # Título del gráfico
                    title_base = f'Performance Analysis: {Y_metric_prin1}'
                    if Y_metric_prin2:
                        title_base += f' - {Y_metric_prin2}'
                    title_base += f' and {secondary_label}\n File System: {fs_type.upper()} - File Format: {file_format.upper()}'
                    if dir_bench == "DLIOv1":
                        title_base += f' - Transfer Size: {unique_ts}'
                    title_base += f'\n{access_label}'.upper()
                    plt.title(title_base)

                    plt.grid(True, which="both", ls="--")
                    plt.tight_layout()

                    # Guardar gráfico
                    file_out = f"{global_counter}_Graphic_Performance_Analysis_{access_label}_{file_format}_{fs_type}_Scaling.jpg"
                    file_output_dir = os.path.join(output_dir, file_out)
                    plt.savefig(file_output_dir, format='jpg', bbox_inches='tight', dpi=300)
                    plt.show()
                    plt.close(fig)
    
def plot_performance_combined_with_ideal2(data, generate_summary, summary_formatted_general, tabla_perf, acces_mode, prediction_lineal, 
                                             dir_bench, Y_metric_prin1, Y_metric_sec1, Y_metric_sec2, 
                                             Y_metric_prin2=None, secondary_label="Data Transfer Rate", 
                                             ylabel_primary="Time(s)", color_1="seagreen", color_3='crimson', 
                                             color_2=None, secondary_unit='MiB/s', output_dir='Gráficos', 
                                             fs_scenary='lustre_2ost', global_counter=0):
        """
        Genera y guarda gráficos de rendimiento combinados con líneas de tendencia ideales.
        """
        unique_access = data['Scale_Type'].unique()
        unique_formats = data['File_Format'].unique()
        processes_to_include = [4, 8, 16, 32, 64]  # Ajuste de procesos

        for access in unique_access:
            access_label = acces_mode(access)
            for file_format in unique_formats:
                for fs_type in data['FS Type'].unique():
                    for unique_ts in data['Transfer_Size'].unique():
                        # Filtrar datos para el modo de acceso, formato de archivo y tipo de sistema de archivos actual
                        filtered_data = data[
                            (data['Scale_Type'] == access) & 
                            (data['File_Format'] == file_format) & 
                            (data['FS Type'] == fs_type) & 
                            (data['Transfer_Size'] == unique_ts) &
                            (data['Processes IO'].isin(processes_to_include))
                        ]

                        if filtered_data.empty:
                            continue

                        # Ajustar unidades
                        is_bandwidth = True if secondary_label == "Data Transfer Rate" else False
                        adjusted_data, secondary_unit = adjust_units(filtered_data, is_bandwidth)

                        # Generar resumen
                        summary = generate_summary(adjusted_data, Y_metric_prin1, Y_metric_sec1, Y_metric_prin2, fs_type)
                        
                        # Formatear resumen
                        summary_formatted = summary_formatted_general(summary, Y_metric_prin1, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2)
                        
                        # Crear tabla de rendimiento
                        tabla_perf(summary_formatted, access_label, file_format, output_dir, Y_metric_sec1, secondary_unit, fs_type, Y_metric_prin2, global_counter)
                        
                        # Incrementar el contador global
                        global_counter += 1

                        # Predicción lineal
                        y_pred_linear, margin_of_error = prediction_lineal(summary, 'Processes IO', 'Nodes', Y_metric_prin1)
                        y2_pred_linear, margin_of_error2 = prediction_lineal(summary, 'Processes IO', 'Nodes', Y_metric_sec1)

                        # Crear el gráfico principal
                        fig, ax1 = plt.subplots(figsize=(14, 10))
                        positions = summary['Processes IO'].values

                        ax1.plot(positions, summary[f'{Y_metric_prin1}_mean'], color=color_1, label=Y_metric_prin1, marker='o')
                        ax1.fill_between(positions, summary[f'{Y_metric_prin1}_mean'] - summary[f'{Y_metric_prin1}_std'], 
                                         summary[f'{Y_metric_prin1}_mean'] + summary[f'{Y_metric_prin1}_std'], color=color_1, alpha=0.2)
                        ax1.scatter(positions, summary[f'{Y_metric_prin1}_mean'], color=color_1, label=Y_metric_prin1, marker='o')
                        ax1.errorbar(positions, summary[f'{Y_metric_prin1}_mean'], 
                                     yerr=summary[f'{Y_metric_prin1}_std'], 
                                     fmt='none', ecolor=color_1, alpha=0.2)

                        if Y_metric_prin2:
                            ax1.plot(positions, summary[f'{Y_metric_prin2}_mean'], color=color_2, label=Y_metric_prin2, marker='x')
                            ax1.fill_between(positions, summary[f'{Y_metric_prin2}_mean'] - summary[f'{Y_metric_prin2}_std'], 
                                             summary[f'{Y_metric_prin2}_mean'] + summary[f'{Y_metric_prin2}_std'], color=color_2, alpha=0.2)

                        # Añadir línea de tendencia y margen de error
                        ax1.plot(positions, y_pred_linear, color='red', linewidth=2, label='Línea de Tendencia')
                        ax1.fill_between(positions, y_pred_linear - margin_of_error, y_pred_linear + margin_of_error, 
                                         color='red', alpha=0.2, label='Margen de Error')

                        ax1.set_xlabel('Processes IO(p) - Nodes(N)' + (" - Object Storage Target(OST)" if fs_type == 'lustre' else ""))
                        ax1.set_ylabel(ylabel_primary, color=color_1)
                        ax1.tick_params(axis='y', labelcolor=color_1)
                        ax1.set_xticks(positions)
                        ax1.legend(loc='upper left')

                        # Eje Y secundario para la métrica secundaria
                        ax2 = ax1.twinx()
                        ax2.bar(positions - 7/15, summary[f'{Y_metric_sec1}_mean'], width=3, color=color_3, 
                                label=f"{secondary_label} ({secondary_unit})", alpha=0.5)
                        ax2.set_ylabel(f"{secondary_label} ({secondary_unit})", color=color_3)
                        ax2.tick_params(axis='y', labelcolor=color_3)
                        ax2.set_ylim(0, max(summary[f'{Y_metric_sec1}_mean']) * 1.5)

                        # Añadir línea de tendencia y margen de error para la métrica secundaria
                        ax2.plot(positions, y2_pred_linear, color='blue', linewidth=2, label='Línea de Tendencia Secundaria')
                        ax2.fill_between(positions, y2_pred_linear - margin_of_error2, y2_pred_linear + margin_of_error2, 
                                         color='blue', alpha=0.2, label='Margen de Error Secundario')

                        ax2.legend(loc='upper right')

                        # Título del gráfico
                        title_base = f'Performance Analysis: {Y_metric_prin1} and {secondary_label}\n{access_label}'
                        plt.title(title_base)

                        plt.grid(True, which="both", ls="--")
                        plt.tight_layout()

                        # Guardar gráfico
                        file_out = f"{global_counter}_Performance_Analysis_with_Ideal_{access_label}_{file_format}_{fs_type}_{fs_scenary}.jpg"
                        file_output_dir = os.path.join(output_dir, file_out)
                        plt.savefig(file_output_dir, format='jpg', bbox_inches='tight', dpi=300)
                        plt.close(fig)
