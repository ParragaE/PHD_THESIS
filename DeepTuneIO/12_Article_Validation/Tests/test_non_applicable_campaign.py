from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Validation.campaign import dataset_validation_policy

def test_tfrecord_256_is_fig8_validation_ready():
    p=dataset_validation_policy("DLIOv1","TFRecord_256kts_64bs")
    assert p["exact_scalar_validation"] is True
    assert p["figures"] == [8]
