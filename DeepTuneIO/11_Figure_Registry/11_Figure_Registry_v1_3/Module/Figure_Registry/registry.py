from __future__ import annotations
from pathlib import Path
import json, re
from collections import defaultdict
import pandas as pd

FIGURE_EXTENSIONS={'.png','.pdf','.svg'}

ARTICLE01_PERFORMANCE_RULES={
 ('lustre_1ost','shared'):'11',('lustre_1ost','shared_reload_shuffle'):'12',
 ('lustre_2ost','shared'):'13',('lustre_2ost','shared_reload_shuffle'):'14',
 ('lustre_4ost','shared'):'15',('lustre_4ost','shared_reload_shuffle'):'16',
}
ARTICLE01_PERFORMANCE_PANELS={
 '05_bandwidth_vs_io_time':('a','Bandwidth + I/O Time'),
 '06_iops_vs_io_time':('b','IOPS + I/O Time'),
}
ARTICLE01_DLIO_ACCESS_RULES={
 'hdf5_64bs':{'figure':'2','mode':'shared','semantics':'HDF5 shared; sequential offsets; low metadata overhead; regular ~4 MiB data requests.'},
 'npz_64bs':{'figure':'3','mode':'file_per_process','semantics':'NPZ multi-access/file-per-process; sequential pattern, independent files and regular request granularity.'},
 'tfrecord_256kts_64bs':{'figure':'4','mode':'file_per_process','semantics':'TFRecord multi-access/file-per-process; fixed 256 KiB transfer and regular/predictable access.'},
 'tfrecord_1mts_64bs':{'figure':'5','mode':'file_per_process','semantics':'TFRecord multi-access/file-per-process; fixed 1 MiB transfer and fewer I/O operations.'},
}
DLIO_PANELS={
 ('03_temporal_pattern',4):('a','Temporal I/O pattern — 4 processes'),
 ('04_spatial_pattern_by_process',4):('b','Spatial I/O pattern — 4 processes'),
 ('03_temporal_pattern',48):('c','Temporal I/O pattern — 48 processes'),
 ('04_spatial_pattern_by_process',48):('d','Spatial I/O pattern — 48 processes'),
}
DG_PANELS={
 ('03_temporal_pattern',4):('a','Temporal I/O pattern — 4 processes'),
 ('04_spatial_pattern_by_process',4):('b','Spatial I/O pattern — 4 processes'),
 ('03_temporal_pattern',64):('c','Temporal I/O pattern — 64 processes'),
 ('04_spatial_pattern_by_process',64):('d','Spatial I/O pattern — 64 processes'),
}

def _safe_json(v):
    if isinstance(v,dict): return v
    if v is None or (isinstance(v,float) and pd.isna(v)): return {}
    try: return json.loads(str(v))
    except Exception: return {}

def _normalize_format(v):
    s=str(v or '').strip().lower().lstrip('.')
    return {'h5':'hdf5','hdf5':'hdf5','npz':'npz','tfrecords':'tfrecord','tfrecord':'tfrecord'}.get(s,s)

def _normalize_mode_from_matrix_row(row):
    app=str(row.get('application','')).strip().lower()
    merged={**_safe_json(row.get('experiment_configuration_signature')),**_safe_json(row.get('application_configuration_signature'))}
    strategy=str(merged.get('access_strategy','')).strip().lower()
    if strategy=='shared': return 'shared'
    if strategy in {'shared_reload_shuffle','shared+reload','shared_reload'}: return 'shared_reload_shuffle'
    access=str(merged.get('access_mode','')).strip().lower()
    if access=='shared': return 'shared'
    if access in {'multi','file_per_process','file per process','independent'}: return 'file_per_process'
    if access=='shared_reload_shuffle': return 'shared_reload_shuffle'
    dlm=merged.get('data_loading_mode')
    if 'deepgalaxy' in app:
        if str(dlm)=='0': return 'shared'
        if str(dlm)=='1': return 'shared_reload_shuffle'
    return 'unknown'

def discover_experiment_matrices(root):
    r=Path(root)/'results'; return sorted(r.rglob('experiment_matrix*.csv')) if r.exists() else []

def load_experiment_jobs(root):
    rows=[]
    for path in discover_experiment_matrices(root):
        try: df=pd.read_csv(path)
        except Exception: continue
        for _,row in df.iterrows():
            jobs=[x.strip() for x in str(row.get('job_ids','')).split(';') if x.strip()]
            for rep,tok in enumerate(jobs,1):
                try: jid=int(float(tok))
                except Exception: continue
                rows.append({'job_id':jid,'configuration_id':row.get('configuration_id',''),'replicate':rep,
                    'application':row.get('application',''),'nodes':row.get('nodes',pd.NA),'processes':row.get('processes',pd.NA),
                    'ppn':row.get('ppn',pd.NA),'data_loading_mode':_normalize_mode_from_matrix_row(row),
                    'filesystem':row.get('filesystem',''),'stripe_count':row.get('stripe_count',pd.NA),
                    'stripe_size_bytes':row.get('stripe_size_bytes',pd.NA),'file_format':_normalize_format(row.get('file_format','')),
                    'operation_mode':row.get('operation_mode',''),'matrix_source':str(path)})
    if not rows: return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates('job_id',keep='last').sort_values('job_id').reset_index(drop=True)

def discover_figures(root):
    r=Path(root)/'results'
    if not r.exists(): return []
    return sorted(p for p in r.rglob('*') if p.is_file() and p.suffix.lower() in FIGURE_EXTENSIONS and any(t in str(p).lower() for t in ('figures','visualization','access_pattern')))

def group_logical_figures(paths):
    g=defaultdict(dict)
    for p in paths: g[str(p.with_suffix('')).lower()][p.suffix.lower().lstrip('.')]=p
    out=[]
    for k in sorted(g):
        f=g[k]; rep=f.get('pdf') or f.get('png') or f.get('svg') or next(iter(f.values()))
        out.append({'representative':rep,'pdf':f.get('pdf'),'png':f.get('png'),'svg':f.get('svg'),'formats':';'.join(sorted(f))})
    return out

def discover_json_manifests(root):
    r=Path(root)/'results'; return sorted(p for p in r.rglob('*.json') if 'manifest' in p.name.lower()) if r.exists() else []

def load_manifests(root):
    out=[]
    for p in discover_json_manifests(root):
        try: d=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        if isinstance(d,dict): d['_manifest_path']=str(p); out.append(d)
    return out

def _manifest_figure_index(manifests):
    idx={}
    for m in manifests:
        c=[]
        for k in ('figures','figures_and_products','created','products'):
            if isinstance(m.get(k),list): c.extend(m[k])
        for item in c:
            p=Path(str(item)); idx[str(p).lower()]=m; idx[p.name.lower()]=m; idx[str(p.with_suffix('')).lower()]=m
    return idx

def _manifest_for_figure(p,idx): return idx.get(str(p).lower()) or idx.get(str(p.with_suffix('')).lower()) or idx.get(p.name.lower()) or {}

def _job_id_from_access_path(p):
    for part in p.parts:
        m=re.fullmatch(r'job[_-](\d+)',str(part),flags=re.I)
        if m: return int(m.group(1))
    return None

def _manifest_job_ids(m):
    vals=[]
    for k in ('job_id','job_ids'):
        if m.get(k) is not None: vals.append(m[k])
    md=m.get('metadata',{})
    if isinstance(md,dict):
        for k in ('job_id','job_ids'):
            if md.get(k) is not None: vals.append(md[k])
    out=[]
    for v in vals:
        toks=v if isinstance(v,list) else re.split(r'[;,\s]+',str(v))
        for t in toks:
            try: out.append(int(float(t)))
            except Exception: pass
    return sorted(set(out))

def _infer_family(p):
    s=str(p).lower()
    if 'access_pattern' in s:return 'access_pattern'
    if 'performance' in s:return 'performance'
    return 'visualization'

def _infer_mode_from_path(p):
    parts=[str(x).lower() for x in p.parts]
    if 'shared_reload_shuffle' in parts:return 'shared_reload_shuffle'
    if 'shared' in parts:return 'shared'
    if 'file_per_process' in parts:return 'file_per_process'
    return ''

def _metrics_for_figure(p):
    n=p.stem.lower()
    if 'spatial_pattern_by_process' in n:return 'I/O Process','File Offset','Request Size'
    if 'spatial_temporal_3d' in n:return 'I/O Process / Operation Order','File Offset','Request Size'
    if 'temporal_pattern' in n:return 'Start Time','File Offset','Request Size'
    if 'spatial_pattern' in n:return 'Operation Order','File Offset','Request Size'
    if 'bandwidth_vs_io_time' in n:return 'Configuration','Bandwidth + I/O Time',''
    if 'iops_vs_io_time' in n:return 'Configuration','IOPS + I/O Time',''
    if 'bandwidth' in n:return 'Configuration','Bandwidth',''
    if 'iops' in n:return 'Configuration','IOPS',''
    if 'execution_time' in n:return 'Configuration','Execution Time',''
    return '','',''

def _unique_paths(values):
    """Return ordered unique non-empty path strings."""
    return list(dict.fromkeys(
        str(v) for v in values
        if v is not None and str(v).strip()
    ))


def _filter_files_by_job_ids(files, job_ids):
    """
    Keep only files belonging to the selected JobID(s).

    This is intentionally conservative: a campaign-level source file is not
    considered direct provenance unless its path/name contains one of the
    selected JobIDs.
    """
    if not job_ids:
        return []

    tokens = {str(int(j)) for j in job_ids}

    selected = []

    for value in files:
        path_str = str(value)

        if any(job_id in path_str for job_id in tokens):
            selected.append(path_str)

    return _unique_paths(selected)


def _local_access_pattern_sources(figure_path: Path):
    """
    Discover the immediate data products used by an access-pattern figure.

    The figure lives inside:
        .../Figures/Access_Pattern/job_<JOBID>/

    Therefore only files from that same directory are direct figure inputs.
    """
    folder = figure_path.parent

    candidates = [
        folder / "access_pattern_events_normalized.csv",
        folder / "access_pattern_summary.csv",
    ]

    return [
        str(path)
        for path in candidates
        if path.exists()
    ]



def _source_files_from_manifest(m):
    c=[]
    for k in ('selected_source_event_csvs','source_file','source','input_csv','normalized_events_csv','summary_csv','consolidated_csv','grouped_csv'):
        v=m.get(k)
        if isinstance(v,list): c.extend(str(x) for x in v if x)
        elif v: c.append(str(v))
    for k in ('source_event_csvs','source_files','grouped_files'):
        if isinstance(m.get(k),list): c.extend(str(x) for x in m[k] if x)
    return list(dict.fromkeys(c))

def _find_grouped_csv_for_performance_figure(path,root):
    mode=_infer_mode_from_path(path); r=Path(root)/'results'; c=sorted(r.rglob('performance_grouped_*.csv')) if r.exists() else []
    if not c:return None
    if mode:
        exact=[p for p in c if p.stem.lower()==f'performance_grouped_{mode}'.lower()]
        if exact:return exact[-1]
        mm=[p for p in c if mode in p.stem.lower()]
        if mm:return mm[-1]
    return c[-1]

def _configs_from_grouped_csv(path):
    if path is None:return set()
    try:df=pd.read_csv(path)
    except Exception:return set()
    out=set()
    if {'nodes','processes'}.issubset(df.columns):
        for n,p in zip(pd.to_numeric(df.nodes,errors='coerce'),pd.to_numeric(df.processes,errors='coerce')):
            if pd.notna(n) and pd.notna(p):out.add((int(n),int(p)))
    return out

def _select_performance_jobs(jobs,mode,configs):
    if jobs.empty:return jobs
    out=jobs.copy()
    if mode:out=out[out.data_loading_mode.astype(str).str.lower().eq(mode.lower())]
    if configs:
        mask=[(int(n),int(p)) in configs if pd.notna(n) and pd.notna(p) else False for n,p in zip(out.nodes,out.processes)]
        out=out.loc[mask]
    return out.copy()

def _join_values(series,numeric=False):
    if series is None:return ''
    vals=pd.Series(series).dropna().tolist()
    if numeric:
        clean=[]
        for v in vals:
            try:
                f=float(v);clean.append(int(f) if f.is_integer() else f)
            except Exception:pass
        vals=clean
    return ';'.join(str(v) for v in sorted(set(vals),key=lambda x:(str(type(x)),str(x))))

def _single_int(v):
    toks=[x.strip() for x in str(v or '').split(';') if x.strip()]
    if len(toks)!=1:return None
    try:return int(float(toks[0]))
    except Exception:return None

def _base(row):
    return {'article_id':'Article_01_Parallel_IO_Analysis','article_figure':'','article_panel':'','article_caption_role':'',
      'article_reference_type':'','article_validation_family':'','article_expected_semantics':'','mapping_status':'UNMAPPED',
      'mapping_method':'','validation_status':row.get('validation_status','PENDING') or 'PENDING','validation_method':''}

def map_article01_row(row):
    r=_base(row); app=str(row.get('application','')).strip().lower(); family=str(row.get('visualization_family','')).strip().lower(); logical=str(row.get('logical_figure','')).strip().lower(); mode=str(row.get('data_loading_mode','')).strip().lower(); proc=_single_int(row.get('processes')); scenario=str(row.get('scenario','')).strip().lower()
    if app in {'dliov1','dlio'}:
        rule=ARTICLE01_DLIO_ACCESS_RULES.get(str(row.get('dataset_group','')).strip().lower())
        if not rule:return r
        if family!='access_pattern':return r
        if mode!=rule['mode']:
            r.update(mapping_status='NOT_IN_ARTICLE',mapping_method=f"Dataset expects {rule['mode']}; observed {mode or 'unknown'}",validation_status='NOT_IN_ARTICLE');return r
        panel=DLIO_PANELS.get((logical,proc))
        if panel:
            r.update(article_figure=rule['figure'],article_panel=panel[0],article_caption_role=panel[1],article_reference_type='STRUCTURAL_REFERENCE',article_validation_family='access_pattern',article_expected_semantics=rule['semantics'],mapping_status='MATCHED_RULE',mapping_method=f"Article01 DLIO rule: dataset={row.get('dataset_group')}, mode={mode}, processes={proc}, logical={logical}",validation_status='PENDING_STRUCTURAL_VALIDATION',validation_method='DXT_STRUCTURAL_AND_PROVENANCE');return r
        r.update(mapping_status='NOT_IN_ARTICLE',mapping_method=f"Article 01 Figure {rule['figure']} maps only temporal/spatial 4P and 48P views",validation_status='NOT_IN_ARTICLE');return r
    if app=='deepgalaxy':
        if family=='access_pattern':
            panel=DG_PANELS.get((logical,proc))
            if mode=='shared' and panel:
                r.update(article_figure='10',article_panel=panel[0],article_caption_role=panel[1],article_reference_type='STRUCTURAL_REFERENCE',article_validation_family='access_pattern',article_expected_semantics='DeepGalaxy shared HDF5: irregular spatial distribution, small/heterogeneous requests, and more interleaved temporal behavior at scale.',mapping_status='MATCHED_RULE',mapping_method=f'Article01 Fig10 rule: shared, {proc}P, {logical}',validation_status='PENDING_STRUCTURAL_VALIDATION',validation_method='DXT_STRUCTURAL_AND_PROVENANCE');return r
            r.update(mapping_status='NOT_IN_ARTICLE',mapping_method='Auxiliary DeepGalaxy access-pattern product',validation_status='NOT_IN_ARTICLE');return r
        if family=='performance':
            fig=ARTICLE01_PERFORMANCE_RULES.get((scenario,mode));panel=ARTICLE01_PERFORMANCE_PANELS.get(logical)
            if fig and panel:
                r.update(article_figure=fig,article_panel=panel[0],article_caption_role=panel[1],article_reference_type='SCALAR_REFERENCE',article_validation_family='performance',mapping_status='MATCHED_RULE',mapping_method=f'Article01 performance rule: scenario={scenario}, mode={mode}, logical={logical}');return r
            r.update(mapping_status='NOT_IN_ARTICLE',mapping_method='Auxiliary performance product',validation_status='NOT_IN_ARTICLE');return r
    return r

def apply_article_mapping(df,article_id='Article_01_Parallel_IO_Analysis'):
    out=df.copy();fields=['article_id','article_figure','article_panel','article_caption_role','article_reference_type','article_validation_family','article_expected_semantics','mapping_status','mapping_method','validation_status','validation_method']
    for f in fields:
        if f not in out.columns:out[f]=''
    for i,row in out.iterrows():
        for k,v in map_article01_row(row.to_dict()).items():out.at[i,k]=v
    return out

def build_article_mapping_audit(df):
    cols=['figure_id','application','dataset_group','logical_figure','scenario','data_loading_mode','job_ids','nodes','processes','article_figure','article_panel','article_caption_role','article_reference_type','article_validation_family','mapping_status','provenance_status','validation_status','validation_method']
    return df[[c for c in cols if c in df.columns]].copy()

def build_registry(campaign_root, application, dataset_group, scenario):
    root = Path(campaign_root)

    logical = group_logical_figures(discover_figures(root))
    manifests = load_manifests(root)
    midx = _manifest_figure_index(manifests)
    jobs = load_experiment_jobs(root)

    rows = []

    for i, item in enumerate(logical, 1):

        fig = item["representative"]
        family = _infer_family(fig)
        manifest = _manifest_for_figure(fig, midx)
        mode = _infer_mode_from_path(fig)

        # ------------------------------------------------------------
        # Provenance layers
        # ------------------------------------------------------------

        campaign_sources = _source_files_from_manifest(manifest)

        sources = []
        upstream_sources = []

        selected = pd.DataFrame()
        product = ""

        # ============================================================
        # ACCESS PATTERN
        # ============================================================

        if family == "access_pattern":

            product = "DXT"

            # --------------------------------------------------------
            # Resolve JobID represented by this figure
            # --------------------------------------------------------

            ids = []

            path_job = _job_id_from_access_path(fig)

            if path_job is not None:
                ids.append(path_job)

            # Only use manifest JobIDs if path does not already
            # identify the experiment.
            if not ids:
                ids.extend(_manifest_job_ids(manifest))

            ids = sorted(set(ids))

            # --------------------------------------------------------
            # Resolve experiment metadata
            # --------------------------------------------------------

            if ids and not jobs.empty:
                selected = jobs[
                    jobs.job_id.isin(ids)
                ].copy()

            # --------------------------------------------------------
            # Direct figure sources
            # --------------------------------------------------------
            #
            # These are the files directly consumed by the
            # visualization for THIS JobID.
            # --------------------------------------------------------

            direct_candidates = [
                fig.parent / "access_pattern_events_normalized.csv",
                fig.parent / "access_pattern_summary.csv",
            ]

            sources = [
                str(path)
                for path in direct_candidates
                if path.exists()
            ]

            # --------------------------------------------------------
            # Local visualization manifest
            # --------------------------------------------------------

            lm = (
                fig.parent /
                "access_pattern_visualization_manifest.json"
            )

            local = {}

            if lm.exists():
                try:
                    local = json.loads(
                        lm.read_text(encoding="utf-8")
                    )
                except Exception:
                    local = {}

            # Modern manifests may explicitly declare which
            # event CSVs generated the figure.
            selected_event_csvs = local.get(
                "selected_source_event_csvs",
                []
            )

            if isinstance(selected_event_csvs, list):
                sources.extend(
                    str(v)
                    for v in selected_event_csvs
                    if v
                )

            sources = list(dict.fromkeys(sources))

            # --------------------------------------------------------
            # Upstream DXT provenance
            # --------------------------------------------------------
            #
            # The manifests may contain all DXT files from the
            # campaign. Keep only files containing THIS JobID.
            # --------------------------------------------------------

            upstream_candidates = []

            upstream_candidates.extend(
                campaign_sources
            )

            upstream_candidates.extend(
                _source_files_from_manifest(local)
            )

            if ids:

                id_tokens = {
                    str(int(job_id))
                    for job_id in ids
                }

                upstream_sources = [
                    str(path)
                    for path in upstream_candidates
                    if any(
                        token in str(path)
                        for token in id_tokens
                    )
                ]

            upstream_sources = list(
                dict.fromkeys(upstream_sources)
            )

            # --------------------------------------------------------
            # Provenance status
            # --------------------------------------------------------

            if (
                sources
                and upstream_sources
                and not selected.empty
            ):
                provenance_status = "COMPLETE"

            elif (
                sources
                and not selected.empty
            ):
                provenance_status = (
                    "DIRECT_COMPLETE_UPSTREAM_PARTIAL"
                )

            else:
                provenance_status = "PARTIAL"

        # ============================================================
        # PERFORMANCE
        # ============================================================

        elif family == "performance":

            product = "Consolidated"

            gc = _find_grouped_csv_for_performance_figure(
                fig,
                root
            )

            if gc is not None:
                sources.append(str(gc))

            selected = _select_performance_jobs(
                jobs,
                mode,
                _configs_from_grouped_csv(gc)
            )

            sources = list(dict.fromkeys(sources))

            provenance_status = (
                "COMPLETE"
                if sources and not selected.empty
                else "PARTIAL"
            )

        # ============================================================
        # OTHER VISUALIZATION
        # ============================================================

        else:

            sources = list(
                dict.fromkeys(campaign_sources)
            )

            provenance_status = (
                "COMPLETE"
                if sources
                else "PARTIAL"
            )

        # ------------------------------------------------------------
        # Figure metrics
        # ------------------------------------------------------------

        mx, my, mc = _metrics_for_figure(fig)

        # ------------------------------------------------------------
        # Registry row
        # ------------------------------------------------------------

        rows.append({
            "figure_id": f"FIGREG_{i:04d}",

            "article_figure": "",

            "application": application,
            "dataset_group": dataset_group,
            "scenario": scenario,

            "visualization_family": family,
            "logical_figure": fig.stem,

            "figure_pdf": (
                str(item["pdf"])
                if item["pdf"]
                else ""
            ),

            "figure_png": (
                str(item["png"])
                if item["png"]
                else ""
            ),

            "figure_svg": (
                str(item["svg"])
                if item["svg"]
                else ""
            ),

            "figure_formats": item["formats"],

            # --------------------------------------------------------
            # Provenance
            # --------------------------------------------------------

            "source_product": product,

            "source_files": ";".join(
                sources
            ),

            "upstream_source_files": ";".join(
                upstream_sources
            ),

            "campaign_source_files": ";".join(
                campaign_sources
            ),

            # --------------------------------------------------------
            # Experiment metadata
            # --------------------------------------------------------

            "job_ids": (
                _join_values(
                    selected.get("job_id"),
                    True
                )
                if not selected.empty
                else ""
            ),

            "nodes": (
                _join_values(
                    selected.get("nodes"),
                    True
                )
                if not selected.empty
                else ""
            ),

            "processes": (
                _join_values(
                    selected.get("processes"),
                    True
                )
                if not selected.empty
                else ""
            ),

            "data_loading_mode": (
                _join_values(
                    selected.get(
                        "data_loading_mode"
                    )
                )
                if not selected.empty
                else mode
            ),

            "filesystem": (
                _join_values(
                    selected.get("filesystem")
                )
                if not selected.empty
                else ""
            ),

            "stripe_count": (
                _join_values(
                    selected.get(
                        "stripe_count"
                    ),
                    True
                )
                if not selected.empty
                else ""
            ),

            "file_format": (
                _join_values(
                    selected.get(
                        "file_format"
                    )
                )
                if not selected.empty
                else ""
            ),

            "configuration_ids": (
                _join_values(
                    selected.get(
                        "configuration_id"
                    )
                )
                if not selected.empty
                else ""
            ),

            # --------------------------------------------------------
            # Visualization semantics
            # --------------------------------------------------------

            "metric_x": mx,
            "metric_y": my,
            "metric_color": mc,

            # --------------------------------------------------------
            # Validation
            # --------------------------------------------------------

            "provenance_status": provenance_status,
            "validation_status": "PENDING",
            "validation_notes": "",
        })

    return apply_article_mapping(
        pd.DataFrame(rows)
    )
    
def save_registry(df,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True);csv=out/'figure_registry.csv';js=out/'figure_registry.json';pa=out/'figure_provenance_audit.csv';ma=out/'article_mapping_audit.csv';df.to_csv(csv,index=False);js.write_text(df.to_json(orient='records',indent=2,force_ascii=False),encoding='utf-8');cols=['figure_id','logical_figure','visualization_family','provenance_status','job_ids','source_files','validation_status'];df[[c for c in cols if c in df.columns]].to_csv(pa,index=False);build_article_mapping_audit(df).to_csv(ma,index=False);return csv,js,pa,ma
