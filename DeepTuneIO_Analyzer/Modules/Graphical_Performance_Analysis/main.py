# main.py
# Este es el archivo principal que coordina la ejecución del programa. 
# Importa funciones de los módulos anteriores y realiza las operaciones necesarias.
import os
import pandas as pd
from src.data_processing import adjust_units, generate_summary
from src.formatting import summary_formatted_general
from src.plotting import tabla_perf, plot_performance_combined, plot_performance_combined_with_ideal
from src.prediction import prediction_lineal
from src.utils import acces_mode

import matplotlib.pyplot as plt

# Configuración de estilo de matplotlib y seaborn
plt.rc('font', size=20)  # Ajustes globales para el tamaño de la fuente
plt.rc('axes', titlesize=20)  # Tamaño del título
plt.rc('axes', labelsize=20)  # Tamaño de las etiquetas de los ejes
plt.rc('xtick', labelsize=20)  # Tamaño de las etiquetas de las marcas en x
plt.rc('ytick', labelsize=20)  # Tamaño de las etiquetas de las marcas en y
plt.rc('legend', fontsize=20)  # Tamaño de la leyenda
plt.rc('font', weight='bold')  # Negrita global
plt.rc('axes', titleweight='bold', labelweight='bold')  # Negrita en títulos y etiquetas de ejes

# Configuración inicial
base_file_name = "Analisis_IO"
name_event = 'JSC24'
app_name = "DeepGalaxy"  # "DeepGalaxy" "DLIOv1" 
dir_work = "Articulo"
dir_metric = 'Metric_perf_2'  # IO Time - Data Transfer Rate - IOPs
input_dir = 'Output_JSC24'  # Dir 2

# Obtener el directorio de salida
if app_name == "DeepGalaxy":
    dir_bench = "DeepGalaxy"  # dir 3
    dir_fs = "bw512"  # dir 4
    fs_scenary = "lustre_2ost"  # dir 5 "lustre_1ost" "lustre_4ost" "nfs_SnGPU_e1"

elif app_name == "DLIOv1":
    dir_bench = "DLIOv1"  # dir 3
    dir_fs = 'TFRecord'  # dir 4 'HDF5' 'TFRecord' 'NPZ'
    fs_scenary = "lustre_ost"  # dir 5

file_Perf = f'5b_Analisis_IO_{dir_bench}_Perf_{dir_fs}_{fs_scenary}_{name_event}_iops_dep_v1.csv'
output_dir = os.path.join(dir_work, input_dir, dir_bench, dir_fs, fs_scenary, "Gráficos", dir_metric)
os.makedirs(output_dir, exist_ok=True)

# Métricas de los ejes
X_metric = "Processes IO"
Y_metric_prin1 = "IO_Time(s)"
Y_metric_prin2 = "Run_Time(s)"
Y_metric_sec1 = "Bandwidth(MiB/s)"
Y_metric_sec2 = "IOPs"

file_path = os.path.join(dir_work, input_dir, dir_bench, dir_fs, fs_scenary, file_Perf)
data = pd.read_csv(file_path, sep=',')

global_counter = 0  # Inicializa un contador global

# Definir las llamadas a las funciones de plot
plot_performance_combined(data, generate_summary, summary_formatted_general, tabla_perf, acces_mode, 
                          dir_bench, Y_metric_prin1, Y_metric_sec1, Y_metric_sec2, 
                          Y_metric_prin2=None, secondary_label="Data Transfer Rate", 
                          ylabel_primary="Time(s)", color_1="seagreen", color_3='crimson', 
                          color_2=None, secondary_unit='MiB/s', output_dir=output_dir, 
                          fs_scenary=fs_scenary, global_counter=global_counter)

plot_performance_combined_with_ideal(data, generate_summary, summary_formatted_general, tabla_perf, acces_mode, 
                                     prediction_lineal, dir_bench, Y_metric_prin1, Y_metric_sec1, Y_metric_sec2, 
                                     Y_metric_prin2=None, secondary_label="Data Transfer Rate", 
                                     ylabel_primary="Time(s)", color_1="seagreen", color_3='crimson', 
                                     color_2=None, secondary_unit='MiB/s', output_dir=output_dir, 
                                     fs_scenary=fs_scenary, global_counter=global_counter)
