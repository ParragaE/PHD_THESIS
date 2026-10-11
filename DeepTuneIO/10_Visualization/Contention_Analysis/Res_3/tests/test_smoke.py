import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"Module"))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"Access_Pattern"/"Module"))
from contention_heatmaps import build_overlap_rectangles

def test_overlap():
    events=pd.DataFrame({"process_io":[0,1],"start_time_s":[0,.5],"end_time_s":[2,1.5],"offset_bytes":[0,5],"request_size_bytes":[10,10]})
    pairs=pd.DataFrame({"case":["B_partial"],"event_a":[0],"event_b":[1],"process_a":[0],"process_b":[1],"file_a":["f"],"file_b":["f"],"start_s":[.5],"end_s":[1.5]})
    out=build_overlap_rectangles(pairs,events)
    assert len(out)==1 and out.iloc[0].o0==5 and out.iloc[0].o1==10
