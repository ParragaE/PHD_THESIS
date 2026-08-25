from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Validation.campaign import discover_results

def test_discovers_canonical_npz_file_per_process(tmp_path):
    d=tmp_path/"results"/"Figures"/"Performance"/"Data"; d.mkdir(parents=True)
    p=d/"performance_grouped_dliov1_npz_64bs_lustre_ost_npz_file_per_process.csv"
    p.write_text("nodes,processes,stripe_count\n1,4,1\n")
    got=discover_results(tmp_path, application="DLIOv1", dataset_group="NPZ_64bs", scenario="lustre_ost", file_format=".npz", mode="file_per_process")
    assert got == p

def test_discovers_legacy_tfrecord_file_per_process(tmp_path):
    d=tmp_path/"results"/"Figures"/"Performance"/"Data"; d.mkdir(parents=True)
    p=d/"performance_grouped_file_per_process.csv"
    p.write_text("nodes,processes,stripe_count\n1,4,1\n")
    got=discover_results(tmp_path, application="DLIOv1", dataset_group="TFRecord_1mts_64bs", scenario="lustre_ost", file_format=".tfrecords", mode="file_per_process")
    assert got == p
