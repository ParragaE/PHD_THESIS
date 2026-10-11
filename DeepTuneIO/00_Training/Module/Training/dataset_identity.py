
"""Automatic dataset/experiment identity for DeepTuneIO-Training."""
from dataclasses import dataclass, asdict
from collections import Counter
import numpy as np
import h5py


def _safe_token(value):
    return str(value).replace(" ", "").replace("/", "-").replace("\\", "-")


def inspect_image_dictionary(images_dict):
    """Infer reproducibility-relevant image properties from loaded source data."""
    if not images_dict:
        raise ValueError("El dataset fuente está vacío.")

    class_names = sorted(images_dict)
    counts = {name: len(images_dict[name]) for name in class_names}
    samples = [img for name in class_names for img in images_dict[name] if isinstance(img, np.ndarray)]
    if not samples:
        raise ValueError("No se encontraron imágenes numpy válidas.")

    shapes = Counter(tuple(x.shape) for x in samples)
    dtypes = Counter(str(x.dtype) for x in samples)

    if len(shapes) != 1:
        raise ValueError(f"Las imágenes no tienen una única forma: {dict(shapes)}")
    if len(dtypes) != 1:
        raise ValueError(f"Las imágenes no tienen un único dtype: {dict(dtypes)}")

    shape = next(iter(shapes))
    dtype = next(iter(dtypes))

    if len(shape) == 2:
        height, width = shape
        channels, color_mode = 1, "GRAY"
    elif len(shape) == 3:
        height, width, channels = shape
        color_mode = {1:"GRAY", 3:"RGB", 4:"RGBA"}.get(channels, f"C{channels}")
    else:
        raise ValueError(f"Forma de imagen no soportada: {shape}")

    unique_counts = sorted(set(counts.values()))
    uniform = len(unique_counts) == 1
    images_per_class = unique_counts[0] if uniform else None

    return {
        "num_classes": len(class_names),
        "class_names": class_names,
        "class_counts": counts,
        "uniform_images_per_class": uniform,
        "images_per_class": images_per_class,
        "total_images": sum(counts.values()),
        "image_height": int(height),
        "image_width": int(width),
        "channels": int(channels),
        "color_mode": color_mode,
        "dtype": dtype,
        "source_shape": "x".join(map(str, shape)),
    }


def hdf5_layout_token(chunk_shape=None, compression=None, compression_opts=None):
    if chunk_shape is None:
        chunk = "contiguous"
    else:
        chunk = "ch" + "x".join(str(int(x)) for x in chunk_shape)

    if compression is None:
        comp = "nocomp"
    elif compression_opts is None:
        comp = _safe_token(compression)
    else:
        comp = f"{_safe_token(compression)}{_safe_token(compression_opts)}"
    return f"{chunk}_{comp}"


def build_dataset_id(
    source_dataset,
    train_info,
    data_format,
    val_info=None,
    hdf5_chunk_shape=None,
    hdf5_compression=None,
    hdf5_compression_opts=None,
    transfer_size=None,
    npz_compressed=None,
    jpeg_quality=None,
):
    # TRAIN
    nclasses = train_info["num_classes"]
    train_ipc = train_info["images_per_class"]

    if train_ipc is not None:
        train_token = f"tr{train_ipc}ixC"
    else:
        train_token = f"tr{train_info['total_images']}imgVar"

    # VALIDATION
    val_token = None

    if val_info is not None:
        val_ipc = val_info["images_per_class"]

        if val_ipc is not None:
            val_token = f"va{val_ipc}ixC"
        else:
            val_token = f"va{val_info['total_images']}imgVar"

    # Imagen: detectado automáticamente
    image_token = (
        f"{train_info['color_mode']}"
        f"{train_info['image_height']}x{train_info['image_width']}_"
        f"{train_info['dtype']}"
    )

    # Configuración específica del formato
    fmt = data_format.lower()

    if fmt == "hdf5":
        specific = "HDF5_" + hdf5_layout_token(
            hdf5_chunk_shape,
            hdf5_compression,
            hdf5_compression_opts,
        )

    elif fmt == "tfrecord":
        specific = "TFRecord_" + (
            f"ts{_safe_token(transfer_size)}"
            if transfer_size is not None
            else "tsdefault"
        )

    elif fmt == "npz":
        specific = (
            "NPZ_compressed"
            if npz_compressed
            else "NPZ_uncompressed"
        )

    elif fmt == "jpeg":
        specific = "JPEG_" + (
            f"q{int(jpeg_quality)}"
            if jpeg_quality is not None
            else "source"
        )

    else:
        specific = _safe_token(data_format)

    parts = [
        "DTIO",
        _safe_token(source_dataset),
        f"{nclasses}C",
        train_token,
    ]

    if val_token is not None:
        parts.append(val_token)

    parts.extend([
        image_token,
        specific,
    ])

    return "_".join(parts)

def build_dataset_id_o(source_dataset, source_info, data_format,
                     hdf5_chunk_shape=None, hdf5_compression=None,
                     hdf5_compression_opts=None, transfer_size=None,
                     npz_compressed=None, jpeg_quality=None):
    nclasses = source_info["num_classes"]
    ipc = source_info["images_per_class"]
    count_token = f"{ipc}ixC" if ipc is not None else f"{source_info['total_images']}imgVar"
    image_token = (
        f"{source_info['color_mode']}"
        f"{source_info['image_height']}x{source_info['image_width']}_"
        f"{source_info['dtype']}"
    )

    fmt = data_format.lower()
    if fmt == "hdf5":
        specific = "HDF5_" + hdf5_layout_token(
            hdf5_chunk_shape, hdf5_compression, hdf5_compression_opts
        )
    elif fmt == "tfrecord":
        specific = "TFRecord_" + (
            f"ts{_safe_token(transfer_size)}" if transfer_size is not None else "tsdefault"
        )
    elif fmt == "npz":
        specific = "NPZ_" + ("compressed" if npz_compressed else "uncompressed")
    elif fmt == "jpeg":
        specific = "JPEG_" + (
            f"q{int(jpeg_quality)}" if jpeg_quality is not None else "source"
        )
    else:
        specific = _safe_token(data_format)

    return (
        f"DTIO_{_safe_token(source_dataset)}_{nclasses}C_{count_token}_"
        f"{image_token}_{specific}"
    )


def build_experiment_id(dataset_id, batch_size, access_mode, read_strategy,
                        epochs=None, execution_mode=None):
    parts = [
        dataset_id,
        f"bs{int(batch_size)}",
        _safe_token(access_mode),
        _safe_token(read_strategy),
    ]
    if epochs is not None:
        parts.append(f"ep{int(epochs)}")
    if execution_mode is not None:
        parts.append(_safe_token(execution_mode))
    return "_".join(parts)


def inspect_hdf5_physical_layout(filename):
    """Read the physical properties actually stored in the generated HDF5."""
    result = {"layouts": [], "compressions": []}
    with h5py.File(filename, "r") as h5:
        for split_name in ("train", "val"):
            if split_name not in h5:
                continue
            for class_name, group in h5[split_name].items():
                ds = group["images"]
                result["layouts"].append(ds.chunks)
                result["compressions"].append((ds.compression, ds.compression_opts))
    result["layouts"] = sorted(set(map(str, result["layouts"])))
    result["compressions"] = sorted(set(map(str, result["compressions"])))
    return result


def build_tiny_imagenet_expected_info(
    num_classes,
    train_images_per_class,
    val_images_per_class=50,
    image_height=64,
    image_width=64,
    channels=3,
    color_mode="RGB",
    dtype="uint8",
):
    """
    Build the expected logical metadata for the Tiny ImageNet
    subset used by DeepTuneIO-Training without reading source
    JPEG files.

    The official Tiny ImageNet validation set contains
    50 validation images per class.

    Class names are intentionally NOT generated here because
    they must be obtained from the actual HDF5 (reuse path) or
    from the source dataset (creation path).
    """

    num_classes = int(num_classes)
    train_images_per_class = int(train_images_per_class)
    val_images_per_class = int(val_images_per_class)

    if num_classes <= 0:
        raise ValueError("num_classes debe ser > 0.")

    if train_images_per_class <= 0:
        raise ValueError(
            "train_images_per_class debe ser > 0."
        )

    if val_images_per_class <= 0:
        raise ValueError(
            "val_images_per_class debe ser > 0."
        )

    source_shape = (
        int(image_height),
        int(image_width),
        int(channels),
    )

    train_info = {
        "num_classes": num_classes,
        "class_names": None,
        "uniform_images_per_class": True,
        "images_per_class": train_images_per_class,
        "total_images": (
            num_classes * train_images_per_class
        ),
        "image_height": int(image_height),
        "image_width": int(image_width),
        "channels": int(channels),
        "color_mode": str(color_mode),
        "dtype": str(dtype),
        "source_shape": source_shape,
    }

    val_info = {
        "num_classes": num_classes,
        "class_names": None,
        "uniform_images_per_class": True,
        "images_per_class": val_images_per_class,
        "total_images": (
            num_classes * val_images_per_class
        ),
        "image_height": int(image_height),
        "image_width": int(image_width),
        "channels": int(channels),
        "color_mode": str(color_mode),
        "dtype": str(dtype),
        "source_shape": source_shape,
    }

    return train_info, val_info

