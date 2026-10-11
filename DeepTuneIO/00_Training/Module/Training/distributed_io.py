"""Distributed HDF5 I/O for DeepTuneIO-Training."""

import numpy as np


def read_hdf5_distributed_shared(
    filename,
    split,
    class_names,
    execution_mode="hpc",
):
    """
    Read one partition of a shared HDF5 dataset per Horovod rank.

    Parameters
    ----------
    filename : str or Path
        Shared HDF5 file.

    split : str
        HDF5 split to read: "train" or "val".

    class_names : sequence of str
        Global class ordering used to generate stable labels.

    execution_mode : str
        Must be "hpc".

    Returns
    -------
    images : numpy.ndarray
        Images assigned to the current Horovod rank.

    labels : numpy.ndarray
        Integer labels corresponding to ``class_names``.
    """

    if execution_mode.lower() != "hpc":
        raise ValueError(
            "read_strategy='distributed_shared' requiere "
            "execution_mode='hpc'."
        )

    import h5py
    import horovod.tensorflow.keras as hvd

    if not hvd.is_initialized():
        hvd.init()

    if split not in {"train", "val"}:
        raise ValueError(
            f"Split no válido: {split!r}. "
            "Valores permitidos: 'train' o 'val'."
        )

    rank = hvd.rank()
    size = hvd.size()

    with h5py.File(filename, "r", swmr=True) as hdf5_file:

        if split not in hdf5_file:
            raise KeyError(
                f"El HDF5 no contiene el split {split!r}."
            )

        split_group = hdf5_file[split]

        # ----------------------------------------------------
        # Total global de imágenes del split.
        # ----------------------------------------------------

        total_images = 0

        for class_name in class_names:
            if class_name not in split_group:
                raise KeyError(
                    f"La clase {class_name!r} no existe "
                    f"en el split {split!r}."
                )

            total_images += split_group[class_name]["images"].shape[0]

        # ----------------------------------------------------
        # Reparto balanceado.
        #
        # Los primeros ranks reciben una imagen adicional
        # cuando total_images no es divisible por size.
        # ----------------------------------------------------

        base = total_images // size
        remainder = total_images % size

        local_count = base + (1 if rank < remainder else 0)

        start_index = (
            rank * base
            + min(rank, remainder)
        )

        end_index = start_index + local_count

        # ----------------------------------------------------
        # Lectura únicamente del intervalo correspondiente
        # al rank actual.
        # ----------------------------------------------------

        images_list = []
        labels_list = []

        current_index = 0

        for label_idx, class_name in enumerate(class_names):

            dataset = split_group[class_name]["images"]
            num_images = dataset.shape[0]

            class_start = current_index
            class_end = current_index + num_images

            overlap_start = max(start_index, class_start)
            overlap_end = min(end_index, class_end)

            if overlap_start < overlap_end:

                local_start = overlap_start - class_start
                local_end = overlap_end - class_start

                images_list.append(
                    dataset[local_start:local_end]
                )

                labels_list.extend(
                    [label_idx] * (local_end - local_start)
                )

            current_index = class_end

        # ----------------------------------------------------
        # Construcción de arrays locales.
        # ----------------------------------------------------

        if images_list:
            images_array = np.concatenate(
                images_list,
                axis=0
            )
        else:
            images_array = np.empty((0,), dtype=np.uint8)

        labels_array = np.asarray(
            labels_list,
            dtype=np.int64
        )

    return images_array, labels_array
