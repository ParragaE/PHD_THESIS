"""DeepTuneIO Analyzer - Training processor for local/HPC experiments."""
from pathlib import Path
import time
import numpy as np

from .io_utils import (
    load_images_from_folder_limited, save_as_hdf5_complex, save_as_tfrecord,
    save_as_npz, read_hdf5_complex, read_tfrecord, read_npz,
    verify_images_dict, calculate_total_io_size_jpeg, inspect_hdf5_complex,
    HDF5BatchSequence,
)
from .distributed_io import read_hdf5_complex_shared
from .model import build_and_train_model, build_and_train_sequence, get_horovod


def _dict_to_arrays(images_dict):
    images, labels = [], []
    label_map = {label: idx for idx, label in enumerate(sorted(images_dict.keys()))}
    for label in sorted(images_dict.keys()):
        group_images = images_dict[label]
        images.extend(group_images)
        labels.extend([label_map[label]] * len(group_images))
    return np.asarray(images), np.asarray(labels), len(label_map)


def _root(execution_mode):
    if execution_mode == "local":
        return True
    return get_horovod("hpc").rank() == 0


def process_training(
    data_format, folder_path, action, output_dir, input_filename=None,
    access_mode="individual", read_strategy="full", batch_size=32,
    epochs=5, execution_mode="local", application="DeepGalaxy",
    dataset_group="unknown", scenario="unknown", filesystem="unknown",
    max_classes=None, max_images_per_class=None,
):
    start_total = time.perf_counter()
    data_format = data_format.lower()
    action = action.lower()
    access_mode = access_mode.lower()
    read_strategy = read_strategy.lower()
    execution_mode = execution_mode.lower()

    if data_format not in {"jpeg", "hdf5", "tfrecord", "npz"}:
        raise ValueError("Formato no soportado.")
    if action not in {"transform", "train", "both"}:
        raise ValueError("action debe ser transform, train o both")
    if access_mode not in {"individual", "shared"}:
        raise ValueError("access_mode debe ser individual o shared")
    if read_strategy not in {"full", "batch"}:
        raise ValueError("read_strategy debe ser full o batch")
    if access_mode == "shared" and execution_mode != "hpc":
        raise ValueError("shared representa acceso multiproceso Horovod y requiere execution_mode=hpc")
    if read_strategy == "batch" and data_format != "hdf5":
        raise ValueError("En esta versión inicial read_strategy=batch está implementado para HDF5.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = input_filename or f"images.{data_format}"
    filepath = output_dir / filename

    metrics = {
        "application": application, "dataset_group": dataset_group,
        "scenario": scenario, "filesystem": filesystem,
        "data_format": data_format, "access_mode": access_mode,
        "read_strategy": read_strategy, "execution_mode": execution_mode,
        "action": action, "epochs": int(epochs), "batch_size": int(batch_size),
        "max_classes": max_classes, "max_images_per_class": max_images_per_class,
        "num_images": None, "num_classes": None,
        "source_load_time_s": None, "transform_write_time_s": None,
        "training_read_time_s": None, "training_time_s": None,
        "total_time_s": None, "io_size_bytes": None,
    }

    source = None

    if action in {"transform", "both"}:
        t0 = time.perf_counter()
        source = load_images_from_folder_limited(
            folder_path, max_classes=max_classes,
            max_images_per_class=max_images_per_class
        )
        metrics["source_load_time_s"] = time.perf_counter() - t0
        if not source:
            raise ValueError(
                "No se encontraron imágenes. Se espera <ruta>/<clase>/images/*.JPEG"
            )
        verify_images_dict(source)

        t0 = time.perf_counter()
        if data_format == "jpeg":
            metrics["io_size_bytes"] = int(calculate_total_io_size_jpeg(folder_path))
            metrics["transform_write_time_s"] = 0.0
        elif data_format == "hdf5":
            if execution_mode == "hpc":
                hvd = get_horovod("hpc")
                size = save_as_hdf5_complex(source, str(output_dir), filename) if hvd.rank() == 0 else 0
            else:
                size = save_as_hdf5_complex(source, str(output_dir), filename)
            metrics["io_size_bytes"] = int(size)
            metrics["transform_write_time_s"] = time.perf_counter() - t0
        elif data_format == "tfrecord":
            metrics["io_size_bytes"] = int(save_as_tfrecord(source, str(filepath)))
            metrics["transform_write_time_s"] = time.perf_counter() - t0
        else:
            metrics["io_size_bytes"] = int(save_as_npz(source, str(filepath)))
            metrics["transform_write_time_s"] = time.perf_counter() - t0

    if action in {"train", "both"}:
        # Batch HDF5: do not materialize the complete HDF5 dataset in RAM.
        if data_format == "hdf5" and read_strategy == "batch" and access_mode == "individual":
            t0 = time.perf_counter()
            sequence = HDF5BatchSequence(filepath, batch_size=batch_size, shuffle=False)
            metrics["training_read_time_s"] = time.perf_counter() - t0
            metrics["num_images"] = len(sequence.samples)
            metrics["num_classes"] = len(sequence.class_names)
            if metrics["io_size_bytes"] is None:
                metrics["io_size_bytes"] = int(Path(filepath).stat().st_size)
            _, _, train_time = build_and_train_sequence(
                sequence, metrics["num_classes"], epochs=epochs,
                execution_mode=execution_mode
            )
            metrics["training_time_s"] = float(train_time)

        else:
            t0 = time.perf_counter()
            if data_format == "jpeg":
                if source is None:
                    source = load_images_from_folder_limited(
                        folder_path, max_classes=max_classes,
                        max_images_per_class=max_images_per_class
                    )
                images, labels, num_classes = _dict_to_arrays(source)
            elif data_format == "hdf5" and access_mode == "shared":
                images, labels = read_hdf5_complex_shared(str(filepath), execution_mode)
                labels = labels - np.min(labels)
                num_classes = len(np.unique(labels))
            elif data_format == "hdf5":
                d, size = read_hdf5_complex(str(filepath))
                images, labels, num_classes = _dict_to_arrays(d)
                metrics["io_size_bytes"] = metrics["io_size_bytes"] or int(size)
            elif data_format == "tfrecord":
                images, labels, size = read_tfrecord(str(filepath), (64, 64, 3))
                num_classes = len(np.unique(labels))
                metrics["io_size_bytes"] = metrics["io_size_bytes"] or int(size)
            else:
                d, size = read_npz(str(filepath))
                images, labels, num_classes = _dict_to_arrays(d)
                metrics["io_size_bytes"] = metrics["io_size_bytes"] or int(size)

            metrics["training_read_time_s"] = time.perf_counter() - t0
            metrics["num_images"] = int(len(images))
            metrics["num_classes"] = int(num_classes)
            images = images.astype(np.float32) / 255.0
            _, _, train_time = build_and_train_model(
                images, labels, int(num_classes), epochs=epochs,
                execution_mode=execution_mode
            )
            metrics["training_time_s"] = float(train_time)

    metrics["total_time_s"] = time.perf_counter() - start_total
    if _root(execution_mode):
        print(f"Tiempo total: {metrics['total_time_s']:.2f} segundos")
    return metrics
