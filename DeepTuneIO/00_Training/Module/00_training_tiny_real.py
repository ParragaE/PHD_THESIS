
import argparse, csv, os
from pathlib import Path
from Training.processor_tiny_real import run_tiny_real


def get_job_id():
    """
    Return the scheduler JobID when available.

    Priority:
      1. SLURM_JOB_ID
      2. PBS_JOBID
      3. LSB_JOBID
      4. JOB_ID

    Local executions return an empty string.
    """
    scheduler_variables = (
        "SLURM_JOB_ID",
        "PBS_JOBID",
        "LSB_JOBID",
        "JOB_ID",
    )

    for variable in scheduler_variables:
        value = os.environ.get(variable)

        if value:
            return str(value)

    return ""


def save_csvs(metrics, history, resource_metadata_dir, run_id):
    resource_dir = Path(resource_metadata_dir)
    resource_dir.mkdir(parents=True, exist_ok=True)

    experiment_id = metrics["experiment_id"]

    # Execution identity is already attached to metrics
    # by main() before persistence.

    # Short filenames avoid Windows path-length problems while
    # identity remains explicitly stored inside the CSV.
    summary_path = (
        resource_dir
        / f"HDF5_{run_id}_Resource_Metadata.csv"
    )

    with summary_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=list(metrics.keys()),
        )
        writer.writeheader()
        writer.writerow(metrics)

    history_dir = (
        resource_dir.parent
        / "Training_History"
    )

    history_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_path = (
        history_dir
        / f"HDF5_{run_id}_Training_History.csv"
    )

    fields = [
        "dataset_id",
        "experiment_id",
        "run_id",
        "job_id",
        "epoch",
        "loss",
        "accuracy",
        "val_loss",
        "val_accuracy",
    ]

    n = len(history.get("loss", []))

    with history_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as fh:

        writer = csv.DictWriter(
            fh,
            fieldnames=fields,
        )

        writer.writeheader()

        for i in range(n):

            writer.writerow({
                "dataset_id":
                    metrics["dataset_id"],

                "experiment_id":
                    experiment_id,

                "run_id":
                    metrics["run_id"],

                "job_id":
                    metrics["job_id"],

                "epoch":
                    i + 1,

                "loss":
                    history.get(
                        "loss",
                        [None] * n,
                    )[i],

                "accuracy":
                    history.get(
                        "accuracy",
                        [None] * n,
                    )[i],

                "val_loss":
                    history.get(
                        "val_loss",
                        [None] * n,
                    )[i],

                "val_accuracy":
                    history.get(
                        "val_accuracy",
                        [None] * n,
                    )[i],
            })

    return summary_path, history_path


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--train-dir", required=True)
    p.add_argument("--val-dir", required=True)
    p.add_argument("--dataset-output-root", required=True)
    p.add_argument("--resource-metadata-dir", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--num-classes", type=int, default=10)
    p.add_argument("--images-per-class", type=int, default=100)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--filesystem", default="Local")
    p.add_argument("--execution-mode", default="local", choices=["local","hpc"])
    p.add_argument("--access-mode", default="individual", choices=["individual","shared"])
    p.add_argument("--read-strategy", default="full", choices=["full", "full_shared", "distributed_shared", "batch"])
    p.add_argument("--chunk-images", type=int)
    p.add_argument("--compression", choices=["gzip","lzf"])
    p.add_argument("--compression-opts", type=int)
    a = p.parse_args(argv)

    metrics, history, hdf5_path = run_tiny_real(
        train_dir=a.train_dir, val_dir=a.val_dir,
        dataset_output_root=a.dataset_output_root,
        num_classes=a.num_classes, images_per_class=a.images_per_class,
        epochs=a.epochs, batch_size=a.batch_size,
        chunk_images=a.chunk_images,
        compression=a.compression,
        compression_opts=a.compression_opts,
        filesystem=a.filesystem,
        execution_mode=a.execution_mode,
        access_mode=a.access_mode,
        read_strategy=a.read_strategy,
    )

    # Execution identity.
    #
    # dataset_id    -> physical dataset
    # experiment_id -> experimental configuration
    # run_id        -> concrete repetition
    # job_id        -> scheduler job, when available
    metrics["run_id"] = a.run_id
    metrics["job_id"] = get_job_id()

    # Persist shared result files only once.
    #
    # local -> the single process writes the CSV files.
    # hpc   -> every Horovod rank executes the workload,
    #          but only rank 0 writes the shared CSV files.

    should_write_results = True
    rank = 0

    if a.execution_mode == "hpc":
        import horovod.tensorflow.keras as hvd

        # Horovod was initialized inside run_tiny_real().
        rank = hvd.rank()
        should_write_results = (rank == 0)

    if should_write_results:
        summary, history_path = save_csvs(
            metrics,
            history,
            a.resource_metadata_dir,
            a.run_id,
        )

        print("\nDATASET_ID   :", metrics["dataset_id"])
        print("EXPERIMENT_ID:", metrics["experiment_id"])
        print("HDF5         :", hdf5_path)
        print("Metadata CSV :", summary)
        print("History CSV  :", history_path)

    return metrics
