"""CNN model and portable local/HPC training for DeepTuneIO Training."""
import time
import numpy as np
import tensorflow as tf


def get_horovod(execution_mode="local"):
    """Import and initialize Horovod only in HPC mode."""
    if execution_mode.lower() != "hpc":
        return None
    try:
        import horovod.tensorflow.keras as hvd
    except ImportError as exc:
        raise RuntimeError(
            "EXECUTION_MODE='hpc' requiere horovod.tensorflow.keras."
        ) from exc
    if not hvd.is_initialized():
        hvd.init()
    return hvd


def build_model(num_classes, input_shape=(64, 64, 3)):
    return tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=input_shape),
        tf.keras.layers.Conv2D(32, (3, 3), activation="relu"),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation="relu"),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])


def build_and_train_model(images, labels, num_classes, epochs=5,
                          batch_size=32, execution_mode="local"):
    start_time = time.time()
    hvd = get_horovod(execution_mode)

    print(f"Shape de images: {images.shape}")
    print(f"Shape de labels: {labels.shape}")

    if labels.size:
        assert np.min(labels) >= 0 and np.max(labels) < num_classes

    model = build_model(num_classes, tuple(images.shape[1:]))
    optimizer = tf.keras.optimizers.Adam()
    callbacks = []
    verbose = 1

    if hvd is not None:
        optimizer = hvd.DistributedOptimizer(optimizer)
        callbacks = [
            hvd.callbacks.BroadcastGlobalVariablesCallback(0),
            hvd.callbacks.MetricAverageCallback(),
        ]
        verbose = 1 if hvd.rank() == 0 else 0

    model.compile(
        optimizer=optimizer,
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
        run_eagerly=True,
    )
    history = model.fit(
        images,
        labels,
        batch_size=batch_size,
        epochs=epochs,
        callbacks=callbacks,
        verbose=verbose,
    )

    training_time = time.time() - start_time
    if hvd is None or hvd.rank() == 0:
        print(f"Tiempo de entrenamiento: {training_time:.2f} segundos")
        print(f"Historial de entrenamiento: {history.history}")

    return model, history, training_time


def build_and_train_sequence(
    sequence,
    num_classes,
    epochs=5,
    execution_mode="local",
    validation_sequence=None,
):
    """Train directly from a batch-producing Sequence."""
    start_time = time.time()
    hvd = get_horovod(execution_mode)

    if len(sequence) == 0:
        raise ValueError("La secuencia HDF5 no contiene muestras.")

    first_images, _ = sequence[0]
    model = build_model(num_classes, tuple(first_images.shape[1:]))

    optimizer = tf.keras.optimizers.Adam()
    callbacks = []
    verbose = 1
    if hvd is not None:
        optimizer = hvd.DistributedOptimizer(optimizer)
        callbacks = [
            hvd.callbacks.BroadcastGlobalVariablesCallback(0),
            hvd.callbacks.MetricAverageCallback(),
        ]
        verbose = 1 if hvd.rank() == 0 else 0

    model.compile(
        optimizer=optimizer,
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
        run_eagerly=True,
    )
    history = model.fit(
        sequence,
        validation_data=validation_sequence,
        epochs=epochs,
        callbacks=callbacks,
        verbose=verbose,
    )
    training_time = time.time() - start_time

    if hvd is None or hvd.rank() == 0:
        print(f"Tiempo de entrenamiento: {training_time:.2f} segundos")
        print(f"Historial de entrenamiento: {history.history}")

    return model, history, training_time


def summarize_history(history):
    h = history.history
    def last(k): return float(h[k][-1]) if h.get(k) else None
    return {
        "train_loss_final": last("loss"),
        "train_accuracy_final": last("accuracy"),
        "train_loss_best": float(min(h["loss"])) if h.get("loss") else None,
        "train_accuracy_best": float(max(h["accuracy"])) if h.get("accuracy") else None,
        "val_loss_final": last("val_loss"),
        "val_accuracy_final": last("val_accuracy"),
        "val_loss_best": float(min(h["val_loss"])) if h.get("val_loss") else None,
        "val_accuracy_best": float(max(h["val_accuracy"])) if h.get("val_accuracy") else None,
    }


def build_and_train_model_with_validation(
    train_images, train_labels, val_images, val_labels,
    num_classes, epochs=5, batch_size=32, execution_mode="local"
):
    start_time = time.time()
    hvd = get_horovod(execution_mode)
    model = build_model(num_classes, tuple(train_images.shape[1:]))
    optimizer = tf.keras.optimizers.Adam()
    callbacks, verbose = [], 1

    if hvd is not None:
        optimizer = hvd.DistributedOptimizer(optimizer)
        callbacks = [
            hvd.callbacks.BroadcastGlobalVariablesCallback(0),
            hvd.callbacks.MetricAverageCallback(),
        ]
        verbose = 1 if hvd.rank() == 0 else 0

    model.compile(
        optimizer=optimizer,
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
        run_eagerly=True,
    )
    history = model.fit(
        train_images, train_labels,
        validation_data=(val_images, val_labels),
        batch_size=batch_size,
        epochs=epochs,
        callbacks=callbacks,
        verbose=verbose,
    )
    return model, history, time.time() - start_time
