from __future__ import annotations
from pathlib import Path
import pandas as pd

def _jid_col(df):
    for c in ['job_id','JobID','Jobid','jobid']:
        if c in df.columns:return c
    return None

def diagnose(*, indexer_csv, matrix_csv, consolidated_csv, performance_shared_csv, performance_reload_csv, nodes, processes):
    idx=pd.read_csv(indexer_csv); mat=pd.read_csv(matrix_csv); con=pd.read_csv(consolidated_csv)
    ps=pd.read_csv(performance_shared_csv); pr=pd.read_csv(performance_reload_csv)
    def filt(df):
        n=next((c for c in ['nodes','Nodes'] if c in df.columns),None); p=next((c for c in ['processes','Processes','process_io'] if c in df.columns),None)
        return df[(pd.to_numeric(df[n],errors='coerce')==nodes)&(pd.to_numeric(df[p],errors='coerce')==processes)].copy() if n and p else df.iloc[0:0].copy()
    return {'indexer':filt(idx),'matrix':filt(mat),'consolidated':filt(con),'performance_shared':filt(ps),'performance_reload':filt(pr)}
