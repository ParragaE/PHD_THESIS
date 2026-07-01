import os
from pathlib import Path

# Configuración de rutas y nombres de archivos
output_dir = Path('Output_DLIOv1_PDPTA_24')
event_name = 'PDPTA24'
benchmark_dir = "DLIOv1"
dir_fs_scenary ='1ost'
exp_file_formats = "Exp_HDF5_4bs"
#exp_file_formats = "Exp_TFRecord_256kts"
#exp_file_formats = "Exp_NPZ"

dir_DXT = 'DXT'
file_name = "1_DLIOv1_hdf5_ws_N1p4e1b4_Sr_1f70ksf_Lssz1mOST1_7886538_CESGARES_PDPTA24_dxt_analysis.csv"
#file_name = "1_DLIOv1_TFRecord_ws_N1p4e1b4_Sr_4f9ksf256kts_Lssz1mOST1_7882413_CESGARES__dxt_analysis.csv"
#file_name = "1_DLIOv1_NPZ_ws_N1p4e1b4_Sr_4f9ksf_Lssz1mOST1_7882731_CESGARES__dxt_analysis.csv"

base_file_name = 'Analisis_IO'  # Define esta variable adecuadamente

input_path = os.path.join(output_dir, dir_fs_scenary, exp_file_formats, dir_DXT, file_name)
output_path = output_dir / dir_fs_scenary / "Gráficos"
output_path.mkdir(parents=True, exist_ok=True)  # Asegura la creación del directorio de salida
