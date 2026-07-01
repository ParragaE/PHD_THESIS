import re
import os

def extract_deepgalaxy_variables(line):
    """
    Extrae variables de una línea de comando específica para la aplicación DeepGalaxy.
    """
    pattern = re.compile(r'# exe: python dg_train.py --epochs (\d+) --arch (\S+) -f (\S+) -d (\S+) --num-camera (\d+) -m (\d)')
    match = pattern.match(line.strip())
    if match:
        return {
            'Epochs': match.group(1),
            'CNN Arch': match.group(2),
            'File Name Dataset': os.path.basename(match.group(3)),
            'Dataset': match.group(4),
            'NCamera': match.group(5),
            'Data Loading Mode': 'Shared' if match.group(6) == '0' else 'Shared/Reload/Shuffle'
        }
    return None


def extract_dliov1_variables(line):
    """
    Extrae variables de una línea de comando específica para la aplicación DLIOv1.

    Args:
        line (str): Línea de texto que contiene la línea de comando a analizar.

    Returns:
        dict: Diccionario con las variables extraídas o None si no se encuentra la línea específica.
    """
    pattern = re.compile(r'# exe: python src/dlio_benchmark.py -f (\S+) -fa (\S+) -nf (\d+) -sf (\d+) -rl (\d+) -bs (\d+)(?: -ts (\d+))?(?: -ec (\d+))? -df (\S+) -gd \d+ -k \d+')
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 65536 -rl 131072 -bs 64 -ec 0 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/HDF5_S_ws_1mSS1SC_4p -gd 0 -k 1 
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 65536 -rl 131072 -bs 64 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost_ScalingFormat23/HDF5_S_ws_1mSS1SC_4p -gd 0 -go 0 -k 1
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 131072 -rl 131072 -bs 64 -ec 0 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost_ScalingFormat23/HDF5_S_ws_1mSS2SC_8p -gd 0 -go 0 -k 1 
                           # exe: python src/dlio_benchmark.py -f npz -fa multi -nf 4 -sf 196608 -rl 131072 -bs 64 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/NPZ_ss_1mSS1SC_4p -gd 1 -go 1 -k 1 
                           # exe: python src/dlio_benchmark.py -f tfrecord -fa multi -nf 4 -sf 196608 -rl 131072 -bs 64 -ts 1048576 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/TFr_ss_1mSS1SC_4p -gd 0 -k 1 
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 786432 -rl 131072 -bs 64 -ec 0 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_1ost/HDF5_S_ws_1mSS1SC_48p -gd 0 -k 1 
    match = pattern.match(line.strip())
    if match:

        file_format = match.group(1).lower()
        if file_format in ['hdf5', 'h5']:
           
            variables = {
                'File Format': match.group(1),
                'File Access': match.group(2),
                'Nfile': match.group(3),
                'Sample File': match.group(4),
                'Record Length': match.group(5),
                'Batch Size': match.group(6),
                'Chunking': match.group(7),
                'Dataset Path': match.group(8)
            }
        elif file_format == 'tfrecord':
            variables = {
                'File Format': match.group(1),
                'File Access': match.group(2),
                'Nfile': match.group(3),
                'Sample File': match.group(4),
                'Record Length': match.group(5),
                'Batch Size': match.group(6),
                'Transfer Size': match.group(7),
                'Dataset Path': match.group(8)
            }            
        else:
            variables = {
                'File Format': match.group(1),
                'File Access': match.group(2),
                'Nfile': match.group(3),
                'Sample File': match.group(4),
                'Record Length': match.group(5),
                'Batch Size': match.group(6),
                'Dataset Path': match.group(9)
            }

        #variables['Dataset Path'] = match.group(9)
        return variables
    return None

def extract_dliov1_variables_v1(line):
    """
    Extrae variables de una línea de comando específica para la aplicación DLIOv1.

    Args:
        line (str): Línea de texto que contiene la línea de comando a analizar.

    Returns:
        dict: Diccionario con las variables extraídas o None si no se encuentra la línea específica.
    """
    pattern = re.compile(r'# exe: python src/dlio_benchmark.py -f (\S+) -fa (\S+) -nf (\d+) -sf (\d+) -rl (\d+) -bs (\d+)(?: -ts (\d+))?(?: -ec (\d+))? -df (\S+) -gd \d+ -k \d+')
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 65536 -rl 131072 -bs 64 -ec 0 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/HDF5_S_ws_1mSS1SC_4p -gd 0 -k 1 
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 65536 -rl 131072 -bs 64 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost_ScalingFormat23/HDF5_S_ws_1mSS1SC_4p -gd 0 -go 0 -k 1
                           # exe: python src/dlio_benchmark.py -f hdf5 -fa shared -nf 1 -sf 131072 -rl 131072 -bs 64 -ec 0 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost_ScalingFormat23/HDF5_S_ws_1mSS2SC_8p -gd 0 -go 0 -k 1 
                           # exe: python src/dlio_benchmark.py -f npz -fa multi -nf 4 -sf 196608 -rl 131072 -bs 64 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/NPZ_ss_1mSS1SC_4p -gd 1 -go 1 -k 1 
                           # exe: python src/dlio_benchmark.py -f tfrecord -fa multi -nf 4 -sf 196608 -rl 131072 -bs 64 -ts 1048576 -df /mnt/lustre/scratch/nlsas//home/res/resd01/resd01epp/dlio_benchmark/dataset_ost/TFr_ss_1mSS1SC_4p -gd 0 -k 1 
    match = pattern.match(line.strip())
    if match:
        file_format = match.group(1).lower()
        variables = {
            'File Format': match.group(1),
            'File Access': match.group(2),
            'Nfile': match.group(3),
            'Sample File': match.group(4),
            'Record Length': match.group(5),
            'Batch Size': match.group(6),
            'Dataset Path': match.group(9)
        }
        if file_format in ['hdf5', 'h5'] and match.group(8):
        #if file_format == 'hdf5' and match.group(8):
            variables['Enable Chunking'] = match.group(8)
            variables['Dataset Path'] = match.group(9)
        if file_format == 'tfrecord' and match.group(7):
            variables['Transfer Size'] = match.group(7)
            variables['Dataset Path'] = match.group(9)

        #variables['Dataset Path'] = match.group(9)
        return variables
    return None

def extract_dliov1_variables_vp(line):
    """
    Extrae variables de una línea de comando específica para la aplicación DLIOv1.
    """
    pattern = re.compile(r'# exe: python src/dlio_benchmark.py -f (\S+) -fa (\S+) -nf (\d+) -sf (\d+) -rl (\d+) -bs (\d+)(?: -ts (\d+))?(?: -ec (\d+))? -df (\S+) -gd \d+ -k \d+')
    match = pattern.match(line.strip())
    if match:
        return {
            'File Format': match.group(1),
            'File Access': match.group(2),
            'Nfile': match.group(3),
            'Sample File': match.group(4),
            'Record Length': match.group(5),
            'Batch Size': match.group(6),
            'Transfer Size': match.group(7) if match.group(7) else 0,
            'Enable Chunking': match.group(8) if match.group(8) else 0,
            'Dataset Path': match.group(9)
        }
    return None

def extract_variables_from_file(file_path, app_name):
    """
    Lee un archivo de texto y extrae variables específicas según el nombre de la aplicación.
    """
    if app_name not in ['DeepGalaxy', 'DLIOv1']:
        raise ValueError(f"Nombre de aplicación no soportado: {app_name}")

    with open(file_path, 'r') as file:
        for line in file:
            if app_name == 'DeepGalaxy':
                variables = extract_deepgalaxy_variables(line)
            elif app_name == 'DLIOv1':
                variables = extract_dliov1_variables(line)
            if variables:
                return variables
    return None
