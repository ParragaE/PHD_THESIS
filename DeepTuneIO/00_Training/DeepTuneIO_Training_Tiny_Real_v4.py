#!/usr/bin/env python3
"""
DeepTuneIO_Training_Tiny_Real_v4.py

Orquestador principal de DeepTuneIO-Training v4 para Tiny ImageNet.

Permite ejecutar el mismo núcleo en:
  - local: full, batch
  - HPC/Horovod: full_shared, distributed_shared

La configuración experimental se recibe por argumentos de línea de comandos.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd


def parse_args():
    p = argparse.ArgumentParser(
        description="DeepTuneIO-Training v4 - Tiny ImageNet (LOCAL/HPC)"
    )

    # Entorno
    p.add_argument(
        "--execution-mode",
        choices=["local", "hpc"],
        required=True,
        help="Entorno de ejecución.",
    )
    p.add_argument(
        "--filesystem",
        required=True,
        help="Etiqueta del sistema de archivos: Local, Lustre_1OST, Lustre_4OST, NFS, etc.",
    )
    p.add_argument(
        "--read-strategy",
        choices=["full", "batch", "full_shared", "distributed_shared", "direct"],
        required=True,
        help="Estrategia de lectura HDF5.",
    )

    p.add_argument("--data-format", choices=["HDF5", "JPEG"], default="HDF5")

    # Dataset / resultados
    p.add_argument("--train-dir", type=Path, required=True)
    p.add_argument("--val-dir", type=Path, required=True)
    p.add_argument("--dataset-output-root", type=Path, required=True)
    p.add_argument("--results-root", type=Path, required=True)

    # Workload
    p.add_argument("--num-classes", type=int, default=10)
    p.add_argument("--images-per-class", type=int, default=100)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--dataset-scope", choices=["train-val", "train-only"], default="train-val", help="Dataset utilizado: train-val o train-only.",)

    p.add_argument(
        "-go",
        "--generate-only",
        action="store_true",
        help="Genera o reutiliza y valida el dataset transformado, y termina sin ejecutar lectura de entrenamiento ni entrenamiento.",
    )

    # Identidad de ejecución
    p.add_argument(
        "--run-id",
        required=True,
        help="Identificador de la repetición, por ejemplo run001.",
    )

    # Layout físico HDF5
    p.add_argument(
        "--chunk-images",
        type=int,
        default=None,
        help="Número de imágenes por chunk. Omitir para contiguous.",
    )
    p.add_argument(
        "--compression",
        default=None,
        help="Compresión HDF5, por ejemplo gzip. Omitir para none.",
    )
    p.add_argument(
        "--compression-opts",
        type=int,
        default=None,
        help="Nivel/opción de compresión HDF5.",
    )

    return p.parse_args()


def get_scheduler_job_id():
    for name in ("SLURM_JOB_ID", "PBS_JOBID", "LSB_JOBID", "JOB_ID"):
        value = os.environ.get(name)
        if value:
            return value
    return ""


def derive_access_mode(read_strategy):
    mapping = {
        "full": "individual",
        "batch": "individual",
        "full_shared": "shared",
        "distributed_shared": "shared",
        "direct": "individual",
    }
    return mapping[read_strategy]


def validate_configuration(args):
    if args.data_format == "JPEG":
        allowed = {"direct"}
    elif args.execution_mode == "local":
        allowed = {"full", "batch"}
    else:
        allowed = {"full_shared", "distributed_shared"}

    if args.read_strategy not in allowed:
        raise ValueError(
            f"read_strategy={args.read_strategy!r} no es válida para "
            f"execution_mode={args.execution_mode!r}. "
            f"Permitidas: {sorted(allowed)}"
        )

    if not args.train_dir.exists():
        raise FileNotFoundError(f"TRAIN_DIR no existe: {args.train_dir}")

    if not args.val_dir.exists():
        raise FileNotFoundError(f"VAL_DIR no existe: {args.val_dir}")

    if args.num_classes <= 0:
        raise ValueError("--num-classes debe ser > 0")
    if args.images_per_class <= 0:
        raise ValueError("--images-per-class debe ser > 0")
    if args.epochs <= 0:
        raise ValueError("--epochs debe ser > 0")
    if args.batch_size <= 0:
        raise ValueError("--batch-size debe ser > 0")

    args.dataset_output_root.mkdir(parents=True, exist_ok=True)
    args.results_root.mkdir(parents=True, exist_ok=True)


def build_history_dataframe(metrics, history):
    n_epochs = len(history.get("loss", []))
    rows = []

    for i in range(n_epochs):
        rows.append(
            {
                "dataset_id": metrics.get("dataset_id", ""),
                "experiment_id": metrics.get("experiment_id", ""),
                "run_id": metrics.get("run_id", ""),
                "job_id": metrics.get("job_id", ""),
                "epoch": i + 1,
                "loss": history.get("loss", [None] * n_epochs)[i],
                "accuracy": history.get("accuracy", [None] * n_epochs)[i],
                "val_loss": history.get("val_loss", [None] * n_epochs)[i],
                "val_accuracy": history.get(
                    "val_accuracy", [None] * n_epochs
                )[i],
            }
        )

    return pd.DataFrame(rows)


def save_results(metrics, history_df, results_root, filesystem, run_id):
    data_format = metrics.get("data_format", "HDF5")
    resource_metadata_dir = (
        results_root
        / data_format
        / filesystem
        / "results"
        / "Resource_Metadata"
    )
    training_history_dir = (
        results_root
        / data_format
        / filesystem
        / "results"
        / "Training_History"
    )

    resource_metadata_dir.mkdir(parents=True, exist_ok=True)
    training_history_dir.mkdir(parents=True, exist_ok=True)

    resource_metadata_file = (
        resource_metadata_dir
        / f"{data_format}_{run_id}_Resource_Metadata.csv"
    )
    training_history_file = (
        training_history_dir
        / f"{data_format}_{run_id}_Training_History.csv"
    )

    pd.DataFrame([metrics]).to_csv(resource_metadata_file, index=False)
    history_df.to_csv(training_history_file, index=False)

    return resource_metadata_file, training_history_file


def main():
    args = parse_args()

    # El script puede estar en la raíz v4 o en Module/.
    script_dir = Path(__file__).resolve().parent
    candidate_module_dirs = [
        script_dir / "Module",
        script_dir,
    ]

    module_dir = None
    for candidate in candidate_module_dirs:
        if (candidate / "Training" / "processor_tiny_real.py").exists():
            module_dir = candidate
            break

    if module_dir is None:
        raise FileNotFoundError(
            "No se encontró Module/Training/processor_tiny_real.py "
            f"a partir de {script_dir}"
        )

    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    from Training.processor_tiny_real import run_tiny_real

    validate_configuration(args)

    access_mode = derive_access_mode(args.read_strategy)
    job_id = get_scheduler_job_id()

    print("=" * 78)
    print("DEEPTUNEIO-TRAINING V4")
    print("=" * 78)
    print("Execution mode :", args.execution_mode)
    print("Filesystem     :", args.filesystem)
    print("Data format    :", args.data_format)
    print("Read strategy  :", args.read_strategy)
    print("Access mode    :", access_mode)
    print("Run ID         :", args.run_id)
    print("Job ID         :", job_id if job_id else "(vacío/local)")
    print("Num classes    :", args.num_classes)
    print("Images/class   :", args.images_per_class)
    print("Epochs         :", args.epochs)
    print("Batch size     :", args.batch_size)
    print("Dataset scope  :", args.dataset_scope)
    print("TRAIN          :", args.train_dir)
    print("VAL            :", args.val_dir)
    print("Dataset output :", args.dataset_output_root)
    print("Results root   :", args.results_root)
    print("=" * 78)

    metrics, history, processed_dataset_path = run_tiny_real(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        dataset_output_root=args.dataset_output_root,
        num_classes=args.num_classes,
        images_per_class=args.images_per_class,
        epochs=args.epochs,
        batch_size=args.batch_size,
        chunk_images=args.chunk_images,
        compression=args.compression,
        compression_opts=args.compression_opts,
        filesystem=args.filesystem,
        access_mode=access_mode,
        read_strategy=args.read_strategy,
        execution_mode=args.execution_mode,
        data_format=args.data_format,
        dataset_scope=args.dataset_scope,
        generate_only=args.generate_only,
    )

    # Identidad de ejecución: responsabilidad del orquestador.
    metrics["run_id"] = args.run_id
    metrics["job_id"] = job_id

    if args.execution_mode == "hpc":
        # run_tiny_real() ya inicializó Horovod.
        import horovod.tensorflow.keras as hvd
        rank = hvd.rank()
        size = hvd.size()
    else:
        rank = 0
        size = 1

    history_df = build_history_dataframe(metrics, history)

    # Todos los ranks ejecutan el workload.
    # Solo rank 0 persiste resultados.
    if rank == 0:
        resource_file, history_file = save_results(
            metrics=metrics,
            history_df=history_df,
            results_root=args.results_root,
            filesystem=args.filesystem,
            run_id=args.run_id,
        )
    else:
        resource_file = None
        history_file = None

    required = (
        "dataset_id",
        "experiment_id",
        "run_id",
        "job_id",
        "training_time_s",
        "total_time_s",
    )
    missing = [name for name in required if name not in metrics]
    if missing:
        raise RuntimeError(f"Faltan métricas obligatorias: {missing}")

    print()
    print("=" * 78)
    print("DEEPTUNEIO-TRAINING V4 - EJECUCIÓN COMPLETADA")
    print("=" * 78)
    print("Execution mode :", args.execution_mode)
    print("Filesystem     :", args.filesystem)
    print("Data format    :", args.data_format)
    print("Read strategy  :", args.read_strategy)
    print("Access mode    :", access_mode)
    print("Run ID         :", args.run_id)
    print("Job ID         :", job_id if job_id else "(vacío/local)")
    print("Rank / Size    :", f"{rank}/{size}")
    print("Dataset ID     :", metrics["dataset_id"])
    print("Experiment ID  :", metrics["experiment_id"])
    print("Processed data :", processed_dataset_path)
    print("Total time (s) :", metrics["total_time_s"])

    if rank == 0:
        print("Resource CSV   :", resource_file)
        print("History CSV    :", history_file)
    else:
        print("CSV            : no escritos por este rank")

    print("=" * 78)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
