from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import DeepTuneIO_Indexer_v10 as mainmod


def test_build_semantic_signatures_is_imported():
    assert hasattr(mainmod, "build_semantic_signatures")
    assert callable(mainmod.build_semantic_signatures)
