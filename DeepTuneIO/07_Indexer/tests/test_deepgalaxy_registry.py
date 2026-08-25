from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deeptuneio.adapters import AdapterRegistry, DeepGalaxyAdapter


COMMAND = (
    "python dg_train.py --epochs 1 --arch EfficientNetB4 "
    "-f /mnt/lustre/hsm/data/output_bw_512.hdf5 "
    "-d s_* --num-camera 14 -m 0"
)


def test_registry_selects_deepgalaxy():
    registry = AdapterRegistry()
    adapter = registry.select("", COMMAND, "", "")
    assert isinstance(adapter, DeepGalaxyAdapter)


def test_registry_has_single_deepgalaxy_adapter():
    registry = AdapterRegistry()
    count = sum(isinstance(a, DeepGalaxyAdapter) for a in registry.adapters)
    assert count == 1
