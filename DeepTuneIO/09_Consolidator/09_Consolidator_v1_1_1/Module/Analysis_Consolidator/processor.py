"""
DeepTuneIO — Module 09: Consolidator v1.1.1
============================================

Build a canonical execution-level dataset with one row per JobID.

v1.1.1 semantics
----------------
- Indexer remains the execution-universe anchor.
- Parser, DXT and PERF remain scientific evidence sources for Article 01.
- SEFF is optional environment/resource metadata (SLURM-specific producer).
- Training is optional application/training metadata and future validation evidence.
- `consolidation_status` describes CORE I/O/performance consolidation, not global
  presence of every optional metadata source.
- Source availability is preserved independently.
- `performance_analysis_ready` expresses row-level readiness for the current
  BW/Tio/IOPS performance view.
- Numeric configuration conflicts are compared numerically, avoiding false
  conflicts such as 2 vs 2.0 or 1048576 vs 1048576.0.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Any
import json, math
import pandas as pd

SCHEMA_VERSION="deeptuneio.consolidated_execution.v1.1"
MODULE_VERSION="1.1.1"

@dataclass
class SourceSpec:
    name:str; path:Path; job_column:str; prefix:str

def _normalize_jobid(series): return pd.to_numeric(series,errors="coerce").astype("Int64")
def _normalize_format(value):
    if value is None or pd.isna(value): return None
    x=str(value).strip().lower().lstrip('.')
    return {"h5":"hdf5","hdf":"hdf5","hdf5":"hdf5","tfrecord":"tfrecord","tfrecords":"tfrecord","npz":"npz","jpeg":"jpeg","jpg":"jpeg"}.get(x,x)
def _normalize_fs(value):
    if value is None or pd.isna(value): return None
    x=str(value).strip().lower()
    if "lustre" in x:return "lustre"
    if "nfs" in x:return "nfs"
    return x

def _load_source(spec):
    if not spec.path.exists(): raise FileNotFoundError(f"{spec.name}: source not found: {spec.path}")
    df=pd.read_csv(spec.path)
    if spec.job_column not in df.columns: raise KeyError(f"{spec.name}: missing JobID column '{spec.job_column}'")
    df=df.copy(); df["_job_id"]=_normalize_jobid(df[spec.job_column])
    if df["_job_id"].isna().any(): raise ValueError(f"{spec.name}: invalid JobID values")
    dup=df["_job_id"].duplicated(keep=False)
    if dup.any():
        ids=sorted(df.loc[dup,"_job_id"].astype(int).unique().tolist())
        raise ValueError(f"{spec.name}: expected one row per JobID, duplicates: {ids[:20]}")
    rename={c:f"{spec.prefix}{c}" for c in df.columns if c!="_job_id"}
    return df.rename(columns=rename)

def _same_numeric(a,b,rtol=1e-8,atol=1e-8):
    if pd.isna(a) or pd.isna(b): return None
    try:return math.isclose(float(a),float(b),rel_tol=rtol,abs_tol=atol)
    except (TypeError,ValueError):return str(a).strip()==str(b).strip()
def _same_text(a,b,normalizer=None):
    if pd.isna(a) or pd.isna(b): return None
    return normalizer(a)==normalizer(b) if normalizer else str(a).strip().lower()==str(b).strip().lower()
def _status(values):
    obs=[x for x in values if x is not None]
    return "NOT_CHECKED" if not obs else ("PASS" if all(obs) else "FAIL")

def _conflict(label,pairs):
    obs=[(src,val) for src,val in pairs if not pd.isna(val)]
    if len(obs)<2:return None
    numeric={"nodes","processes","stripe_size_bytes","stripe_count"}
    if label in numeric:
        vals=[]
        for src,val in obs:
            try: vals.append((src,float(val)))
            except (TypeError,ValueError): vals.append((src,str(val).strip()))
        first=vals[0][1]
        equal=True
        for _,v in vals[1:]:
            if isinstance(first,float) and isinstance(v,float): equal &= math.isclose(first,v,rel_tol=1e-8,abs_tol=1e-8)
            else: equal &= first==v
        if equal:return None
    elif label=="file_format":
        if len({_normalize_format(v) for _,v in obs})<=1:return None
    elif label=="filesystem":
        if len({_normalize_fs(v) for _,v in obs})<=1:return None
    else:
        if len({str(v).strip() for _,v in obs})<=1:return None
    return f"{label}: "+", ".join(f"{src}={val}" for src,val in obs)

def _availability_status(configured,available):
    if not configured:return "NOT_CONFIGURED"
    return "AVAILABLE" if available else "NOT_AVAILABLE"

def _present_number(v,positive=False):
    try:
        x=float(v)
        return math.isfinite(x) and (x>0 if positive else True)
    except (TypeError,ValueError):return False

def build_consolidated_execution(indexer_csv,parser_csv,dxt_csv,perf_csv,seff_csv=None,training_csv=None):
    specs=[
        SourceSpec("indexer",Path(indexer_csv),"job_id","indexer__"),
        SourceSpec("parser",Path(parser_csv),"Jobid","parser__"),
        SourceSpec("dxt",Path(dxt_csv),"Jobid","dxt__"),
        SourceSpec("perf",Path(perf_csv),"Jobid","perf__"),
    ]
    if seff_csv is not None: specs.append(SourceSpec("seff",Path(seff_csv),"jobid","seff__"))
    if training_csv is not None: specs.append(SourceSpec("training",Path(training_csv),"job_id","training__"))
    configured={s.name for s in specs}
    loaded={s.name:_load_source(s) for s in specs}
    base=loaded["indexer"].copy(); indexer_jobs=set(base["_job_id"].astype(int)); source_coverage={}
    for spec in specs:
        if spec.name=="indexer":continue
        df=loaded[spec.name]; jobs=set(df["_job_id"].astype(int))
        source_coverage[spec.name]={"rows":len(df),"matched_indexer_jobs":len(indexer_jobs&jobs),"missing_from_source":len(indexer_jobs-jobs),"extra_not_in_indexer":len(jobs-indexer_jobs)}
        base=base.merge(df,on="_job_id",how="left",validate="one_to_one")

    cmap={"experiment_id":"indexer__experiment_id","job_id":"_job_id","sequence_id":"indexer__sequence_id","application":"indexer__application","application_version":"indexer__application_version","platform":"indexer__platform","resource_project":"indexer__resource_project","job_state":"indexer__job_state","exit_code":"indexer__exit_code","start_time":"indexer__start_time","end_time":"indexer__end_time","runtime_s":"indexer__runtime_s","nodes":"indexer__nodes","processes":"indexer__processes","ppn":"indexer__ppn","cores_per_node":"indexer__cores_per_node","filesystem":"indexer__filesystem","mount_point":"indexer__mount_point","stripe_size_bytes":"indexer__stripe_size_bytes","stripe_count":"indexer__stripe_count","file_format":"indexer__file_format","batch_size":"indexer__batch_size","epochs":"indexer__epochs","operation_mode":"indexer__operation_mode","configuration_signature":"indexer__configuration_signature","application_configuration_signature":"indexer__application_configuration_signature","dataset_configuration_signature":"indexer__dataset_configuration_signature","experiment_configuration_signature":"indexer__experiment_configuration_signature","execution_status":"indexer__execution_status","instrumentation_status":"indexer__instrumentation_status","metadata_status":"indexer__metadata_status"}
    canonical=pd.DataFrame(index=base.index)
    for t,s in cmap.items(): canonical[t]=base[s] if s in base.columns else pd.NA
    pmap={"io_total_bytes":"perf__IO_Total_Bytes","io_total_mib":"perf__IO_Total_MiB","io_time_s":"perf__IO_Time_s","unique_io_time_s":"perf__Unique_IO_Time_s","shared_io_time_s":"perf__Shared_IO_Time_s","bandwidth_mib_s":"perf__Bandwidth_Darshan_MiB_s","io_time_ratio":"perf__IO_Time_Ratio","bytes_per_process":"perf__Bytes_per_Proc"}
    for t,s in pmap.items(): canonical[t]=base[s] if s in base.columns else pd.NA
    parser_map={"posix_bytes_read":"parser__POSIX_BYTES_READ","posix_bytes_written":"parser__POSIX_BYTES_WRITTEN","posix_reads":"parser__POSIX_READS","posix_writes":"parser__POSIX_WRITES","posix_opens":"parser__POSIX_OPENS","posix_seq_reads":"parser__POSIX_SEQ_READS","posix_consecutive_reads":"parser__POSIX_CONSEC_READS","access_pattern_detected":"parser__Access_Pattern_Detected","parser_files_coverage":"parser__Files_Coverage"}
    for t,s in parser_map.items(): canonical[t]=base[s] if s in base.columns else pd.NA
    reads=pd.to_numeric(canonical["posix_reads"],errors="coerce"); iot=pd.to_numeric(canonical["io_time_s"],errors="coerce")
    canonical["parser_posix_reads_per_perf_io_s"]=reads.where(iot>0)/iot.where(iot>0)
    dmap={"dxt_request_size_mean_bytes":"dxt__Request Size Means(bytes)","dxt_request_size_std_bytes":"dxt__Request Size STD(bytes)","dxt_request_size_min_bytes":"dxt__Min Request Size (bytes)","dxt_request_size_max_bytes":"dxt__Max Request Size (bytes)","dxt_latency_operation_mean_s":"dxt__Latency x Operation Means(s)","dxt_throughput_mean_bytes_s":"dxt__Throughput Means(bytes/s)","dxt_iops":"dxt__IOPS","dxt_ost_mapping_coverage":"dxt__OST_Mapping_Coverage","dxt_ost_byte_conservation_rate":"dxt__OST_Byte_Conservation_Rate","dxt_layout_match_rate":"dxt__OST_Layout_Match_Rate"}
    for t,s in dmap.items(): canonical[t]=base[s] if s in base.columns else pd.NA
    canonical["indexer_iops"]=base["indexer__iops"] if "indexer__iops" in base.columns else pd.NA
    reads_posix=pd.to_numeric(canonical["posix_reads"],errors="coerce").fillna(0)
    writes_posix=pd.to_numeric(canonical["posix_writes"],errors="coerce").fillna(0)
    io_time_perf=pd.to_numeric(canonical["io_time_s"],errors="coerce")
    proc_count=pd.to_numeric(canonical["processes"],errors="coerce")
    fmt_norm=canonical["file_format"].map(_normalize_format)
    canonical["posix_data_operations"]=reads_posix+writes_posix
    canonical["iops_posix"]=canonical["posix_data_operations"].where(io_time_perf>0)/io_time_perf.where(io_time_perf>0)
    meta=fmt_norm.map({"hdf5":16.0,"npz":5.0,"tfrecord":0.0})
    canonical["legacy_ds_meta_operations_per_process"]=meta
    canonical["legacy_ds_meta_operations_total"]=meta*proc_count
    legacy_data=canonical["posix_data_operations"].copy(); scale=fmt_norm.isin(["npz","tfrecord"])
    legacy_data.loc[scale]=legacy_data.loc[scale]*proc_count.loc[scale]
    canonical["legacy_ds_data_operations"]=legacy_data
    canonical["legacy_total_operations_ds"]=legacy_data+canonical["legacy_ds_meta_operations_total"]
    canonical["iops_ds_legacy"]=canonical["legacy_total_operations_ds"].where(io_time_perf>0)/io_time_perf.where(io_time_perf>0)
    canonical["iops_ds_legacy_validation_status"]=fmt_norm.map({"hdf5":"VALIDATED_AGAINST_ARTICLE01_ORIGINAL","npz":"UNVALIDATED_LEGACY_RECONSTRUCTION","tfrecord":"UNVALIDATED_LEGACY_RECONSTRUCTION"}).fillna("NOT_APPLICABLE")

    seff_map={"cpu_utilized_seconds":"seff__cpu_utilized_seconds","cpu_efficiency_pct":"seff__cpu_efficiency_pct","core_walltime_seconds":"seff__core_walltime_seconds","job_wallclock_seconds":"seff__job_wallclock_seconds","memory_utilized_bytes":"seff__memory_utilized_bytes","memory_efficiency_pct":"seff__memory_efficiency_pct","total_memory_requested_bytes":"seff__total_memory_requested_bytes","seff_status":"seff__seff_status"}
    for t,s in seff_map.items(): canonical[t]=base[s] if s in base.columns else pd.NA
    training_fields=["training_status","epochs_expected","epochs_completed","final_epoch","final_loss","final_accuracy","final_validation_loss","final_validation_accuracy","min_loss","min_loss_epoch","min_validation_loss","min_validation_loss_epoch","max_accuracy","max_accuracy_epoch","max_validation_accuracy","max_validation_accuracy_epoch","training_time_total_s","metric_records","metrics_status","missing_metrics"]
    for field in training_fields:
        s=f"training__{field}"; canonical[field]=base[s] if s in base.columns else pd.NA

    availability=pd.DataFrame(index=base.index); availability["indexer_available"]=True
    presence={"parser":"parser__Jobid","dxt":"dxt__Jobid","perf":"perf__Jobid","seff":"seff__jobid","training":"training__job_id"}
    for src,col in presence.items(): availability[f"{src}_available"]=base[col].notna() if col in base.columns else False

    validation_rows=[]
    for i,row in base.iterrows():
        node_checks=[_same_numeric(row.get("indexer__nodes"),row.get("dxt__Nodes")),_same_numeric(row.get("indexer__nodes"),row.get("seff__nodes"))]
        proc_checks=[_same_numeric(row.get("indexer__processes"),row.get("parser__Nprocs")),_same_numeric(row.get("indexer__processes"),row.get("dxt__Process_IO")),_same_numeric(row.get("indexer__processes"),row.get("perf__Processes_IO"))]
        stripe_size_checks=[_same_numeric(row.get("indexer__stripe_size_bytes"),row.get("parser__LUSTRE_STRIPE_SIZE")),_same_numeric(row.get("indexer__stripe_size_bytes"),row.get("dxt__Stripe_size"))]
        stripe_count_checks=[_same_numeric(row.get("indexer__stripe_count"),row.get("parser__LUSTRE_STRIPE_WIDTH")),_same_numeric(row.get("indexer__stripe_count"),row.get("dxt__Stripe_count"))]
        format_checks=[_same_text(row.get("indexer__file_format"),row.get("parser__File_Format"),_normalize_format),_same_text(row.get("indexer__file_format"),row.get("dxt__File Format"),_normalize_format),_same_text(row.get("indexer__file_format"),row.get("perf__File_Format"),_normalize_format),_same_text(row.get("indexer__file_format"),row.get("seff__file_format"),_normalize_format)]
        fs_checks=[_same_text(row.get("indexer__filesystem"),row.get("parser__FS Type"),_normalize_fs),_same_text(row.get("indexer__filesystem"),row.get("dxt__File System Type"),_normalize_fs)]
        pairs={
            "nodes":[("indexer",row.get("indexer__nodes")),("dxt",row.get("dxt__Nodes")),("seff",row.get("seff__nodes"))],
            "processes":[("indexer",row.get("indexer__processes")),("parser",row.get("parser__Nprocs")),("dxt",row.get("dxt__Process_IO")),("perf",row.get("perf__Processes_IO"))],
            "stripe_size_bytes":[("indexer",row.get("indexer__stripe_size_bytes")),("parser",row.get("parser__LUSTRE_STRIPE_SIZE")),("dxt",row.get("dxt__Stripe_size"))],
            "stripe_count":[("indexer",row.get("indexer__stripe_count")),("parser",row.get("parser__LUSTRE_STRIPE_WIDTH")),("dxt",row.get("dxt__Stripe_count"))],
            "file_format":[("indexer",row.get("indexer__file_format")),("parser",row.get("parser__File_Format")),("dxt",row.get("dxt__File Format")),("perf",row.get("perf__File_Format")),("seff",row.get("seff__file_format"))],
            "filesystem":[("indexer",row.get("indexer__filesystem")),("parser",row.get("parser__FS Type")),("dxt",row.get("dxt__File System Type"))],
        }
        conflicts=[c for label,p in pairs.items() if (c:=_conflict(label,p))]
        statuses={"nodes_consistency":_status(node_checks),"processes_consistency":_status(proc_checks),"stripe_size_consistency":_status(stripe_size_checks),"stripe_count_consistency":_status(stripe_count_checks),"file_format_consistency":_status(format_checks),"filesystem_consistency":_status(fs_checks)}
        config="FAIL" if any(v=="FAIL" for v in statuses.values()) else ("PASS" if any(v=="PASS" for v in statuses.values()) else "NOT_CHECKED")

        parser_av=bool(availability.loc[i,"parser_available"]); dxt_av=bool(availability.loc[i,"dxt_available"]); perf_av=bool(availability.loc[i,"perf_available"]); seff_av=bool(availability.loc[i,"seff_available"]); train_av=bool(availability.loc[i,"training_available"])
        core_complete=parser_av and perf_av and config!="FAIL"
        consolidation_status="COMPLETE" if core_complete else "PARTIAL"
        row_canon=canonical.loc[i]
        performance_ready=(core_complete and _present_number(row_canon.get("nodes"),True) and _present_number(row_canon.get("processes"),True) and pd.notna(row_canon.get("access_pattern_detected")) and _present_number(row_canon.get("io_time_s"),True) and _present_number(row_canon.get("bandwidth_mib_s")) and _present_number(row_canon.get("iops_posix")))
        io_ready=parser_av and config!="FAIL"
        detailed_ready=io_ready and dxt_av
        validation_rows.append({
            "job_id":int(row["_job_id"]), **{k:bool(availability.loc[i,k]) for k in availability.columns}, **statuses,
            "configuration_consistency":config,"configuration_conflicts":" | ".join(conflicts),
            "source_completeness_status":"COMPLETE" if all(bool(availability.loc[i,f"{s}_available"]) for s in ["parser","dxt","perf"] + (["seff"] if "seff" in configured else []) + (["training"] if "training" in configured else [])) else "PARTIAL",
            "consolidation_status":consolidation_status,
            "io_analysis_ready":bool(io_ready),"detailed_io_analysis_ready":bool(detailed_ready),"performance_analysis_ready":bool(performance_ready),
            "resource_metadata_status":_availability_status("seff" in configured,seff_av),
            "training_metadata_status":_availability_status("training" in configured,train_av),
        })

    validation=pd.DataFrame(validation_rows)
    canonical=pd.concat([canonical,availability],axis=1)
    for c in ["configuration_consistency","configuration_conflicts","source_completeness_status","consolidation_status","io_analysis_ready","detailed_io_analysis_ready","performance_analysis_ready","resource_metadata_status","training_metadata_status"]:
        canonical[c]=validation[c].values
    source_cols=[c for c in base.columns if c!="_job_id"]
    consolidated=pd.concat([canonical.reset_index(drop=True),base[source_cols].reset_index(drop=True)],axis=1)
    manifest={
        "module":"DeepTuneIO Module 09 Consolidator","module_version":MODULE_VERSION,"schema_version":SCHEMA_VERSION,
        "join_policy":"Indexer anchor + LEFT JOIN + one_to_one validation","execution_granularity":"one row per JobID",
        "consolidation_semantics":"COMPLETE means core aggregate I/O/performance evidence is analytically usable; optional metadata does not downgrade this status.",
        "indexer_jobs":len(indexer_jobs),"consolidated_rows":len(consolidated),
        "complete_rows":int((validation.consolidation_status=="COMPLETE").sum()),"partial_rows":int((validation.consolidation_status=="PARTIAL").sum()),
        "source_complete_rows":int((validation.source_completeness_status=="COMPLETE").sum()),"source_partial_rows":int((validation.source_completeness_status=="PARTIAL").sum()),
        "io_analysis_ready_rows":int(validation.io_analysis_ready.sum()),"detailed_io_analysis_ready_rows":int(validation.detailed_io_analysis_ready.sum()),"performance_analysis_ready_rows":int(validation.performance_analysis_ready.sum()),
        "resource_metadata_available_rows":int((validation.resource_metadata_status=="AVAILABLE").sum()),"training_metadata_available_rows":int((validation.training_metadata_status=="AVAILABLE").sum()),
        "configuration_consistency_pass":int((validation.configuration_consistency=="PASS").sum()),"configuration_consistency_fail":int((validation.configuration_consistency=="FAIL").sum()),
        "source_coverage":source_coverage,"sources":{s.name:str(s.path) for s in specs},
        "optional_sources":{"seff":"configured" if "seff" in configured else "not_configured","training":"configured" if "training" in configured else "not_configured"},
        "ownership":{"identity_configuration":"Indexer","aggregate_io":"Parser","access_pattern_summary":"DXT","performance":"PERF","resource_usage":"environment-specific metadata adapter (SEFF when SLURM)","training_results":"Training summary / application adapter"},
        "readiness_policy":{"io_analysis_ready":"Parser available + configuration not conflicting","detailed_io_analysis_ready":"io_analysis_ready + DXT available","performance_analysis_ready":"core consolidation complete + nodes/processes/access mode + I/O time + bandwidth + iops_posix available"},
    }
    return consolidated,validation,manifest

def write_outputs(consolidated,validation,manifest,output_dir,suffix):
    output_dir=Path(output_dir); execution_dir=output_dir/"Execution"; validation_dir=output_dir/"Validation"; metadata_dir=output_dir/"Metadata"
    for d in [execution_dir,validation_dir,metadata_dir]: d.mkdir(parents=True,exist_ok=True)
    ep=execution_dir/f"consolidated_execution_{suffix}.csv"; vp=validation_dir/f"consolidation_validation_{suffix}.csv"; mp=metadata_dir/f"consolidation_manifest_{suffix}.json"
    consolidated.to_csv(ep,index=False); validation.to_csv(vp,index=False); mp.write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
    return {"execution":ep,"validation":vp,"manifest":mp}
