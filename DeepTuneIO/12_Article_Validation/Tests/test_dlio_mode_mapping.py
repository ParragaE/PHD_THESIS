from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Validation.campaign import result_access_mode

def test_dlio_multi_maps_to_file_per_process():
    assert result_access_mode("DLIOv1","multi") == "file_per_process"

def test_shared_is_unchanged():
    assert result_access_mode("DLIOv1","shared") == "shared"
    assert result_access_mode("DeepGalaxy","shared_reload_shuffle") == "shared_reload_shuffle"
