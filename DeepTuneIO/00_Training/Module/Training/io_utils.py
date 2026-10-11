"""I/O utilities for DeepTuneIO Training.

Derived from data_utils3.py and data_utils3shared.py supplied by the user.
"""
from pathlib import Path
import os
import numpy as np
import h5py
import tensorflow as tf
import cv2


def get_file_size(file_path):
    return os.path.getsize(file_path)


def calculate_total_io_size_jpeg(folder):
    total_size = 0
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith((".JPEG", ".jpg", ".png")):
                total_size += os.path.getsize(os.path.join(root, file))
    return total_size


def read_image_posix(path):
    """Read an encoded image through unbuffered POSIX-visible I/O.

    The encoded bytes are read explicitly so Darshan POSIX/DXT_POSIX can
    capture the physical I/O. Image decoding remains handled by OpenCV.
    """
    try:
        with open(path, "rb", buffering=0) as f:
            encoded = f.read()

        buffer = np.frombuffer(encoded, dtype=np.uint8)
        return cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    except (OSError, ValueError):
        return None


def load_images_from_folder(folder):
    images_dict = {}
    for root, dirs, files in os.walk(folder):
        for dir_name in dirs:
            subdir_path = os.path.join(root, dir_name, "images")
            if os.path.exists(subdir_path):
                images_dict[dir_name] = []
                for file in os.listdir(subdir_path):
                    if file.endswith((".JPEG", ".jpg", ".png")):
                        path = os.path.join(subdir_path, file)
                        image = read_image_posix(path)
                        if image is None:
                            continue
                        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        images_dict[dir_name].append(image)
    return images_dict


def verify_images_dict(images_dict):
    for label, images in images_dict.items():
        for image in images:
            if not isinstance(image, np.ndarray):
                print(f"Error: {label} contiene un elemento que no es una imagen: {image}")


def save_as_tfrecord(images_dict, filename):
    def _bytes_feature(value):
        return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

    label_map = {label: idx for idx, label in enumerate(images_dict.keys())}
    with tf.io.TFRecordWriter(filename) as writer:
        for label, images in images_dict.items():
            label_idx = label_map[label]
            for image in images:
                if not isinstance(image, np.ndarray):
                    continue
                feature = {
                    "image": _bytes_feature(image.tobytes()),
                    "label": tf.train.Feature(
                        int64_list=tf.train.Int64List(value=[label_idx])
                    ),
                }
                example = tf.train.Example(
                    features=tf.train.Features(feature=feature)
                )
                writer.write(example.SerializeToString())
    return get_file_size(filename)


def _parse_image_function(example_proto):
    desc = {
        "image": tf.io.FixedLenFeature([], tf.string),
        "label": tf.io.FixedLenFeature([], tf.int64),
    }
    return tf.io.parse_single_example(example_proto, desc)


def read_tfrecord(filename, image_shape=(64, 64, 3)):
    dataset = tf.data.TFRecordDataset(filename).map(_parse_image_function)
    images, labels = [], []
    for features in dataset:
        image = np.frombuffer(
            features["image"].numpy(), dtype=np.uint8
        ).reshape(image_shape)
        images.append(image)
        labels.append(features["label"].numpy())
    return np.array(images), np.array(labels), get_file_size(filename)


def save_as_hdf5_complex(images_dict, save_dir, filename):
    output_path = os.path.join(save_dir, filename)
    with h5py.File(output_path, "w") as hdf5_file:
        train_group = hdf5_file.create_group("train")
        for label, images in images_dict.items():
            if len(images) > 0:
                sub_group = train_group.create_group(label)
                sub_group.create_dataset(
                    "images", data=np.array(images, dtype=np.uint8)
                )
    return get_file_size(output_path)


def read_hdf5_complex(filename):
    with h5py.File(filename, "r") as hdf5_file:
        images_dict = {}
        for group_name, group in hdf5_file["train"].items():
            images_dict[group_name] = group["images"][:]
    return images_dict, get_file_size(filename)


def save_as_npz(images_dict, filename):
    np.savez(
        filename,
        **{
            label: np.array(images, dtype=np.uint8)
            for label, images in images_dict.items()
            if len(images) > 0
        },
    )
    return get_file_size(filename)


def read_npz(filename):
    with np.load(filename) as data:
        images_dict = {label: data[label] for label in data}
    return images_dict, get_file_size(filename)


def print_hdf5_structure(file_path):
    group_count = 0

    def print_structure(name, obj):
        nonlocal group_count
        if isinstance(obj, h5py.Group):
            print(f"Grupo: {name}")
            group_count += 1
        elif isinstance(obj, h5py.Dataset):
            num_images = obj.shape[0] if len(obj.shape) > 0 else 0
            print(
                f"Dataset: {name}, Forma: {obj.shape}, "
                f"Tipo de dato: {obj.dtype}, Número de imágenes: {num_images}"
            )

    with h5py.File(file_path, "r") as file:
        file.visititems(print_structure)
    print(f"\nNúmero total de grupos: {group_count}")


def load_images_from_folder_limited(folder, max_classes=None, max_images_per_class=None):
    """Load a deterministic subset of a Tiny-ImageNet-style tree.

    Expected class layout: <folder>/<class>/images/*.JPEG
    """
    images_dict = {}
    class_dirs = []
    for root, dirs, files in os.walk(folder):
        for dir_name in dirs:
            subdir_path = os.path.join(root, dir_name, "images")
            if os.path.isdir(subdir_path):
                class_dirs.append((dir_name, subdir_path))

    class_dirs = sorted(class_dirs, key=lambda x: x[0])
    if max_classes is not None:
        class_dirs = class_dirs[:int(max_classes)]

    for dir_name, subdir_path in class_dirs:
        files = sorted(
            f for f in os.listdir(subdir_path)
            if f.endswith((".JPEG", ".jpg", ".png"))
        )
        if max_images_per_class is not None:
            files = files[:int(max_images_per_class)]

        images = []
        for file in files:
            path = os.path.join(subdir_path, file)
            image = read_image_posix(path)
            if image is None:
                continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            images.append(image)

        if images:
            images_dict[dir_name] = images

    return images_dict


def inspect_hdf5_complex(filename):
    """Return class/image counts without loading image arrays into RAM."""
    class_names = []
    total_images = 0
    with h5py.File(filename, "r") as hdf5_file:
        train = hdf5_file["train"]
        class_names = sorted(train.keys())
        for label in class_names:
            total_images += int(train[label]["images"].shape[0])
    return class_names, total_images, get_file_size(filename)


class HDF5BatchSequence(tf.keras.utils.Sequence):
    """Read one HDF5 split by batch without loading it completely.

    The HDF5 file is opened for each __getitem__ call. This keeps
    the implementation portable and makes the I/O occur during
    model.fit(), rather than during an initial full read.
    """

    def __init__(
        self,
        filename,
        split="train",
        batch_size=32,
        shuffle=False,
        class_names=None,
    ):
        super().__init__()

        self.filename = str(filename)
        self.split = str(split)
        self.batch_size = int(batch_size)
        self.shuffle = bool(shuffle)

        if self.split not in {"train", "val"}:
            raise ValueError(
                f"Split no válido: {self.split!r}. "
                "Use 'train' o 'val'."
            )

        self.samples = []

        with h5py.File(self.filename, "r") as hdf5_file:

            if self.split not in hdf5_file:
                raise KeyError(
                    f"El HDF5 no contiene el split "
                    f"{self.split!r}."
                )

            split_group = hdf5_file[self.split]

            if class_names is None:
                self.class_names = sorted(split_group.keys())
            else:
                self.class_names = list(class_names)

            for class_idx, label in enumerate(self.class_names):

                if label not in split_group:
                    continue

                n = int(
                    split_group[label]["images"].shape[0]
                )

                self.samples.extend(
                    (label, image_idx, class_idx)
                    for image_idx in range(n)
                )

        self.indices = np.arange(
            len(self.samples),
            dtype=np.int64,
        )

        self.on_epoch_end()

    def __len__(self):
        return int(
            np.ceil(
                len(self.samples) / self.batch_size
            )
        )

    def __getitem__(self, batch_index):

        idx = self.indices[
            batch_index * self.batch_size:
            (batch_index + 1) * self.batch_size
        ]

        images = []
        labels = []

        with h5py.File(self.filename, "r") as hdf5_file:

            split_group = hdf5_file[self.split]

            for sample_idx in idx:

                class_name, image_idx, class_idx = (
                    self.samples[int(sample_idx)]
                )

                image = split_group[
                    class_name
                ]["images"][image_idx]

                images.append(
                    image.astype(np.float32) / 255.0
                )

                labels.append(class_idx)

        return (
            np.asarray(images, dtype=np.float32),
            np.asarray(labels, dtype=np.int64),
        )

    def on_epoch_end(self):
        if self.shuffle:
            np.random.shuffle(self.indices)

def load_tiny_val(val_dir, selected_classes=None, max_images_per_class=None):
    from pathlib import Path
    val_dir = Path(val_dir)
    annotation_file = val_dir / "val_annotations.txt"
    image_dir = val_dir / "images"
    selected = set(selected_classes) if selected_classes else None
    grouped, counts = {}, {}

    with annotation_file.open("r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            filename, label = parts[0], parts[1]
            if selected is not None and label not in selected:
                continue
            if max_images_per_class is not None and counts.get(label, 0) >= int(max_images_per_class):
                continue
            image = read_image_posix(str(image_dir / filename))
            if image is None:
                continue
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            grouped.setdefault(label, []).append(image)
            counts[label] = counts.get(label, 0) + 1
    return grouped


def save_hdf5_train_val(train_dict, val_dict, filename, dataset_id,
                        chunk_images=None, compression=None, compression_opts=None):
    from pathlib import Path
    filename = Path(filename)
    filename.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(filename, "w") as h5:
        h5.attrs["dataset_id"] = dataset_id
        h5.attrs["source_dataset"] = "TinyImageNet"
        h5.attrs["color_mode"] = "RGB"
        h5.attrs["image_height"] = 64
        h5.attrs["image_width"] = 64
        h5.attrs["channels"] = 3
        h5.attrs["chunk_images"] = -1 if chunk_images is None else int(chunk_images)
        h5.attrs["compression"] = "none" if compression is None else str(compression)
        h5.attrs["compression_opts"] = "none" if compression_opts is None else str(compression_opts)

        for split_name, data in (("train", train_dict), ("val", val_dict)):
            if data is None:
                continue

            split = h5.create_group(split_name)
            for label in sorted(data):
                arr = np.asarray(data[label], dtype=np.uint8)
                if len(arr) == 0:
                    continue
                kwargs = {}
                if chunk_images is not None:
                    kwargs["chunks"] = (
                        min(int(chunk_images), len(arr)),
                        arr.shape[1], arr.shape[2], arr.shape[3]
                    )
                if compression is not None:
                    kwargs["compression"] = compression
                    if compression_opts is not None:
                        kwargs["compression_opts"] = compression_opts
                split.create_group(label).create_dataset("images", data=arr, **kwargs)

    return filename.stat().st_size


def read_hdf5_split(filename, split_name, class_names):
    images, labels = [], []
    label_map = {name: i for i, name in enumerate(class_names)}
    with h5py.File(filename, "r") as h5:
        split = h5[split_name]
        for name in class_names:
            if name not in split:
                continue
            arr = split[name]["images"][:]
            images.extend(arr)
            labels.extend([label_map[name]] * len(arr))
    return np.asarray(images), np.asarray(labels, dtype=np.int64)


def inspect_hdf5_dataset_info(filename):
    """
    Reconstruct logical TRAIN/VAL dataset information directly
    from an existing DeepTuneIO-Training HDF5 file.

    This function inspects HDF5 metadata only. It does not
    materialize image arrays in memory.
    """
    filename = Path(filename)

    if not filename.exists():
        raise FileNotFoundError(filename)

    with h5py.File(filename, "r") as f:

        if "train" not in f:
            raise ValueError(
                "El HDF5 debe contener el grupo 'train'."
            )

        train_classes = sorted(f["train"].keys())

        has_val = "val" in f

        val_classes = (
            sorted(f["val"].keys())
            if has_val
            else []
        )


        if not train_classes:
            raise ValueError(
                "El grupo TRAIN no contiene clases."
            )

        if has_val and train_classes != val_classes:
            raise ValueError(
                "Las clases TRAIN y VAL no coinciden."
            )

        class_names = train_classes

        train_counts = []
        val_counts = []

        reference_shape = None
        reference_dtype = None

        # ----------------------------------------------------
        # TRAIN
        # ----------------------------------------------------

        for class_name in class_names:

            group = f["train"][class_name]

            if "images" not in group:
                raise ValueError(
                    f"Falta dataset images en "
                    f"train/{class_name}"
                )

            ds = group["images"]

            if ds.ndim != 4:
                raise ValueError(
                    f"Forma inesperada en train/{class_name}/images: "
                    f"{ds.shape}"
                )

            current_shape = tuple(ds.shape[1:])
            current_dtype = str(ds.dtype)

            if reference_shape is None:
                reference_shape = current_shape
                reference_dtype = current_dtype

            if current_shape != reference_shape:
                raise ValueError(
                    "Las imágenes TRAIN no tienen forma uniforme."
                )

            if current_dtype != reference_dtype:
                raise ValueError(
                    "Las imágenes TRAIN no tienen dtype uniforme."
                )

            train_counts.append(int(ds.shape[0]))
        # ----------------------------------------------------
        # VAL
        # ----------------------------------------------------

        if has_val:
            for class_name in class_names:

                group = f["val"][class_name]

                if "images" not in group:
                    raise ValueError(
                        f"Falta dataset images en "
                        f"val/{class_name}"
                    )

                ds = group["images"]

                if tuple(ds.shape[1:]) != reference_shape:
                    raise ValueError(
                        "TRAIN y VAL no tienen la misma forma de imagen."
                    )

                if str(ds.dtype) != reference_dtype:
                    raise ValueError(
                        "TRAIN y VAL no tienen el mismo dtype."
                    )

                val_counts.append(int(ds.shape[0]))


        height, width, channels = reference_shape

        color_mode = f.attrs.get(
            "color_mode",
            "RGB" if channels == 3 else "unknown",
        )

        if isinstance(color_mode, bytes):
            color_mode = color_mode.decode("utf-8")

        # ----------------------------------------------------
        # Información compatible con inspect_image_dictionary
        # ----------------------------------------------------

        train_info = {
            "num_classes": len(class_names),
            "class_names": class_names,
            "uniform_images_per_class": (
                len(set(train_counts)) == 1
            ),
            "images_per_class": (
                train_counts[0]
                if len(set(train_counts)) == 1
                else None
            ),
            "total_images": sum(train_counts),
            "image_height": int(height),
            "image_width": int(width),
            "channels": int(channels),
            "color_mode": str(color_mode),
            "dtype": reference_dtype,
            "source_shape": (
                int(height),
                int(width),
                int(channels),
            ),
        }

        if has_val:
            val_info = {
                "num_classes": len(class_names),
                "class_names": class_names,
                "uniform_images_per_class": (
                    len(set(val_counts)) == 1
                ),
                "images_per_class": (
                    val_counts[0]
                    if len(set(val_counts)) == 1
                    else None
                ),
                "total_images": sum(val_counts),
                "image_height": int(height),
                "image_width": int(width),
                "channels": int(channels),
                "color_mode": str(color_mode),
                "dtype": reference_dtype,
                "source_shape": (
                    int(height),
                    int(width),
                    int(channels),
                ),
            }
        else:
            val_info = None


        stored_dataset_id = f.attrs.get(
            "dataset_id",
            None,
        )

        if isinstance(stored_dataset_id, bytes):
            stored_dataset_id = stored_dataset_id.decode("utf-8")

    return train_info, val_info, stored_dataset_id

