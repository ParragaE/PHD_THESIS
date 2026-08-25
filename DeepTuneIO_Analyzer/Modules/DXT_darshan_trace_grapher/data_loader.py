import os
import pandas as pd
from pathlib import Path

def load_data(output_dir, dir_fs_scenary, exp_ff_hdf5, exp_ff_npz, exp_ff_tfrecord, dir_DXT, fname_hdf5, fname_npz, fname_tfrecord):
    path_hdf5 = os.path.join(output_dir, dir_fs_scenary, exp_ff_hdf5, dir_DXT, fname_hdf5)
    path_npz = os.path.join(output_dir, dir_fs_scenary, exp_ff_npz, dir_DXT, fname_npz)
    path_tfrecord = os.path.join(output_dir, dir_fs_scenary, exp_ff_tfrecord, dir_DXT, fname_tfrecord)

    df_hdf5 = pd.read_csv(path_hdf5)
    df_npz = pd.read_csv(path_npz)
    df_tfrecord = pd.read_csv(path_tfrecord)

    return df_hdf5, df_npz, df_tfrecord
