from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/"Module"
sys.path.insert(0,str(ROOT))
from Article_Reference.article01_extractor import extract_dlio_performance

def test_fig8_explicit_figure_labels_are_present():
    rows,_=extract_dlio_performance([])
    f8=[r for r in rows if r["figure"]==8]
    assert len(f8)==12
    assert {r["source_type"] for r in f8}=={"ARTICLE_FIGURE"}
    bw=[r for r in f8 if r["metric"]=="bandwidth"]
    iops=[r for r in f8 if r["metric"]=="iops"]
    tio=[r for r in f8 if r["metric"]=="io_time"]
    assert [r["reference_value"] for r in bw]==[325.2,566.3,5626.9,21157.5,21429.8]
    assert [r["reference_value"] for r in iops]==[1304.7,2265.1,22509.2,84638.8,85101.5]
    assert [r["reference_value"] for r in tio]==[301.7,4.7]
