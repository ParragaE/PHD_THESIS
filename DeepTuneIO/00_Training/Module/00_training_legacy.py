"""DeepTuneIO Analyzer - Module 00: Training."""
import argparse, csv
from pathlib import Path
from Training.processor import process_training

def _safe(x):
    return str(x).replace(" ", "_").replace("/", "-").replace("\\", "-")

def save_metrics_csv(metrics, data_dir):
    data_dir = Path(data_dir); data_dir.mkdir(parents=True, exist_ok=True)
    keys = ("application","dataset_group","scenario","data_format","access_mode","read_strategy")
    stem = "training_" + "_".join(_safe(metrics[k]) for k in keys)
    path = data_dir / f"{stem}.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(metrics.keys()))
        w.writeheader(); w.writerow(metrics)
    return path

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--execution-mode", default="local", choices=["local","hpc"])
    p.add_argument("--application", default="DeepTuneIO_Training")
    p.add_argument("--dataset-group", default="TinyImageNet")
    p.add_argument("--scenario", default="local_test")
    p.add_argument("--filesystem", default="local")
    p.add_argument("--data-format", required=True, choices=["jpeg","hdf5","tfrecord","npz"])
    p.add_argument("--action", required=True, choices=["transform","train","both"])
    p.add_argument("--folder-path", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--data-dir", default="Data")
    p.add_argument("--input-filename")
    p.add_argument("--access-mode", default="individual", choices=["individual","shared"])
    p.add_argument("--read-strategy", default="full", choices=["full","batch"])
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--epochs", type=int, default=1)
    p.add_argument("--max-classes", type=int)
    p.add_argument("--max-images-per-class", type=int)
    p.add_argument("--no-save-csv", action="store_true")
    a = p.parse_args(argv)

    metrics = process_training(
        data_format=a.data_format, folder_path=a.folder_path, action=a.action,
        output_dir=a.output_dir, input_filename=a.input_filename,
        access_mode=a.access_mode, read_strategy=a.read_strategy,
        batch_size=a.batch_size, epochs=a.epochs,
        execution_mode=a.execution_mode, application=a.application,
        dataset_group=a.dataset_group, scenario=a.scenario,
        filesystem=a.filesystem, max_classes=a.max_classes,
        max_images_per_class=a.max_images_per_class,
    )
    if not a.no_save_csv:
        print("CSV:", save_metrics_csv(metrics, a.data_dir))
    return metrics

if __name__ == "__main__":
    main()
