from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deeptuneio.adapters.base import ApplicationAdapter
from deeptuneio.adapters.deepgalaxy import DeepGalaxyAdapter

def test_generic_adapter_no_hardcoded_expected_metrics():
    s = ApplicationAdapter().application_metrics_status({"summary":{"throughput":1.0}}, [])
    assert s["status"] == "AVAILABLE"
    assert s["expected_metrics"] == []

def test_deepgalaxy_available():
    series=[{"metrics":{"loss":1,"accuracy":.5,"validation_loss":1.1,"validation_accuracy":.4}}]
    s=DeepGalaxyAdapter().application_metrics_status({},series)
    assert s["status"]=="AVAILABLE" and s["missing_metrics"]==[]

def test_deepgalaxy_partial():
    series=[{"metrics":{"loss":1,"accuracy":.5,"validation_loss":1.1}}]
    s=DeepGalaxyAdapter().application_metrics_status({},series)
    assert s["status"]=="PARTIAL"
    assert s["available"] is True
    assert s["missing_metrics"]==["validation_accuracy"]

def test_deepgalaxy_unavailable():
    s=DeepGalaxyAdapter().application_metrics_status({},[])
    assert s["status"]=="UNAVAILABLE"
    assert s["available"] is False
